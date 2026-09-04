# 云手机研发知识库

本知识库面向"基于 OpenClaw 的云手机研发智能体工作流"，沉淀协议、架构、历史方案等核心资料，供 RAG 检索和 Agent 调用。

## 目录结构

```
memory/knowledge-base/
├── cloud-phone/          # 云手机领域知识
│   ├── protocols/        # 协议文档
│   ├── architecture/       # 架构文档
│   └── history/            # 历史方案
├── samples/              # 样例输出
│   ├── prd/                # PRD 样例
│   ├── tech-docs/          # 技术方案样例
│   └── git-summaries/        # 变更总结样例
└── INDEX.md              # 全局索引
```

## 核心主题

- 云手机音视频传输（WebRTC、低延迟编码、QoS）
- 云手机虚拟化与容器化
- 云手机协议与信令
- 云手机应用生态（云OS、APK 管理、应用分发）

## 使用方式

各 Skill 通过 `memory_search` 检索本知识库，确保输出与云手机现有规范一致。
