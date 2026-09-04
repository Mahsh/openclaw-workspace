# 专利交底书 P1

---

## 一、发明名称

一种基于RTP扩展的交互模式感知传输保护方法及系统

## 二、技术领域

本发明涉及实时音视频传输技术领域，具体涉及一种在交互式远程渲染流媒体系统中，基于RTP头部扩展携带交互模式标识，实现终端差异化传输保护策略的方法。

## 三、背景技术

### 3.1 云手机系统架构

云手机（Cloud Phone）将移动终端操作系统运行于云端服务器，用户通过轻量级终端远程访问。其典型架构采用非对称双链路设计：上行控制链路基于TCP Socket传输交互指令（触摸、按键、传感器数据等），下行媒体链路基于WebRTC RTP/RTCP协议传输编码后的音视频流。

### 3.2 现有技术的问题

在现有WebRTC传输框架中，终端接收端对下行视频流的传输保护策略（前向纠错FEC冗余度、否定确认NACK重传次数和等待时间）采用固定配置或仅基于网络质量指标（丢包率、往返时延）动态调整。

这种机制在云手机场景下面临根本性缺陷：

**缺陷一：不理解交互上下文。** 用户在玩动作游戏时（高频触摸/陀螺仪输入），每一帧的交互时效性极高，丢一帧可能导致操作"不跟手"；而用户在打字输入时（低频键盘事件），丢一帧几乎无感。但现有传输保护策略对两者一视同仁。

**缺陷二：策略与需求错配。** 高频交互场景下，应增加FEC冗余度和NACK重传次数，宁可多用带宽也要保证每帧到达；低频交互场景下，应减少保护开销，将带宽留给后续帧以获得更高画质。但现有机制无法做出这种区分。

**缺陷三：单条指令不包含场景语义。** 上行指令的典型格式为：

```json
{"cmdType":100020, "data":{"opttype":16, "x":-0.02, "y":0.37}}
```

单条指令仅携带原始操作数据（坐标、传感器值），不包含"用户正在做什么"的语义信息。服务端无法从单条指令推断当前交互场景。

### 3.3 现有技术的不足

现有RTP协议及其扩展机制（如RFC 8285）定义了通用头部扩展格式，但未定义面向交互式远程渲染场景的交互模式标识字段。现有WebRTC拥塞控制（GCC/BBR）和传输保护机制完全基于网络维度做决策，不理解应用层的交互语义。

## 四、发明内容

### 4.1 总体思路

本发明的核心思路是：在云端建立上行指令的滑动窗口聚合分类机制，将一段时间窗口内的多条原始指令聚合为高层交互模式分类，通过RTP头部扩展字段传递给终端，终端据此动态调整传输保护策略。

```
上行指令流 → opttype解析 → 基础分类 → 滑动窗口统计 → 交互模式分类(IM)
                                                         ↓
                                              写入RTP Header Extension
                                                         ↓
                                              终端解析IM → 查询策略表 → 调整FEC/NACK
```

### 4.2 上行指令聚合分类方法

#### 4.2.1 第一层：单条指令基础分类

云端收到上行TCP指令后，解析JSON中的 `opttype` 字段，映射为基础分类：

| opttype值 | 操作类型 | 基础分类 |
|-----------|---------|---------|
| 10 | 触摸按下（ACTION_DOWN） | TOUCH |
| 11 | 触摸移动（ACTION_MOVE） | TOUCH_MOVE |
| 12 | 触摸抬起（ACTION_UP） | TOUCH |
| 16 | 传感器/陀螺仪数据 | SENSOR |
| 20 | 按键事件 | KEY |

基础分类映射规则通过配置文件管理，支持热更新。

#### 4.2.2 第二层：滑动窗口聚合分类

云端维护一个滑动时间窗口（默认500ms），统计窗口内的基础分类事件，输出交互模式分类标识（IM值）。

**分类算法：**

```python
class InteractionModeAggregator:
    def __init__(self, config):
        self.window_ms = config.get('window_ms', 500)
        self.high_freq_threshold = config.get('high_freq_threshold', 20)
        self.sensor_threshold = config.get('sensor_threshold', 10)
        self.event_buffer = []  # (timestamp_ms, base_category)
    
    def on_command(self, opttype):
        base_cat = self._map_opttype(opttype)
        self.event_buffer.append((now_ms(), base_cat))
        self._prune()
    
    def classify(self):
        """每编码一帧时调用"""
        self._prune()
        if not self.event_buffer:
            return 0x00  # NONE
        
        move_count = len([e for e in self.event_buffer if e[1] == 'TOUCH_MOVE'])
        sensor_count = len([e for e in self.event_buffer if e[1] == 'SENSOR'])
        touch_count = len([e for e in self.event_buffer if e[1] in ('TOUCH', 'TOUCH_MOVE')])
        key_count = len([e for e in self.event_buffer if e[1] == 'KEY'])
        
        if sensor_count > self.sensor_threshold:
            return 0x01  # HIGH_FREQ
        if move_count > self.high_freq_threshold:
            return 0x01  # HIGH_FREQ
        if key_count > 0 and touch_count == 0:
            return 0x03  # KEY_INPUT
        if touch_count <= 3:
            return 0x02  # LOW_FREQ
        if key_count > 0:
            return 0x05  # COMMAND
        return 0x02  # 默认LOW_FREQ
    
    def _prune(self):
        cutoff = now_ms() - self.window_ms
        self.event_buffer = [e for e in self.event_buffer if e[0] > cutoff]
```

**交互模式分类标识（IM）编码定义：**

| IM值 | 名称 | 触发条件 |
|------|------|---------|
| 0x00 | NONE | 窗口内无交互指令 |
| 0x01 | HIGH_FREQ | 500ms内TOUCH_MOVE>20次或SENSOR>10次 |
| 0x02 | LOW_FREQ | 500ms内触摸事件≤3次 |
| 0x03 | KEY_INPUT | 仅有键盘输入事件 |
| 0x04 | GESTURE | 手势操作（预留） |
| 0x05 | COMMAND | 混合操作/系统命令 |
| 0x06-0x1F | RESERVED | 预留扩展 |
| 0x20-0xFF | CUSTOM | 业务自定义 |

**分类刷新时机：** 聚合分类器在每帧编码时调用一次，输出当前IM值。非每条指令触发刷新。

### 4.3 RTP扩展字段注入

#### 4.3.1 字段格式

在RTP头部扩展（RFC 8285 One-Byte Header Extension）中定义交互模式标识字段（IM Field），占8 bit。IM字段作为IRRM（Interactive Remote Rendering Metadata）扩展的一部分，通过SDP协商启用。

```
 0                   1
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ID   | len=0 |    IM Field   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

#### 4.3.2 注入规则

a) 云端编码器在每帧编码时查询聚合分类器获取最新IM值，写入该帧所有RTP包的扩展头部；

b) 每一帧的所有RTP包均携带IM字段（非仅首包），确保终端在丢包后仍可从相邻帧获取交互模式信息；

c) IM值为0x00时仍正常携带，不省略。

### 4.4 终端差异化传输保护策略

#### 4.4.1 策略映射表

终端维护预定义的策略映射表，根据IM值查询对应的FEC/NACK参数：

| IM值 | FEC冗余率 | NACK最大重传次数 | NACK等待时间 | 策略意图 |
|------|----------|---------------|------------|---------|
| 0x00 NONE | 基准×1.0 | 2次 | 30ms | 常规保护 |
| 0x01 HIGH_FREQ | 基准×1.5 | 4次 | 15ms | 激进保护，保证每帧到达 |
| 0x02 LOW_FREQ | 基准×1.0 | 2次 | 30ms | 常规保护 |
| 0x03 KEY_INPUT | 基准×0.5 | 1次 | 50ms | 保守保护，节省带宽 |
| 0x05 COMMAND | 基准×1.0 | 2次 | 30ms | 常规保护 |

#### 4.4.2 动态切换逻辑

```python
def update_protection_policy(rtp_packet):
    im = parse_im_field(rtp_packet.ext_header)
    
    if im != current_im:
        policy = POLICY_TABLE[im]
        fec_controller.set_redundancy(policy.fec_ratio)
        nack_controller.set_max_retransmit(policy.nack_max_retry)
        nack_controller.set_wait_time(policy.nack_wait_ms)
        current_im = im
```

#### 4.4.3 策略生效粒度

传输保护策略的切换以帧为单位。当IM值发生变化时，从下一帧开始应用新策略，当前帧保持原策略不变。

### 4.5 SDP协商

通过SDP扩展属性协商IM字段的使用：

```
Offer:  a=extmap:1 urn:cloudphone:irrm:v3
Answer: a=extmap:1 urn:cloudphone:irrm:v3
```

支持通过字段子集协商在弱网下关闭IM字段：

```
弱网:  a=irrm-fields: CSA    （仅保留锚点字段，关闭IM）
恢复:  a=irrm-fields: IM,CSA,FIT  （恢复全字段）
```

## 五、技术方案效果

| 效果 | 说明 |
|------|------|
| 传输保护场景化 | 不同交互场景采用不同FEC/NACK策略 |
| 高频场景可靠性提升 | HIGH_FREQ模式下FEC冗余+50%、NACK重传翻倍，弱网下帧到达率提升约15-25% |
| 低频场景带宽节省 | KEY_INPUT模式下FEC冗余-50%，节省带宽用于画质提升 |
| 无额外信令开销 | IM字段嵌入RTP头部扩展，不需要独立信令通道 |
| 热更新灵活 | 分类规则通过配置文件管理，无需重启服务 |

## 六、权利要求要点

1. **一种基于RTP扩展的交互模式感知传输保护方法**，应用于交互式远程渲染流媒体系统，其特征在于，包括：
   - 服务端维护滑动时间窗口，统计窗口内上行交互指令的类型和频率，计算交互模式分类标识；
   - 服务端在每帧视频编码时查询当前交互模式分类标识，将其写入该帧所有RTP包的头部扩展字段；
   - 终端接收端解析RTP头部扩展中的交互模式分类标识，从预定义的策略映射表中查询对应的前向纠错冗余度和否定确认重传参数，应用于当前帧的传输保护。

2. 根据权利要求1所述的方法，其特征在于，所述滑动时间窗口的默认长度为500ms，窗口内统计的指令类型包括触摸移动事件计数和传感器事件计数，当触摸移动事件超过阈值或传感器事件超过阈值时输出高频交互模式。

3. 根据权利要求1所述的方法，其特征在于，上行交互指令通过TCP Socket传输，包含操作类型字段（opttype），服务端根据操作类型字段进行基础分类后输入聚合分类器。

4. 根据权利要求1所述的方法，其特征在于，所述交互模式分类标识在每帧的所有RTP包中均携带，而非仅在首包中携带，以确保丢包后终端仍可从相邻帧获取交互模式信息。

5. 根据权利要求1所述的方法，其特征在于，高频交互模式对应的前向纠错冗余度高于常规模式，否定确认最大重传次数多于常规模式；键盘输入模式对应的前向纠错冗余度低于常规模式。

6. 根据权利要求1所述的方法，其特征在于，还包括：通过SDP信令协商交互模式分类标识字段的使用，在弱网条件下通过SDP重新协商关闭该字段以减少协议开销。

7. 根据权利要求1所述的方法，其特征在于，所述交互模式分类标识的分类规则通过配置文件管理，支持运行时热更新。

8. **一种基于RTP扩展的交互模式感知传输保护系统**，包括：
   - 指令聚合分类模块，部署于服务端，维护滑动时间窗口并输出交互模式分类标识；
   - RTP扩展注入模块，部署于服务端编码器，将交互模式分类标识写入RTP头部扩展；
   - 传输保护策略模块，部署于终端接收端，根据交互模式分类标识动态调整前向纠错和否定确认参数。
