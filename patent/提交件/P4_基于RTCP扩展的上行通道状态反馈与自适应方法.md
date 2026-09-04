# 专利交底书 P4

---

## 一、发明名称

一种基于RTCP扩展的上行通道状态反馈与终端自适应方法及系统

## 二、技术领域

本发明涉及实时音视频传输技术领域，具体涉及一种在交互式远程渲染流媒体系统中，服务端通过RTCP应用定义报文向终端反馈上行控制链路状态，终端据此调整播放策略的方法。

## 三、背景技术

### 3.1 非对称双链路架构的问题

云手机系统采用非对称双链路架构：上行控制链路基于TCP Socket传输交互指令，下行媒体链路基于WebRTC RTP/RTCP传输音视频流。两条链路物理独立、协议不同、方向相反。

这种架构导致一个关键问题：**上行通道状态对下行不可见。**

### 3.2 上行拥堵的体验割裂

当上行TCP Socket发生拥堵时（如用户从Wi-Fi切换到弱信号4G），用户的操作指令积压在终端的TCP发送队列中，无法及时到达云端。此时：

- 云端收不到新指令，但仍按旧状态继续编码推送画面
- 终端不知道上行已堵，看到的画面在响应"过时的操作"
- 用户感觉"控制不了手机"，操作和画面严重不同步

### 3.3 现有技术的不足

现有WebRTC/RTCP协议提供了多种反馈机制：
- RTCP Receiver Report：反馈下行RTP流的接收质量（丢包、抖动）
- RTCP REMB/TCC：反馈下行带宽估计
- RTCP NACK/PLI：请求重传或关键帧

**但所有这些反馈都是面向"下行媒体链路"的，没有任何机制让服务端向终端反馈"上行控制链路"的健康状态。**

### 3.4 为什么不用RTP扩展

一种直觉方案是将上行状态信息放在RTP头部扩展中逐帧携带。但这存在语义错配：
- RTP头部扩展应携带与当前帧相关的**媒体元数据**
- 上行通道状态是**控制面信息**，与具体帧无关
- 逐帧携带控制面信息浪费带宽（每包增加1字节）
- RTCP天然就是传输控制反馈的通道，发送频率（2-4次/秒）足够满足上行状态感知需求

## 四、发明内容

### 4.1 总体思路

本发明的核心思路是：**在服务端监控上行TCP指令的接收状态，基于"活跃检测+接收间隔超时"的双重判断逻辑计算上行状态等级，通过RTCP应用定义报文（APP Packet）定期发送给终端，终端据此调整播放策略。**

```
上行TCP指令流 → 服务端监控模块
                      ↓
              活跃状态检测（最近5秒有指令=活跃）
                      ↓
              接收间隔计算（当前时间 - 最后收到时间）
                      ↓
              双重判断 → USF状态等级
                      ↓
              打包RTCP APP报文(name=CPUS)
                      ↓
              定期/事件触发发送到终端
                      ↓
终端: 解析RTCP APP → USF状态 → 调整Jitter Buffer + 提示用户
```

### 4.2 RTCP APP报文定义

#### 4.2.1 报文格式

采用RTCP APP报文类型（PT=204，RFC 3550第6.7节），自定义名称为"CPUS"（Cloud Phone Uplink Status）：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|V=2|P| subtype |   PT=204      |           length              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         SSRC/CSRC                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          name (ASCII)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   USF Field   |  USF Detail   |         Reserved              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

各字段定义：
- subtype：应用自定义子类型，设为0x01
- PT=204：RTCP APP报文类型
- name：4字节ASCII，固定为"CPUS"
- USF Field：上行状态反馈主字段（8 bit）
- USF Detail：辅助信息（8 bit），编码最近一次指令接收间隔（单位10ms）
- Reserved：保留，置0

#### 4.2.2 USF主字段编码

| 值 | 状态 | 语义 |
|----|------|------|
| 0x00 | NORMAL | 上行通道正常 |
| 0x01-0x0F | MILD_LAG | 轻度滞后 |
| 0x10-0x3F | MODERATE_LAG | 中度滞后 |
| 0x40-0xFE | SEVERE_LAG | 严重滞后 |
| 0xFF | OUTAGE | 疑似中断 |

#### 4.2.3 USF Detail字段

编码服务端最近一次收到上行指令距今的时间间隔，单位10ms，范围0-2550ms。为终端提供定量化的上行延迟参考。

### 4.3 上行状态监控与判定

#### 4.3.1 双重判断逻辑

核心设计：**只有"用户明显在操作但指令突然不来了"才判定为拥堵。** 用户不操作时不会误报。

```python
class UplinkStatusMonitor:
    ACTIVITY_WINDOW = 5000     # 活跃判断窗口(ms)
    MILD_THRESH = 500          # 轻度滞后阈值(ms)
    SEVERE_THRESH = 2000       # 严重滞后阈值(ms)
    OUTAGE_THRESH = 5000       # 中断阈值(ms)
    
    def __init__(self):
        self.last_recv_time = 0
        self.is_active = False
    
    def on_command(self):
        """每收到一条上行指令"""
        self.last_recv_time = now_ms()
        self.is_active = True
    
    def compute_usf(self):
        """计算当前USF状态"""
        elapsed = now_ms() - self.last_recv_time
        
        # 双重判断：活跃 + 超时
        if self.is_active and elapsed > self.MILD_THRESH:
            if elapsed < self.SEVERE_THRESH:
                return 0x10, elapsed // 10   # MODERATE_LAG
            elif elapsed < self.OUTAGE_THRESH:
                return 0x40, elapsed // 10   # SEVERE_LAG
            else:
                return 0xFF, 255              # OUTAGE
        else:
            return 0x00, elapsed // 10        # NORMAL
    
    def periodic_check(self):
        """每秒调用，更新活跃状态"""
        if now_ms() - self.last_recv_time > self.ACTIVITY_WINDOW:
            self.is_active = False  # 5秒无指令，视为非活跃
```

#### 4.3.2 设计要点

**为什么需要活跃检测？**

如果不检测活跃状态，仅基于接收间隔判断：
- 用户放下手机去喝水 → 10秒无指令 → 误判为OUTAGE → 终端误报警
- 正确行为：用户不操作时，上行"没有指令"是正常的，不应报拥堵

**活跃检测逻辑：**
- 最近5秒内有指令到达 → 标记为活跃
- 超过5秒无指令 → 标记为非活跃
- 非活跃状态下，无论接收间隔多长，USF均为NORMAL

### 4.4 RTCP APP发送策略

#### 4.4.1 发送规则

```python
class USFSender:
    DEFAULT_INTERVAL = 500     # 默认发送间隔(ms)
    MAX_INTERVAL = 2000        # 最大发送间隔(ms)
    STABLE_COUNT_THRESHOLD = 3 # 连续未变化次数阈值
    
    def __init__(self):
        self.last_usf = 0x00
        self.stable_count = 0
        self.current_interval = self.DEFAULT_INTERVAL
        self.last_send_time = 0
    
    def should_send(self, current_usf):
        now = now_ms()
        
        # 规则1：状态变化时立即发送
        if current_usf != self.last_usf:
            self.last_usf = current_usf
            self.stable_count = 0
            self.current_interval = self.DEFAULT_INTERVAL
            return True
        
        # 规则2：状态稳定时降低发送频率
        self.stable_count += 1
        if self.stable_count >= self.STABLE_COUNT_THRESHOLD:
            self.current_interval = self.MAX_INTERVAL
        
        # 规则3：到达发送间隔
        if now - self.last_send_time >= self.current_interval:
            return True
        
        return False
```

#### 4.4.2 发送时机总结

| 条件 | 行为 |
|------|------|
| 会话建立 | 立即发送NORMAL |
| USF值变化 | 立即发送（不等周期） |
| USF值稳定 | 每500ms发送一次 |
| USF连续3次未变 | 降至每2秒发送一次 |
| SDP协商关闭 | 停止发送 |

### 4.5 终端自适应策略

#### 4.5.1 策略映射

```python
class UplinkAdaptiveController:
    def on_rtcp_app_cpus(self, usf, detail):
        if usf >= 0x40:
            # 严重滞后/中断
            self.jitter_buffer.set_depth(MIN_DEPTH)
            self.send_rtcp_feedback("LOW_FPS_REQUEST")
            self.ui.show_hint("网络不稳定，操作可能延迟")
            
        elif usf >= 0x10:
            # 中度滞后
            self.jitter_buffer.set_depth(LOW_DEPTH)
            
        elif usf >= 0x01:
            # 轻度滞后
            self.logger.info("Uplink mild lag detected")
            
        else:
            # 正常
            self.ui.hide_hint()
```

#### 4.5.2 策略意图

| USF状态 | 终端行为 | 原因 |
|---------|---------|------|
| NORMAL | 正常播放 | 上行通畅 |
| MILD_LAG | 记录日志 | 可能有轻微波动，暂不干预 |
| MODERATE_LAG | 降低Jitter Buffer | 上行变慢，减少缓冲避免"画面超前于操作" |
| SEVERE_LAG | 最小缓冲+请求降帧率+提示用户 | 上行严重拥堵，画面可能在响应旧操作 |
| OUTAGE | 最小缓冲+网络警告 | 上行疑似断开 |

#### 4.5.3 "降低Jitter Buffer"的逻辑

为什么上行拥堵时要降低下行Jitter Buffer？

- 上行拥堵 → 操作指令延迟到达云端 → 云端推送的画面在响应"旧操作"
- 如果终端Jitter Buffer很深（如缓冲10帧），看到的画面是"更旧的操作响应"
- 降低缓冲 → 尽快呈现最新帧 → 虽然可能不连续，但至少画面更接近"当前状态"

### 4.6 SDP协商

```
启用USF:  a=irrm-usf-rtcp: enabled
设置间隔:  a=irrm-usf-interval: 500
关闭USF:  a=irrm-usf-rtcp: disabled    （弱网可关闭以减少RTCP开销）
```

## 五、技术方案效果

| 效果 | 说明 |
|------|------|
| 上行状态可见 | 终端首次能感知上行控制通道的健康度 |
| 避免体验割裂 | 上行拥堵时终端主动调整播放策略，避免"操作-画面不同步" |
| 无误报 | 活跃检测机制确保用户不操作时不会误判为拥堵 |
| 语义正确 | 控制面信息走RTCP，不污染RTP数据通道 |
| 开销最小 | RTCP发送频率低（2次/秒），弱网可关闭 |
| 事件驱动 | 状态变化时立即发送，不等周期，保证时效性 |

## 六、权利要求要点

1. **一种基于RTCP扩展的上行通道状态反馈方法**，应用于交互式远程渲染流媒体系统，其特征在于，包括：
   - 服务端监控上行控制链路的指令接收状态，维护终端活跃状态标记；
   - 当检测到终端处于活跃交互状态且指令接收间隔超过预设阈值时，服务端生成上行状态反馈信息；
   - 服务端将所述上行状态反馈信息编码为RTCP应用定义报文，发送至终端；
   - 终端解析所述RTCP应用定义报文，根据上行状态等级采取相应的播放策略自适应措施。

2. 根据权利要求1所述的方法，其特征在于，所述活跃状态标记的判定逻辑为：当服务端在最近5秒内收到过上行指令时标记为活跃，超过5秒未收到指令时标记为非活跃；非活跃状态下不触发上行状态反馈。

3. 根据权利要求1所述的方法，其特征在于，所述RTCP应用定义报文的名称字段固定为"CPUS"，包含上行状态主字段和接收间隔辅助字段。

4. 根据权利要求1所述的方法，其特征在于，所述RTCP应用定义报文的发送策略为：状态变化时立即发送，状态稳定时按固定间隔发送，连续多次未变化时降低发送频率。

5. 根据权利要求1所述的方法，其特征在于，终端收到严重滞后或中断状态时，采取的措施包括：降低抖动缓冲区深度、通过RTCP反馈请求服务端降低帧率、向用户显示网络异常提示。

6. 根据权利要求1所述的方法，其特征在于，还包括：通过SDP信令协商RTCP应用定义报文的启用状态和发送间隔，在弱网条件下可关闭该报文以减少控制通道开销。

7. **一种基于RTCP扩展的上行通道状态反馈系统**，包括：
   - 上行监控模块，部署于服务端，监控指令接收状态并计算上行状态等级；
   - RTCP报文发送模块，部署于服务端，将上行状态编码为RTCP应用定义报文并发送；
   - 自适应控制模块，部署于终端，解析RTCP报文并调整播放策略。
