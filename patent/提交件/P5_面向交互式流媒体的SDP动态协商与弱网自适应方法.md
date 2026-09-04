# 专利交底书 P5

---

## 一、发明名称

一种面向交互式流媒体的SDP动态协商与弱网自适应方法及系统

## 二、技术领域

本发明涉及实时音视频传输技术领域，具体涉及一种在交互式远程渲染流媒体系统中，基于SDP信令动态协商RTP扩展字段子集、结合跨包冗余保护和上行双通道容灾的弱网自适应方法。

## 三、背景技术

### 3.1 RTP扩展元数据的协议开销

在交互式远程渲染流媒体系统中，通过在RTP头部扩展中携带交互元数据（如交互模式标识、指令序列锚点、帧意图标记等），可以显著优化终端的传输保护和播放策略。然而，这些扩展字段会增加每个RTP包的头部开销。

在正常网络条件下，每个RTP包增加6-8字节的扩展头部开销（相对于1200字节的MTU占比约0.5%）可以接受。但在弱网条件（丢包率>10%、带宽受限）下，额外的头部开销会加剧网络负担，且部分字段（如交互模式标识）在弱网下的价值降低，此时应优先保留最关键的字段（如指令序列锚点）。

### 3.2 现有SDP协商机制的局限性

现有WebRTC的SDP协商机制（RFC 8829）支持在会话建立时通过 `a=extmap` 属性协商RTP头部扩展的使用。但该机制存在以下局限：

**局限一：不支持字段子集选择。** 标准SDP只能声明"使用或不使用某个扩展URI"，无法声明"使用该扩展中的部分字段"。要么全有，要么全无。

**局限二：运行时调整成本高。** 虽然可以通过SDP re-offer/answer在会话中途修改配置，但现有机制缺乏针对弱网场景的快速字段裁剪和恢复流程。

**局限三：缺乏弱网联动策略。** RTP扩展字段的启用状态与网络状况指标（丢包率、延迟）之间没有标准化的联动机制。

### 3.3 上行容灾的必要性

当上行TCP通道发生严重拥堵时，关键交互指令（如游戏中的紧急闪避操作）可能延迟数秒才能到达云端。标准WebRTC的DataChannel基于SCTP协议，提供了独立于TCP的UDP传输通道，但现有云手机系统未将DataChannel用于上行控制指令的容灾传输。

### 3.4 元数据自身可靠性问题

在极弱网环境（丢包率>10%）下，RTP扩展字段本身也会丢包。如果携带关键锚点信息（如指令序列锚点）的包丢失了，后续依赖该锚点的延迟计算将中断。现有方案缺乏对扩展字段自身的容错保护机制。

## 四、发明内容

### 4.1 总体思路

本发明的核心思路是：**建立基于网络状况指标的弱网状态机，通过SDP自定义属性支持RTP扩展字段的动态子集协商，结合跨包冗余保护机制保证关键元数据可靠性，并在上行TCP严重拥堵时启用DataChannel双通道容灾。**

```
网络状况监控 → 弱网状态机
                    ↓
        ┌───────────┼───────────┐
        ▼           ▼           ▼
  SDP动态协商   跨包冗余保护   上行双通道容灾
  (裁剪字段)   (锚点帧机制)   (TCP+DataChannel)
```

### 4.2 SDP动态字段子集协商

#### 4.2.1 SDP自定义属性定义

定义新的SDP媒体级属性 `a=irrm-fields`，用于声明启用的RTP扩展字段子集：

```
a=irrm-fields:<field-list>
```

`<field-list>` 为逗号分隔的字段名称列表，有效值包括：`IM`（交互模式）、`CSA`（指令序列锚点）、`FIT`（帧意图）。

**示例：**

```
全量模式:  a=irrm-fields: IM,CSA,FIT     （正常网络，6字节有效数据）
中间模式:  a=irrm-fields: CSA,FIT         （中度弱网，5字节有效数据）
精简模式:  a=irrm-fields: CSA             （严重弱网，4字节有效数据）
```

#### 4.2.2 默认行为

若SDP中未声明 `a=irrm-fields` 属性，默认启用全部已协商的字段。

#### 4.2.3 SDP重新协商流程

在会话进行中，任一端可通过SDP re-offer/answer流程修改字段子集：

```
终端检测到弱网:
  1. 生成SDP re-offer: a=irrm-fields: CSA
  2. 通过信令通道（WebSocket）发送re-offer
  3. 云端收到后回复SDP answer确认
  4. 双方从下一帧开始应用新字段子集
  5. RTP媒体流不中断
```

**协商原则：**
- 服务端在Answer中只能确认或进一步缩减字段子集，不能增加Offer中未声明的字段
- 重新协商期间，现有RTP流按原字段配置继续传输
- Answer确认后，从下一个关键帧（I帧）开始应用新字段配置

#### 4.2.4 RTCP USF的动态开关

上行状态反馈通过RTCP APP报文传输，也可通过SDP独立控制启停：

```
启用:  a=irrm-usf-rtcp: enabled
关闭:  a=irrm-usf-rtcp: disabled   （弱网关闭以减少RTCP开销）
```

### 4.3 弱网状态机

#### 4.3.1 状态定义

终端维护一个弱网状态机，根据实时网络指标驱动状态转换：

| 状态 | 描述 | RTP字段子集 | USF RTCP | 上行容灾 |
|------|------|-----------|----------|---------|
| NORMAL | 正常网络 | IM,CSA,FIT | enabled | 关闭 |
| MILD_WEAK | 轻度弱网 | IM,CSA,FIT | enabled | 关闭 |
| MODERATE_WEAK | 中度弱网 | CSA,FIT | disabled | 关闭 |
| SEVERE_WEAK | 严重弱网 | CSA | disabled | 启用 |

#### 4.3.2 转换条件

```python
class WeakNetworkStateMachine:
    def __init__(self):
        self.state = "NORMAL"
        self.packet_loss_history = []
    
    def update(self, packet_loss_rate, rtt_ms):
        """每1秒调用一次"""
        
        if self.state == "NORMAL":
            if packet_loss_rate > 0.05:  # 丢包率>5%
                self._transition("MILD_WEAK")
                
        elif self.state == "MILD_WEAK":
            if packet_loss_rate > 0.10:  # 丢包率>10%
                self._transition("MODERATE_WEAK")
            elif packet_loss_rate < 0.03:  # 恢复
                self._transition("NORMAL")
                
        elif self.state == "MODERATE_WEAK":
            if packet_loss_rate > 0.20:  # 丢包率>20%
                self._transition("SEVERE_WEAK")
            elif packet_loss_rate < 0.05:  # 恢复
                self._transition("NORMAL")
                
        elif self.state == "SEVERE_WEAK":
            if packet_loss_rate < 0.05 and self._stable_for(3):  
                # 丢包率<5%持续3秒
                self._transition("NORMAL")
    
    def _transition(self, new_state):
        self.state = new_state
        self._apply_config(new_state)
        self._trigger_sdp_renegotiation(new_state)
```

#### 4.3.3 迟滞设计

为避免状态频繁抖动，转换条件设置迟滞区间：
- 从NORMAL到MILD_WEAK的阈值是5%，但从MILD_WEAK回到NORMAL的阈值是3%
- 从SEVERE_WEAK恢复需要丢包率<5%**持续3秒**

### 4.4 跨包冗余保护机制

#### 4.4.1 锚点帧与普通帧

为保证弱网下关键元数据（特别是指令序列锚点CSA）的可靠传递，定义锚点帧机制：

**锚点帧：** 每N个连续帧中（默认N=30，约500ms），第1帧定义为锚点帧。锚点帧携带当前已协商的全部RTP扩展字段。

**普通帧：** 锚点帧之间的帧为普通帧。普通帧至少携带CSA字段，其他字段可选携带。

```
帧序列:  [锚点帧]  [普通帧]  [普通帧]  ...  [锚点帧]
字段:    IM+CSA+FIT  CSA+FIT   CSA+FIT       IM+CSA+FIT
(全量模式下)

帧序列:  [锚点帧]  [普通帧]  [普通帧]  ...  [锚点帧]
字段:    CSA        CSA       CSA            CSA
(精简模式下)
```

#### 4.4.2 锚点丢失容错

当终端未收到某帧的CSA字段（因丢包）时：

```python
class AnchorFaultTolerance:
    def __init__(self):
        self.last_valid_csa = None
        self.last_anchor_time = None
        self.last_known_delay = None
    
    def on_rtp_received(self, rtp_packet):
        csa = parse_csa(rtp_packet)
        
        if csa is not None and csa != 0:
            # 正常：收到有效锚点
            self.last_valid_csa = csa
            self.last_anchor_time = now_ms()
            return "HIGH_CONFIDENCE", csa
        
        elif self.last_valid_csa is not None:
            # 容错：使用最近锚点估算
            estimated_delay = (now_ms() - self.last_anchor_time) + self.last_known_delay
            return "LOW_CONFIDENCE", estimated_delay
        
        else:
            # 无可用锚点
            return "NO_DATA", None
```

低置信度延迟样本仅用于统计展示，不参与拥塞控制决策。

#### 4.4.3 锚点帧间隔自适应

锚点帧间隔N可根据网络状况自适应调整：

| 丢包率 | N值 | 锚点频率 | 冗余开销 |
|--------|-----|---------|---------|
| <5% | 60 | ~1Hz | 低 |
| 5-10% | 30 | ~2Hz | 中 |
| 10-20% | 10 | ~6Hz | 高 |
| >20% | 1（每帧都是锚点） | 30Hz | 最高 |

### 4.5 上行双通道容灾机制

#### 4.5.1 触发条件

终端监控TCP发送队列积压量：

```python
class UplinkRescueController:
    THRESHOLD_BYTES = 32768    # 32KB积压阈值
    SAMPLE_PERIOD_MS = 200     # 采样周期
    CONSECUTIVE_COUNT = 3      # 连续超标次数
    
    def __init__(self):
        self.over_threshold_count = 0
        self.rescue_active = False
    
    def monitor(self):
        pending_bytes = tcp_socket.get_unsent_bytes()
        
        if pending_bytes > self.THRESHOLD_BYTES:
            self.over_threshold_count += 1
        else:
            self.over_threshold_count = 0
        
        if self.over_threshold_count >= self.CONSECUTIVE_COUNT and not self.rescue_active:
            self._activate_rescue()
        elif self.over_threshold_count == 0 and self.rescue_active:
            self._deactivate_rescue()
```

#### 4.5.2 DataChannel配置

容灾通道使用WebRTC DataChannel，配置为低延迟模式：

```javascript
const rescueChannel = peerConnection.createDataChannel('cloudphone-rescue', {
    ordered: false,          // 无序传输，最低延迟
    maxRetransmits: 0,       // 不重传，丢失就丢弃
    protocol: 'cloudphone-cmd-v1'
});
```

#### 4.5.3 容灾消息格式

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   MsgType     |    Priority   |       SequenceID (16bit)      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Payload (variable)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- MsgType：消息类型（与IM字段的映射关系一致）
- Priority：优先级（0=最高，255=最低），仅Priority≤3的关键指令走容灾通道
- SequenceID：消息序列号，用于云端去重

#### 4.5.4 云端去重

云端同时监听TCP主通道和DataChannel容灾通道：

```python
class CommandDeduplicator:
    def __init__(self, window_size=1000):
        self.received_seqs = set()
        self.window_size = window_size
    
    def on_command(self, channel, msg):
        seq = msg.sequence_id
        
        if seq in self.received_seqs:
            return  # 已处理过，丢弃（后到的副本）
        
        self.received_seqs.add(seq)
        self._prune_old_seqs()
        
        # 处理指令（取先到者）
        process_command(msg)
```

### 4.6 交互模式SDP声明

终端在SDP中声明当前交互模式偏好，辅助云端配置默认编码策略：

```
a=irrm-session-mode: action          // gaming | productivity | media | adaptive
a=irrm-latency-budget: 80            // 端到端延迟预算(ms)
```

当用户切换应用（如从游戏切到文档）时，终端发起SDP re-offer更新模式声明，云端无缝切换编码Profile。

## 五、技术方案效果

| 效果 | 说明 |
|------|------|
| 协议开销自适应 | 弱网下通过字段裁剪减少RTP头部开销（6字节→4字节），节省带宽 |
| 关键信息可靠 | 跨包冗余保护确保丢包率20%下延迟测量锚点仍可维持 |
| 上行容灾 | TCP严重拥堵时关键指令通过DataChannel旁路到达，避免操作完全中断 |
| 状态机防抖 | 迟滞设计避免弱网状态频繁切换导致的SDP协商风暴 |
| 无缝切换 | SDP re-offer不中断RTP媒体流，用户无感知 |
| 联合优化 | 字段裁剪+冗余保护+双通道容灾三者协同，覆盖弱网全链路 |

## 六、权利要求要点

1. **一种面向交互式流媒体的弱网自适应方法**，应用于交互式远程渲染流媒体系统，其特征在于，包括：
   - 在SDP中定义扩展字段子集声明属性，支持通过SDP重新协商动态调整RTP扩展字段的使用子集；
   - 终端根据网络状况指标驱动弱网状态机，在弱网条件下触发SDP重新协商缩减为关键字段子集以减少协议开销；
   - 定义锚点帧和普通帧的跨包冗余机制，锚点帧携带完整扩展字段，普通帧至少携带指令序列锚点字段；
   - 当上行TCP通道发生严重拥堵时，关键交互指令同时通过WebRTC DataChannel备用通道发送，服务端通过序列标识去重取先到者。

2. 根据权利要求1所述的方法，其特征在于，所述弱网状态机包含迟滞区间：进入弱网状态的丢包率阈值高于退出弱网状态的丢包率阈值，且从严重弱网状态恢复需要网络指标持续改善达到预设时长。

3. 根据权利要求1所述的方法，其特征在于，所述SDP扩展字段子集声明属性支持以下子集组合：全量模式包含交互模式、指令序列锚点和帧意图三个字段；精简模式仅包含指令序列锚点字段。

4. 根据权利要求1所述的方法，其特征在于，锚点帧的间隔根据当前网络丢包率自适应调整，丢包率越高间隔越短。

5. 根据权利要求1所述的方法，其特征在于，当指令序列锚点字段因丢包不可用时，终端使用最近一个成功接收的锚点信息进行延迟估算，并将估算结果标记为低置信度，低置信度样本不参与拥塞控制决策。

6. 根据权利要求1所述的方法，其特征在于，所述WebRTC DataChannel备用通道配置为无序、不重传模式以最小化延迟；终端仅将优先级高于阈值的关键指令通过备用通道发送。

7. 根据权利要求1所述的方法，其特征在于，上行TCP通道拥堵的判定条件为：TCP发送队列积压量连续多个采样周期超过预设阈值。

8. 根据权利要求1所述的方法，其特征在于，SDP重新协商过程中现有RTP媒体流不中断，新字段配置从服务端确认后的下一个关键帧开始应用。

9. **一种面向交互式流媒体的弱网自适应系统**，包括：
   - SDP协商模块，支持扩展字段子集的动态声明和重新协商；
   - 弱网状态机模块，根据网络指标驱动状态转换并触发配置调整；
   - 跨包冗余模块，按可配置间隔产生锚点帧并提供锚点丢失容错；
   - 上行容灾模块，监控TCP通道状态并在严重拥堵时启用DataChannel双通道传输。
