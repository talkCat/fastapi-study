# SKILLS 教学：它和 Tools 到底有什么不一样

这份文档专门讲一件事：

- `Skill` 是什么
- `Tool` 是什么
- 两者的边界在哪里
- 在真实 Agent / Codex 工作流里，什么时候该用 Skill，什么时候该用 Tool

如果你前面已经学过：

- `003-openai-structured-output.ipynb`
- `004-openai-function-calling.ipynb`
- `005-stock-agent-demo-v1.ipynb`

那这份文档正好用来补上更高一层的认知。

---

## 1. 先给一个最短答案

一句话区分：

- `Tool`：给模型或应用提供“可调用的能力”
- `Skill`：给智能体提供“如何完成某类任务的工作说明书”

更直接一点：

- `Tool` 解决的是“能做什么”
- `Skill` 解决的是“应该怎么做”

你可以把它们类比成：

- `Tool` 像 Java 里的一个接口能力，例如 `StockQuoteService#getQuote(symbol)`
- `Skill` 像团队内部的开发 SOP、领域手册、脚本集合、最佳实践指南

---

## 2. 为什么很多人会混淆

因为它们都在“增强 Agent 能力”。

但增强的层次不一样：

1. `Tool` 是运行时能力
2. `Skill` 是方法论和流程能力

`Tool` 让模型或应用有机会去“拿数据、调接口、执行函数”。

`Skill` 让智能体知道：

- 先读哪些文件
- 按什么步骤排查
- 哪些脚本优先复用
- 哪些目录结构和格式是团队约定

所以它们不是互斥关系，而是不同层。

---

## 3. 一个非常实用的判断标准

遇到一个需求时，先问自己两个问题：

### 问题 1：我缺的是“能力”还是“方法”

如果缺的是：

- 查实时股价
- 查数据库
- 调外部 API
- 读日历
- 发邮件

这通常是 `Tool`。

如果缺的是：

- 如何在这个仓库里新增 notebook
- 如何按团队规范生成 Skill
- 如何排查某类线上问题
- 如何处理某个公司特有的数据格式

这通常是 `Skill`。

### 问题 2：这个东西要不要被模型当成“函数”去调用

如果答案是“要”，大概率是 `Tool`。

因为 Tool 天然有：

- 名称
- 参数 schema
- 返回结果

如果答案是“不要，它更像一套步骤和经验”，大概率是 `Skill`。

---

## 4. Skill 和 Tool 的核心差异

| 维度 | Skill | Tool |
|---|---|---|
| 作用层次 | 方法、流程、领域知识 | 可执行能力、可调用函数 |
| 主要解决的问题 | “怎么做” | “做什么” |
| 触发方式 | 任务匹配后加载说明 | 模型或程序在运行时调用 |
| 典型形态 | `SKILL.md` + scripts/references/assets | function schema / API / 本地函数 |
| 是否需要参数 schema | 不一定 | 通常必须有 |
| 是否返回结构化调用结果 | 不一定 | 通常要有明确结果 |
| 是否适合实时数据 | 不适合单独承担 | 非常适合 |
| 是否适合沉淀团队经验 | 非常适合 | 不适合单独承担 |
| 是否可以包含脚本 | 可以 | 也可以，但重点不同 |
| 是否能替代对方 | 不能 | 不能 |

最重要的一句：

`Skill` 不是 `Tool` 的别名，`Tool` 也不是 `Skill` 的简化版。

---

## 5. 用你当前项目举例

### 5.1 什么是 Tool

在 `004-openai-function-calling.ipynb` 里，你已经见过典型 Tool：

- `get_stock_quote(symbol)`
- `get_stock_news(symbol)`
- `get_company_profile(symbol)`

这些都是 Tool，因为它们有明确输入输出：

输入：

```python
symbol = "AAPL"
```

输出：

```python
{
    "symbol": "AAPL",
    "price": 215.32,
    "change_percent": 1.82
}
```

模型或应用可以明确地“调用它们”。

### 5.2 什么是 Skill

假设你现在要做一个新 Skill：`openai-notebook-author`

它的职责不是去查股价，而是教智能体：

1. 新 notebook 放到 `notebooks/openai/`
2. 文件名按 `001/002/003...` 递增
3. 先参考上一份 notebook 的教学节奏
4. 新文件写完后做 JSON 校验
5. 必要时同步更新 `docs/openai_chat_agent_learning_plan.md`

这就不是 Tool。

因为这里没有一个“我要传什么参数、立刻返回什么业务数据”的函数接口。

它更像一套工作规则和流程模板。

---

## 6. Skill 的典型结构是什么

一个 Skill 至少要有一个 `SKILL.md`。

常见结构：

```text
my-skill/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   └── some_helper.py
├── references/
│   └── domain_notes.md
└── assets/
    └── template.txt
```

各部分作用：

- `SKILL.md`
  这是核心说明书，定义这个 Skill 何时用、怎么用

- `scripts/`
  放可复用脚本，解决重复性、高确定性工作

- `references/`
  放领域文档、规范、接口说明，按需读取

- `assets/`
  放模板、素材、示例文件

所以 Skill 本身更像一个“带资源包的任务手册”。

---

## 7. Tool 的典型结构是什么

Tool 更像一个显式函数能力。

在 OpenAI Function Calling 里，它通常长这样：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "查询股票当前价格和涨跌幅",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"}
                },
                "required": ["symbol"]
            }
        }
    }
]
```

然后模型会返回：

```python
tool_call.function.name
tool_call.function.arguments
```

你的应用执行之后，再把结果传回去。

所以 Tool 的关注点是：

- 函数名
- 参数
- 执行
- 返回

它不是工作流手册。

---

## 8. 一个更贴近工程实践的类比

如果按 Java 项目来类比：

### Tool 更像这些东西

- `UserService#getById(id)`
- `StockQuoteClient#getQuote(symbol)`
- `NewsService#search(symbol)`
- 一个可被系统调用的 REST API

特点：

- 调用边界清晰
- 输入输出清晰
- 运行时可执行

### Skill 更像这些东西

- 团队内部开发规范
- 某类任务的排查手册
- 某个领域的业务规则说明
- 一个“遇到这种需求就按这个顺序做”的操作指南

特点：

- 强调流程和经验
- 强调约定和上下文
- 不一定是一条调用就能完成

---

## 9. Skill 和 Tool 的关系，不是二选一

很多真实系统里，最佳方案是：

- 用 `Skill` 管流程
- 用 `Tool` 做执行

例如“生成一份新的 OpenAI 教学 notebook”这个任务：

Skill 告诉智能体：

1. 先读上一份 notebook
2. 再读学习计划文档
3. 生成新 notebook 时保持相同教学节奏
4. 完成后做 JSON 校验
5. 顺手更新学习计划里的列表

Tool 或脚本负责：

- 校验 notebook JSON 是否合法
- 扫描现有编号
- 生成模板文件

你会发现：

- Skill 定义了工作流
- Tool 负责工作流中的具体动作

这才是合理分层。

---

## 10. 什么时候优先做成 Skill

优先做成 Skill 的典型场景：

1. 这个任务有一套固定步骤，但不是单个函数能描述清楚
2. 这个任务强依赖仓库约定、团队约定、公司知识
3. 这个任务经常重复出现，但每次上下文会略有不同
4. 这个任务需要先看文档、再选脚本、再做修改
5. 你希望把“经验”沉淀下来，而不是只沉淀一个 API

例子：

- “按本仓库风格新增一份教学 notebook”
- “按团队规范创建一个新 Skill”
- “排查某个服务的发布问题”
- “处理公司自定义报表格式”

---

## 11. 什么时候优先做成 Tool

优先做成 Tool 的典型场景：

1. 需要访问实时数据
2. 需要明确输入输出
3. 需要在运行时被模型反复调用
4. 需要执行有副作用的动作
5. 需要把系统能力暴露给模型

例子：

- 查股票价格
- 查新闻
- 查天气
- 发通知
- 写数据库

---

## 12. 常见误区

### 误区 1：Skill 就是“更高级的 Tool”

不对。

Skill 和 Tool 不是上下级关系，而是不同维度。

- Skill 偏流程和知识
- Tool 偏执行和能力

### 误区 2：只要有脚本，就是 Tool

不对。

Skill 里也可以带脚本。

关键不在“有没有脚本”，而在这个东西的主要职责是什么：

- 如果主要职责是给任务提供步骤和约束，它还是 Skill
- 如果主要职责是暴露一个可调用能力，它才更像 Tool

### 误区 3：有了 Tool 就不需要 Skill

不对。

Tool 只会告诉系统“这里有个能力”。

但很多复杂任务真正难的不是“有没有能力”，而是：

- 先做哪一步
- 哪些文件先读
- 哪些情况该降级
- 哪些输出格式必须遵守

这些更适合放在 Skill 里。

### 误区 4：有了 Skill 就不需要 Tool

也不对。

Skill 可以告诉你“该查股价”，但它本身不等于“股价查询能力”。

查实时股价这种事，还是要靠 Tool 或外部 API。

---

## 13. 你可以怎么设计一套教学顺序

下面是一条比较稳的学习路线。

### 第 1 阶段：先学 Tool

目标：

- 理解函数调用
- 理解 schema
- 理解工具结果回传

你当前项目里对应：

- `004-openai-function-calling.ipynb`

这个阶段先回答：

- 工具怎么定义
- 模型怎么发起调用
- 应用怎么执行
- 工具结果怎么回传

### 第 2 阶段：再学多个 Tool 如何组合到业务里

目标：

- 把结构化输出和工具调用串起来
- 做一个最小业务闭环

你当前项目里对应：

- `005-stock-agent-demo-v1.ipynb`

这个阶段先回答：

- 意图识别怎么做
- 不同意图怎么路由不同工具
- 工具结果怎么组织成最终答案

### 第 3 阶段：再学 Skill

目标：

- 学会把重复工作沉淀成方法包
- 学会把团队约定、流程、脚本整合到一个 Skill 里

这个阶段先回答：

- 哪些知识应该写进 `SKILL.md`
- 哪些内容应该放 `references/`
- 哪些动作应该做成 `scripts/`
- 何时触发 Skill，何时不该触发

### 第 4 阶段：最后再组合 Skill + Tool

目标：

- 让智能体既知道“怎么做”，又真的“能做到”

这时你就会得到一套更成熟的系统：

- Skill 管流程、约束、领域经验
- Tool 管实时能力、外部数据、执行动作

---

## 14. 给你一套可执行的教学大纲

如果你想单独做一轮 SKILLS 教学，我建议按下面结构讲。

### 第 1 课：Skill 是什么

重点：

- Skill 的定位
- Skill 的目录结构
- `SKILL.md` 的作用
- `scripts/references/assets` 各自负责什么

练习：

- 手写一个最小 `SKILL.md`

### 第 2 课：Skill 和 Tool 的差异

重点：

- 输入输出边界
- 运行时 vs 方法论
- 谁负责调用，谁负责执行

练习：

- 把 5 个场景分别判断成 Skill / Tool / 两者都要

### 第 3 课：怎样设计一个好 Skill

重点：

- 内容要短，不要把大堆说明都塞进 `SKILL.md`
- 变体信息放 `references/`
- 重复动作放 `scripts/`
- 不要把 Skill 写成 README 大杂烩

练习：

- 为“新增 OpenAI 教学 notebook”设计一个 Skill 草案

### 第 4 课：Skill 如何和 Tool 配合

重点：

- Skill 管步骤
- Tool 管执行
- 一条业务链路里两者如何衔接

练习：

- 设计一个“股票助手开发 Skill”，其中引用 `get_stock_quote` 等工具

### 第 5 课：落到你的项目里

重点：

- 哪些地方适合 Skill 化
- 哪些地方只要保留 Tool 即可
- 哪些地方不值得做成任何抽象

练习：

- 列出当前仓库未来最值得新增的 3 个 Skills

---

## 15. 一个最小 Skill 示例

下面是一个极简 `SKILL.md` 示例：

```markdown
---
name: openai-notebook-author
description: Create or update OpenAI teaching notebooks in this repo. Use when adding a new numbered notebook under notebooks/openai and keeping docs in sync.
---

# OpenAI Notebook Author

## Workflow

1. Read the previous notebook in `notebooks/openai/`.
2. Read `docs/openai_chat_agent_learning_plan.md`.
3. Keep the same teaching rhythm: goal, concept, code, summary.
4. Validate the generated notebook JSON.
5. Update the notebook list in the learning plan if needed.

## References

- Read `references/notebook_style.md` when matching style.

## Scripts

- Run `scripts/validate_notebook.py <path>` after writing the notebook.
```

这个 Skill 里没有任何“实时查数据”的能力。

它做的事是：

- 告诉智能体如何在这个仓库里新增 notebook
- 告诉智能体要读哪些文件
- 告诉智能体最后怎么校验

这就是典型 Skill。

---

## 16. 一个最小 Tool 示例

```python
def get_stock_quote(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "price": 215.32,
        "change_percent": 1.82,
    }
```

它的特点很明确：

- 有入参 `symbol`
- 有返回值
- 运行时真的会执行

这就是典型 Tool。

---

## 17. 如果只能记住 5 句话

1. `Tool` 是能力接口，`Skill` 是工作说明书。
2. `Tool` 回答“系统能做什么”，`Skill` 回答“这类任务应该怎么做”。
3. `Tool` 适合实时数据和执行动作，`Skill` 适合沉淀流程、规范和经验。
4. `Skill` 可以引用脚本和文档，甚至指导如何使用 Tool，但它本身不是 Tool。
5. 好的 Agent 往往不是只靠 Tool，也不是只靠 Skill，而是两者分层配合。

---

## 18. 结合你当前阶段的建议

你现在最合适的顺序是：

1. 先把 `003/004/005` 真正跑通
2. 再回头理解 `Skill` 为什么更像“开发和运维层的能力封装”
3. 然后给这个仓库设计 1 个最小 Skill，而不是一下子设计 10 个

我建议你的第一个 Skill 就做这个方向：

- “OpenAI 教学 notebook 生成 Skill”

因为它最贴近你当前仓库，也最容易马上看到收益。
