# 基于 OpenClaw 的云手机研发智能体工作流

> **第二届"智领未来"AI竞赛 · 技术研发类课题**

## 一、课题定位

本课题面向云手机产品研发全生命周期，基于 **OpenClaw 智能体编排平台**，构建覆盖**技术调研、需求管理、方案评审、代码交付**的 AI 工作流，解决传统研发中"调研慢、文档繁、评审难、总结耗"的痛点，实现研发效率与质量的双提升。

## 二、核心问题

| 研发阶段 | 痛点 | 传统做法 | 智能体做法 |
|----------|------|----------|------------|
| 技术调研 | 技术点多、资料散、整理慢 | 人工检索 + 复制粘贴 | 多 Agent 并行调研 + 自动生成结构化报告 |
| 需求管理 | 格式不统一、术语不一致 | 人工套用模板 | RAG 检索历史 PRD + 自动生成标准 PRD |
| 方案评审 | 对比分析耗时、架构图难画 | Word + 手绘图 | 自动生成方案对比 + Mermaid/SVG 架构图 + 评审清单 |
| 代码交付 | 变更总结费时、影响面难评估 | 人工看 diff | 自动分析 git diff + 影响面分层 + 风险提示 |

## 三、整体架构

```
┌─────────────────────────────────────────────────┐
│         OpenClaw 智能体编排层                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ 调研 Agent │  │ 文档 Agent │  │ 代码 Agent │      │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘      │
│        │              │              │           │
│  ┌─────┴──────────────┴──────────────┴────┐    │
│  │         RAG 私有知识库层                 │    │
│  │  云手机协议文档 │ 架构文档 │ 历史方案  │    │
│  └─────────────────────────────────────────┘    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Skill 库 │  │ Git 集成 │  │ Cron 调度 │      │
│  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────
```

## 四、四大核心场景

### 4.1 技术调研智能体（tech-research）

- **能力**：单点深度调研、多点并行调研、技术雷达定时扫描
- **工具**：`web_search`、`web_fetch`、`sessions_spawn`、`sessions_yield`、`write`
- **输出**：结构化 Markdown 调研报告，归档到 `memory/research/`
- **亮点**：子 Agent 并行、技术雷达自动化、与云手机场景深度绑定

### 4.2 需求文档生成智能体（prd-generator）

- **能力**：输入需求要点，输出标准 PRD；支持变更追踪和历史 PRD 检索
- **工具**：`memory_search`、`write`、`read`
- **输出**：PRD Markdown，归档到 `memory/knowledge-base/samples/prd/`
- **亮点**：RAG 保证术语和格式一致，支持 diff 对比

### 4.3 技术方案 + 评审辅助（tech-doc）

- **能力**：技术选型对比、架构图生成、评审检查清单
- **工具**：`web_search`、`memory_search`、`sessions_spawn`、`write`
- **输出**：技术方案文档，归档到 `memory/knowledge-base/samples/tech-docs/`
- **亮点**：自动生成 Mermaid 架构图、可执行评审清单

### 4.4 代码提交总结（git-summary）

- **能力**：分析 git diff，输出结构化变更总结、影响面分层、风险提示
- **工具**：`exec`、`write`、`memory_search`
- **输出**：变更总结文档，归档到 `memory/knowledge-base/samples/git-summaries/`
- **亮点**：协议/业务/配置/基础设施分层识别，支持批量多分支汇总

## 五、Skill 清单与目录

| Skill | 目录 | 说明 |
|-------|------|------|
| `tech-research` | `workspace/skills/tech-research/` | 已有，本课题增强并作为核心亮点 |
| `prd-generator` | `workspace/skills/prd-generator/` | 新增，PRD 自动生成与变更追踪 |
| `tech-doc` | `workspace/skills/tech-doc/` | 新增，技术方案与评审辅助 |
| `git-summary` | `workspace/skills/git-summary/` | 新增，Git 变更总结 |

## 六、知识库与 RAG

私有知识库路径：`memory/knowledge-base/cloud-phone/`

- **协议文档**：WebRTC、音视频、信令协议
- **架构文档**：云手机整体架构、模块交互
- **历史方案**：过往技术调研、PRD、技术方案、变更总结

Agent 通过 `memory_search` 检索知识库，确保输出与组织规范一致。

## 七、自动化调度

通过 OpenClaw `cron` 实现：

- **技术雷达**：每周一上午自动扫描云手机相关技术动态
- **每日复盘**：每日自动生成/汇总研发工作记录

配置详见 `workspace/HEARTBEAT.md`。

## 八、创新点

1. **多 Agent 协同**：调研、文档、代码三类 Agent 通过 `sessions_spawn` + `sessions_yield` 协同工作
2. **RAG 私有知识库**：将云手机协议、架构、历史方案沉淀为知识库，提升输出一致性与专业性
3. **Skill 体系化**：自研 4 个 Skill 覆盖研发全生命周期
4. **Cron 自动化**：定时技术雷达和每日复盘，实现"无人值守"的研发信息流动
5. **可落地、可演示**：所有 Skill 均有明确目录、模板、样例，可直接运行

## 九、目录结构

```
workspace/
├── docs/competition/              # 竞赛交付文档
│   ├── README.md                  # 本文件
│   └── architecture.md            # 架构详解
├── skills/
│   ├── tech-research/             # 技术调研 Skill（已有+增强）
│   ├── prd-generator/             # PRD 生成 Skill（新增）
│   ├── tech-doc/                  # 技术方案 Skill（新增）
│   └── git-summary/               # Git 总结 Skill（新增）
├── memory/
│   ├── knowledge-base/            # RAG 私有知识库
│   │   ├── cloud-phone/           # 领域知识
│   │   └── samples/               # 样例输出
│   └── research/                  # 调研报告
└── HEARTBEAT.md                   # 定时任务配置
```

## 十、演示与验证

详见 `docs/competition/architecture.md` 和 `memory/knowledge-base/samples/` 下的样例输出。
