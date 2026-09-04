# Change Summary - media_server

## Branch Info

- **Branch:** `feature/reduce_resolution_by_client`
- **Base Commit:** `c30c63dfbc3`
- **Latest Commit:** `d367267f`
- **Author:** dwxumeng1_2198
- **Version:** `2.0.14` → `2.1.1`
- **Time Range:** 2026-06-25 ~ 2026-06-26

---

## Summary

本分支实现**根据客户端解码能力动态限制云机出流分辨率**功能。核心改动：
1. 解析客户端上报的解码宽高参数，据此智能降档出流分辨率（720P / 1080P / 1440P）
2. 新增档位信息（gearSet）下发机制，告知客户端支持的分辨率档位
3. 将客户端分辨率及镜像分辨率写入 System Property 供 OS 层使用
4. 兼容旧版客户端 DPI 兜底，并增加解码宽高对调的边界判断

---

## Change Detail

### 1. 协议层解析 - 获取客户端解码能力

**文件:** `media/jni/impl/protocols/gx_proto.cpp`

从客户端协议报文 `/decoder/width` 和 `/decoder/height` 字段解析解码宽高，填充到 `VideoExtraParams` 中：

```cpp
extraParams.decodeWidth = dom.getNestingInt("/decoder/width", 0);
extraParams.decodeHeight = dom.getNestingInt("/decoder/height", 0);
```

### 2. 数据结构扩展

**文件:** `media/jni/capture.h`

- `VideoExtraParams` 新增 `decodeWidth` / `decodeHeight` 字段（默认 0）
- `CphCapture` 新增成员变量 `mDecodeWidth` / `mDecodeHeight`
- 新增 4 个私有方法：
  - `setClientSize()` — 写入 client.width/client.height 系统属性
  - `setMirrorSize()` — 写入 net.mirror.width/net.mirror.height 系统属性
  - `notifyGearInfo()` — 向客户端下发档位信息
  - `getGearInfo()` — 构造档位 JSON 报文
- `calcResolutionNormal` / `calcResolutionFolding` 新增 `decodeWidth` / `decodeHeight` 参数
- `calcDensityFolding` 移除 `clientWidth` / `clientHeight` 参数（简化）

### 3. 核心逻辑 - 分辨率计算与限制

**文件:** `media/jni/capture2.cpp`

#### 3.1 解码能力校验

新增 `isDecoderOK2()` 函数，判断目标分辨率是否在客户端解码能力范围内，支持宽高对调：

```cpp
static bool isDecoderOK2(int32_t tw, int32_t th, int32_t dw, int32_t dh) {
    return (dw <= 0) || (dh <= 0) || (tw <= dw && th <= dh) || (tw <= dh && th <= dw);
}
```

> `dw <= 0` 或 `dh <= 0` 表示客户端未上报解码能力，不做限制。

#### 3.2 普通模式分辨率计算 (`calcResolutionNormal`)

原有逻辑：直接返回物理宽度（2K 设备限制为 1280），按客户端宽高比计算高度。

**新逻辑：**
1. 初始以 `min(PhysicalWidth, 1280)` 为基准计算目标宽高
2. 校验是否满足客户端解码能力 → 满足则返回
3. 否则降档到 1080P（需物理宽度 ≥ 1080 且客户端解码宽度 ≥ 1080）
4. 校验 1080P 是否满足 → 满足则返回
5. 兜底到 720P

#### 3.3 折叠屏模式分辨率计算 (`calcResolutionFolding`)

**新逻辑：** 每计算一个候选分辨率后，增加 `isDecoderOK2` 校验：
- 先尝试 1440P（物理宽度 ≥ 1440 的设备）→ 校验
- 再尝试 1080P（物理宽度 ≥ 1080 的设备）→ 校验
- 兜底 720P

> 注意：折叠屏的 1080P 分支由 `else if` 改为 `if`，去掉了条件限制。

#### 3.4 档位信息生成 (`getGearInfo`)

构造 JSON 报文下发给客户端，包含 3 个档位：

| Level | 宽度 | 高度 | 帧率 | 码率(kbps) | 支持条件 |
|-------|------|------|------|------------|----------|
| 1 | 720 | 按比例 | 60 | 1000-3000 | 始终支持 |
| 2 | 1080 | 按比例 | 60 | 3000-7000 | 宽度 ≥ 1080 |
| 3 | 1440 | 按比例 | 60 | 4000-10000 | 宽度 ≥ 2KMaxEncodeWidth |

报文格式：
```json
{
  "type": "gearSet",
  "message": {
    "profileLevel": 3,
    "profiles": [...]
  }
}
```

### 4. Capture 层集成

**文件:** `media/jni/capture.cpp`

#### 4.1 `setHardwareInitParams` — 初始化参数处理

- 保存客户端解码宽高到成员变量
- 调用 `calcResolutionNormal` / `calcResolutionFolding` 时传入 `decodeWidth` / `decodeHeight`
- `calcDensityFolding` 调用简化，不再传客户端宽高
- 新增 `newClient` 标志：当 capability > 0 时标记为新客户端
- 新客户端场景下自动调用 `setClientSize()` 和 `notifyGearInfo()`
- 日志增加 `decoder:WxH` 字段

#### 4.2 `updateResolution` — 运行时分辨率更新

- 同样传入 `decodeWidth` / `decodeHeight` 到计算函数
- 分辨率变更后调用 `setClientSize()` 和 `notifyGearInfo()`
- 日志增加 decoder 信息

#### 4.3 `checkHardwareOn` — 视频流启动

- 启动视频编码前，若 capability & 4，调用 `setMirrorSize()` 写入镜像分辨率

#### 4.4 `clientDecideOK` — 旧版客户端兼容

- 旧版客户端（capability ≤ 0）不再调用 `getDensitySize`，改用 `calcDensityNormal` 兜底
- 主要针对定制镜像场景

### 5. 版本号更新

**文件:** `media/jni/app.cpp`

| 项目 | 旧值 | 新值 |
|------|------|------|
| 版本号 | `2.0.14` | `2.1.1` |
| 时间戳 | `2026-06-24 09:45` | `2026-06-26 14:45` |

### 6. 更新日志

**文件:** `更新日志.txt`

记录 `2.1.0` 和 `2.1.1` 版本变更：

**2.1.0:**
1. 根据客户端参数限制云机出流分辨率
2. 发送档位信息给客户端

**2.1.1:**
1. 设置 client.width 和 net.mirror 给 OS 使用
2. 兜底旧版客户端 DPI（主要是定制镜像）
3. 客户端解码分辨率宽高对调判断

---

## 代码统计

| 文件 | 变动 |
|------|------|
| `media/jni/app.cpp` | 版本号 + 时间戳 |
| `media/jni/capture.cpp` | +68/-17 核心集成 |
| `media/jni/capture.h` | +17/-3 接口定义 |
| `media/jni/capture2.cpp` | +85/-4 算法实现 |
| `media/jni/impl/protocols/gx_proto.cpp` | +2 协议解析 |
| `更新日志.txt` | +10 版本记录 |
| **合计** | **+154/-32** |

---

## 备注

- 第二个 commit 的 commit message 标注了"待测试"，建议重点关注分辨率降档的边界场景
- 折叠屏模式中 `mPhysicalWidth >= 1080` 分支从 `else if` 改为 `if`，逻辑上所有设备都会走一次 1080P 判断，需确认是否符合预期
