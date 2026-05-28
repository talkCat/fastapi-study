# Harness Subagent Design

这份文档记录当前项目中引入 Subagent / 多智能体能力的设计方案。

目标不是把已有单智能体推翻，而是在现有 `HarnessChatAgent` 基础上，学习并逐步实现 Harness 风格的多智能体协作：

- 分工清楚
- 上下文隔离
- 权限受控
- 结果可验证
- 过程可复盘
- 最终由 coordinator 综合

## 1. 当前状态

当前聊天智能体已经是一个 Harness 风格的单 coordinator。

核心入口：

```text
app/api/routers/chat_agent.py
  -> app/services/chat_agent.py
    -> app/agents/harness.py
```

当前运行链路：

```text
用户请求
  -> ChatAgentService
  -> HarnessChatAgent
  -> SkillRegistry.select_skills(...)
  -> ModelClient.plan(...)
  -> ToolRegistry.decide_permission(...)
  -> ToolRegistry.execute(...)
  -> ledger / SSE events
  -> ModelClient.stream_chat(...)
  -> 最终回答
```

也就是说，`HarnessChatAgent` 当前已经承担 coordinator 职责：

- 管理 session history
- 裁剪上下文
- 选择 Skill
- 调用模型规划
- 执行权限裁决
- 调用 Tool
- 记录 ledger
- 处理 approval checkpoint
- 生成最终回答

Subagent 设计必须保留这个核心事实：

```text
HarnessChatAgent 是唯一 coordinator。
Subagent 是 coordinator 管理的内部 worker，不直接面向用户。
```

## 2. 为什么不是直接多开几个 agent

多智能体的价值不是“并行更多模型调用”。

如果只是把任务复制给多个 agent，会产生更大的混乱：

- 多个 agent 拿到完整上下文，旧假设互相污染
- 多个 agent 同时改同一批文件，冲突不可控
- worker 只返回局部结论，没人负责综合
- 实现者自己验证自己，结论容易过度自信
- ledger 看不到清晰的职责边界

Harness 风格的多智能体要解决的是：

```text
复杂任务
  -> 按职责拆分不确定性
  -> 每个 worker 拿最小上下文
  -> 每个 worker 有工具和生命周期边界
  -> worker 返回结构化结果
  -> coordinator 综合、取舍、决定下一步
  -> verification 独立判断是否完成
```

因此，本项目的设计重点是：

- 不追求一开始并行
- 不让 subagent 直接写主会话
- 不让 subagent 直接给最终答案
- 不让 worker 的 scratchpad 进入长期记忆
- 不让 implementation worker 自己成为唯一验证者

## 3. 角色划分

### 3.1 Coordinator

当前由 `HarnessChatAgent` 承担。

职责：

- 接收用户请求
- 拥有全局上下文
- 创建 `ExecutionRun`
- 决定是否委派 subagent
- 为 subagent 切上下文快照
- 决定 subagent 是否允许执行
- 记录主 ledger
- 综合 worker 结果
- 决定下一步是继续规划、调用工具、要求审批，还是最终回答

Coordinator 不应该把理解工作完全外包。

worker 可以带回局部发现，但 coordinator 必须把它们压缩成清晰、具体、可执行的下一步。

### 3.2 Research Subagent

只读调查型 worker。

适合任务：

- 查代码结构
- 查某个功能在哪里实现
- 对比文档和代码是否一致
- 找出相关文件、接口、测试
- 总结当前实现边界

默认权限：

- 可以读文件
- 可以搜索仓库
- 不允许写文件
- 不允许安装依赖
- 不允许执行高风险命令

输出重点：

- findings
- evidence
- unknowns
- suggested next actions

### 3.3 Implementation Subagent

改代码型 worker。

适合任务：

- 在明确文件范围内实现一个小功能
- 修一个清晰 bug
- 添加小范围测试

默认权限：

- 需要 allowed paths
- 需要明确 write scope
- 中高风险操作需要 approval
- 不允许改 coordinator 未授权的文件

输出重点：

- changed files
- implementation summary
- assumptions
- verification performed
- residual risks

Implementation subagent 不应该成为第一阶段目标。学习时应先实现 research 和 verification。

### 3.4 Verification Subagent

独立验证型 worker。

适合任务：

- 检查某个修改是否真的满足需求
- 运行或建议测试
- 检查 ledger 是否完整
- 检查工具结果和最终回答是否一致
- 判断是否缺少证据

默认权限：

- 可以读取相关代码和测试
- 可以运行低风险测试
- 不共享 implementation subagent 的 scratchpad
- 不直接相信 implementation subagent 的自我总结

输出重点：

- passed
- failed
- missing evidence
- required follow-up

Verification 的原则是：

```text
代码已经改了 != 问题已经解决
模型说完成 != 已经验证完成
```

## 4. 上下文管理

多智能体下，上下文管理遵循一个核心原则：

```text
Coordinator 拥有全局上下文。
Subagent 只拿任务所需的上下文切片。
```

### 4.1 Coordinator 上下文

由 `ExecutionRun` 维护：

```text
run_id
session_id
message
history_snapshot
selected_skill_names
max_steps
auto_approve_tools
ledger
status
plan
completed_steps
current_loop_step
pending_approval_id
```

这些状态只允许 coordinator 修改。

Subagent 不能直接修改：

- session history
- run.plan
- run.completed_steps
- run.ledger
- pending approval
- final answer

### 4.2 Subagent 输入上下文

Subagent 输入应该是只读快照。

建议结构：

```python
@dataclass
class SubAgentTask:
    task_id: str
    parent_run_id: str
    role: Literal["research", "implementation", "verification"]
    objective: str
    user_message: str
    relevant_history: list[dict[str, str]]
    selected_skill_summaries: list[dict]
    prior_observations: list[dict]
    allowed_tools: list[str]
    allowed_paths: list[str]
    constraints: list[str]
    max_steps: int = 2
```

这里的 `relevant_history` 不等于完整 session history。

切分规则：

- 普通 research：只给当前用户问题、少量历史、相关文件路径
- verification：给任务目标、变更摘要、测试目标、必要 ledger 片段
- implementation：给明确目标、允许修改文件、接口约束、验证要求

### 4.3 Subagent 私有工作上下文

每个 subagent 可以有自己的 scratchpad：

- 读过哪些文件
- 中间假设
- 局部工具结果
- 失败尝试
- 临时计划

这些默认不进入主 run。

Coordinator 只接收压缩后的结构化结果。

### 4.4 Subagent 输出上下文

建议结构：

```python
@dataclass
class SubAgentResult:
    task_id: str
    parent_run_id: str
    role: str
    ok: bool
    summary: str
    findings: list[str]
    evidence: list[dict]
    changed_files: list[str]
    risks: list[str]
    missing_evidence: list[str]
    proposed_next_actions: list[str]
```

`evidence` 应尽量可定位：

```json
[
  {
    "type": "file",
    "path": "app/agents/harness.py",
    "line": 19,
    "note": "HarnessChatAgent 当前承担 coordinator 职责"
  }
]
```

## 5. 生命周期

Subagent 不是一个长期在线的第二聊天窗口，而是有生命周期的受管执行单元。

推荐生命周期：

```text
created
  -> context_prepared
  -> permission_checked
  -> running
  -> completed | failed | aborted
  -> result_summarized
  -> evicted
```

解释：

- `created`：coordinator 创建任务
- `context_prepared`：上下文切片完成
- `permission_checked`：检查 role、tools、paths 是否允许
- `running`：worker 执行
- `completed`：正常返回结构化结果
- `failed`：执行失败
- `aborted`：超时、审批拒绝、上游取消
- `result_summarized`：coordinator 接收并压缩结果
- `evicted`：丢弃 scratchpad，只保留报告和 ledger 摘要

生命周期边界的意义：

- 防止 worker 长期污染主上下文
- 防止未验证假设进入长期记忆
- 让错误能定位到 research、implementation、verification 或 synthesis
- 让 SSE / ledger 可以展示任务进度

## 6. Delegation Policy

模型可以建议委派，但 Harness 必须裁决是否真的委派。

新增 planner action：

```json
{
  "action": "delegate",
  "role": "research",
  "objective": "检查当前 HarnessChatAgent 的 query loop 如何记录 ledger",
  "allowed_tools": ["repo.search", "repo.read"],
  "allowed_paths": ["app/agents", "tests"],
  "reason": "需要先隔离做只读代码调查"
}
```

裁决规则示例：

| Role | 默认裁决 | 条件 |
|---|---|---|
| `research` | allow | 只读工具、路径在项目内 |
| `verification` | allow | 只读或低风险测试 |
| `implementation` | ask | 有明确 allowed paths |
| unknown role | deny | 未注册角色 |
| write outside allowed paths | deny | 越界写入 |
| high risk tool | ask | 需要用户审批 |

建议新增：

```text
app/agents/subagents.py
app/agents/subagent_policy.py
```

第一版也可以先只建 `app/agents/subagents.py`，把 policy 放在同一个文件里。

## 7. Ledger 与 SSE 事件

多智能体必须可复盘。

主 ledger 应记录 coordinator 视角，而不是记录 worker 的全部 scratchpad。

建议新增事件：

```text
subagent_start
subagent_result
synthesis
verification
```

主 ledger 示例：

```text
input
context
plan-1
delegate-1
subagent-start-1
subagent-result-1
synthesis-1
plan-2
answer
done
```

`subagent-start` 数据示例：

```json
{
  "role": "research",
  "task_id": "research-001",
  "objective": "检查 app/agents/harness.py 的 query loop",
  "allowed_tools": ["repo.search", "repo.read"],
  "allowed_paths": ["app/agents", "tests"]
}
```

`subagent-result` 数据示例：

```json
{
  "role": "research",
  "task_id": "research-001",
  "ok": true,
  "summary": "当前 HarnessChatAgent 已承担 coordinator 职责。",
  "findings_count": 3,
  "evidence_count": 2,
  "risk_count": 0
}
```

`synthesis` 数据示例：

```json
{
  "accepted_findings": 3,
  "discarded_findings": 0,
  "next_action": "answer",
  "reason": "research 结果足够支持回答，无需工具调用"
}
```

SSE 可以和 ledger 保持一致：

```text
event: subagent_start
event: subagent_result
event: synthesis
```

前端不需要理解 subagent 私有推理，只需要看到：

- 谁被委派
- 为什么委派
- 边界是什么
- 返回了什么证据
- coordinator 如何综合

## 8. 与 Skill / Tool / Approval 的关系

### 8.1 Skill

Skill 是工作流知识模块。

它回答：

```text
某类任务应该怎么做？
有哪些 references / scripts / planner hints？
```

Subagent 不是 Skill。

Subagent 回答：

```text
这个局部职责由哪个 worker 执行？
上下文如何隔离？
结果如何回报？
```

不要设计成“每个 Skill 一个 agent”。

更合理的关系：

```text
Coordinator 选择 Skill
Coordinator 根据任务复杂度决定是否委派 Subagent
Subagent 在 Skill / Tool 边界内执行局部任务
Coordinator 综合结果
```

### 8.2 Tool

Tool 是受管执行能力。

Subagent 使用 Tool 时仍然必须经过权限边界。

第一版可以不让 subagent 直接执行真实 Tool，而是通过 coordinator 提供的受限 facade：

```text
ResearchSubAgent
  -> allowed_tools: repo.search / repo.read
  -> 不直接拿完整 ToolRegistry
```

这样可以避免 worker 绕过主 Harness 的权限裁决。

### 8.3 Approval

Approval 应该按风险分层：

- read-only research：默认 allow
- verification 运行低风险测试：默认 allow
- implementation 写文件：ask
- 高风险命令：ask
- 越界写入：deny

Subagent approval 不应绕过现有 approval 体系。

可以复用 `ApprovalTicket` 思路，但要扩展 ticket 数据：

```python
@dataclass
class SubAgentApprovalTicket:
    approval_id: str
    run_id: str
    task_id: str
    role: str
    requested_action: str
    allowed_paths: list[str]
    allowed_tools: list[str]
```

第一版学习实现里，可以先不做 implementation subagent，因此暂时不需要复杂 approval。

## 9. Coordinator Synthesis

多智能体系统最容易出错的地方不是委派，而是没有综合。

错误示例：

```text
Research worker 说 A。
Verification worker 说 B。
Coordinator 直接把 A 和 B 拼给用户。
```

正确做法：

```text
Coordinator 读取 worker 结果
  -> 判断哪些发现有证据
  -> 判断哪些发现冲突
  -> 丢弃无证据结论
  -> 提炼下一步
  -> 更新 run.plan 或最终回答
```

Synthesis 输出建议：

```python
@dataclass
class SynthesisResult:
    accepted_findings: list[str]
    rejected_findings: list[str]
    conflicts: list[str]
    next_action: Literal["answer", "tool", "delegate", "ask_user"]
    reason: str
```

Coordinator 的规则：

1. 不原样转发 worker 报告。
2. 不把 worker 临时假设写入长期记忆。
3. 不把无证据结论当事实。
4. 如果 verification 不通过，不能声称任务完成。
5. 最终回答必须反映 evidence 和 residual risks。

## 10. Verification 设计

独立验证是多智能体最值得学习的部分。

Verification subagent 不应该共享 implementation subagent 的 scratchpad。

它应该拿到：

- 原始用户目标
- coordinator 的完成定义
- 变更摘要
- changed files
- 测试命令或验证要求
- 必要 ledger 摘要

它不应该拿到：

- implementation worker 的完整中间推理
- implementation worker 的自我说服过程
- 未压缩的临时上下文

验证问题清单：

1. 用户要求是否被逐条覆盖？
2. 实际改动是否只发生在允许范围？
3. 是否有测试、静态检查或可解释的手工验证？
4. 工具结果是否支持最终回答？
5. 是否存在未声明的风险？
6. 是否需要用户审批或人工 review？

验证输出：

```json
{
  "passed": false,
  "missing_evidence": [
    "没有运行 tests/test_chat_agent_runtime.py",
    "没有验证 SSE 中是否包含 subagent_result"
  ],
  "required_follow_up": [
    "补充单元测试",
    "用 FakeModelClient 验证 delegate action"
  ]
}
```

## 11. 最小实现路线

### Phase 1：只读 Research Subagent

目标：

- 学会 delegation
- 学会上下文切片
- 学会 subagent ledger
- 学会 coordinator synthesis

范围：

- 新增 `SubAgentTask`
- 新增 `SubAgentResult`
- 新增 `ResearchSubAgent`
- 在 `HarnessChatAgent` 中支持 `delegate: research`
- 只允许只读工具或内存模拟工具
- 不改文件
- 不做并行

推荐测试：

- planner 返回 `delegate`
- Harness 记录 `subagent-start`
- ResearchSubAgent 返回结构化结果
- Harness 记录 `subagent-result`
- Harness 记录 `synthesis`
- 最终回答来自 coordinator，而不是 worker 原文

### Phase 2：Verification Subagent

目标：

- 学会独立验证
- 学会区分“已执行”和“已完成”

范围：

- 新增 `VerificationSubAgent`
- 输入为任务目标、ledger 摘要、tool result、完成定义
- 输出 `passed / missing_evidence / required_follow_up`
- coordinator 根据验证结果决定是否完成

推荐测试：

- 没有证据时 verification 不通过
- 有 tool result 但缺测试时标记 missing evidence
- coordinator 不在 verification failed 时声称完成

### Phase 3：Implementation Subagent

目标：

- 学会写入边界
- 学会 approval
- 学会 implementation / verification 分离

范围：

- 支持 allowed paths
- 支持 write scope
- 支持 approval
- 写入后必须进入 verification

推荐测试：

- 越界文件写入被 deny
- medium/high risk action 进入 approval
- implementation 完成后触发 verification
- verification 未通过时最终状态不能是 completed

### Phase 4：有限并行

目标：

- 学会并行不是第一目标，而是受控优化

范围：

- 只允许 parallel_safe 的 research tasks 并行
- 并行结果仍由 coordinator synthesis
- ledger 记录每个 task_id

不建议在前三个阶段之前实现并行。

## 12. 推荐文件结构

第一版：

```text
app/agents/subagents.py
tests/test_chat_agent_subagents.py
```

成熟后可以拆成：

```text
app/agents/subagents/
├── __init__.py
├── types.py
├── policy.py
├── runner.py
├── research.py
├── verification.py
└── implementation.py
```

学习项目不需要一开始就拆这么细。

当前更推荐：

```text
app/agents/subagents.py
```

等 Phase 2 或 Phase 3 后再拆。

## 13. Planner Prompt 需要增加的能力

当前 planner 只需要决定：

```text
answer
tool
```

Subagent 之后可以扩展为：

```text
answer
tool
delegate
```

Prompt 增量规则：

```text
如果问题需要先调查代码、文档或测试结构，可以请求 delegate。
只允许请求已注册的 role。
delegate 只能提出任务目标和边界，是否执行由 Harness 决定。
不要假装 subagent 已经执行。
不要把 delegate 当作最终答案。
```

模型输出示例：

```json
{
  "action": "delegate",
  "role": "research",
  "objective": "查找聊天智能体中 approval 恢复流程的实现位置和测试覆盖",
  "allowed_paths": ["app/agents", "app/services", "tests"],
  "allowed_tools": ["repo.search", "repo.read"],
  "reason": "需要先隔离调查实现与测试，再决定是否修改"
}
```

Guard 规则：

- role 不存在：fallback to answer 或 deny
- allowed paths 为空：补默认只读路径或 deny
- allowed tools 包含高风险工具：ask 或 deny
- objective 过宽：ask user 或缩小任务

Pre-plan routing 规则：

- 如果用户消息里出现明确存在的仓库相对路径，例如 `app/agents/harness.py`，并且是第 1 步，可以不先调用 LLM planner，直接生成 `research` delegate。
- 这个规则不是按“检查、查看、分析”等关键词硬编码，而是按可验证的 repo path 建立边界。
- research subagent 返回证据后，coordinator 可以在下一步直接进入 `answer`，不必再次调用 planner 询问“是否应该回答”。
- 这样可以避免把主 planner 的完整系统提示词、Skills 摘要和工具列表塞进一个明显只需要只读调查的路由决策里。

## 14. 与当前代码的接入点

建议从 `HarnessChatAgent._run_loop_stream(...)` 接入。

当前逻辑：

```text
plan
  -> if action != tool: answer
  -> if action == tool: permission + execute
```

扩展后：

```text
pre-plan route
  -> if explicit repo path: delegate research without LLM planning request
plan
  -> if action == answer: answer
  -> if action == tool: permission + execute
  -> if action == delegate: subagent policy + run + synthesis + continue loop
```

伪代码：

```python
if plan.get("action") == "delegate":
    task = self._subagent_task_from_plan(run, plan)
    decision = self.subagent_policy.decide(task)
    if decision == "deny":
        self._remember_subagent_denial(...)
        return {"tool_result": latest_tool_result, ...}
    if decision == "ask":
        return self._create_subagent_approval(...)

    result = yield from self._run_subagent_stream(run, task)
    synthesis = self._synthesize_subagent_result(run, task, result)
    self._remember_subagent_result(run, task, result, synthesis)
    run.current_loop_step = step_no + 1
    continue
```

注意：

- subagent result 不等于 tool result
- 可以新增 `completed_steps[*]["subagent_result"]`
- 也可以新增 `run.completed_delegations`
- 第一版为了少改类型，可以先把 subagent result 放进 `completed_steps`

示例：

```json
{
  "step_no": 1,
  "plan": {"action": "delegate", "role": "research"},
  "tool_result": null,
  "subagent_result": {
    "role": "research",
    "summary": "..."
  },
  "synthesis": {
    "next_action": "answer"
  }
}
```

## 15. 完成标准

当前实现进度：

- `ResearchSubAgent` 已实现，只读调查并返回结构化证据。
- `VerificationSubAgent` 已实现，用 coordinator 可见证据做独立检查。
- `ImplementationSubAgent` 已实现受控写入：只接受 delegate plan 中明确给出的 `files`，并受 `allowed_paths` 限制。
- 明确 repo path 的只读调查已支持 pre-plan routing：先确定性路由到 `research`，research 完成后确定性进入 answer，避免浪费 planning 上下文。
- `implementation` 委派默认需要 approval；审批通过后执行，随后自动进入 verification。
- Harness 已输出 `delegate`、`delegate_batch`、`subagent_start`、`subagent_result`、`verification`、`synthesis` 事件。
- 有限并行已实现：`delegate_batch` 只允许并行执行只读 `research` task，不允许批量 implementation。

Phase 1 完成标准：

- 有 `SubAgentTask` / `SubAgentResult`
- 有 read-only `ResearchSubAgent`
- planner 可以产生 `delegate`
- Harness 可以裁决并运行 research subagent
- ledger 和 SSE 能看到 subagent start/result/synthesis
- coordinator 最终回答
- 有 FakeModelClient 单元测试

Phase 2 完成标准：

- 有 `VerificationSubAgent`
- verification 不共享 implementation scratchpad
- verification 失败时 coordinator 不声称完成
- 有缺证据场景测试

Phase 3 完成标准：

- implementation 有 allowed paths
- 写入类任务需要 approval
- 越界写入被拒绝
- implementation 后强制 verification

## 16. 教学建议

学习顺序不要从 implementation subagent 开始。

推荐顺序：

```text
1. 先讲 coordinator 与 subagent 的职责边界
2. 实现 read-only research subagent
3. 加 ledger / SSE 可观察事件
4. 加 coordinator synthesis
5. 加 independent verification
6. 最后再加 implementation subagent
```

这样最能体现 Harness Engineering 的核心：

```text
可靠性来自边界、证据、审批、验证和复盘轨迹，
不是来自更多 agent 数量。
```
