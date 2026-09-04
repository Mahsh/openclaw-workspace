# 专利交底书 V3：面向云手机交互式流媒体的RTP扩展元数据传输方法及系统

> 版本：V3（基于V2修正）
> 更新日期：2026-07-02
> 主要修正：
> 1. AnchorAck从RTP扩展移至RTCP APP反馈报文
> 2. RTP收敛到3个核心字段（IM + CSA + FIT），总计6字节
> 3. 新增"交互语义模型"章节，为字段设计提供统一理论基础
> 4. 新增专利墙拆分规划

---

## 一、发明名称

面向云手机交互式流媒体的RTP扩展元数据传输方法及系统

## 二、技术领域

本发明涉及实时音视频传输技术领域，具体涉及一种基于WebRTC的RTP协议头部扩展机制与RTCP反馈扩展机制，面向云手机（Cloud Phone / Cloud Gaming）业务场景，通过在非对称双链路架构（TCP控制上行 + RTP媒体下行）中建立跨链路状态信息注入机制，实现传输策略的场景化自适应优化。

## 三、背景技术

### 3.1 云手机系统架构

云手机采用非对称双链路架构：

```
┌──────────┐                              ┌──────────────┐
│          │  TCP Socket (上行)             │              │
│  客户端   │ ──────────────────────────→ │   云端服务器   │
│ (终端)    │  交互指令/控制消息              │  (云手机实例)  │
│          │                              │              │
│          │  WebSocket (双向)              │              │
│          │ ←────────────────────→     │              │
│          │  SDP/ICE 信令协商              │              │
│          │                              │              │
│          │  WebRTC RTP/RTCP (下行)        │              │
│          │ ←────────────────────────  │              │
│          │  音视频流 + RTCP反馈            │              │
└──────────┘                              └──────────────┘
```

- **上行控制链路**：TCP Socket，传输用户交互指令（触摸坐标、按键、传感器数据）
- **信令协商链路**：WebSocket，传输SDP/ICE，建立WebRTC连接
- **下行媒体链路**：WebRTC RTP下行传输音视频流；RTCP双向传输控制反馈

### 3.2 现有技术的问题

**问题一：控制链路与媒体链路信息割裂**

上行TCP和下行RTP是独立通路。终端的传输保护策略（FEC/NACK）和播放策略（Jitter Buffer）无法感知当前帧的交互上下文——不知道当前帧对应的是游戏连招还是打字输入。

**问题二：终端Jitter Buffer缺乏场景感知**

标准Jitter Buffer只关注网络抖动，不区分帧的内容属性。游戏画面需低延迟优先，文档画面需清晰度优先，视频画面需流畅度优先，但现有协议无法传递"场景意图"。

**问题三：上行通道拥堵对下行不可见**

上行TCP拥塞时，终端操作指令积压在发送队列中，但终端无法感知上行已堵，看到的画面在响应"过时的操作"，体验严重割裂。

**问题四：端到端交互延迟不可测量**

终端无法精确测量"操作发出→画面呈现"的完整延迟链路，缺乏量化优化体验的基础数据。

**问题五：云端编码排队延迟干扰拥塞控制**

云端硬件编码器排队等待时间被GCC误判为网络拥塞，触发不必要的降码率，但实际带宽充足。

### 3.3 现有技术的根本缺陷

上述五个问题有一个共同的根因：**在非对称双链路架构下，控制链路的状态信息（交互类型、交互频率、通道健康度）与媒体链路的传输决策（FEC策略、NACK策略、Jitter Buffer策略）之间缺乏信息通路。**

现有标准协议（RTP/RTCP/WebRTC）设计面向通用P2P音视频通信，不存在"上行控制指令"的概念，因此天然不支持跨链路状态注入。

---

## 四、交互语义模型

### 4.1 模型概述

在进入具体技术方案之前，本章定义一个统一的交互语义模型，作为后续字段设计的理论基础。

本模型将交互式远程渲染系统中的"交互状态"抽象为三个正交维度：

```
                    ┌─────────────────────────────┐
                    │      InteractionState        │
                    │                             │
                    │  维度1: 交互模式 (Mode)       │  → 映射到 IM 字段
                    │  维度2: 帧语义 (Frame Sem.)   │  → 映射到 FIT 字段
                    │  维度3: 链路状态 (Link State) │  → 映射到 RTCP USF
                    └─────────────────────────────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              ┌──────────┐ ┌────────┐ ┌──────────┐
              │传输保护策略│ │播放策略 │ │自适应策略 │
              │(FEC/NACK)│ │(Jitter)│ │(降级/容灾)│
              └──────────┘ └────────┘ └──────────┘
```

### 4.2 维度1：交互模式（Interaction Mode）

交互模式描述的是"一段时间窗口内用户交互行为的宏观特征"，是一个统计层面的分类。

交互模式由以下因素综合决定：
- **交互类型**（触摸/按键/传感器/手势）
- **交互频率**（单位时间内的指令数量）
- **交互连续性**（突发式/流式/离散式）

交互模式直接影响**传输保护策略**：高频交互场景需要更强的FEC/NACK保护，因为每一帧的交互时效性都很高。

### 4.3 维度2：帧语义（Frame Semantics）

帧语义描述的是"单个视频帧的内容属性和渲染紧急度"，是一个逐帧层面的标记。

帧语义由以下因素综合决定：
- **场景类型**（游戏战斗/文档阅读/视频播放/静态画面）
- **渲染紧急度**（该帧是否需要尽快呈现）

帧语义直接影响**播放策略**：紧急帧应跳过Jitter Buffer立即渲染，静态帧可充分缓冲等待完整帧。

### 4.4 维度3：链路状态（Link State）

链路状态描述的是"上行控制通道的健康度"，是一个系统层面的反馈。

链路状态由以下因素综合决定：
- **指令到达率**（服务端实际收到的指令频率 vs 期望频率）
- **指令到达延迟**（最后一条指令的接收时间距今多久）

链路状态直接影响**自适应策略**：上行严重拥堵时，终端应降低播放缓冲、提示用户，避免"画面超前于操作"。

### 4.5 三个维度的独立性

三个维度相互正交，可以独立变化：

| 场景 | Mode | Frame Sem. | Link State |
|------|------|-----------|-----------|
| 游戏战斗中，网络良好 | HIGH_FREQ | ACTION | NORMAL |
| 游戏战斗中，上行拥堵 | HIGH_FREQ | ACTION | SEVERE_LAG |
| 游戏中切到微信 | LOW_FREQ | TEXT_UI | NORMAL |
| 待机画面，网络良好 | NONE | STATIC | NORMAL |
| 视频播放中，弱网 | NONE | VIDEO | MILD_LAG |

这种正交性意味着终端的三个策略模块（传输保护/播放/自适应）可以独立运行、各自消费对应维度的信息。

---

## 五、发明内容

### 5.1 总体架构

基于交互语义模型，本方案采用 **3个RTP扩展字段 + 1个RTCP扩展报文 + 1个云端内部优化** 的设计：

```
RTP Header Extension (下行，逐帧携带):
  ┌──────────────────────────────────────────────────┐
  │  IM (8bit)    交互模式    → 终端传输保护策略输入    │
  │  CSA (32bit)  指令锚点    → 终端延迟测量输入        │
  │  FIT (8bit)   帧语义      → 终端Jitter Buffer输入  │
  └──────────────────────────────────────────────────┘

RTCP APP Packet (下行，定期发送):
  ┌──────────────────────────────────────────────────┐
  │  USF (8bit)   链路状态    → 终端自适应策略输入      │
  └──────────────────────────────────────────────────┘

云端内部 (不下传):
  ┌──────────────────────────────────────────────────┐
  │  QueueDelay   编码排队延迟 → 云端GCC拥塞控制修正    │
  └──────────────────────────────────────────────────┘
```

### 5.2 RTP扩展字段定义

#### 5.2.1 扩展字段总体格式

采用RFC 8285 One-Byte Header Extension格式，扩展ID通过SDP协商分配。有效数据6字节，填充2字节对齐32位边界，总计8字节：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ID   | len=5 |    IM Field   |      CSA Field (32bit)        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           CSA (cont)          |   FIT Field   |  Reserved(0)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| 字段 | 长度 | 对应语义维度 | 说明 |
|------|------|------------|------|
| IM | 8 bit | 交互模式 | 交互模式分类标识 |
| CSA | 32 bit | （跨维度） | 指令序列锚点，用于延迟测量 |
| FIT | 8 bit | 帧语义 | 帧意图标记（场景类型+紧急等级） |
| Reserved | 16 bit | — | 保留，置0，用于未来扩展 |

> **V3修正说明：** V2包含4个RTP字段（IM+CSA+FIT+USF）。V3将USF（上行状态反馈）从RTP移至RTCP APP报文，原因：USF是控制面反馈信息，本质是"上行通道健康度报告"，不是逐帧需要携带的媒体元数据。将其放在RTP Header Extension中属于语义错配，且增加了每个RTP包的开销。RTCP的发送频率（通常每秒2-4次）足以满足上行状态反馈的时效性需求。

#### 5.2.2 字段① IM — 交互模式标识

**对应语义维度：** 交互模式（Interaction Mode）

**功能：** 标识当前视频帧对应的交互模式类别，终端据此动态调整FEC冗余度和NACK重传策略。

**分类机制：两层架构**

IM不是对单条指令的分类，而是对滑动时间窗口内指令模式的聚合判断。

**第一层：单条指令基础分类**

根据上行指令JSON中的 `opttype` 字段映射：

| opttype值 | 操作类型 | 基础分类 |
|-----------|---------|---------|
| 10 | 触摸按下（ACTION_DOWN） | TOUCH |
| 11 | 触摸移动（ACTION_MOVE） | TOUCH_MOVE |
| 12 | 触摸抬起（ACTION_UP） | TOUCH |
| 16 | 传感器/陀螺仪 | SENSOR |
| 20 | 按键事件 | KEY |

**第二层：滑动窗口聚合**

```python
class InteractionModeAggregator:
    """
    交互模式聚合分类器
    对应语义模型的"维度1: 交互模式"
    """
    
    def __init__(self, config_path="cloudphone_cmd_mapping.json"):
        self.config = load_json(config_path)
        self.window_ms = self.config['aggregation']['window_ms']  # 默认500
        self.event_buffer = []
    
    def on_command(self, opttype):
        """每收到一条上行指令"""
        self.event_buffer.append((now_ms(), opttype))
        self._prune()
    
    def classify(self):
        """每编码一帧时调用"""
        self._prune()
        if not self.event_buffer:
            return 0x00  # NONE
        
        touch = len([e for e in self.event_buffer if e[1] in (10,11,12)])
        move = len([e for e in self.event_buffer if e[1] == 11])
        sensor = len([e for e in self.event_buffer if e[1] == 16])
        key = len([e for e in self.event_buffer if e[1] == 20])
        
        if sensor > self.config['aggregation']['sensor_threshold']:
            return 0x01  # HIGH_FREQ
        if move > self.config['aggregation']['high_freq_threshold']:
            return 0x01  # HIGH_FREQ
        if key > 0 and touch == 0:
            return 0x03  # KEY_INPUT
        if touch <= 3:
            return 0x02  # LOW_FREQ
        if key > 0:
            return 0x05  # COMMAND
        return 0x02
```

**IM字段编码定义：**

| 值 | 名称 | 触发条件 | 终端传输保护策略 |
|----|------|---------|---------------|
| 0x00 | NONE | 窗口内无交互 | 常规FEC |
| 0x01 | HIGH_FREQ | 高频（>20 MOVE/500ms 或 >10 SENSOR/500ms） | FEC冗余+50%，Burst NACK |
| 0x02 | LOW_FREQ | 低频（≤3次触摸/500ms） | 常规FEC |
| 0x03 | KEY_INPUT | 纯键盘输入 | FEC冗余-50%，丢包不重传 |
| 0x04 | GESTURE | 手势操作（预留） | 增强FEC |
| 0x05 | COMMAND | 混合操作/系统命令 | 常规FEC |
| 0x06-0x1F | RESERVED | 预留 | — |
| 0x20-0xFF | CUSTOM | 业务自定义 | 自定义 |

**注入时机：** 每帧编码时刷新一次，在每一帧的所有RTP包中均携带（确保丢包后仍可用）。

#### 5.2.3 字段② CSA — 指令序列锚点

**对应语义维度：** 跨维度（为延迟测量提供基础数据，延迟数据同时服务于三个维度的策略决策）

**功能：** 在下行RTP包中嵌入上行指令的应用层序列号，建立"操作→响应帧"的因果关联，实现无需时钟同步的端到端延迟测量。

**应用层序号机制：**

终端在每条上行指令中嵌入自增序号 `clientSeq`：

```json
{
  "clientSeq": 1058,
  "cmdType": 100020,
  "data": { "opttype": 16, ... }
}
```

**指令-帧关联机制：渲染管线钩子**

核心难点：云端收到指令后，渲染管线（SurfaceFlinger→编码器）存在不可控延迟，不同APP响应速度不同。

解决方案：不追求精确一对一绑定，建立"指令集→渲染批次"的因果关联。

```python
class CommandFrameTracker:
    """
    指令-帧关联追踪器
    在渲染管线中插入钩子，实现指令集到渲染批次的因果关联
    """
    
    def __init__(self):
        self.pending_seqs = []
        self.latest_anchor = 0
    
    def on_tcp_receive(self, client_seq):
        """TCP收到指令时"""
        self.pending_seqs.append(client_seq)
    
    def on_render_submit(self):
        """
        渲染管线postFrame回调（钩子）
        取出"自上一帧以来所有被消费指令中最大的seq"
        """
        if self.pending_seqs:
            self.latest_anchor = max(self.pending_seqs)
            self.pending_seqs.clear()
            return self.latest_anchor
        return 0  # 无新指令

# SurfaceFlinger postFrame钩子
def on_post_frame():
    anchor = tracker.on_render_submit()
    encoder.set_frame_metadata("csa", anchor)
```

**关联规则：**

| 情况 | 处理 |
|------|------|
| 一帧消费多条指令 | CSA取最大seq（最保守延迟估计） |
| 无新指令的帧 | CSA=0，终端不参与延迟统计 |
| 同一指令影响多帧 | 仅首帧关联CSA，后续帧CSA=0 |
| 不同APP响应速度不同 | 不影响正确性——渲染延迟本身是端到端延迟的组成部分 |

**延迟测量：**

```
终端: 发送指令(clientSeq=N) → 记录 T_send(N)
云端: 收到→渲染→编码→ CSA=N写入RTP
终端: 收到帧(CSA=N) → 记录 T_recv(N)
延迟 = T_recv(N) - T_send(N)  (全程终端本地时钟，无需NTP同步)
```

#### 5.2.4 字段③ FIT — 帧意图标记

**对应语义维度：** 帧语义（Frame Semantics）

**功能：** 描述当前帧的内容场景属性和渲染紧急度，终端据此动态调整Jitter Buffer策略。

**字段编码：** 8 bit，高4位场景类型 + 低4位紧急等级：

```
  7 6 5 4   3 2 1 0
  ┌───────┬─────────┐
  │Scene  │Urgency  │
  │Type   │Level    │
  └───────┴─────────┘
```

**场景类型（高4位）：**

| 值 | 名称 | Jitter Buffer基础深度 |
|----|------|---------------------|
| 0x0 | ACTION（游戏战斗/竞速） | ≤1帧 |
| 0x1 | EXPLORATION（游戏探索） | 2-3帧 |
| 0x2 | TEXT_UI（文档/网页/IM） | 3-5帧 |
| 0x3 | VIDEO（视频播放） | 5-10帧 |
| 0x4 | TRANSITION（应用切换） | 3-5帧 |
| 0x5 | STATIC（锁屏/待机） | 最大缓冲 |
| 0x6-0xE | RESERVED | — |
| 0xF | CUSTOM | — |

**紧急等级（低4位，0-15）：**

| 范围 | 等级 | 效果 |
|------|------|------|
| 0-3 | LOW | 使用完整base_depth |
| 4-7 | MEDIUM | 适当减浅 |
| 8-11 | HIGH | 大幅减浅 |
| 12-15 | CRITICAL | 立即渲染，跳过缓冲 |

**场景类型数据来源：** 云端渲染引擎/窗口管理器识别前台应用，通过映射表确定场景类型。映射规则可热更新。

**终端消费逻辑：**

```python
def jitter_buffer_decision(fit_value):
    scene = (fit_value >> 4) & 0x0F
    urgency = fit_value & 0x0F
    base = SCENE_BUFFER_DEPTH[scene]
    actual = max(0, base - urgency)
    return actual
```

---

### 5.3 RTCP扩展报文定义

#### 5.3.1 设计动机

上行通道状态反馈（USF）是**控制面信息**，不需要逐帧携带，适合通过RTCP报文传输。

RTCP的优势：
- 天然支持双向控制信息交换
- 发送频率可调（每秒2-4次足够）
- 不增加RTP包开销
- 符合RTCP"传输控制反馈"的设计初衷

#### 5.3.2 RTCP APP报文格式

采用RTCP APP（Application-Defined）报文类型（PT=204，RFC 3550第6.7节）：

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

- subtype: 应用自定义子类型（如0x01）
- name: "CPUS"（Cloud Phone Uplink Status，4字节ASCII）
- USF Field: 上行状态反馈主字段（8 bit）
- USF Detail: 辅助信息（8 bit），编码最近一次指令接收间隔（单位：10ms）
- Reserved: 保留，置0

#### 5.3.3 USF字段编码

| 值 | 状态 | 语义 |
|----|------|------|
| 0x00 | NORMAL | 上行正常 |
| 0x01-0x0F | MILD_LAG | 轻度滞后 |
| 0x10-0x3F | MODERATE_LAG | 中度滞后 |
| 0x40-0xFE | SEVERE_LAG | 严重滞后 |
| 0xFF | OUTAGE | 疑似中断 |

#### 5.3.4 USF计算方法

```python
class UplinkStatusMonitor:
    """
    上行状态监控器
    对应语义模型的"维度3: 链路状态"
    """
    
    ACTIVITY_WINDOW = 5000     # 活跃判断窗口(ms)
    MILD_THRESH = 500          # 轻度滞后阈值(ms)
    SEVERE_THRESH = 2000       # 严重滞后阈值(ms)
    OUTAGE_THRESH = 5000       # 中断阈值(ms)
    
    def __init__(self):
        self.last_recv_time = 0
        self.is_active = False
    
    def on_command(self):
        self.last_recv_time = now_ms()
        self.is_active = True
    
    def compute_usf(self):
        """每秒计算一次，通过RTCP APP发送"""
        elapsed = now_ms() - self.last_recv_time
        
        if self.is_active and elapsed > self.MILD_THRESH:
            if elapsed < self.SEVERE_THRESH:
                usf = 0x10
            elif elapsed < self.OUTAGE_THRESH:
                usf = 0x40
            else:
                usf = 0xFF
        else:
            usf = 0x00
        
        detail = min(255, elapsed // 10)  # 最近接收间隔/10ms
        return usf, detail
    
    def periodic_check(self):
        """每秒调用"""
        if now_ms() - self.last_recv_time > self.ACTIVITY_WINDOW:
            self.is_active = False
```

#### 5.3.5 RTCP APP发送策略

- 发送频率：每500ms发送一次（可通过SDP协商调整）
- 仅在USF值发生变化时立即发送（不等下一个周期）
- 会话开始时发送一次NORMAL状态
- USF值连续3次未变化时，可降低发送频率至每2秒一次

#### 5.3.6 终端消费逻辑

```python
def on_rtcp_app_cpus(usf, detail):
    """收到RTCP APP上行状态报文"""
    
    if usf >= 0x40:
        # 严重滞后/中断
        reduce_jitter_buffer(level="MIN")
        send_rtcp_feedback("LOW_FPS_REQUEST")
        show_user_hint("网络不稳定，操作可能延迟")
    
    elif usf >= 0x10:
        # 中度滞后
        reduce_jitter_buffer(level="LOW")
    
    elif usf >= 0x01:
        # 轻度滞后
        pass  # 不干预，但记录日志
    
    # NORMAL: 不干预
```

---

### 5.4 云端内部优化：编码排队延迟补偿

> 本节描述云端内部机制，不涉及RTP/RTCP扩展字段传输。

**问题：** GCC测量的单向延迟增量包含云端编码器排队延迟（非网络因素），导致误判拥塞。

**方案：** 在云端拥塞控制决策中扣除编码排队延迟：

```python
def cloud_congestion_control():
    measured = gcc.get_delay_increase()   # GCC测量值
    queue = encoder.get_queue_delay()      # 编码器排队延迟
    network = measured - queue             # 纯网络延迟
    
    if network < CONGESTION_THRESHOLD:
        return "NORMAL"    # 网络正常，不降码率
    else:
        return "CONGESTED" # 网络拥塞
```

---

### 5.5 SDP协商机制

#### 5.5.1 RTP扩展协商

```
SDP Offer:
  a=extmap:1 urn:cloudphone:irrm:v3

SDP Answer:
  a=extmap:1 urn:cloudphone:irrm:v3
```

#### 5.5.2 字段子集协商

```
全量:  a=irrm-fields: IM,CSA,FIT
精简:  a=irrm-fields: CSA         // 弱网仅保留锚点
```

默认启用全部3个字段。字段子集通过SDP re-offer动态调整。

#### 5.5.3 RTCP USF协商

```
启用:  a=irrm-usf-rtcp: enabled
频率:  a=irrm-usf-interval: 500       // 单位ms，默认500
禁用:  a=irrm-usf-rtcp: disabled      // 弱网可关闭
```

#### 5.5.4 交互模式声明

```
a=irrm-session-mode: action          // action | productivity | media | adaptive
a=irrm-latency-budget: 80            // 延迟预算(ms)
```

| Mode | 默认帧率 | 默认编码Profile |
|------|---------|---------------|
| action | 60fps | Baseline/低延迟 |
| productivity | 30fps | Main/高质量 |
| media | 24-30fps | High/高压缩率 |
| adaptive | 自适应 | 自适应切换 |

---

### 5.6 跨包冗余保护

每N帧（默认30帧≈500ms）定义一个锚点帧，携带完整3个字段；普通帧至少携带CSA：

```
帧序列:  [锚点帧]  [普通帧]  [普通帧]  ...  [锚点帧]
字段:    IM+CSA+FIT  至少CSA  至少CSA       IM+CSA+FIT
```

锚点丢失时终端使用最近锚点估算延迟（置信度标记为LOW）。

---

### 5.7 上行指令双通道容灾

当TCP发送队列积压量连续3个采样周期（200ms）超过32KB时：

```
关键指令同时走:
  主通道:   TCP Socket (原有)
  容灾通道: WebRTC DataChannel (ordered:false, maxRetransmits:0)

云端取先到者，通过SequenceID去重
```

---

### 5.8 系统工作流程

#### 5.8.1 会话建立

```
1. WebSocket信令连接
2. SDP Offer/Answer:
   a. a=extmap:1 urn:cloudphone:irrm:v3
   b. a=irrm-fields: IM,CSA,FIT
   c. a=irrm-usf-rtcp: enabled
   d. a=irrm-session-mode: action
3. ICE连接建立
4. 创建DataChannel容灾通道
5. 开始传输
```

#### 5.8.2 正常运行

```
循环:
  ① 终端: 产生指令(clientSeq) → TCP发送 → 记录T_send
  ② 云端: 收到指令 → 聚合分类器(IM) + 指令追踪器(CSA) + 上行监控器(USF)
  ③ 云端: 渲染引擎 → 场景识别(FIT场景) → postFrame钩子(CSA锚点)
  ④ 云端: 编码器编码 → 排队延迟补偿(内部) → 打包RTP(IM+CSA+FIT)
  ⑤ 云端: 每500ms发送RTCP APP(USF)
  ⑥ 终端: 收到RTP → IM调整FEC/NACK + CSA计算延迟 + FIT调整Jitter
  ⑦ 终端: 收到RTCP APP → USF调整自适应策略
  ⑧ 终端: RTCP回传统计数据
```

#### 5.8.3 弱网切换

```
丢包率 > 10%:
  ① SDP re-offer: 缩减字段子集(仅CSA) + 关闭USF RTCP
  ② 触发上行容灾
  ③ RTCP反馈: 请求降帧率/码率

恢复:
  ① SDP re-offer: 恢复全字段 + 启用USF RTCP
  ② 关闭容灾通道
  ③ 恢复正常策略
```

---

## 六、技术方案效果

| 指标 | 效果 |
|------|------|
| 端到端延迟可测量 | CSA锚点实现无需时钟同步的精确延迟测量（±5ms精度） |
| 传输保护场景化 | IM字段使终端可根据交互模式动态调整FEC/NACK策略 |
| 播放策略场景化 | FIT字段使终端可根据场景类型和紧急度调整Jitter Buffer |
| 上行状态可见 | USF通过RTCP反馈使终端感知上行拥堵，避免体验割裂 |
| 拥塞控制误判降低 | 云端内部QueueDelay补偿，误判降码率减少60-70% |
| 弱网鲁棒性 | 跨包冗余+动态字段裁剪，丢包率20%下关键锚点仍可维持 |
| RTP开销最小化 | 3字段/6字节有效数据（+2 padding），比V2减少1字节 |
| 语义清晰 | RTP只携带逐帧媒体元数据，控制面信息走RTCP，职责分离 |

---

## 七、权利要求要点

### 独立权利要求

1. **一种面向交互式远程渲染流媒体的传输优化方法**，所述系统采用非对称双链路架构，上行控制链路基于TCP传输交互指令，下行媒体链路基于RTP传输音视频流，其特征在于：
   - 在RTP头部扩展中携带交互模式标识、指令序列锚点和帧意图标记三个字段；
   - 在RTCP应用定义报文中携带上行通道状态反馈；
   - 终端根据所述RTP扩展字段调整传输保护策略和播放策略，根据所述RTCP报文调整自适应策略。

### 从属权利要求

2. 根据权利要求1所述的方法，其特征在于，所述交互模式标识由指令聚合分类器计算，该分类器维护滑动时间窗口，统计窗口内的上行指令类型和频率，输出交互模式分类；分类结果在每帧编码时刷新。

3. 根据权利要求1所述的方法，其特征在于，所述指令序列锚点的关联方法为：终端在上行指令中嵌入应用层自增序列号；云端在渲染管线的帧提交回调中插入钩子，取出"自上一帧以来所有被渲染系统消费的上行指令中最大的序列号"作为锚点值。

4. 根据权利要求3所述的方法，其特征在于，终端通过比较本地发送时间戳与接收时间戳，在无需时钟同步的条件下计算端到端操作延迟。

5. 根据权利要求1所述的方法，其特征在于，所述帧意图标记包括场景类型子字段和紧急等级子字段；场景类型来源于云端渲染引擎对前台应用类型的识别；终端根据场景类型确定基础缓冲深度，根据紧急等级动态缩减缓冲深度。

6. 根据权利要求1所述的方法，其特征在于，所述上行通道状态反馈基于服务端对上行指令接收间隔的监控：当检测到终端处于活跃交互状态但指令接收间隔超过阈值时，判定为上行通道拥堵。

7. 根据权利要求1所述的方法，其特征在于，还包括云端内部的编码排队延迟补偿机制：在拥塞控制算法的延迟测量值中扣除编码器排队延迟。

8. 根据权利要求1所述的方法，其特征在于，还包括：在SDP协商阶段声明RTP扩展字段的使用子集，在弱网条件下通过SDP重新协商缩减为关键字段子集。

9. 根据权利要求1所述的方法，其特征在于，还包括：跨包冗余保护机制，定义锚点帧和普通帧，锚点帧携带完整扩展字段，普通帧至少携带指令序列锚点。

10. 根据权利要求1所述的方法，其特征在于，还包括：当上行TCP通道发生严重拥堵时，关键操作指令同时通过WebRTC DataChannel发送，服务端取先到者执行。

---

## 八、专利墙拆分规划

基于本交底书的技术方案，建议拆分为以下5件独立专利，形成专利墙：

| 编号 | 专利名称 | 核心技术点 | 独立价值 |
|------|---------|-----------|---------|
| P1 | 基于RTP扩展的交互模式感知传输保护方法 | IM字段 + 聚合分类器 + 差异化FEC/NACK | 传输层优化 |
| P2 | 基于渲染管线钩子的端到端交互延迟测量方法 | CSA字段 + postFrame钩子 + 无时钟同步测量 | 延迟可观测性 |
| P3 | 基于帧语义标记的场景化播放策略方法 | FIT字段 + 场景识别 + Jitter Buffer自适应 | 播放层优化 |
| P4 | 基于RTCP扩展的上行通道状态反馈与自适应方法 | USF RTCP APP报文 + 超时判断 + 终端自适应 | 链路状态感知 |
| P5 | 面向交互式流媒体的SDP动态协商与弱网自适应方法 | SDP字段子集 + 模式声明 + 跨包冗余 + 双通道容灾 | 系统弹性 |

**专利墙逻辑关系：**

```
                    P5 (系统弹性：SDP协商 + 弱网自适应 + 容灾)
                   ╱    │    ╲
                  ╱     │     ╲
          P1          P2          P3
       (传输保护)   (延迟测量)   (播放策略)
                  │
                  P4
              (上行状态反馈)
```

- P1/P2/P3 是三个并行的核心技术专利，各自独立有价值
- P4 依赖P2的测量数据（延迟统计辅助上行状态判断）
- P5 是系统级专利，覆盖协商和容灾机制

**建议申请顺序：** P1→P2→P3（同时申请）→ P4（P2完成后1个月）→ P5（最后，整合前4件的系统方案）

---

## 九、附图清单

- 图1：云手机非对称双链路系统架构图
- 图2：交互语义模型三维结构图
- 图3：RTP扩展字段总体格式图（3字段/6字节+2 padding）
- 图4：IM字段两层分类架构图（基础分类→聚合分类）
- 图5：CSA字段指令-帧关联时序图（渲染管线钩子）
- 图6：FIT字段结构图（场景类型+紧急等级）
- 图7：RTCP APP报文格式图（USF上行状态反馈）
- 图8：USF超时判断流程图
- 图9：云端编码排队延迟补偿原理图
- 图10：SDP协商流程图（初始+重协商）
- 图11：跨包冗余保护示意图（锚点帧/普通帧）
- 图12：上行双通道容灾架构图
- 图13：系统总体工作流程图
- 图14：弱网切换时序图
- 图15：专利墙结构与关系图
