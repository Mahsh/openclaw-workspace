# 演示脚本与验证清单

## 一、演示目标

展示"基于 OpenClaw 的云手机研发智能体工作流"从需求到代码的全流程 AI 提效能力。

## 二、演示流程（约 10 分钟）

### 环节 1：技术调研（3 分钟）

**用户输入：**
> "调研一下 WebRTC 在弱网环境下的 QoS 降档方案，要适合云手机场景。"

**预期行为：**
- `tech-research` 触发
- 使用 `web_search` + `web_fetch` 检索资料
- 生成结构化报告并保存到 `memory/research/`
- 更新 `memory/research/INDEX.md`

**展示点：**
- 自动搜索中英文资料
- 结构化输出（背景、方案对比、落地建议）
- 与云手机场景结合

---

### 环节 2：生成 PRD（3 分钟）

**用户输入：**
> "基于刚才的调研，帮我写一份《云手机弱网自适应》的需求文档。"

**预期行为：**
- `prd-generator` 触发
- 检索 `memory/research/` 和 `memory/knowledge-base/` 相关内容
- 生成标准 PRD

**展示点：**
- RAG 检索历史文档保证术语一致
- 标准 PRD 模板输出
- 自动归档

---

### 环节 3：生成技术方案（2 分钟）

**用户输入：**
> "针对这个需求，写一个技术方案，对比一下自研和开源两种方案。"

**预期行为：**
- `tech-doc` 触发
- 生成方案对比表
- 输出 Mermaid 架构图
- 输出评审检查清单

**展示点：**
- 多维度方案对比
- 架构图自动生成
- 评审清单可执行

---

### 环节 4：代码变更总结（2 分钟）

**用户输入：**
> "总结一下 feature/webrtc-qos 分支的改动。"

**预期行为：**
- `git-summary` 触发
- 执行 `git diff` 分析
- 输出影响面分层 + 风险提示

**展示点：**
- Git 集成
- 协议/业务/配置分层识别
- 风险提示

---

## 三、验证清单

| 检查项 | 验证方式 |
|--------|----------|
| Skill 文件存在 | `ls workspace/skills/` |
| PRD 模板可用 | `cat workspace/skills/prd-generator/scripts/prd_template.md` |
| 技术方案模板可用 | `cat workspace/skills/tech-doc/scripts/tech_doc_template.md` |
| Git 总结模板可用 | `cat workspace/skills/git-summary/scripts/summary_template.md` |
| 知识库索引 | `cat workspace/memory/knowledge-base/INDEX.md` |
| 样例文档 | `cat workspace/memory/knowledge-base/samples/prd/*.md` |
| Cron 任务 | 查看 OpenClaw cron 列表 |

## 四、补充材料

- 竞赛主文档：`docs/competition/README.md`
- 架构详解：`docs/competition/architecture.md`
- 心跳调度：`workspace/HEARTBEAT.md`
