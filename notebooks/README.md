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
