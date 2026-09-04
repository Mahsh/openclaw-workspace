# 跨 OpenClaw 实例同步部署指南

本文档说明如何将当前环境的能力（Skill + 知识库）快速复制到另一台 OpenClaw 实例。

## 一、核心原则

| 同步物 | 方式 | 说明 |
|--------|------|------|
| Skill 定义（代码） | **Git** | 存在 `skills/` 下，人人复用，版本可控 |
| 知识库骨架 | **Git** | `memory/knowledge-base/` 的结构和索引 |
| 竞赛文档 | **Git** | `docs/competition/` 项目产出 |
| 知识内容 | **Dify RAG** | 调研报告/PRD/方案通过 Dify API 实时共享 |
| 个人配置 | 不同步 | `TOOLS.md`, `HEARTBEAT.md`, openclaw.json 每台机器各自配置 |

## 二、目录说明

### 2.1 必须同步（Git）

| 目录 | 内容 | 说明 |
|------|------|------|
| `skills/` | 所有 Skill | tech-research, prd-generator, tech-doc, git-summary, dify-rag, intent-router |
| `docs/` | 项目文档 | 竞赛 README, 架构, Demo |
| `memory/knowledge-base/` | 知识库结构 | INDEX.md + 样例 |
| `competition-entries.md` | 竞赛课题 | 参照 |

### 2.2 不同步（每台机器自己配置）

| 文件 | 原因 |
|------|------|
| `TOOLS.md` | 含 Dify API Key |
| `HEARTBEAT.md` | Cron 调度可能因实例而异 |
| `openclaw.json` | 模型 API Key |
| `agents/*/sessions/*` | 会话历史 |
| `openclaw-workspace-state.json` | 状态文件 |

## 三、新实例部署步骤

### 3.1 前置条件

- 已安装 OpenClaw
- 已配置模型（openclaw.json 中指定可用的 provider/model）

### 3.2 拉取代码

```bash
# 假设新实例的 workspace 目录
cd ~/.openclaw/workspace

# 如果从零开始
git init
git remote add origin <你的仓库地址>
git pull origin main

# 或者如果已有仓库
git pull
```

### 3.3 配置个人文件

复制以下文件并填入自己的值（**不要从别的机器拷贝**）：
- `openclaw.json` — 模型配置（apiKey 每台不同）
- `TOOLS.md` — Dify 配置（如果有线上 Dify 环境）

### 3.4 验证 Skill 生效

```bash
openclaw status
# 或
ls ~/.openclaw/workspace/skills/
```

看到 `tech-research/`、`prd-generator/`、`tech-doc/`、`git-summary/`、`dify-rag/`、`intent-router/` 即生效。

### 3.5 （可选）Dify 联动

如果团队共用 Dify 知识库，在新实例配置：

```bash
export DIFY_API_BASE=https://api.dify.ai
export DIFY_API_KEY=***
export DIFY_DATASET_ID=<共享知识库ID>
```

配置后，新实例即可检索团队共享的全部知识。

## 四、日常协作流程

```
科研/需求/方案 产出
    │
    ├──① Git push  →  Skill 代码演进（团队评审）
    │
    └──② Dify 上传 → 知识内容入库（实时共享）
```

- **Skill 升级**：修改 SKILL.md → git commit → git push → 其他人 git pull
- **知识积累**：调研/PRD/方案产出 → 本地归档 + Dify 上传 → 全体可检索

## 五、常见问题

### Q: 为什么知识内容不走 Git？
A: 知识是持续产生的数据，走 Git 会产生大量 diff 噪音和冲突；Dify RAG 天然适合检索共享知识，且支持向量搜索。

### Q: 新实例需要什么最小配置？
A: 只需 openclaw.json（模型接入）+ 已配置的 skills 目录。知识库内容通过 Dify 按需检索。

### Q: 敏感信息如何保护？
A: .gitignore 已排除 TOOLS.md、openclaw.json 等。务必确认这些文件不在 git 跟踪中。

## 六、相关命令速查

```bash
# 查看当前跟踪的文件
git ls-files

# 添加/移除跟踪
git add <file>
git rm --cached <file>

# 提交推送
git add .
git commit -m "xxx"
git push

# 新实例拉取
git pull
```