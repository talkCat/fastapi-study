# LangChain Advanced Usage 学习计划

这个目录用于学习 LangChain 的高级用法。

它和 `notebooks/langchain/` 的区别：

- `notebooks/langchain/`：先学习 LangChain 基础抽象，例如 model、messages、tools、agent、middleware
- `notebooks/langchain-Advanced usage/`：学习更接近生产系统的能力，例如 guardrails、human-in-the-loop、长期记忆、MCP、多代理等

## 学习顺序

### 001 Guardrails

文件：

- `001-guardrails.ipynb`

目标：

1. 理解 guardrails 是 agent 的运行时安全边界
2. 学习 `PIIMiddleware` 和 `HumanInTheLoopMiddleware`
3. 学习 before-agent 输入拦截
4. 学习 after-agent 输出拦截
5. 学习 wrap-tool-call 工具拦截
6. 学习多个 guardrails 如何组合
7. 对比本仓库 Harness 的 approval、allowed_paths、ledger、verification

### 002 Runtime

文件：

- `002-runtime.ipynb`

目标：

1. 理解 Runtime 是 agent 本轮执行时的运行时对象
2. 区分 `messages`、`state`、`context`、`store`
3. 学会在 tool 中读取 `ToolRuntime.context`
4. 学会用 `ToolRuntime.store` 做跨轮持久记忆
5. 学会用 `ToolRuntime.stream_writer` 发送自定义流事件
6. 学会在 middleware / dynamic prompt 中读取 runtime
7. 接入当前 `.env` 的真实模型配置运行 Runtime 示例
8. 对比本仓库 Harness 的 session、ledger、memory、SSE 事件

### 003 Context Engineering

文件：

- `003-context-engineering.ipynb`

目标：

1. 理解 context engineering 不是“把所有东西塞进 prompt”
2. 区分 model context、tool context、life-cycle context
3. 学会用 `dynamic_prompt` 根据 runtime 生成 prompt
4. 学会用 `wrap_model_call` 临时注入模型上下文
5. 学会用 `ToolRuntime.store` 让工具读写长期上下文
6. 学会按权限裁剪模型可见工具
7. 对比本仓库 Harness 的 context budget、ledger、subagent synthesis

### 004 Human-in-the-loop

文件：

- `004-human-in-the-loop.ipynb`

目标：

1. 理解 human-in-the-loop 解决的是高风险动作审批问题
2. 学会使用 `HumanInTheLoopMiddleware`
3. 理解为什么 HITL 必须配合 checkpointer
4. 跑通 approve / reject / edit 三种恢复决策
5. 理解 thread_id 如何让暂停任务可恢复
6. 对比本仓库 Harness 的 `approval_required` 和 `stream_resume_approval`

## 学习原则

1. 高级用法必须和工程边界一起学，不能只看 API。
2. 危险工具只做模拟，不在 Notebook 中自动执行。
3. 涉及真实模型的课时必须显式读取 `.env`，不要在 Notebook 中硬编码密钥。
4. 每个高级能力都要回答：它解决什么风险，它不能替代什么业务规则。
