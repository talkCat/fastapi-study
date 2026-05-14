# OpenAI 聊天与股票智能体学习计划

这份计划专门写给有 Java 背景、正在学习 Python 和 FastAPI 的开发者。

目标很明确：

1. 先在当前项目中接入 OpenAI，跑通最简单的聊天接口
2. 再逐步升级到结构化输出、函数调用
3. 最后做一个股票行情智能体 demo

这份计划不是泛泛而谈，而是基于你当前这个项目的分层结构来设计：

- `router`
- `service`
- `schema`
- 统一返回体 `ApiResponse<T>`
- FastAPI 接口测试

---

## 0. OpenAI 官方文档入口

后续教学模块会用到下面这些官方文档：

| 学习内容 | 官方文档 |
|------|------|
| OpenAI Python SDK 快速开始 | https://developers.openai.com/api/docs/quickstart |
| Responses API | https://platform.openai.com/docs/api-reference/responses |
| Chat Completions API | https://platform.openai.com/docs/api-reference/chat |
| Conversation state / 多轮对话 | https://developers.openai.com/api/docs/guides/conversation-state |
| Structured Outputs / 结构化输出 | https://developers.openai.com/api/docs/guides/structured-outputs |
| Function Calling / 工具调用 | https://developers.openai.com/api/docs/guides/function-calling |
| OpenAI Models | https://developers.openai.com/api/docs/models |
| OpenAI Agents SDK | https://openai.github.io/openai-agents-python/quickstart/ |

当前 Notebook 教学模块：

- `notebooks/openai/001-openai-chat-basics.ipynb`
- `notebooks/openai/002-openai-chat-history.ipynb`
- `notebooks/openai/003-openai-structured-output.ipynb`
- `notebooks/openai/004-openai-function-calling.ipynb`
- `notebooks/openai/005-stock-agent-demo-v1.ipynb`
- `notebooks/agent-practice/001-weather-assistant-agent.ipynb`

这份 Notebook 同时兼容两种模式：

- OpenAI 官方接口：优先学习 `Responses API`
- 本地私有兼容网关：使用 `Chat Completions API`

你当前本地配置是：

```env
OPENAI_MODEL=qwq
OPENAI_BASE_URL=http://192.168.102.19:8082/v1
```

已验证该私有网关：

- 支持 `/v1/chat/completions`
- 不支持 `/v1/responses`

所以当前 Notebook 会自动选择 `chat.completions.create(...)`。

---

## 1. 最终推荐路线

结合当前项目现状，我的最终建议是：

1. 第一阶段先学 `OpenAI Python SDK + Responses API`
2. 第二阶段再学 `Structured Outputs`
3. 第三阶段再学 `Function Calling`
4. 第四阶段做单 Agent 的股票助手
5. 第五阶段做天气助手这种更贴近业务工具复用的智能体实战
6. 第六阶段再评估 `OpenAI Agents SDK`
7. `LangChain` 放到第二阶段之后再接触
8. `LangGraph` 只在复杂长流程场景再引入

核心原因：

- 你现在最需要先看懂“怎么接 OpenAI”
- 而不是一上来就学一个很厚的 Agent 框架
- 先把官方 SDK 跑通，后面再学框架会更轻松

可以把它理解成：

- 第一阶段：先学 JDBC / HTTP Client
- 第二阶段：再学更高级的框架封装

---

## 2. 为什么不建议一开始就上 LangChain

`LangChain` 是值得学的，但不适合你当前作为第一步。

原因有 3 个：

### 原因 1：会掩盖底层调用过程

如果你一上来就用 LangChain，很容易只会“拼框架”，但没真正理解：

- 请求是怎么发给模型的
- 多轮上下文是怎么传的
- 工具调用的本质是什么
- 结构化输出到底是模型能力还是框架能力

### 原因 2：你当前项目已经有自己的分层

你这个仓库已经有：

- `router -> service -> repository`
- `schema`
- 统一返回体

所以最合理的学习方式是：

- 先把 OpenAI 当成一个外部 SDK 接进现有 service 层

而不是先把整个系统改造成某个 Agent 框架范式。

### 原因 3：股票智能体的第一版不需要复杂编排

股票行情智能体 demo 的第一版，通常只需要：

1. 用户提问
2. 模型识别意图
3. 调用行情工具
4. 组织回答

这一步用官方 SDK 就完全够了。

---

## 3. 推荐学习框架选择

### 第一阶段主线

推荐：

- `OpenAI Python SDK`
- `Responses API`

官方文档：

- OpenAI Python SDK 快速开始：https://developers.openai.com/api/docs/quickstart
- Responses API：https://platform.openai.com/docs/api-reference/responses
- Chat Completions API：https://platform.openai.com/docs/api-reference/chat

作用：

- 做最简单的聊天
- 学对话状态
- 学结构化输出
- 学函数调用

这是你当前阶段的主线。

### 第二阶段补充

推荐：

- `OpenAI Agents SDK`

官方文档：

- OpenAI Agents SDK Quickstart：https://openai.github.io/openai-agents-python/quickstart/

适合场景：

- 一个 Agent 使用多个工具
- 需要 handoff
- 需要 trace
- 需要更标准的 agent 编排

### 第三阶段可选

推荐：

- `LangChain`

适合场景：

- 想同时兼容多个模型供应商
- 想快速试验 agent 模板
- 想使用生态里的记忆、检索、工具封装

但是它不建议作为第一个 OpenAI 接入方案。

### 更复杂流程时再考虑

推荐：

- `LangGraph`

适合场景：

- 长流程
- 多阶段状态流转
- 可恢复执行
- 多 Agent 工作流
- Human-in-the-loop

---

## 4. 学习总阶段图

```text
阶段 1：官方 SDK 简单聊天
    ↓
阶段 2：多轮对话与会话状态
    ↓
阶段 3：结构化输出
    ↓
阶段 4：函数调用
    ↓
阶段 5：股票行情智能体 Demo v1
    ↓
阶段 6：天气助手智能体实战
    ↓
阶段 7：OpenAI Agents SDK / LangChain
    ↓
阶段 8：LangGraph（只在复杂工作流时）
```

---

## 5. 分阶段学习计划

## 阶段 0：准备阶段

目标：

- 把当前项目环境准备好
- 理解后续代码放在哪里

需要完成：

1. 准备 OpenAI API Key
2. 在 `.env` 中增加 OpenAI 配置
3. 熟悉当前项目的 `router / service / schema` 分层
4. 熟悉项目里的统一返回体

建议新增配置项：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-5.4-mini
```

如果使用本地私有兼容网关：

```env
OPENAI_API_KEY=your-local-key
OPENAI_BASE_URL=http://192.168.102.19:8082/v1
OPENAI_MODEL=qwq
```

参考文档：

- OpenAI Python SDK 快速开始：https://developers.openai.com/api/docs/quickstart
- 模型列表接口：https://platform.openai.com/docs/api-reference/models

学习重点：

- 为什么 API Key 不要写死在代码里
- 为什么模型名要走配置
- 为什么 `service` 层最适合接 OpenAI SDK

完成标准：

- 你能清楚说出后续聊天代码应该放在哪几个文件里

---

## 阶段 1：最简单聊天接口

目标：

- 在当前项目中实现一个最小可运行聊天接口

建议新增模块：

- `app/api/routers/ai_chat.py`
- `app/services/ai_chat.py`
- `app/schemas/ai_chat.py`

建议接口：

- `POST /api/v1/ai/chat`

请求示例：

```json
{
  "message": "你好，请介绍一下你自己"
}
```

响应示例：

```json
{
  "code": 200,
  "message": "调用成功",
  "data": {
    "reply": "你好，我是一个示例聊天助手"
  }
}
```

这一阶段只做：

1. 单轮对话
2. 不做数据库存储
3. 不做工具调用
4. 不做多轮上下文

学习重点：

- 如何创建 OpenAI client
- 如何在 service 里发起模型调用
- 如何把模型结果包装成统一返回体

参考文档：

- Responses API：https://platform.openai.com/docs/api-reference/responses
- Chat Completions API：https://platform.openai.com/docs/api-reference/chat

当前项目说明：

- OpenAI 官方接口优先用 `client.responses.create(...)`
- 你的 `qwq` 私有网关使用 `client.chat.completions.create(...)`

完成标准：

- 你可以从 Swagger 调用 `/api/v1/ai/chat`
- 模型能返回一句自然语言回复

---

## 阶段 2：多轮对话与会话状态

目标：

- 让聊天支持上下文

这一阶段可以学习两种思路：

1. 自己维护历史消息
2. 使用 OpenAI 返回的响应 ID 串联上下文

参考文档：

- Conversation state：https://developers.openai.com/api/docs/guides/conversation-state

兼容网关说明：

- OpenAI 官方 Responses API 可学习 `previous_response_id`
- 私有网关如果只支持 Chat Completions，就优先自己维护 `messages` 历史

建议你学习顺序：

1. 先理解会话状态是什么
2. 再决定状态落在哪里

建议新增表：

- `chat_sessions`
- `chat_messages`

建议记录字段：

### `chat_sessions`

- `id`
- `session_code`
- `title`
- `created_at`

### `chat_messages`

- `id`
- `session_id`
- `role`
- `content`
- `openai_response_id`
- `created_at`

学习重点：

- 多轮对话为什么不能只靠一个接口参数
- 哪些状态存 OpenAI 侧，哪些状态存自己数据库
- 为什么聊天记录最好持久化

完成标准：

- 你能发起第二轮问题
- 模型能基于上一轮上下文回答

---

## 阶段 3：结构化输出

目标：

- 让模型输出稳定 JSON，而不是只会聊天

这一阶段很重要，因为股票智能体真正需要的是：

- 提取股票代码
- 提取意图
- 提取时间范围
- 判断是“查行情”还是“问分析”

建议练习接口：

- `POST /api/v1/ai/parse-intent`

输入：

```json
{
  "message": "帮我看下 AAPL 最近一周的走势"
}
```

期望输出：

```json
{
  "code": 200,
  "message": "识别成功",
  "data": {
    "intent": "stock_quote",
    "symbol": "AAPL",
    "time_range": "7d",
    "needs_analysis": true
  }
}
```

学习重点：

- 为什么业务接口不能只依赖自由文本
- 为什么结构化输出更适合后续工具调用
- 为什么 Pydantic schema 在这一阶段特别有价值

参考文档：

- Structured Outputs：https://developers.openai.com/api/docs/guides/structured-outputs

完成标准：

- 你能稳定得到结构化结果
- 输出能被 Pydantic 正确校验

---

## 阶段 4：函数调用

目标：

- 让模型不是只“说”，而是能“决定调用你的函数”

建议先不要接真实股票行情 API，先写 mock 工具：

- `get_stock_quote(symbol)`
- `get_stock_news(symbol)`
- `get_company_profile(symbol)`

可以先返回固定数据，例如：

```python
{
    "symbol": "AAPL",
    "price": 215.32,
    "change_percent": 1.82
}
```

学习重点：

1. 模型如何选择调用哪个工具
2. 应用如何真正执行本地函数
3. 函数结果如何回传给模型
4. 为什么“工具调用”才是 Agent 的核心能力之一

参考文档：

- Function Calling：https://developers.openai.com/api/docs/guides/function-calling

完成标准：

- 用户问“苹果现在多少钱”
- 模型触发工具调用
- 接口返回整理后的自然语言结果

---

## 阶段 5：股票行情智能体 Demo v1

目标：

- 做一个最小可运行的股票智能体

建议接口：

- `POST /api/v1/stock-agent/chat`

第一版功能只做：

1. 查询最新价格
2. 查询涨跌幅
3. 查询公司简介
4. 查询最近新闻摘要

不建议第一版就做：

- 技术指标分析
- 自动交易建议
- 长篇研究报告
- 多 Agent 协作

建议内部流程：

```text
用户问题
  -> 模型识别意图
  -> 触发工具调用
  -> 获取行情/新闻数据
  -> 模型组织自然语言答案
  -> 统一返回体输出
```

学习重点：

- 聊天能力和业务工具如何组合
- 为什么第一版要控制边界
- 为什么“可用”比“炫技”更重要

完成标准：

- 你能从 Swagger 直接问：
  - “苹果现在股价多少”
  - “英伟达最近有什么新闻”
- 系统能返回可读答案

---

## 阶段 6：再学习 OpenAI Agents SDK

目标：

- 在你已经理解 SDK / 结构化输出 / 工具调用之后，再进入标准 Agent 形态

这时再学，会轻松很多。

因为你已经知道：

- Agent 本质还是模型 + 工具 + 状态
- 框架只是把这些概念做了更好的封装

建议在这一阶段做两个方向：

1. 用 Agents SDK 重写前面的股票助手
2. 对比它和“直接用 SDK”写法的差别

学习重点：

- `Agent`
- `Runner`
- `tools`
- `handoff`
- tracing

参考文档：

- OpenAI Agents SDK Quickstart：https://openai.github.io/openai-agents-python/quickstart/

完成标准：

- 你能解释“为什么这里值得用 Agents SDK，而不是继续手写”

---

## 阶段 7：是否还要学 LangChain

建议结论：

- 要学，但放后面

适合你什么时候学：

1. 你已经会官方 SDK
2. 你已经会函数调用
3. 你已经做过一个小型 Agent Demo
4. 你想比较不同框架风格

你可以把 LangChain 当成：

- 第二套 agent 框架视角
- 生态型框架
- 适合快速拼装 demo 的工具箱

但不要把它当成第一步。

---

## 6 周节奏建议

### 第 1 周

- 理解 OpenAI 接入思路
- 配置 API Key
- 实现最小聊天接口

### 第 2 周

- 做多轮聊天
- 设计会话表和消息表
- 学会保存上下文

### 第 3 周

- 学结构化输出
- 做意图识别接口

### 第 4 周

- 学函数调用
- 实现 mock 股票工具

### 第 5 周

- 做股票智能体 Demo v1
- 打通行情查询、新闻摘要

### 第 6 周

- 学 OpenAI Agents SDK
- 对比是否需要 LangChain

---

## 8. 结合当前项目的推荐落地目录

建议后续新增如下文件：

```text
app/
├── api/
│   └── routers/
│       ├── ai_chat.py
│       └── stock_agent.py
├── services/
│   ├── ai_chat.py
│   └── stock_agent.py
├── schemas/
│   ├── ai_chat.py
│   └── stock_agent.py
├── models/
│   ├── chat_session.py
│   └── chat_message.py
```

建议新增文档：

- `docs/openai_chat_guide.md`
- `docs/stock_agent_guide.md`

---

## 9. 你当前阶段最应该记住的结论

1. 不要一开始就上 LangChain
2. 先用官方 SDK 学底层调用
3. 先做简单聊天，再做结构化输出和函数调用
4. 股票智能体第一版先做小，不要一口气做复杂研究系统
5. 当你已经真正理解 Agent 的本质后，再学 Agents SDK 和 LangChain，收益最大

---

## 10. 下一步执行建议

按优先级，下一步最建议做的是：

1. 在 `.env` 增加 OpenAI 配置
2. 新增 `ai_chat` 模块
3. 先实现 `POST /api/v1/ai/chat`
4. 跑通最小聊天
5. 再进入第二阶段

如果你准备继续，我建议下一步直接进入：

- “在当前项目中落一个最小 OpenAI 聊天模块”

这样你不是停留在计划层，而是马上进入可运行代码阶段。
