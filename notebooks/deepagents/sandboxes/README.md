# Deep Agents Sandboxes 学习线

这个目录用于学习 Deep Agents 沙盒执行环境。

配套官方文档：

- [Sandboxes](https://docs.langchain.com/oss/python/deepagents/sandboxes)
- [Sandbox integrations](https://docs.langchain.com/oss/python/integrations/sandboxes)
- [Going to production](https://docs.langchain.com/oss/python/deepagents/going-to-production)

## 学习目标

学完这一组 notebook 后，应该能理解并跑通：

1. 什么是 sandbox，以及为什么 agent 需要沙盒隔离。
2. 沙盒的隔离边界能保护什么、不能保护什么。
3. Sandbox as Tool 和 Agent in Sandbox 两种架构模式的区别。
4. 如何使用 `LangSmithSandbox` 创建沙盒 agent。
5. 如何在沙盒中执行命令、传输文件。
6. Thread-scoped 和 assistant-scoped 的生命周期管理。
7. 沙盒环境中的安全注意事项。

## 课时规划

- `001-sandbox-overview.ipynb`：沙盒概念、隔离边界、架构模式、可用 provider。
- `002-sandbox-with-langsmith.ipynb`：使用 LangSmithSandbox 创建 agent，执行命令与文件传输。
- `003-sandbox-lifecycle-and-patterns.ipynb`：生命周期管理、安全实践、生产化考量。

## 当前环境

- 沙盒 provider：LangSmith Sandbox（内置于 `deepagents`）
- 模型网关：支持 OpenAI / Anthropic / Google 等任意 provider
- 框架：`deepagents` + `langchain`

API Key 不要硬编码在 notebook 中，统一从 `.env` 读取。
