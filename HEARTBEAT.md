## 心跳任务调度（HEARTBEAT.md）

本文件定义 OpenClaw 在云手机研发工作流中的定时调度任务。

---

## 1. 技术雷达（每周一上午 9:00-12:00 检查）

- 读取 `skills/tech-research/assets/radar_sources.json` 的关注源
- 对每个源执行 `web_fetch` 抓取最近一周的更新
- 按 `filter_rules` 过滤，保留与云手机/音视频/低延迟相关的有价值内容
- 生成周报：`memory/research/tech-radar-YYYY-MM-DD.md`
- 更新 `memory/research/INDEX.md`
- 上次扫描：2026-07-01（已生成 tech-radar-2026-07-01.md）

---

## 2. 每日研发复盘（每日 18:00）

- 读取当天会话/任务记录
- 汇总当天完成的调研、PRD、技术方案、代码总结
- 生成 `memory/YYYY-MM-DD.md` 日报摘要
- 识别未完成项，加入次日待办
- 每周五汇总生成周报

---

## 3. 知识库索引维护（每次生成新文档后）

- PRD、技术方案、变更总结生成后，归档到 `memory/knowledge-base/samples/`
- 更新 `memory/knowledge-base/INDEX.md`
- 更新 `memory/research/INDEX.md`

---

## 4. Cron 任务清单

| 任务 | 调度 | 触发 Skill | 输出 |
|------|------|-----------|------|
| 技术雷达 | 每周一 09:00 | tech-research | `memory/research/tech-radar-YYYY-MM-DD.md` |
| 每日复盘 | 每日 18:00 | 主 Agent + memory_search | `memory/YYYY-MM-DD.md` |

---

## 5. 触发关键词

- "技术雷达"、"扫描技术动态"
- "今日复盘"、"日报"、"周报"
- "归档"、"更新索引"
