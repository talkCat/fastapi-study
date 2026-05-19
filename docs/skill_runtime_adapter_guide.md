# Skill Runtime Adapter Guide

这份文档说明当前项目的标准 Skill Adapter / Skill Runtime。

目标：

- Skill 包下载后，不只作为 Prompt 说明，也可以声明可执行工具。
- 优先支持标准 `agents/tools.json` manifest。
- 对没有 manifest 的开源 Skill，提供通用 Python 脚本执行工具作为兜底。
- Harness 继续负责权限裁决、工具执行、ledger 记录和流式返回。

## 1. 分层边界

```text
Skill
  -> 说明怎么做
  -> 提供 references / scripts
  -> 可选声明 agents/tools.json

Skill Runtime Adapter
  -> 读取 agents/tools.json（可选）
  -> 把声明过的脚本转换成 ToolDefinition
  -> 提供通用 skill.scripts.list / skill.python.run
  -> 统一接入 ToolRegistry

ToolRegistry
  -> 权限裁决 allow / ask / deny
  -> 执行工具
  -> 返回结构化 ToolResult
```

## 2. 两种接入方式

### 方式 A：标准 manifest，推荐

Skill 包提供 `agents/tools.json`，系统自动生成明确命名的工具。

优点：

- 参数清晰
- 风险级别清晰
- 模型更容易选对工具
- 团队更容易审计

### 方式 B：通用 Python 脚本工具，兜底

对于没有 `agents/tools.json` 的开源 Skill，系统提供两个通用工具：

| 工具 | 风险 | 说明 |
|---|---|---|
| `skill.scripts.list` | low | 列出某个 Skill 包内的 Python 脚本 |
| `skill.python.run` | medium | 执行某个 Skill 包内的 Python 脚本 |

示例：

```json
{
  "tool_name": "skill.scripts.list",
  "arguments": {
    "skill_name": "stock-price-query"
  }
}
```

返回：

```json
{
  "skill": "stock-price-query",
  "scripts": [
    {"path": "scripts/stock_query.py", "size_bytes": 13351}
  ],
  "count": 1
}
```

执行脚本：

```json
{
  "tool_name": "skill.python.run",
  "arguments": {
    "skill_name": "stock-price-query",
    "script": "scripts/stock_query.py",
    "args": ["AAPL", "us"],
    "timeout_seconds": 20,
    "output_format": "json"
  }
}
```

`skill.python.run` 是 `medium` 风险工具，默认不会自动执行，除非请求里设置 `auto_approve_tools=true`。

## 3. 标准 manifest：`agents/tools.json`

Skill 包如果想自动暴露脚本工具，需要增加：

```text
my-skill/
├── SKILL.md
├── agents/
│   └── tools.json
└── scripts/
    └── some_tool.py
```

示例：

```json
{
  "version": 1,
  "tools": [
    {
      "name": "normalize-location",
      "description": "Normalize a location string.",
      "script": "scripts/normalize_location.py",
      "risk_level": "low",
      "parallel_safe": true,
      "timeout_seconds": 5,
      "output_format": "text",
      "arguments": [
        {"name": "location", "required": true},
        {"name": "mode", "flag": "--mode"}
      ]
    }
  ]
}
```

注册后的工具名会是：

```text
skill.<skill-name>.<tool-name>
```

例如：

```text
skill.weather.build-wttr-query
```

## 4. 当前支持字段

| 字段 | 说明 |
|---|---|
| `name` | 工具短名，会拼成 `skill.<skill>.<name>` |
| `description` | 给模型看的工具说明 |
| `script` | Skill 目录内的 Python 脚本路径 |
| `risk_level` | `low` / `medium` / `high` |
| `parallel_safe` | 是否可以并发 |
| `timeout_seconds` | 最大执行时间 |
| `output_format` | `text` 或 `json` |
| `arguments` | 参数映射规则 |

参数规则：

- 没有 `flag`：作为位置参数传给脚本
- 有 `flag`：作为命令行选项传给脚本
- `required=true`：缺失时报错

## 5. 安全边界

当前 Runtime 有这些限制：

1. manifest 工具只执行 `agents/tools.json` 显式声明的脚本。
2. 通用工具只执行用户明确指定的 Skill 内 Python 脚本。
3. 脚本路径不能逃出 Skill 目录。
4. 当前只支持 Python 脚本。
5. 不使用 shell，使用参数数组执行。
6. 每个脚本有 timeout。
7. 工具仍然走 `ToolRegistry.decide_permission(...)`。
8. `skill.python.run` 默认为 `medium` 风险，必须审批或显式自动批准。

这比“扫描 scripts 后全部自动暴露并自动执行”安全得多。

## 6. 当前示例

`weather-query-assistant` 已经增加：

```text
.agents/skills/weather-query-assistant/agents/tools.json
```

它会自动注册：

```text
skill.weather.normalize-location
skill.weather.build-wttr-query
skill.weather.build-open-meteo-query
```

这些工具不是手写进 `ToolRegistry` 的，而是由 `SkillRuntimeAdapter` 自动适配。

`stock-price-query` 没有 `agents/tools.json`，但可以通过通用工具使用：

```text
skill.scripts.list     -> 发现 scripts/stock_query.py
skill.python.run       -> 执行 scripts/stock_query.py
```

## 7. 和手写通用工具的关系

项目里仍然可以维护通用工具：

```text
weather.current
docx.inspect
docx.extract_text
docx.create
docx.replace_text
```

它们适合沉淀成稳定能力。

Skill Runtime 工具适合让 Skill 包自带的小脚本快速接入。

判断标准：

```text
高频、稳定、跨 Skill 复用 -> 手写通用 Tool
Skill 私有、轻量脚本 -> agents/tools.json 自动适配
无 manifest 的开源 Skill -> skill.scripts.list + skill.python.run 兜底执行
```
