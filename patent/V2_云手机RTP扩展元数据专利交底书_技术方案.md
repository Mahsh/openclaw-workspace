# 专利交底书 V2：面向云手机交互式流媒体的RTP扩展元数据传输方法及系统

> 版本：V2（基于V1修正）
> 更新日期：2026-07-02
> 主要修正：移除QueueDelay字段、完善CmdTypeID聚合机制、修正AnchorSeq帧关联逻辑、修正AnchorAck映射机制

---

## 一、发明名称

面向云手机交互式流媒体的RTP扩展元数据传输方法及系统

## 二、技术领域

本发明涉及实时音视频传输技术领域，具体涉及一种基于WebRTC的RTP协议头部扩展机制，面向云手机（Cloud Phone / Cloud Gaming）业务场景，通过在非对称双链路架构（TCP控制上行 + WebRTC媒体下行）中建立跨链路状态信息注入机制，实现传输策略的场景化自适应优化。

## 三、背景技术

### 3.1 云手机系统架构

云手机（Cloud Phone）是将移动终端的操作系统与应用程序运行于云端服务器，用户通过轻量级终端设备远程访问云端虚拟手机的计算服务形态。其典型系统架构采用非对称双链路设计：

```
┌──────────┐                              ┌──────────────┐
│          │  TCP Socket                  │              │
│  客户端   │ ──────────────────────────→ │   云端服务器   │
│ (终端)    │  (上行：触摸/按键/控制指令)     │  (云手机实例)  │
│          │                              │              │
│          │  WebSocket                   │              │
│          │ ←────────────────────→     │              │
│          │  (双向：SDP/ICE信令协商)       │              │
│          │                              │              │
│          │  WebRTC RTP/RTCP             │              │
│          │ ←────────────────────────  │              │
│          │  (下行：音视频流)              │              │
└──────────┘                              └──────────────┘
```

- **上行控制链路**：基于TCP Socket，传输用户交互指令（触摸坐标、按键事件、传感器数据等），指令以JSON格式编码，包含opttype（操作类型）、坐标数据、设备标识等字段
- **信令协商链路**：基于WebSocket，传输SDP offer/answer和ICE候选信息，用于建立WebRTC P2P连接
- **下行媒体链路**：基于WebRTC RTP/RTCP协议，传输云端编码器输出的音视频流

### 3.2 云手机上行指令格式示例

终端上行的交互指令典型格式如下：

```json
{
  "cmdType": 100020,
  "data": {
    "data": {
      "accuracy": 3,
      "x": -0.020350715,
      "y": 0.374094,
      "z": 9.841965
    },
    "deviceid": 1,
    "devicetype": 10,
    "opttype": 16
  }
}
```

其中 `opttype` 标识操作类型（如触摸按下、移动、抬起、传感器数据、按键等），`x/y/z` 为坐标或传感器数据。单条指令仅携带原始坐标信息，不包含交互场景语义。

### 3.3 现有技术的问题

在上述非对称架构下，现有技术存在以下关键问题：

**问题一：控制链路与媒体链路信息割裂**

上行TCP控制链路和下行WebRTC媒体链路是两条独立的物理通路，信息不互通：
- 终端不知道"当前接收的视频帧是对应哪条上行指令的响应"
- 终端的Jitter Buffer和传输保护策略无法感知当前帧的交互上下文
- 端到端"操作→画面反馈"延迟缺乏有效的测量手段

**问题二：终端Jitter Buffer策略缺乏场景感知**

标准WebRTC的Jitter Buffer策略只关注网络传输抖动，不区分帧的内容属性。云手机场景下：
- 游戏战斗画面需要低延迟优先（宁可画质抖动也要跟手）
- 文档阅读画面需要清晰度优先（允许适当延迟换取文字清晰）
- 视频播放画面需要流畅度优先（允许缓冲换取连续播放）

现有协议无法将"场景意图"从云端传递给终端播放模块。

**问题三：上行通道拥堵对下行无反馈**

上行TCP Socket发生拥塞时（如网络切换），用户的操作指令积压在发送队列中。终端和下行WebRTC通道均不知道上行已堵，云端继续正常推送画面，导致"操作已过时但画面还在响应旧操作"的体验割裂。

**问题四：云端编码卡顿干扰拥塞控制判断**

云手机在多用户高负载场景下，云端CPU/GPU资源紧张会导致帧在编码器前排队等待。这种"云端排队延迟"会被WebRTC的拥塞控制算法（如GCC）误判为网络拥塞，触发不必要的降码率操作，导致画质下降但实际带宽充足。

**问题五：极端弱网下元数据自身可靠性**

在极弱网环境（丢包率>10%）下，RTP扩展字段本身也会丢包。携带关键锚点信息（如延迟测量锚点）的包丢失后，后续依赖该锚点的计算将全部失效。

## 四、发明内容

### 4.1 总体思路

本发明的核心思路是：**在不改变标准RTP报文载荷结构、不增加额外信令通道的前提下，利用RTP头部扩展空间，将控制链路和云端处理链路的核心状态信息注入到媒体传输链中，实现"控制-处理-传输"三链路的信息打通和协同优化。**

本方案采用**4个RTP扩展字段 + 1个云端内部优化机制**的设计：

```
                     ┌─────────────────────────────────────┐
                     │       RTP 扩展元数据注入（4字段）      │
                     │                                     │
  上行指令聚合 ──→   │  ① CmdTypeID   交互模式分类标记       │
  渲染管线钩子 ──→   │  ② AnchorSeq   延迟测量锚点           │  ──→ 终端消费
  场景识别引擎 ──→   │  ③ FrameInt    帧意图/场景标记         │
  上行监控模块 ──→   │  ④ AnchorAck   上行状态反馈            │
                     └─────────────────────────────────────┘
                     
                     ┌─────────────────────────────────────┐
                     │       云端内部优化机制（不下传）        │
                     │                                     │
  编码器队列   ──→   │  ⑤ QueueDelay  编码排队延迟补偿        │  ──→ 云端GCC修正
                     └─────────────────────────────────────┘
```

### 4.2 RTP扩展字段定义

#### 4.2.1 扩展字段总体格式

采用RTP Header Extension通用格式（RFC 8285 One-Byte Header Extension），扩展ID通过SDP协商分配。有效数据7字节，填充1字节对齐32位边界，总计8字节：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ID   | len=6 |  CmdTypeID  |      AnchorSeq (32bit)          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  AnchorSeq (cont) |  FrameInt |   AnchorAck   |   padding(0)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| 字段 | 长度 | 说明 |
|------|------|------|
| CmdTypeID | 8 bit | 当前交互模式分类标识（滑动窗口聚合） |
| AnchorSeq | 32 bit | 应用层指令序列号锚点，用于延迟测量 |
| FrameInt | 8 bit | 帧意图标记（场景类型 + 紧急等级） |
| AnchorAck | 8 bit | 上行通道状态反馈 |

> **V2修正说明：** 原V1包含QueueDelay字段（8 bit），经分析发现拥塞控制（GCC/BBR）运行在云端发送侧，QueueDelay在云端内部消费即可，无需下传至终端。V2将其从RTP扩展中移除，改为云端内部优化机制（见4.7节）。

#### 4.2.2 字段① CmdTypeID — 交互模式分类标记

**功能：** 标识当前视频帧对应的交互模式，使终端根据交互模式动态调整传输保护策略（FEC冗余度、NACK重传策略）。

##### 4.2.2.1 指令分类的两层架构

CmdTypeID不是对单条指令的分类，而是对**一段时间窗口内指令模式的聚合判断**。采用两层架构：

**第一层：单条指令基础分类**

根据上行指令JSON中的 `opttype` 字段直接映射：

| opttype值 | 操作类型 | 基础分类 |
|-----------|---------|---------|
| 10 | 触摸按下（ACTION_DOWN） | TOUCH |
| 11 | 触摸移动（ACTION_MOVE） | TOUCH_MOVE |
| 12 | 触摸抬起（ACTION_UP） | TOUCH |
| 16 | 传感器/陀螺仪数据 | SENSOR |
| 20 | 按键事件 | KEY |
| 其他 | 扩展类型 | 可配置映射 |

**第二层：滑动窗口聚合分类**

云端维护一个滑动时间窗口（默认500ms），统计窗口内的指令类型和频率，输出交互模式分类：

```python
class CommandAggregator:
    """指令聚合分类器"""
    
    def __init__(self, config):
        self.window_ms = config.get('window_ms', 500)
        self.high_freq_threshold = config.get('high_freq_threshold', 20)
        self.sensor_threshold = config.get('sensor_threshold', 10)
        self.event_buffer = []  # (timestamp, opttype) 列表
    
    def on_command_received(self, opttype):
        """每收到一条上行指令时调用"""
        self.event_buffer.append((now_ms(), opttype))
        self._prune_old_events()
    
    def classify(self):
        """每编码一帧时调用，返回当前交互模式"""
        self._prune_old_events()
        
        if not self.event_buffer:
            return 0x00  # NONE
        
        touch_count = len([e for e in self.event_buffer 
                          if e[1] in (10, 11, 12)])
        move_count = len([e for e in self.event_buffer 
                         if e[1] == 11])
        sensor_count = len([e for e in self.event_buffer 
                           if e[1] == 16])
        key_count = len([e for e in self.event_buffer 
                        if e[1] == 20])
        
        # 分类优先级从高到低
        if sensor_count > self.sensor_threshold:
            return 0x01  # HIGH_FREQ - 高频传感器（游戏陀螺仪）
        
        if move_count > self.high_freq_threshold:
            return 0x01  # HIGH_FREQ - 快速滑动（游戏/刷网页）
        
        if key_count > 0 and touch_count == 0:
            return 0x03  # KEY_INPUT - 纯键盘输入
        
        if touch_count <= 3:
            return 0x02  # LOW_FREQ - 低频触摸（单击/长按）
        
        if key_count > 0:
            return 0x05  # COMMAND - 混合操作
        
        return 0x02  # 默认低频触摸
    
    def _prune_old_events(self):
        """清理窗口外的旧事件"""
        cutoff = now_ms() - self.window_ms
        self.event_buffer = [e for e in self.event_buffer 
                            if e[0] > cutoff]
```

**映射规则可热更新：**

```json
// cloudphone_cmd_mapping.json
{
  "opttype_mapping": {
    "10": "TOUCH",
    "11": "TOUCH_MOVE",
    "12": "TOUCH",
    "16": "SENSOR",
    "20": "KEY"
  },
  "aggregation": {
    "window_ms": 500,
    "high_freq_threshold": 20,
    "sensor_threshold": 10
  }
}
```

##### 4.2.2.2 CmdTypeID字段编码定义

| 值 | 类型名称 | 触发条件 | 终端传输保护策略 |
|----|---------|---------|---------------|
| 0x00 | NONE | 窗口内无交互指令 | 常规FEC策略 |
| 0x01 | HIGH_FREQ | 高频触摸/传感器（500ms内>20次MOVE或>10次SENSOR） | 增强FEC冗余（+50%），优先Burst NACK |
| 0x02 | LOW_FREQ | 低频触摸（500ms内≤3次触摸） | 常规FEC策略 |
| 0x03 | KEY_INPUT | 纯键盘输入 | 低FEC冗余，丢包不重传 |
| 0x04 | GESTURE | 手势操作（预留） | 增强FEC冗余 |
| 0x05 | COMMAND | 混合操作/系统命令 | 常规FEC策略 |
| 0x06-0x1F | RESERVED | 预留扩展 | — |
| 0x20-0xFF | CUSTOM | 业务自定义 | 根据业务需求 |

##### 4.2.2.3 云端注入时机

CmdTypeID在**每帧编码时刷新一次**（而非每条指令更新一次）。编码模块在编码当前帧时，查询聚合分类器获取最新分类结果，写入RTP扩展。

**关键设计：** 终端只能根据**已收到**的RTP包中的CmdTypeID推断交互上下文，丢失包的CmdTypeID不可知。因此，云端在**每一帧**的RTP扩展中都携带CmdTypeID，确保终端即使在丢包后仍能根据相邻帧做出正确判断。

#### 4.2.3 字段② AnchorSeq — 应用层指令序列号锚点

**功能：** 将上行指令的应用层序列号嵌入下行RTP包，建立"操作→响应帧"的因果关联，实现无需时钟同步的端到端延迟测量。

##### 4.2.3.1 应用层序号机制

终端在每条上行指令中嵌入应用层自增序号 `clientSeq`：

```json
{
  "clientSeq": 1058,
  "cmdType": 100020,
  "data": { "opttype": 16, ... }
}
```

> **V2修正说明：** V1使用TCP序列号（seq number），但TCP seq是协议栈内部管理的，应用层不一定能直接获取。V2改为应用层自增序号，实现更简单、可控性更强。

##### 4.2.3.2 指令-帧关联机制（渲染管线钩子）

**核心难点：** 云端收到指令后，渲染管线（SurfaceFlinger→编码器）存在不可控的延迟，不同应用响应速度不同，无法简单地将"某条指令"和"某一帧"做一对一绑定。

**解决方案：** 不追求精确一对一绑定，而是建立"指令集→渲染批次"的因果关联。通过在渲染管线中插入钩子实现：

```
时间线:
  
  TCP:  [Seq=100] [Seq=101]        [Seq=102] [Seq=103]
          │         │                 │         │
          ▼         ▼                 ▼         ▼
  渲染:   ┌─────────────────┐       ┌─────────────────┐
          │  渲染批次 A       │       │  渲染批次 B       │
          │ (消费Seq 100-101) │       │ (消费Seq 102-103) │
          └────────┬────────┘       └────────┬────────┘
                   │                          │
                   ▼                          ▼
  编码:   ┌──────────────┐          ┌──────────────┐
          │  帧 F_N       │          │  帧 F_N+1     │
          │ AnchorSeq=101│          │ AnchorSeq=103│
          └──────────────┘          └──────────────┘
```

**实现步骤：**

**步骤1：指令接收层维护"已消费"标记**

```python
class CommandTracker:
    """指令消费追踪器"""
    
    def __init__(self):
        self.latest_consumed_seq = -1  # 已被渲染系统消费的最大clientSeq
        self.pending_seqs = []         # 已接收但尚未被渲染消费的seq列表
    
    def on_tcp_receive(self, client_seq):
        """TCP收到指令时调用"""
        self.pending_seqs.append(client_seq)
    
    def on_render_submit(self):
        """渲染管线提交一帧时调用（由钩子触发）"""
        if self.pending_seqs:
            consumed = self.pending_seqs.copy()
            self.pending_seqs.clear()
            self.latest_consumed_seq = max(consumed)
            return self.latest_consumed_seq
        return None  # 本帧没有消费新指令
```

**步骤2：渲染管线钩子**

在Android SurfaceFlinger的postFrame回调中插入：

```java
// SurfaceFlinger postFrame回调
void onPostFrame() {
    Integer anchorSeq = commandTracker.onRenderSubmit();
    if (anchorSeq != null) {
        // 将anchorSeq传递给编码器模块
        encoder.setFrameMetadata("anchorSeq", anchorSeq);
    } else {
        encoder.setFrameMetadata("anchorSeq", 0);  // 无新指令
    }
}
```

**步骤3：编码器取出并写入RTP扩展**

```c
void encodeFrame(FrameBuffer* frame) {
    int anchorSeq = getFrameMetadata("anchorSeq");
    
    // 正常编码流程...
    RTPPacket* pkt = createRTPPacket(encoded_data);
    
    // 写入RTP扩展
    pkt->ext_anchor_seq = anchorSeq;
    // ... 其他字段
    
    sendRTP(pkt);
}
```

##### 4.2.3.3 不同应用响应差异的处理

不同APP的渲染响应速度不同（游戏可能2帧响应，IM应用可能5帧），但**不影响关联的正确性**：

- 我们关联的是"指令被渲染系统消费的时刻"，而非"指令应该被响应的时刻"
- 渲染延迟（从指令到达→画面变化）本身就是端到端延迟的组成部分
- 终端计算的 `端到端延迟 = T_recv_rtp - T_send`，天然包含了渲染响应慢的因素

> **这是正确的测量方式：** 如果某APP响应慢（收到指令后500ms才渲染出来），AnchorSeq关联到500ms后的帧，测出的端到端延迟就是500ms+传输延迟。这正是我们想测量的——真实的端到端体验延迟。

##### 4.2.3.4 特殊情况处理

| 情况 | 处理方式 |
|------|---------|
| 一帧消费多条指令 | AnchorSeq取最大seq（最晚到达的指令），测量最保守延迟 |
| 无新指令的帧（自动播放/待机） | AnchorSeq填0，终端不参与延迟统计 |
| 同一指令影响多帧 | 仅首帧关联AnchorSeq，后续帧的AnchorSeq填0 |

##### 4.2.3.5 延迟测量流程

```
终端侧:
  发送指令(clientSeq=N) → 记录 T_send(N)

云端侧:
  收到指令(clientSeq=N) → 渲染 → 编码帧F_M → AnchorSeq=N写入RTP

终端侧:
  收到帧F_M(AnchorSeq=N) → 记录 T_recv(N)
  
  端到端延迟 = T_recv(N) - T_send(N)
  (全程在终端本地时钟体系内计算，无需NTP时钟同步)
```

**延迟数据应用：**
- 终端维护滑动窗口（最近100个样本），统计P50/P95/P99延迟
- P95超过阈值（如200ms）时，通过RTCP反馈请求云端降码率/帧率
- 延迟数据作为RTCP REMB反馈的输入参数

#### 4.2.4 字段③ FrameInt — 帧意图/场景标记

**功能：** 标识当前视频帧的内容属性和渲染紧急度，使终端Jitter Buffer根据场景特征动态调整播放策略。

**字段编码：** 8 bit，高4位为场景类型，低4位为紧急等级：

```
  7 6 5 4   3 2 1 0
  ┌───────┬─────────┐
  │场景类型 │ 紧急等级 │
  └───────┴─────────┘
```

**场景类型（高4位）：**

| 值 | 场景类型 | 典型场景 | Jitter Buffer基础深度 |
|----|---------|---------|---------------------|
| 0x0 | GAME_ACTION | 游戏战斗/竞速 | ≤1帧（最小缓冲） |
| 0x1 | GAME_EXPLORATION | 游戏探索/剧情 | 2-3帧 |
| 0x2 | OFFICE_TEXT | 文档/网页/IM | 3-5帧（清晰度优先） |
| 0x3 | VIDEO_PLAYBACK | 视频播放/动画 | 5-10帧（流畅度优先） |
| 0x4 | UI_TRANSITION | 应用切换/转场 | 3-5帧 |
| 0x5 | STATIC_SCREEN | 静态画面（锁屏） | 最大缓冲 |
| 0x6-0xE | RESERVED | 预留 | — |
| 0xF | CUSTOM | 业务自定义 | — |

**紧急等级（低4位，0-15）：**

由云端根据系统负载和网络状态综合判断：
- 0-3（低）：画面变化小，可充分缓冲
- 4-7（中）：正常交互
- 8-11（高）：密集操作，应尽快渲染
- 12-15（极高）：关键操作响应帧，应立即渲染

**终端Jitter Buffer决策：**

```python
def jitter_buffer_decision(frame_int):
    scene_type = (frame_int >> 4) & 0x0F
    urgency = frame_int & 0x0F
    
    base_depth = SCENE_BUFFER_DEPTH[scene_type]
    # 紧急等级越高，缓冲越浅
    actual_depth = max(0, base_depth - urgency)
    return actual_depth
```

**场景类型数据来源：**

来源于云端渲染引擎，而非编码器：

```
云端渲染引擎/窗口管理器
  → 检测当前前台应用的包名/Activity
  → 查映射表（如 com.tencent.tmgp.sgame → GAME_ACTION）
  → 传递给编码模块
```

映射规则通过配置文件热更新，无需修改编码逻辑。

#### 4.2.5 字段④ AnchorAck — 上行通道状态反馈

**功能：** 云端通过下行RTP流反向通知终端"上行通道是否通畅"，使终端感知上行TCP的拥堵状态。

##### 4.2.5.1 基于指令接收间隔的超时判断（必选方案）

核心逻辑：云端检测"用户是否在活跃操作"与"是否还在收到指令"之间的关系。

```python
class UplinkMonitor:
    """上行通道监控器"""
    
    ACTIVITY_WINDOW_MS = 5000     # 活跃判断窗口：5秒
    MILD_THRESHOLD_MS = 500       # 轻度滞后阈值：500ms
    SEVERE_THRESHOLD_MS = 2000    # 严重滞后阈值：2秒
    OUTAGE_THRESHOLD_MS = 5000    # 中断阈值：5秒
    
    def __init__(self):
        self.last_receive_time = 0
        self.recent_activity = False
    
    def on_command_received(self):
        """每收到一条上行指令"""
        self.last_receive_time = now_ms()
        self.recent_activity = True
    
    def get_anchor_ack(self):
        """计算AnchorAck值"""
        time_since_last = now_ms() - self.last_receive_time
        
        # 最近5秒内有交互，但当前有一段时间没收到 → 可能上行堵了
        if self.recent_activity and time_since_last > self.MILD_THRESHOLD_MS:
            if time_since_last < self.SEVERE_THRESHOLD_MS:
                return 0x10   # 轻度滞后
            elif time_since_last < self.OUTAGE_THRESHOLD_MS:
                return 0x40   # 严重滞后
            else:
                return 0xFF   # 疑似中断
        else:
            return 0x00       # 正常（用户可能本来就没在操作）
    
    def periodic_check(self):
        """每秒调用，更新活跃状态"""
        if now_ms() - self.last_receive_time > self.ACTIVITY_WINDOW_MS:
            self.recent_activity = False
```

> **V2修正说明：** V1方案中AnchorAck基于"终端最新发出的seq与云端最新收到的seq之间的差距"计算，但云端无法获知终端最新发出的seq（除非终端通过RTCP额外上报）。V2改为基于指令接收间隔的超时判断，不依赖终端额外配合，实现更简洁。

##### 4.2.5.2 基于应用层序号差距的增强方案（可选方案）

如果终端在上行指令中携带 `clientSeq`，且通过RTCP定期上报 `latest_client_seq`，云端可精确计算指令差距：

```python
gap = terminal_latest_seq - cloud_latest_received_seq
# gap越大，说明上行拥堵越严重
```

此方案精度更高，但增加协议复杂度，作为增强方案可选实现。

##### 4.2.5.3 AnchorAck编码定义

| 值 | 含义 |
|----|------|
| 0x00 | 正常 |
| 0x01-0x0F | 轻度滞后 |
| 0x10-0x3F | 中度滞后 |
| 0x40-0xFE | 严重滞后 |
| 0xFF | 上行通道疑似中断 |

##### 4.2.5.4 终端消费逻辑

```python
def uplink_congestion_response(anchor_ack):
    if anchor_ack >= 0x40:
        # 严重滞后/中断：上行严重拥堵
        reduce_jitter_buffer_depth(level="MIN")
        send_rtcp_feedback(type="LOW_FPS_REQUEST")
        # 可选：提示用户"网络不稳定，操作可能延迟"
        
    elif anchor_ack >= 0x10:
        # 中度滞后：适当降低缓冲
        reduce_jitter_buffer_depth(level="LOW")
    
    # 轻度或正常：不干预
```

---

### 4.3 SDP协商机制

#### 4.3.1 扩展字段协商

通过SDP `a=extmap` 属性协商：

```
客户端SDP Offer:
  a=extmap:1 urn:cloudphone:rtp-meta:v2

云端SDP Answer:
  a=extmap:1 urn:cloudphone:rtp-meta:v2
```

#### 4.3.2 动态字段子集协商

弱网下可通过SDP自定义属性声明所需字段子集：

```
全量模式:
  a=cloudphone-rtp-meta-fields: CmdTypeID,AnchorSeq,FrameInt,AnchorAck

弱网降级:
  a=cloudphone-rtp-meta-fields: AnchorSeq

恢复:
  a=cloudphone-rtp-meta-fields: CmdTypeID,AnchorSeq,FrameInt,AnchorAck
```

字段子集协商通过SDP re-offer/answer实现，无需中断WebRTC会话。

#### 4.3.3 云手机交互模式协商

```
客户端SDP Offer:
  a=cloudphone-mode: gaming
  a=cloudphone-latency-budget: 80
  a=cloudphone-interaction-rate: high
```

| Mode | 帧率策略 | 码率策略 | 编码Profile |
|------|---------|---------|------------|
| gaming | 60fps优先 | 允许画质波动 | Baseline/低延迟 |
| office | 30fps | 清晰度优先 | Main/高质量 |
| video | 24-30fps | 画质优先 | High/高压缩率 |
| general | 自适应 | 均衡 | 自适应切换 |

会话中途模式变更通过SDP re-offer实现。

---

### 4.4 跨包冗余保护机制

#### 4.4.1 锚点帧与普通帧

每N个连续帧（默认30帧≈500ms）中，第1帧为锚点帧，携带完整4个扩展字段；后续帧为普通帧，至少携带AnchorSeq：

```
帧序列:  [锚点帧]  [普通帧]  [普通帧]  ...  [锚点帧]  ...
字段:    全4字段    至少AnchorSeq          全4字段
```

#### 4.4.2 锚点丢失时的容错

当携带AnchorSeq的包丢失时，终端使用最近锚点的信息进行延迟估算：

```python
if current_anchor_seq is None:
    # 当前帧的AnchorSeq丢失，用上一个锚点估算
    estimated_delay = (recv_time - last_anchor_recv_time) + last_known_delay
    confidence = "LOW"
else:
    actual_delay = recv_time - send_time(current_anchor_seq)
    confidence = "HIGH"
```

---

### 4.5 上行指令双通道容灾机制

#### 4.5.1 触发条件

监控TCP发送队列积压量，当积压量连续3个采样周期（200ms/周期）超过32KB时触发。

#### 4.5.2 双通道并行

关键指令同时通过TCP和WebRTC DataChannel发送，云端取先到者：

```javascript
const rescueChannel = peerConnection.createDataChannel('cloudphone-rescue', {
    ordered: false,
    maxRetransmits: 0,
    protocol: 'cloudphone-cmd-v1'
});
```

#### 4.5.3 消息格式

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   MsgType     |    Priority   |       SequenceID (16bit)      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Payload (variable)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- MsgType：消息类型
- Priority：优先级（仅≤3的关键指令走容灾通道）
- SequenceID：用于云端去重

---

### 4.6 系统工作流程

#### 4.6.1 会话建立

```
1. 客户端通过WebSocket与云端建立信令连接
2. 客户端发送SDP Offer:
   a. 标准WebRTC音视频能力
   b. a=extmap:1 urn:cloudphone:rtp-meta:v2
   c. a=cloudphone-rtp-meta-fields: CmdTypeID,AnchorSeq,FrameInt,AnchorAck
   d. a=cloudphone-mode: gaming
3. 云端回复SDP Answer，确认字段子集和交互模式
4. ICE连接建立
5. 云端创建DataChannel容灾通道
6. 开始音视频流传输
```

#### 4.6.2 正常运行

```
循环:
  ① 终端产生指令(含clientSeq) → TCP发送 → 记录T_send
  ② 云端收到指令 → 聚合分类器更新(→CmdTypeID)
                  → 指令追踪器记录(→pending_seqs)
                  → 上行监控器更新(→last_receive_time)
  ③ 渲染引擎输出画面 → 场景识别(→FrameInt场景部分)
                     → postFrame钩子取出AnchorSeq
  ④ 编码器编码 → 编码器队列报告排队延迟(→QueueDelay, 内部消费)
  ⑤ 打包RTP → 写入4个扩展字段 → 发送
  ⑥ 终端收到RTP → 解析扩展字段:
     - CmdTypeID  → 调整FEC/NACK策略
     - AnchorSeq  → 计算端到端延迟
     - FrameInt   → 调整Jitter Buffer深度
     - AnchorAck  → 感知上行拥堵状态
  ⑦ 终端通过RTCP回传统计数据
```

#### 4.6.3 弱网切换

```
丢包率 > 10%:
  ① SDP re-offer: 缩减扩展字段子集（仅AnchorSeq）
  ② 触发上行容灾: 关键指令双通道
  ③ RTCP反馈: 请求降帧率/码率

恢复（丢包率 < 5% 持续3秒）:
  ① SDP re-offer: 恢复完整字段子集
  ② 关闭容灾通道
  ③ 恢复正常策略
```

---

### 4.7 云端内部优化：编码排队延迟补偿

> 本节描述云端内部机制，不涉及RTP扩展字段传输。

**问题：** WebRTC拥塞控制算法（GCC/BBR）运行在云端发送侧，测量的单向延迟增量包含了"云端编码器排队等待"的非网络延迟，可能误判为网络拥塞。

**方案：** 在云端拥塞控制决策中引入编码排队延迟补偿：

```python
def cloud_congestion_control():
    measured_delay_increase = gcc.get_delay_increase()  # GCC测量的延迟增量
    queue_delay = encoder.get_queue_delay()              # 编码器排队延迟
    
    # 从测量延迟中扣除非网络因素
    network_delay = measured_delay_increase - queue_delay
    
    if network_delay < CONGESTION_THRESHOLD:
        return "NORMAL"       # 网络正常，不降码率
    else:
        return "CONGESTED"    # 网络拥塞，触发降码率
```

**效果：** 避免因云端CPU/GPU负载高导致的误判降码率，保持画质稳定。

---

## 五、技术方案效果

| 指标 | V1 | V2改进 |
|------|----|-------|
| 端到端延迟测量 | 基于TCP seq，应用层不一定可获取 | 改为应用层clientSeq，可控可靠 |
| 指令-帧关联 | 未展开 | 渲染管线钩子+因果标记，解决不同APP响应差异 |
| CmdTypeID映射 | 简单opttype映射 | 滑动窗口聚合分类，匹配真实交互模式 |
| 拥塞控制修正 | QueueDelay下传终端判断（绕路） | 云端内部直接补偿（正确路径） |
| AnchorAck计算 | 依赖终端上报seq（增加复杂度） | 基于接收间隔超时判断（简洁独立） |
| 扩展字段数 | 5个/8字节 | 4个/7字节（+1 padding = 8字节对齐） |

---

## 六、权利要求要点

1. **一种面向云手机交互式流媒体的RTP扩展元数据传输方法**，包括：
   - 在云端对视频帧进行RTP封装时，将控制链路和云端处理链路的状态信息注入RTP头部扩展字段；
   - 所述扩展字段包括：交互模式分类标识、应用层指令序列号锚点、帧意图标记、上行通道状态反馈；
   - 终端接收RTP包后，解析所述扩展字段，用于传输保护策略调整、Jitter Buffer策略调整、端到端延迟测量中的至少一种。

2. 根据权利要求1所述的方法，其特征在于，所述交互模式分类标识由指令聚合分类器计算，该分类器维护滑动时间窗口，统计窗口内的上行指令类型和频率，输出交互模式分类；分类规则通过配置文件管理，支持热更新；分类结果在每帧编码时刷新。

3. 根据权利要求1所述的方法，其特征在于，所述应用层指令序列号锚点的关联方法为：在云端渲染管线的帧提交回调中插入钩子，取出"自上一帧以来所有被渲染系统消费的上行指令中最大的应用层序列号"作为锚点值；不同应用的渲染响应延迟差异被自然包含在端到端延迟测量中。

4. 根据权利要求1所述的方法，其特征在于，所述帧意图标记包括场景类型子字段和紧急等级子字段，场景类型来源于云端渲染引擎对前台应用类型的识别，紧急等级由云端根据系统负载和网络状态综合判断。

5. 根据权利要求1所述的方法，其特征在于，所述上行通道状态反馈基于云端对上行指令接收间隔的监控：当检测到用户处于活跃交互状态但指令接收间隔超过阈值时，判定为上行通道拥堵。

6. 根据权利要求1所述的方法，其特征在于，还包括云端内部的编码排队延迟补偿机制：在拥塞控制算法的延迟测量值中扣除编码器排队延迟，避免非网络因素导致的误判降码率。

7. 根据权利要求1所述的方法，其特征在于，还包括：在SDP协商阶段声明RTP扩展字段的使用子集，在弱网条件下通过SDP重新协商缩减为关键字段子集。

8. 根据权利要求1所述的方法，其特征在于，还包括：跨包冗余保护机制，定义锚点帧和普通帧，锚点帧携带完整扩展字段，普通帧至少携带序列号锚点；当锚点信息丢失时，终端利用最近锚点进行延迟估算。

9. 根据权利要求1所述的方法，其特征在于，还包括：当上行TCP通道发生严重拥堵时，关键操作指令同时通过WebRTC DataChannel发送，云端取先到者执行。

10. 根据权利要求1所述的方法，其特征在于，终端通过比较本地发送时间戳与接收时间戳，在无需时钟同步的条件下计算端到端操作延迟。

---

## 七、附图清单

- 图1：云手机系统架构图（非对称双链路）
- 图2：RTP扩展字段总体格式图
- 图3：CmdTypeID两层分类架构图（基础分类→聚合分类）
- 图4：AnchorSeq指令-帧关联时序图（渲染管线钩子）
- 图5：FrameInt字段结构图（场景类型+紧急等级）
- 图6：AnchorAck超时判断流程图
- 图7：云端编码排队延迟补偿原理图
- 图8：SDP协商流程图
- 图9：跨包冗余保护示意图（锚点帧/普通帧）
- 图10：上行双通道容灾架构图
- 图11：系统总体工作流程图
- 图12：弱网切换时序图
