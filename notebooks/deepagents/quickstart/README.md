# Deep Agents 快速入门

这个目录用于学习 LangChain Deep Agents 框架。

配套官方文档：

- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [Quickstart](https://docs.langchain.com/oss/python/deepagents/quickstart)
- [Customization](https://docs.langchain.com/oss/python/deepagents/customization)
- [Harness](https://docs.langchain.com/oss/python/deepagents/harness)

## 学习目标

学完这一组 notebook 后，应该能理解并跑通：

1. Deep Agents 是什么，以及它能解决什么问题。
2. 如何安装依赖和配置 API Key。
3. 如何创建 search tool 并接入 agent。
4. 如何使用 `create_deep_agent` 创建 agent。
5. 如何运行 agent 并观察其规划、工具调用、子代理委派过程。
6. 如何流式输出 agent 的执行过程。

## 课时规划

- `001-deep-agents-overview.ipynb`：整体架构、Deep Agents 能做什么、核心概念。
- `002-create-search-tool.ipynb`：创建 Tavily 搜索工具。
- `003-create-deep-agent.ipynb`：使用 `create_deep_agent` 创建 agent。
- `004-run-agent.ipynb`：运行 agent 并观察执行过程。
- `005-streaming-agent.ipynb`：流式输出 agent 执行事件。

## 当前环境

使用这些服务：

- 模型网关：支持 OpenAI / Anthropic / Google 等任意 provider
- 搜索工具：Tavily Search API
- 框架：`deepagents` + `langchain`

API Key 不要硬编码在 notebook 中，统一从 `.env` 读取。
