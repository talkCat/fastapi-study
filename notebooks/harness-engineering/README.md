# Harness Engineering 教学区

这个目录用于学习 Claude Code 这类交互式编码代理背后的工程设计方法。

核心主题：

- 模型本身不可靠，可靠性来自持续生效的约束框架
- Prompt 决定模型怎么表达，Harness 决定模型怎么行动
- 编码代理不是聊天机器人加工具，而是一套可中断、可恢复、可解释、可审计的执行系统

当前学习顺序：

1. `001-claude-code-harness-engineering.ipynb`
   - 理解 Harness Engineering 的核心定位
   - 学习九大设计原则
   - 用小型 Python 示例模拟 Prompt 拼装、权限裁决、上下文预算、错误恢复和独立验证

这组 Notebook 不依赖 OpenAI API。重点是从工程结构上理解“如何约束一个能改代码、能跑命令、能持续工作的 AI 编码代理”。

