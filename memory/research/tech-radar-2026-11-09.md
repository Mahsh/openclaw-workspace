# 技术雷达 2026-11-09

> 扫描时间：2026-11-09 15:10 (GMT+8)，补跑（原定周一 09:00，上次扫描 2026-07-01，间隔 4 个月）
> 说明：Google 系站点（webrtc.org / blog.chromium.org / android-developers / cloud.google.com）在本机网络下直连被阻断（HTTP 000），本期改用 GitHub API + Chromium 仓库 autoroll 记录 + GitHub 仓库搜索替代。

## 1. WebRTC（经 Chromium autoroll，2026-11-06 ~ 11-07）

| 变更 | 说明 | 云手机相关度 |
|------|------|-------------|
| SCReAMv2 默认参数调整 | `NumberOfRttsBetweenResetRefWindowIOnCongestion` 默认设为 1e8 | ★★★ SCReAMv2 拥塞恢复路径持续演进，弱网 QoS 方案可参考 |
| SFrame 异步化 + SframeDecryptorHandle | Cisco 贡献：SFrame 解密密钥更新改异步、新增 handle 接口 | ★★★ 安全帧加密（DRM/版权流）链路改造，影响云手机内容版权场景 |
| DataChannel internal id 按 controller 分配 | `datachannel: allocate internal ids per controller` | ★★ 多 peer 隔离，多开/集群场景下 datachannel 管理更稳 |
| 移除 deprecated CallConfig worker queue；RTP 收发器 worker_thread 清理 | 内部线程模型重构 | ★ 上游重构，跟版时注意 |
| SDP 接受 `TCP/DTLS/RTP/SAVPF` 协议名 | 兼容性修复 | ★ |

## 2. FFmpeg（GitHub tags）

- 最新：`n9.1-dev`（开发中）、`n9.0.2`（9.0 分支最新 point release）、`v0.6.1` / `v0.5.3`（旧分支维护）
- 解读：9.x 为主力线，云手机侧若用 FFmpeg 做转封装/转码，建议对齐 9.0.x 稳定点

## 3. GitHub 云手机/云游戏方向新仓库（2026-08 以后创建）

| 仓库 | ⭐ | 摘要 |
|------|----|------|
| BagasRizkyHarySaputra/MLBB-waydroid-LinuxCloudMLBB | 201 | Waydroid(Linux) 跑 MLBB，Sunshine + Artemis/Moonlight 推流到手机，Intel VAAPI 编码、多触点——开源"本地云游戏"参考实现 |
| InukaAsith/TwinDesk | 3780 | 手机/PC 跨设备合一桌面（屏幕/剪贴板/文件共享），非云但跨设备交互参考 |
| playportdev/playport | 790 | iOS 本地跑 Windows 游戏（无云），反向路线对比参考 |

## 关键发现（Top 3）

1. **SCReAMv2 仍在快速迭代**（默认参数变更），与上次雷达（2026-07-01）关注的 QUIC/拥塞方向一脉相承——云手机弱网自适应方案值得跟进 SCReAMv2 行为
2. **SFrame 安全帧加密进入 Chromium 主线**（Cisco 主导、异步化改造），云手机若涉及 DRM 内容分发需关注兼容
3. **Waydroid + Sunshine/Moonlight 开源云游戏链路**社区热度上升，可作为低成本云手机推流方案对比基线

## 未完成源（网络限制）

- webrtc.org/blog、blog.chromium.org、android-developers.googleblog.com、cloud.google.com/blog —— 直连被阻断，待网络恢复后补扫

## 建议

- 下次雷达优先验证 Google 系站点可达性；若持续不可达，把 Chromium autoroll commit（`github.com/chromium/chromium?path=third_party/webrtc`）固化为 WebRTC 替代源
- 可立项调研：SCReAMv2 vs 现有 QoS 降档方案（对照 `webrtc-qos-degradation.md`）
