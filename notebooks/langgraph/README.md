# LangGraph 学习计划

这个目录用于学习 LangGraph。

学习重点不是“再学一个 agent 框架”，而是理解：

- 为什么复杂 agent 需要显式状态
- 为什么流程需要节点、边和检查点
- LangGraph 和 LangChain agent 的关系
- 如何把普通 Python 函数、模型调用、工具调用、人类审批组合成稳定图结构

## 学习顺序

### 001 Overview

文件：

- `001-overview.ipynb`

目标：

1. 理解 LangGraph 是低层 orchestration runtime
2. 区分 state、node、edge、graph、compiled graph
3. 跑通 `StateGraph(MessagesState)` 最小示例
4. 跑通自定义 `TypedDict` state 示例
5. 对比 LangGraph workflow、本仓库 Harness Query Loop、LangChain agent

### 002 Quickstart

文件：

- `002-quickstart.ipynb`

目标：

1. 跑通一个最小 calculator agent graph
2. 理解 tools、model node、tool node、conditional edge 的关系
3. 理解 `Annotated[list[AnyMessage], operator.add]` 为什么能追加消息
4. 学会用 `should_continue` 控制 agent loop 是否继续
5. 对比 Quickstart 的真实模型版本和本课 fake model 版本

### 003 Thinking in LangGraph

文件：

- `003-thinking-in-langgraph.ipynb`

目标：

1. 理解 Thinking in LangGraph 是设计方法，不只是 API 教程
2. 学会把业务流程拆成 node
3. 学会区分 LLM node、data node、action node、human input node
4. 学会设计只保存原始数据和关键决策的 state
5. 用 `Command(update=..., goto=...)` 跑通一个客服邮件 workflow

### 004 Workflows and Agents

文件：

- `004-workflows-agents.ipynb`

目标：

1. 区分 workflow 和 agent 的控制权差异
2. 理解 prompt chaining、routing、parallelization、orchestrator-worker、evaluator-optimizer 等 workflow 模式
3. 跑通一个 evaluator-optimizer workflow
4. 跑通一个动态选择工具的 agent loop
5. 判断什么时候应该用 workflow，什么时候应该用 agent

### 005 Persistence

文件：

- `005-persistence.ipynb`

目标：

1. 理解 persistence 为什么是 LangGraph 的核心能力
2. 理解 thread、checkpoint、state snapshot 的关系
3. 学会用 `InMemorySaver` 保存 graph 执行状态
4. 学会使用 `get_state`、`get_state_history`、`update_state`
5. 对比 LangGraph checkpoint 和本仓库 Harness approval run state

### 006 Fault Tolerance

文件：

- `006-fault-tolerance.ipynb`

目标：

1. 理解 fault tolerance 为什么是长运行 agent 的核心能力
2. 学会用 `RetryPolicy` 处理临时错误
3. 学会用 checkpoint 在节点失败后查看状态
4. 学会从失败节点继续执行 graph
5. 理解重试和外部副作用之间的幂等性风险

### 007 Event Streaming

文件：

- `007-event-streaming.ipynb`

目标：

1. 理解 event streaming 为什么是 agent UI 和服务端观察性的核心能力
2. 学会使用 `.stream(..., stream_mode="updates")`
3. 学会使用 `.stream(..., stream_mode="values")`
4. 学会使用 `.stream(..., stream_mode="debug")`
5. 了解 `astream_events(...)` 的事件结构，并对比本仓库 Harness SSE
6. 理解官方新版 `stream_events(..., version="v3")` 的 typed projections 设计

### 008 Streaming

文件：

- `008-streaming.ipynb`

目标：

1. 区分 event streaming 和 stream-mode API
2. 理解 `version="v2"` 的统一 `StreamPart` 格式
3. 学会同时消费 `updates`、`values`、`custom` 等 stream modes
4. 用 fake chat model 跑通 `messages` token streaming
5. 理解 `tasks`、`checkpoints`、`debug` 适合什么场景
6. 判断哪些内部事件适合转换成前端 SSE 业务事件

### 009 Interrupts

文件：

- `009-interrupts.ipynb`

目标：

1. 理解 `interrupt()` 为什么必须配合 checkpointer 和 `thread_id`
2. 学会从 `__interrupt__` 中读取暂停请求
3. 学会用 `Command(resume=...)` 恢复同一个 graph thread
4. 跑通审批、拒绝、人工编辑、输入校验四种 human-in-the-loop 模式
5. 理解节点恢复时会从节点开头重新执行的副作用风险
6. 学会把 interrupt 映射成 Harness 风格审批事件

### 010 Time Travel

文件：

- `010-time-travel.ipynb`

目标：

1. 理解 time travel 依赖 checkpoint history
2. 学会用 `get_state_history(...)` 找到历史 checkpoint
3. 学会用 `invoke(None, checkpoint.config)` replay 后续节点
4. 学会用 `update_state(...)` 从旧 checkpoint fork 新分支
5. 理解 replay 会重新触发 LLM、API、interrupt 等后续节点副作用
6. 对比 time travel 和本仓库 Harness ledger / approval resume

### 011 Memory

文件：

- `011-memory.ipynb`

目标：

1. 区分 short-term memory 和 long-term memory
2. 学会用 checkpointer 保存同一个 `thread_id` 的短期对话状态
3. 学会用 store 保存跨 thread 的长期用户记忆
4. 理解 `thread_id` 和 `user_id` 的区别
5. 理解长对话为什么需要 trim / delete / summarize
6. 对比 LangGraph memory 和本仓库 Harness 上下文/记忆设计

### 012 Subgraphs

文件：

- `012-subgraphs.ipynb`

目标：

1. 理解 subgraph 是把一个 graph 当作另一个 graph 的节点
2. 学会在父子 state schema 不同时用 wrapper node 调用子图
3. 学会在父子共享 state key 时把 compiled subgraph 直接 add_node
4. 学会用 `subgraphs=True` 观察子图 stream namespace
5. 理解子图 checkpointer 的 per-invocation / per-thread / stateless 模式
6. 跑通子图里的 interrupt 和状态查看

### 013 Serving and Adapters

文件：

- `013-serving-adapters.ipynb`

目标：

1. 理解 LangGraph 图本身不是 HTTP 接口，`CompiledStateGraph` 需要被 Web 层适配后才能给前端或业务系统调用
2. 学会把 FastAPI 请求转换成 LangGraph 的 `input`、`config`、`context`
3. 理解 `session_id` 和 `thread_id` 的映射关系，以及它们如何影响 checkpointer 读取历史状态
4. 学会消费 `agent.astream(...)` 的 `messages`、`updates`、`custom` 等 stream mode
5. 学会把 LangGraph 内部事件转换成前端 SSE 业务事件，例如 `token`、`tool_calls`、`tool_output`、`quick_entries`
6. 理解 `Command(resume=...)` 如何把 HTTP 请求映射成 LangGraph interrupt 恢复
7. 区分图编排逻辑、Web 适配逻辑、业务事件协议、可观测性埋点的边界
8. 对比本仓库 `hb_rs/endpoint.py`：为什么它不是图定义文件，而是 LangGraph Web 适配层

## 学习原则

1. 先看清状态如何流动，再讨论复杂 agent。
2. 先写普通 Python 节点，再把节点替换成模型或 agent。
3. 每个图都要明确：状态字段、节点职责、边的条件、停止条件。
4. 不把 LangGraph 理解成“自动更聪明”，它的价值是让控制流更清楚、可恢复、可验证。
