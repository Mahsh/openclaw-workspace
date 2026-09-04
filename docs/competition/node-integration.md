# Node 节点集成：云手机真机自动化能力

## 一、设计目标

将云手机实例注册为 OpenClaw Node，实现 Agent 对云手机真机/模拟器环境的直接操作，支持自动化测试、日志采集、性能监控等场景。

## 二、架构

```
┌─────────────┐         ┌─────────────────┐         ┌─────────────┐
│  OpenClaw   │  <--->  │  云手机 Node    │  <--->  │  云手机实例  │
│  Gateway    │         │  (Android/iOS)  │         │             │
└─────────────┘         └─────────────────┘         └─────────────┘
```

## 三、集成方式

### 1. 节点注册

在云手机实例上部署 OpenClaw Node 客户端，通过配对码注册到 Gateway：

```bash
# 在云手机或宿主机上执行
openclaw node pair --gateway <gateway-host>
```

### 2. 能力暴露

Node 暴露以下能力供 Agent 调用：

| 能力 | 工具 | 用途 |
|------|------|------|
| 截图 | `nodes camera_snap` | 查看云手机当前界面 |
| 录屏 | `nodes screen_record` | 录制操作过程 |
| 日志 | `nodes invoke logcat` | 采集 Android logcat |
| 命令执行 | `nodes invoke shell` | 执行 adb/shell 命令 |
| 应用管理 | `nodes invoke pm` | 安装/卸载/启动应用 |

### 3. Agent 调用示例

```
用户：帮我检查云手机安装应用后是否崩溃
Agent：
  1. 调用 nodes invoke shell 查看最近崩溃日志
  2. 调用 nodes camera_snap 截图当前界面
  3. 调用 git-summary 生成变更总结
  4. 综合输出诊断报告
```

## 四、应用场景

| 场景 | 说明 |
|------|------|
| 自动化测试 | Agent 自动在云手机上执行安装、启动、操作、断言 |
| 崩溃分析 | 自动拉取 logcat、 tombstone、截图，定位崩溃原因 |
| 性能监控 | 定时采集 CPU、内存、帧率、延迟数据 |
| 兼容性验证 | 批量在不同云手机型号上执行回归测试 |

## 五、落地计划

1. **节点部署**：在云手机实例/宿主机上部署 OpenClaw Node
2. **能力封装**：将常用操作封装为 Skill（如 `cloud-phone-test`、`cloud-phone-diagnose`）
3. **与研发流集成**：
   - 代码提交后自动触发云手机回归测试
   - 测试失败自动生成诊断报告
   - 报告归档到 `memory/knowledge-base/samples/`

## 六、创新价值

- 从"代码侧 Agent"延伸到"真机侧 Agent"
- 实现研发到测试的端到端自动化
- 云手机作为 OpenClaw Node，充分利用其远程、可控、可扩展特性
