# LangChain 学习计划

这一组 Notebook 用来学习 LangChain Python v1 的核心用法。

官方入口：

- https://docs.langchain.com/oss/python/langchain/overview

学习目标不是一开始堆复杂 Agent，而是把 LangChain 的抽象和本仓库已经实现的 Harness 智能体对齐起来：

```text
LangChain agent / model / tool / messages
  对照
本仓库 HarnessChatAgent / ModelClient / ToolRegistry / ledger + completed_steps
```

## 学习顺序

### 001 LangChain Overview And Agent

文件：

- `001-langchain-overview-and-agent.ipynb`

目标：

1. 理解 LangChain 解决的问题
2. 安装 `langchain`、`langchain-openai`
3. 用 `create_agent` 创建第一个 agent
4. 理解 model、tools、system_prompt、messages 的关系
5. 对比本仓库 Harness runtime 的 planner、tool、subagent、ledger

### 002 Models And Messages

后续文件：

- `002-models-and-messages.ipynb`

目标：

1. 学习 LangChain 的模型统一接口
2. 理解 message list 和多轮上下文
3. 对比 OpenAI 原生 `messages`
4. 解释为什么上下文仍然需要裁剪和治理
5. 让消息结构和本仓库 `history_snapshot / completed_steps` 对齐

### 003 Tools And Tool Calling

后续文件：

- `003-tools-and-tool-calling.ipynb`

目标：

1. 学习 LangChain tool 的定义方式
2. 理解工具 schema、docstring 和参数
3. 把本仓库 weather/fund 工具思想映射到 LangChain tool
4. 区分工具声明、工具选择和工具执行权限
5. 对比 LangChain `@tool` 和本仓库 `ToolDefinition`

### 004 Structured Output

后续文件：

- `004-structured-output.ipynb`

目标：

1. 学习 LangChain 结构化输出
2. 用 Pydantic 定义稳定输出
3. 对比本仓库 planner action 的 `answer/tool/delegate/delegate_batch`
4. 解释为什么结构化输出比“提示模型返回 JSON”更可靠
5. 理解 `response_format`、ProviderStrategy 和 ToolStrategy 的差异

### 005 Agents And Control Flow

后续文件：

- `005-agents-and-control-flow.ipynb`

目标：

1. 学习 LangChain agent 的运行循环
2. 理解 agent 何时调用工具、何时回答
3. 对比本仓库 Harness Query Loop
4. 解释 LangChain agent 和自研 Harness 的边界差异
5. 判断哪些控制面仍然应该留在应用层

### 006 LangChain In FastAPI

后续文件：

- `006-langchain-in-fastapi.ipynb`

目标：

1. 把 LangChain agent 接入 FastAPI service
2. 讨论同步、异步和流式返回
3. 加入最小权限控制和错误处理
4. 判断什么时候该复用 LangChain，什么时候该保留自研 Harness
5. 设计新增教学 endpoint 的最小落地路线

### 007 Built-in Middleware

文件：

- `007-built-in-middleware.ipynb`

目标：

1. 学习 LangChain built-in middleware 的控制面能力
2. 认识 Summarization、HumanInTheLoop、CallLimit、Retry、Fallback、PII、ToolSelector、Filesystem、Shell 等 middleware
3. 对比本仓库 Harness 的 context compact、approval、max_steps、permission、ledger、recovery
4. 判断哪些 middleware 可以复用，哪些必须由业务系统兜底
5. 为后续接入 `/langchain-study` 教学 endpoint 做设计准备

### 008 Built-in Middleware Recipes

文件：

- `008-built-in-middleware-recipes.ipynb`

目标：

1. 逐个学习 LangChain built-in middleware 的最小用法
2. 为每种 middleware 提供可读的学习样例
3. 区分本地 `langchain==1.3.1` 可直接运行的 middleware 和 Deep Agents 扩展 middleware
4. 对比 Summarization、HITL、Retry、Fallback、PII、Filesystem、Shell、SubAgent 等能力和本仓库 Harness runtime 的关系
5. 接入当前 `.env` 里的真实模型配置，运行一个低风险 middleware agent demo
6. 形成“哪些可以直接接入，哪些必须由业务 approval / allowed_paths / audit 兜底”的判断标准

### 009 Custom Middleware

文件：

- `009-custom-middleware.ipynb`

目标：

1. 学习 LangChain custom middleware 的 decorator 写法和 class 写法
2. 理解 `before_agent`、`before_model`、`after_model`、`after_agent` 的触发时机
3. 理解 `wrap_model_call` 和 `wrap_tool_call` 为什么适合做恢复、fallback、权限和审计
4. 学会给 middleware 增加自定义 state schema
5. 理解 `can_jump_to` / `jump_to` 这种强控制能力
6. 对比本仓库 Harness 的 ledger、approval、context compact、recovery 应该如何映射到 middleware

## 学习原则

1. 先跑通最小例子，再加工具和结构化输出。
2. 不把 LangChain 当黑盒，要看它和本仓库 Harness runtime 的职责差异。
3. 不把 agent 等同于“会聊天的模型”，重点看工具、状态、上下文和控制流。
4. 不急着迁移现有代码，先通过 notebook 建立判断标准。
