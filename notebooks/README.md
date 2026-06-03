# Notebook 学习区

这个目录专门存放你后续学习 AI、OpenAI、Agent 的 `.ipynb` 文件。

推荐命名规则：

- `001-openai-chat-basics.ipynb`
- `002-openai-chat-history.ipynb`
- `003-openai-structured-output.ipynb`
- `004-openai-function-calling.ipynb`
- `005-stock-agent-demo.ipynb`

如果后续开始学 Codex / Skills，也可以单独分目录：

- `codex/001-codex-skill-development.ipynb`
- `codex/002-build-a-minimal-weather-skill.ipynb`
- `codex/003-refactor-a-skill-with-references.ipynb`
- `codex/004-add-a-script-to-a-skill.ipynb`
- `codex/005-wire-a-skill-into-a-mini-workflow.ipynb`
- `codex/006-run-a-full-weather-skill-session.ipynb`
- `codex/007-handle-errors-and-fallbacks-in-a-skill.ipynb`
- `codex/008-implement-a-real-open-meteo-fallback.ipynb`
- `codex/009-validate-a-skill-end-to-end.ipynb`
- `codex/010-final-recap-how-a-skill-grows.ipynb`
- `codex/011-build-a-weather-customer-service-agent.ipynb`

如果开始做智能体实战，可以单独分目录：

- `agent-practice/001-weather-assistant-agent.ipynb`

如果开始学习 Claude Code 这类编码代理的交互模式和工程约束，可以单独分目录：

- `harness-engineering/001-claude-code-harness-engineering.ipynb`
- `harness-engineering/002-streaming-chat-agent-flow.ipynb`

如果开始学习 LangChain，可以单独分目录：

- `langchain/001-langchain-overview-and-agent.ipynb`
- `langchain-Advanced usage/001-guardrails.ipynb`
- `langchain-multi-agent/001-overview.ipynb`

这样做的好处是：

1. 文件顺序清晰
2. 学习路径清晰
3. 后续回顾时容易按阶段查找

---

## 1. 安装 Jupyter Notebook / JupyterLab

建议继续使用当前项目的虚拟环境。

如果你还没有激活虚拟环境：

```bash
source .venv/bin/activate
```

安装 Notebook 学习所需依赖：

```bash
uv pip install --python .venv/bin/python jupyterlab notebook ipykernel openai python-dotenv
```

给当前虚拟环境注册一个 Jupyter Kernel：

```bash
python -m ipykernel install --user --name fastapi-study-venv --display-name "Python (.venv fastapi-study)"
```

---

## 2. 启动方式

推荐启动 JupyterLab：

```bash
jupyter lab
```

如果你更习惯经典界面：

```bash
jupyter notebook
```

启动后，在浏览器中进入本项目目录，打开对应 `.ipynb` 文件即可。

---

## 3. OpenAI 配置

请先在项目根目录 `.env` 中增加：

```env
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-5.4-mini
OPENAI_BASE_URL=
```

说明：

- `OPENAI_API_KEY`：你的 OpenAI API Key
- `OPENAI_MODEL`：默认模型名
- `OPENAI_BASE_URL`：通常留空，只有接代理或兼容网关时再填

不要把真实 API Key 提交到 Git。

如果使用本地私有模型网关，例如：

```env
OPENAI_API_KEY=your-local-key
OPENAI_MODEL=qwq
OPENAI_BASE_URL=http://192.168.102.19:8082/v1
```

需要注意：

- 这个地址是 OpenAI 兼容网关，不是 OpenAI 官方接口
- 当前已验证它支持 `/v1/chat/completions`
- 当前已验证它不支持 `/v1/responses`，会返回 `Internal Server Error`
- 因此第一份 Notebook 会自动切到 `chat.completions.create(...)`

学习时可以先把它理解成：

- OpenAI SDK：客户端工具
- OpenAI 官方 Responses API：较新的官方接口
- OpenAI 兼容网关：可能只支持部分接口，需要按实际能力调整代码

---

## 4. 推荐使用方式

打开 Notebook 后，建议这样学习：

1. 从上到下顺序执行
2. 每执行一格，就观察变量输出
3. 改一改提示词和问题，再重复运行
4. 不要一开始就追求复杂 Agent，先把最简单聊天跑通

---

## 5. 当前第一份 Notebook

第一份学习文件：

- `openai/001-openai-chat-basics.ipynb`

这一份只做一件事：

- 用 OpenAI 官方 Python SDK 跑通最简单的聊天功能

第二份学习文件：

- `openai/002-openai-chat-history.ipynb`

这一份学习：

- 多轮对话
- `messages` 历史
- 最近 N 轮上下文截断
- 私有兼容网关下的上下文维护方式

后续你再继续学习：

1. 结构化输出
2. 函数调用
3. 股票行情智能体

---

## 6. Codex / Skills 学习 Notebook

如果你想进一步理解：

- `Skill`
- `Tool`
- `Skill + Tool` 的分层关系

可以看：

- `codex/001-codex-skill-development.ipynb`
- `codex/002-build-a-minimal-weather-skill.ipynb`
- `codex/003-refactor-a-skill-with-references.ipynb`
- `codex/004-add-a-script-to-a-skill.ipynb`
- `codex/005-wire-a-skill-into-a-mini-workflow.ipynb`
- `codex/006-run-a-full-weather-skill-session.ipynb`
- `codex/007-handle-errors-and-fallbacks-in-a-skill.ipynb`
- `codex/008-implement-a-real-open-meteo-fallback.ipynb`
- `codex/009-validate-a-skill-end-to-end.ipynb`
- `codex/010-final-recap-how-a-skill-grows.ipynb`
- `codex/011-build-a-weather-customer-service-agent.ipynb`

前十份更偏真实 Skill 目录、开发流程和工作流。第十一份开始进入“Skill 如何接入一个业务型 Agent / 客服流程”的主题。

---

## 7. 智能体实战 Notebook

如果你想把前面学过的 OpenAI API、结构化输出、函数调用和 Skill / Tool 分层真正串起来，可以看：

- `agent-practice/001-weather-assistant-agent.ipynb`

这一份会复用仓库已有的 `weather-query-assistant` Skill，并通过独立的 `.agents/tools/weather/fetch_weather.py` 工具脚本，做一个最小天气助手智能体。

重点流程：

1. 用户问题进入智能体
2. 模型识别天气意图并提取地点
3. 应用代码调用天气工具
4. 模型把工具结果整理成中文回答

这条线适合放在 `openai/004-openai-function-calling.ipynb` 和 `openai/005-stock-agent-demo-v1.ipynb` 之后学习。

---

## 8. Harness Engineering / Claude Code 设计学习

如果你想学习 Claude Code 这类交互式编码代理背后的工程设计，可以看：

- `harness-engineering/001-claude-code-harness-engineering.ipynb`
- `harness-engineering/002-streaming-chat-agent-flow.ipynb`

这一份围绕一个核心观点展开：

```text
Prompt 决定模型怎么说话，Harness 决定模型怎么做事。
```

学习重点：

1. 为什么要把模型当成不稳定部件
2. Prompt 为什么是控制面，而不是人格装饰
3. Query Loop 如何成为代理系统的心跳
4. Tool Permission、Context Compact、Recovery Fuse、Independent Verification 如何共同约束模型行为
5. 如何把个人 AI 编码工具升级成团队可复用的工程系统

这一组 Notebook 不依赖 OpenAI API，适合在理解 `codex/001`、`skills_vs_tools_guide.md` 和 `agent-practice/001` 之后学习。

第二份 `002-streaming-chat-agent-flow.ipynb` 会结合当前项目真实实现，解释 `/chat` 页面、`/api/v1/chat-agent/chat/stream`、`HarnessChatAgent.stream_chat(...)`、Skill 选择、Tool 权限裁决、模型规划和 SSE 事件返回的完整流程。

---

## 9. LangChain 学习 Notebook

如果你想学习 LangChain Python v1，可以看：

- `langchain/README.md`
- `langchain/001-langchain-overview-and-agent.ipynb`
- `langchain/002-models-and-messages.ipynb`
- `langchain/003-tools-and-tool-calling.ipynb`
- `langchain/004-structured-output.ipynb`
- `langchain/005-agents-and-control-flow.ipynb`
- `langchain/006-langchain-in-fastapi.ipynb`
- `langchain/007-built-in-middleware.ipynb`
- `langchain/008-built-in-middleware-recipes.ipynb`
- `langchain/009-custom-middleware.ipynb`

这一组 Notebook 会按照官方文档从 `create_agent`、model、tools、messages 开始，而不是一上来直接堆复杂工作流。

第一份 Notebook 会做五件事：

1. 建立 LangChain 的核心心智模型
2. 安装 `langchain` 和 `langchain-openai`
3. 复用项目 `.env` 创建 `ChatOpenAI`
4. 用 `create_agent` 和一个本地 tool 跑通最小 agent
5. 对比 LangChain agent 和本仓库 `HarnessChatAgent` 的职责边界

第二份 Notebook 会做五件事：

1. 认识 LangChain 的 message 类型
2. 看懂 `system` / `user` / `assistant` / `tool` 的上下文表达
3. 了解模型调用前 messages 如何组织
4. 对比本仓库 `history_snapshot` 和 `completed_steps`
5. 为后续 tools 和 structured output 打好基础

第三份 Notebook 会做五件事：

1. 用 `@tool` 定义 LangChain tool
2. 查看 name、description 和 args schema
3. 用 Pydantic 明确工具参数
4. 对比 LangChain tool 和本仓库 `ToolDefinition`
5. 解释为什么 tool calling 仍然需要权限、审批和恢复机制

第四份 Notebook 会做五件事：

1. 解释 prompt-only JSON 为什么脆弱
2. 用 Pydantic 定义 planner decision schema
3. 本地验证结构化数据
4. 学习 LangChain `response_format`
5. 对比 structured output 和本仓库 planner action

第五份 Notebook 会做五件事：

1. 理解 LangChain agent 是循环，不是一次模型调用
2. 用普通 Python 模拟 ReAct 控制流
3. 创建一个可选运行的 LangChain agent
4. 对比 LangChain agent 和本仓库 Harness Query Loop
5. 判断哪些控制面仍然要留在应用层

第六份 Notebook 会做五件事：

1. 设计 LangChain 接入 FastAPI 的分层方式
2. 区分 `invoke`、`ainvoke`、`stream`、`astream`
3. 写一个最小 Service 封装
4. 讨论如何适配 SSE 和现有页面
5. 明确不要直接绕过 Harness 权限审批边界

第七份 Notebook 会做五件事：

1. 学习 LangChain built-in middleware
2. 对比 middleware 和 Java Filter / Interceptor
3. 认识 context、HITL、limit、retry、fallback、PII、tool selection、filesystem、shell 等控制面
4. 映射到本仓库 Harness 的 ledger、approval、permission、context compact、recovery
5. 判断哪些 middleware 可以复用，哪些必须保留业务兜底

第八份 Notebook 会做五件事：

1. 逐个查看 built-in middleware 的最小用法
2. 用 `FakeListChatModel` 避免真实模型调用
3. 区分本地 LangChain 可运行类和 Deep Agents 扩展类
4. 接入当前 `.env` 真实模型配置，运行一个低风险 middleware agent demo
5. 对比 Filesystem、Shell、SubAgent 等能力和本仓库 approval / allowed_paths 的关系
6. 给出直接接入、业务兜底和暂不接入的判断口径

第九份 Notebook 会做五件事：

1. 学习 custom middleware 的 decorator 写法和 class 写法
2. 理解 node-style hook 和 wrap-style hook 的差异
3. 用 fake model 跑通模型调用拦截、工具调用拦截和自定义 state
4. 学习 `can_jump_to` / `jump_to` 如何提前结束 agent
5. 映射到本仓库 Harness 的 ledger、approval、context compact、recovery

推荐学习顺序：

```text
openai/001-005
  -> agent-practice/001
  -> harness-engineering/001-002
  -> langchain/001-009
  -> langchain-Advanced usage/001-004
  -> langchain-multi-agent/001-006
```

---

## 10. LangChain Advanced Usage 学习 Notebook

如果你想学习更接近生产系统的 LangChain 高级能力，可以看：

- `langchain-Advanced usage/README.md`
- `langchain-Advanced usage/001-guardrails.ipynb`
- `langchain-Advanced usage/002-runtime.ipynb`
- `langchain-Advanced usage/003-context-engineering.ipynb`
- `langchain-Advanced usage/004-human-in-the-loop.ipynb`

这一组 Notebook 会放在基础 LangChain 学习之后，重点不再是“API 怎么调”，而是“系统边界怎么设计”。

第一份 Advanced usage Notebook 会做五件事：

1. 理解 guardrails 是 agent 的运行时安全边界
2. 学习 `PIIMiddleware` 和 `HumanInTheLoopMiddleware`
3. 学习输入 guardrail、输出 guardrail、工具 guardrail
4. 用 fake model 跑通安全拦截，不执行危险工具
5. 对比本仓库 Harness 的 approval、allowed_paths、ledger、verification

第二份 Advanced usage Notebook 会做五件事：

1. 理解 Runtime 是 agent 执行时的运行时对象
2. 区分 `messages`、`state`、`context`、`store`
3. 学会在 tool 中读取 `ToolRuntime.context`
4. 学会用 `ToolRuntime.store` 和 `ToolRuntime.stream_writer`
5. 接入当前 `.env` 的真实模型配置运行 Runtime 示例
6. 对比本仓库 Harness 的 session、ledger、memory、SSE 事件

第三份 Advanced usage Notebook 会做五件事：

1. 理解 context engineering 不是“把所有东西塞进 prompt”
2. 区分 model context、tool context、life-cycle context
3. 学习动态 prompt、临时上下文注入和工具可见性裁剪
4. 用 `ToolRuntime.store` 演示长期上下文
5. 对比本仓库 Harness 的 context budget、ledger、subagent synthesis

第四份 Advanced usage Notebook 会做五件事：

1. 理解 human-in-the-loop 是高风险工具审批机制
2. 学会使用 `HumanInTheLoopMiddleware`
3. 理解 checkpointer 和 `thread_id` 为什么是恢复任务的关键
4. 跑通 approve / reject / edit 三种审批决策
5. 对比本仓库 Harness 的 `approval_required` 和 `stream_resume_approval`

---

## 11. LangChain Multi-agent 学习 Notebook

如果你想学习 LangChain 多智能体设计，可以看：

- `langchain-multi-agent/README.md`
- `langchain-multi-agent/001-overview.ipynb`
- `langchain-multi-agent/002-subagents-handoffs.ipynb`
- `langchain-multi-agent/003-handoffs.ipynb`
- `langchain-multi-agent/004-skills.ipynb`
- `langchain-multi-agent/005-router.ipynb`
- `langchain-multi-agent/006-custom-workflow.ipynb`

这一组 Notebook 按当前学习节奏推进：

1. Overview
2. SubagentsHandoffs
3. Handoffs
4. Skills
5. Router
6. Custom workflow

第一份 Multi-agent Notebook 会做五件事：

1. 理解 multi-agent 解决的是上下文、职责和控制流问题
2. 认识 Subagents、Handoffs、Skills、Router、Custom workflow 五种模式
3. 判断什么时候不需要多智能体
4. 用控制权、上下文隔离、成本和验证来选择模式
5. 对比本仓库 Harness 多智能体设计里的 coordinator、subagent、verification

第二份 Multi-agent Notebook 会做五件事：

1. 理解 supervisor 通过 tools 调用 subagent
2. 跑通 tool-per-agent 的最小实现
3. 理解 subagent 默认无状态和上下文隔离
4. 学习 single dispatch tool 和 enum constraint
5. 对比 subagent 和 handoff 的控制权差异

第三份 Multi-agent Notebook 会做五件事：

1. 理解 handoff 是 active agent / active step 的控制权转移
2. 区分 handoff 和 subagent-as-tool
3. 学会用 state 记录当前 step
4. 学会用 `Command(update=...)` 触发 handoff
5. 学会用 middleware 根据当前 step 动态切换 prompt 和 tools

第四份 Multi-agent Notebook 会做五件事：

1. 理解 Skill 是按需加载的专业能力包，不只是 prompt 模板
2. 区分 Skill、Tool、Subagent、Handoff 的边界
3. 学会用 registry 表达 Skill 元数据和触发条件
4. 学会用 middleware 根据用户意图加载 Skill 指令和工具
5. 对比本仓库 `.agents/skills` 的真实 Skill 目录设计

第五份 Multi-agent Notebook 会做五件事：

1. 理解 router 是分类和分发步骤，不是持续编排器
2. 区分 deterministic routing 和 model routing
3. 学会用 `Command(goto=...)` 表达单目标路由
4. 学会用 `Send(...)` 表达多目标 fan-out
5. 对比本仓库 Harness 的 planner action 路由

第六份 Multi-agent Notebook 会做五件事：

1. 理解 custom workflow 是显式控制流，不是自由 agent 循环
2. 学会用 LangGraph `StateGraph` 定义稳定流程
3. 学会把 research、implementation、verification、synthesis 分成节点
4. 学会用条件边决定是否进入工程工作流
5. 对比本仓库 Harness Query Loop 和 LangGraph workflow
