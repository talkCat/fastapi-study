# 智能体实战 Notebook

这个目录用于把前面学过的 OpenAI API、结构化输出、函数调用、Skill / Tool 分层知识，组合成更接近真实业务的小型智能体。

当前学习顺序：

1. `001-weather-assistant-agent.ipynb`
   - 使用已有 `weather-query-assistant` Skill
   - 使用独立的 `.agents/tools/weather/` 天气查询工具
   - 实现一个最小天气助手智能体

这一组 Notebook 的重点不是引入复杂框架，而是先把最小闭环跑通：

```text
用户问题
  -> 意图识别
  -> 工具调用
  -> 工具结果整理
  -> 自然语言回答
```
