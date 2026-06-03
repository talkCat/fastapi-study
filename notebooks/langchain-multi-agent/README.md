# LangChain Multi-agent 学习计划

这个目录用于学习 LangChain 的多智能体设计。

学习重点不是“多开几个 agent”，而是理解：

- 什么时候单 agent 已经足够
- 什么时候需要拆分上下文和职责
- 不同多智能体模式的控制权在哪里
- 如何在成本、延迟、可靠性和可维护性之间取舍

## 学习顺序

### 001 Overview

文件：

- `001-overview.ipynb`

目标：

1. 理解 multi-agent 解决的是上下文、职责和控制流问题
2. 认识 Subagents、Handoffs、Skills、Router、Custom workflow 五种模式
3. 学会判断什么时候不需要多智能体
4. 学会根据控制权、上下文隔离和成本选择模式
5. 对比本仓库 Harness 多智能体设计里的 coordinator、subagent、verification

### 002 SubagentsHandoffs

文件：

- `002-subagents-handoffs.ipynb`

目标：

1. 理解 supervisor 通过 tools 调用 subagent
2. 跑通 tool-per-agent 的最小实现
3. 理解 subagent 默认无状态和上下文隔离
4. 学习 single dispatch tool 和 enum constraint
5. 区分 sync / async subagent 执行取舍
6. 对比 subagent 和 handoff 的控制权差异

### 003 Handoffs

文件：

- `003-handoffs.ipynb`

目标：

1. 理解 handoff 是 active agent / active step 的控制权转移
2. 区分 handoff 和 subagent-as-tool
3. 学会用 state 记录当前 step
4. 学会用 `Command(update=...)` 触发 handoff
5. 学会用 middleware 根据当前 step 动态切换 prompt 和 tools
6. 理解为什么 handoff 通常需要 checkpointer

### 004 Skills

文件：

- `004-skills.ipynb`

目标：

1. 理解 Skill 是按需加载的专业能力包，不只是 prompt 模板
2. 区分 Skill、Tool、Subagent、Handoff 的边界
3. 学会用 registry 表达 Skill 元数据和触发条件
4. 学会用 middleware 根据用户意图加载 Skill 指令和工具
5. 对比本仓库 `.agents/skills` 的真实 Skill 目录设计

### 005 Router

文件：

- `005-router.ipynb`

目标：

1. 理解 router 是分类和分发步骤，不是持续编排器
2. 区分 deterministic routing 和 model routing
3. 学会用 `Command(goto=...)` 表达单目标路由
4. 学会用 `Send(...)` 表达多目标 fan-out
5. 对比本仓库 Harness 的 planner action 路由

### 006 Custom workflow

文件：

- `006-custom-workflow.ipynb`

目标：

1. 理解 custom workflow 是显式控制流，不是自由 agent 循环
2. 学会用 LangGraph `StateGraph` 定义稳定流程
3. 学会把 research、implementation、verification、synthesis 分成节点
4. 学会用条件边决定是否进入工程工作流
5. 对比本仓库 Harness Query Loop 和 LangGraph workflow

## 学习原则

1. 先判断是否真的需要多智能体，再选择模式。
2. 多智能体的关键是分工、隔离、验证和综合，不是并发数量。
3. 不把第三方 MCP / tool 原始能力无脑暴露给模型。
4. 每个模式都要回答：谁控制下一步，谁持有上下文，谁负责最终综合。
