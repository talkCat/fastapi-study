import json
from datetime import datetime, timezone
from uuid import uuid4

from app.agents.model_client import ModelClient, OpenAICompatibleChatClient
from app.agents.skills import SkillRegistry
from app.agents.tools import ToolRegistry
from app.agents.types import (
    AgentState,
    ApprovalTicket,
    ExecutionRun,
    LedgerEntry,
    SkillDescriptor,
    ToolCall,
    ToolResult,
)


class HarnessChatAgent:
    def __init__(
        self,
        model_client: ModelClient | None = None,
        skill_registry: SkillRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
        max_history_messages: int = 12,
    ):
        self.model_client = model_client or OpenAICompatibleChatClient()
        self.skill_registry = skill_registry or SkillRegistry()
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_history_messages = max_history_messages
        self._sessions: dict[str, list[dict[str, str]]] = {}
        self._runs: dict[str, ExecutionRun] = {}
        self._pending_approvals: dict[str, ApprovalTicket] = {}

    def chat(
        self,
        message: str,
        session_id: str | None = None,
        skill_names: list[str] | None = None,
        auto_approve_tools: bool = False,
        max_steps: int = 4,
    ) -> dict:
        return self._consume_done_event(
            self.stream_chat(
                message=message,
                session_id=session_id,
                skill_names=skill_names,
                auto_approve_tools=auto_approve_tools,
                max_steps=max_steps,
            )
        )

    def stream_chat(
        self,
        message: str,
        session_id: str | None = None,
        skill_names: list[str] | None = None,
        auto_approve_tools: bool = False,
        max_steps: int = 4,
    ):
        active_session_id = session_id or uuid4().hex
        history = self._sessions.setdefault(active_session_id, [])
        compact_history = self._compact_history(history)
        selected_skills = self.skill_registry.select_skills(message, requested_names=skill_names)
        run = self._create_run(
            session_id=active_session_id,
            message=message,
            history_snapshot=compact_history,
            selected_skill_names=[skill.name for skill in selected_skills],
            max_steps=max_steps,
            auto_approve_tools=auto_approve_tools,
        )

        input_entry = self._record(
            run,
            "input",
            AgentState.READY,
            "completed",
            "收到用户消息",
            {"session_id": active_session_id},
        )
        yield _stream_event("ledger", _ledger_to_dict(input_entry))

        context_entry = self._record(
            run,
            "context",
            AgentState.PLANNING,
            "completed",
            "完成上下文裁剪",
            {"history_messages": len(compact_history), "selected_skills": run.selected_skill_names},
        )
        yield _stream_event("ledger", _ledger_to_dict(context_entry))

        result = yield from self._run_loop_stream(run=run, selected_skills=selected_skills)

        if result["needs_approval"]:
            answer = "这个工具调用需要审批后才能执行。请确认是否允许执行该工具。"
            answer_entry = self._record(
                run,
                "answer",
                AgentState.PENDING_APPROVAL,
                "pending",
                "执行暂停，等待审批恢复",
                {"answer_length": len(answer)},
            )
            yield _stream_event("ledger", _ledger_to_dict(answer_entry))
            done_entry = self._record(
                run,
                "done",
                AgentState.PENDING_APPROVAL,
                "pending",
                "执行检查点已保存，等待审批恢复",
                {"session_id": active_session_id},
            )
            yield _stream_event("ledger", _ledger_to_dict(done_entry))
            yield _stream_event(
                "done",
                self._build_response(
                    run=run,
                    answer=answer,
                    tool_result=result["tool_result"],
                    needs_approval=True,
                    pending_approval=result["pending_approval"],
                    key_point="Harness 在 ask 时会落地审批票据和执行账本检查点，后续可从该检查点恢复。",
                ),
            )
            return

        yield from self._stream_answer_and_done(
            run=run,
            selected_skills=selected_skills,
            tool_result=result["tool_result"],
            phase_detail="正在根据计划和工具结果生成最终回答",
            answer_detail="完成最终回答",
            done_detail="会话状态已更新",
            key_point="Harness 会在每步工具观察后重新规划，最后再让模型组织最终回答。",
        )

    def resume_approval(self, approval_id: str, approved: bool) -> dict:
        return self._consume_done_event(self.stream_resume_approval(approval_id=approval_id, approved=approved))

    def stream_resume_approval(self, approval_id: str, approved: bool):
        ticket = self._pending_approvals.get(approval_id)
        if ticket is None:
            raise ValueError(f"Approval ticket not found: {approval_id}")
        if ticket.status != "pending":
            raise ValueError(f"Approval ticket is already resolved: {approval_id}")

        run = self._runs.get(ticket.run_id)
        if run is None:
            raise ValueError(f"Execution run not found for approval: {approval_id}")

        selected_skills = self._selected_skills_from_names(run.selected_skill_names)
        decision = "approved" if approved else "denied"
        ticket.status = decision
        ticket.decision = decision
        ticket.resolved_at = _now_iso()
        run.pending_approval_id = None
        self._pending_approvals.pop(approval_id, None)

        resolution_entry = self._record(
            run,
            "approval-resolution",
            AgentState.TOOL_PERMISSION,
            "completed",
            "审批结果已记录",
            _approval_to_dict(ticket),
            parent_step_id=ticket.step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(resolution_entry))
        yield _stream_event("approval_resolved", _approval_to_dict(ticket))

        if not approved:
            answer = "已拒绝执行该工具调用，本轮到此结束。"
            self._append_session_history(run.session_id, run.message, answer)
            run.status = "completed"
            answer_entry = self._record(
                run,
                "answer",
                AgentState.ANSWERING,
                "completed",
                "用户拒绝工具执行，本轮直接结束",
                {"answer_length": len(answer)},
            )
            yield _stream_event("ledger", _ledger_to_dict(answer_entry))
            done_entry = self._record(
                run,
                "done",
                AgentState.DONE,
                "completed",
                "拒绝结果已写入会话状态",
                {"session_id": run.session_id},
            )
            yield _stream_event("ledger", _ledger_to_dict(done_entry))
            yield _stream_event(
                "done",
                self._build_response(
                    run=run,
                    answer=answer,
                    tool_result=ToolResult(
                        ok=False,
                        tool_name=ticket.tool_call.name,
                        error="Tool call rejected by user",
                    ),
                    needs_approval=False,
                    pending_approval=None,
                    key_point="审批恢复不仅记录结果，还会把拒绝决定写回执行账本，避免同一票据重复使用。",
                ),
            )
            return

        tool_result = yield from self._execute_tool_call_stream(
            run=run,
            tool_call=ticket.tool_call,
            loop_step_no=ticket.loop_step_no,
            parent_step_id=ticket.step_id,
            resumed=True,
        )
        self._remember_step_result(run, ticket.loop_step_no, tool_result)
        run.current_loop_step = ticket.loop_step_no + 1
        run.status = "running"

        result = yield from self._run_loop_stream(run=run, selected_skills=selected_skills)
        if result["needs_approval"]:
            answer = "这个工具调用需要审批后才能执行。请确认是否允许执行该工具。"
            answer_entry = self._record(
                run,
                "answer",
                AgentState.PENDING_APPROVAL,
                "pending",
                "恢复后再次遇到审批，等待新的用户确认",
                {"answer_length": len(answer)},
            )
            yield _stream_event("ledger", _ledger_to_dict(answer_entry))
            done_entry = self._record(
                run,
                "done",
                AgentState.PENDING_APPROVAL,
                "pending",
                "恢复执行已到达新的审批检查点",
                {"session_id": run.session_id},
            )
            yield _stream_event("ledger", _ledger_to_dict(done_entry))
            yield _stream_event(
                "done",
                self._build_response(
                    run=run,
                    answer=answer,
                    tool_result=result["tool_result"],
                    needs_approval=True,
                    pending_approval=result["pending_approval"],
                    key_point="审批恢复后，Harness 会继续进入多步循环；若下一步仍需审批，会再次保存新的检查点。",
                ),
            )
            return

        yield from self._stream_answer_and_done(
            run=run,
            selected_skills=selected_skills,
            tool_result=result["tool_result"],
            phase_detail="审批已通过，正在基于最新工具观察继续规划并生成最终回答",
            answer_detail="恢复后的最终回答已生成",
            done_detail="审批恢复执行已完成并写回会话状态",
            key_point="审批恢复会继续进入多步 Harness Loop，而不是固定在单步工具之后直接结束。",
        )

    def _run_loop_stream(
        self,
        run: ExecutionRun,
        selected_skills: list[SkillDescriptor],
    ):
        latest_tool_result = _dict_to_tool_result(self._latest_tool_result_payload(run))
        while run.current_loop_step <= run.max_steps:
            step_no = run.current_loop_step
            yield _stream_event(
                "phase",
                {
                    "name": "planning",
                    "detail": f"正在为第 {step_no} 步生成行动计划",
                    "run_id": run.run_id,
                    "selected_skills": run.selected_skill_names,
                    "loop_step": step_no,
                    "max_steps": run.max_steps,
                },
            )
            planning_messages = self._planning_messages(
                run.message,
                run.history_snapshot,
                selected_skills,
                prior_steps=run.completed_steps,
                step_no=step_no,
            )
            planning_tools = self.tool_registry.list_openai_tools()
            planning_call_id = self._next_model_call_id(run, "planning")
            yield _stream_event(
                "model_request",
                self._model_request_payload(
                    run=run,
                    call_id=planning_call_id,
                    stage="planning",
                    transport="chat",
                    messages=planning_messages,
                    tools=planning_tools,
                ),
            )
            plan, planning_trace = self._plan(
                run.message,
                run.history_snapshot,
                selected_skills,
                messages=planning_messages,
                tools=planning_tools,
                step_no=step_no,
                prior_steps=run.completed_steps,
            )
            run.plan = plan
            self._remember_plan(run, step_no, plan)
            yield _stream_event(
                "model_response",
                self._model_response_payload(
                    run=run,
                    call_id=planning_call_id,
                    stage="planning",
                    transport="chat",
                    output_text=planning_trace["raw_output"],
                    source=planning_trace["source"],
                    error=planning_trace["error"],
                    parsed=planning_trace["parsed_plan"],
                    final=plan,
                    tool_calls=planning_trace.get("tool_calls"),
                ),
            )
            plan_entry = self._record(
                run,
                f"plan-{step_no}",
                AgentState.PLANNING,
                "completed",
                "模型生成行动计划",
                {"loop_step": step_no, **plan},
            )
            yield _stream_event("ledger", _ledger_to_dict(plan_entry))
            yield _stream_event("plan", {"loop_step": step_no, **plan})

            if plan.get("action") != "tool":
                return {"tool_result": latest_tool_result, "needs_approval": False, "pending_approval": None}

            tool_call = _tool_call_from_plan(plan)
            execution = yield from self._execute_tool_call_with_permission_stream(
                run=run,
                tool_call=tool_call,
                loop_step_no=step_no,
            )
            if execution["needs_approval"]:
                return execution

            latest_tool_result = execution["tool_result"]
            self._remember_step_result(run, step_no, latest_tool_result)
            run.current_loop_step = step_no + 1

        latest_tool_result = _dict_to_tool_result(self._latest_tool_result_payload(run))
        run.plan = {
            "action": "answer",
            "arguments": {},
            "reason": f"max_steps={run.max_steps} reached; stop the loop and produce a final answer",
        }
        return {"tool_result": latest_tool_result, "needs_approval": False, "pending_approval": None}

    def _execute_tool_call_with_permission_stream(
        self,
        run: ExecutionRun,
        tool_call: ToolCall,
        loop_step_no: int,
    ):
        decision = self.tool_registry.decide_permission(tool_call, auto_approve=run.auto_approve_tools)
        permission_status = "completed" if decision == "allow" else ("pending" if decision == "ask" else "failed")
        permission_entry = self._record(
            run,
            f"permission-{loop_step_no}",
            AgentState.TOOL_PERMISSION,
            permission_status,
            "完成工具权限裁决",
            {"tool_name": tool_call.name, "decision": decision, "loop_step": loop_step_no},
        )
        yield _stream_event("ledger", _ledger_to_dict(permission_entry))
        yield _stream_event("permission", permission_entry.data)

        if decision == "deny":
            run.status = "failed"
            tool_result = ToolResult(ok=False, tool_name=tool_call.name, error="Tool call denied")
            self._remember_step_result(run, loop_step_no, tool_result)
            yield _stream_event("tool_result", _tool_result_to_dict(tool_result))
            return {"tool_result": tool_result, "needs_approval": False, "pending_approval": None}

        if decision == "ask":
            run.status = "pending_approval"
            ticket = ApprovalTicket(
                approval_id=uuid4().hex,
                run_id=run.run_id,
                step_id=permission_entry.step_id,
                tool_call=tool_call,
                loop_step_no=loop_step_no,
            )
            self._pending_approvals[ticket.approval_id] = ticket
            run.pending_approval_id = ticket.approval_id
            approval_entry = self._record(
                run,
                f"approval-{loop_step_no}",
                AgentState.PENDING_APPROVAL,
                "pending",
                "工具调用等待用户审批",
                _approval_to_dict(ticket),
                parent_step_id=permission_entry.step_id,
            )
            yield _stream_event("ledger", _ledger_to_dict(approval_entry))
            yield _stream_event("approval_required", _approval_to_dict(ticket))
            tool_result = ToolResult(ok=False, tool_name=tool_call.name, error="Tool call requires approval")
            yield _stream_event("tool_result", _tool_result_to_dict(tool_result))
            return {"tool_result": tool_result, "needs_approval": True, "pending_approval": ticket}

        tool_result = yield from self._execute_tool_call_stream(
            run=run,
            tool_call=tool_call,
            loop_step_no=loop_step_no,
            parent_step_id=permission_entry.step_id,
            resumed=False,
        )
        return {"tool_result": tool_result, "needs_approval": False, "pending_approval": None}

    def _execute_tool_call_stream(
        self,
        run: ExecutionRun,
        tool_call: ToolCall,
        loop_step_no: int,
        parent_step_id: str | None,
        resumed: bool,
    ):
        step_prefix = "tool-resume" if resumed else "tool"
        detail = "审批已通过，恢复执行工具" if resumed else "开始执行工具"
        tool_entry = self._record(
            run,
            f"{step_prefix}-{loop_step_no}",
            AgentState.TOOL_RUNNING,
            "running",
            detail,
            {"tool_name": tool_call.name, "arguments": tool_call.arguments, "loop_step": loop_step_no},
            parent_step_id=parent_step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(tool_entry))
        yield _stream_event("tool_start", tool_entry.data)

        tool_result = self.tool_registry.execute(tool_call)
        tool_result_entry = self._record(
            run,
            f"tool-result-{loop_step_no}",
            AgentState.TOOL_RUNNING,
            "completed" if tool_result.ok else "failed",
            "工具执行完成",
            {**_tool_result_to_dict(tool_result), "loop_step": loop_step_no},
            parent_step_id=tool_entry.step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(tool_result_entry))
        yield _stream_event("tool_result", {**_tool_result_to_dict(tool_result), "loop_step": loop_step_no})
        return tool_result

    def _plan(
        self,
        message: str,
        history: list[dict[str, str]],
        skills: list[SkillDescriptor],
        messages: list[dict[str, str]] | None = None,
        tools: list[dict] | None = None,
        step_no: int = 1,
        prior_steps: list[dict] | None = None,
    ) -> tuple[dict, dict]:
        request_messages = messages or self._planning_messages(message, history, skills)
        planning_tools = tools or self.tool_registry.list_openai_tools()
        try:
            raw_response = self.model_client.plan(request_messages, planning_tools)
            parsed = _plan_from_model_response(raw_response)
            if parsed.get("action") in {"answer", "tool"}:
                guarded_plan = self._guard_plan(message, skills, parsed, step_no=step_no)
                if guarded_plan:
                    return guarded_plan, {
                        "raw_output": str(raw_response.get("content") or ""),
                        "parsed_plan": parsed,
                        "source": "guarded_model",
                        "error": None,
                        "tool_calls": raw_response.get("tool_calls") or [],
                    }
                return parsed, {
                    "raw_output": str(raw_response.get("content") or ""),
                    "parsed_plan": parsed,
                        "source": "model",
                        "error": None,
                        "tool_calls": raw_response.get("tool_calls") or [],
                    }
            return self._fallback_plan(message, skills, step_no=step_no, prior_steps=prior_steps), {
                "raw_output": str(raw_response.get("content") or ""),
                "parsed_plan": parsed,
                "source": "fallback_invalid_plan",
                "error": None,
                "tool_calls": raw_response.get("tool_calls") or [],
            }
        except Exception as exc:
            plan = self._fallback_plan(message, skills, step_no=step_no, prior_steps=prior_steps)
            plan["planner_error"] = str(exc)
            return plan, {
                "raw_output": None,
                "parsed_plan": None,
                "source": "fallback_error",
                "error": str(exc),
            }

    def _answer(
        self,
        message: str,
        history: list[dict[str, str]],
        skills: list[SkillDescriptor],
        plan: dict,
        tool_result: ToolResult | None,
        needs_approval: bool,
    ) -> str:
        if needs_approval:
            return "这个工具调用需要审批后才能执行。请确认是否允许执行该工具。"

        system_prompt = self._answer_prompt(skills)
        payload = {
            "user_message": message,
            "plan": plan,
            "tool_result": _tool_result_to_dict(tool_result) if tool_result else None,
        }
        try:
            return self.model_client.chat(
                [
                    {"role": "system", "content": system_prompt},
                    *history,
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ]
            )
        except Exception:
            if tool_result and tool_result.result:
                summary = tool_result.result.get("summary")
                if summary:
                    return str(summary)
                return json.dumps(tool_result.result, ensure_ascii=False)
            return "我已经收到问题，但模型回答阶段失败。请稍后重试。"

    def _answer_stream(
        self,
        messages: list[dict[str, str]],
        tool_result: ToolResult | None,
        needs_approval: bool,
    ):
        if needs_approval:
            yield {
                "kind": "fallback",
                "text": "这个工具调用需要审批后才能执行。请确认是否允许执行该工具。",
                "source": "approval_gate",
                "error": None,
            }
            return

        try:
            for delta in self.model_client.stream_chat(messages):
                yield {"kind": "delta", "text": delta, "source": "model", "error": None}
        except Exception as exc:
            if tool_result and tool_result.result:
                summary = tool_result.result.get("summary")
                if summary:
                    yield {
                        "kind": "fallback",
                        "text": str(summary),
                        "source": "fallback_summary",
                        "error": str(exc),
                    }
                    return
                yield {
                    "kind": "fallback",
                    "text": json.dumps(tool_result.result, ensure_ascii=False),
                    "source": "fallback_tool_result",
                    "error": str(exc),
                }
                return
            yield {
                "kind": "fallback",
                "text": "我已经收到问题，但模型流式回答阶段失败。请稍后重试。",
                "source": "fallback_error",
                "error": str(exc),
            }

    def _planning_prompt(self, skills: list[SkillDescriptor]) -> str:
        skill_text = "\n\n".join(_skill_prompt(skill) for skill in skills) or "No selected skills."
        return f"""
你是一个 Harness 风格聊天智能体的规划器。

本轮你会直接拿到系统注册好的 tools。
如果需要外部能力，请发起 tool call。
如果不需要工具，请直接用自然语言简短说明原因，不要输出 Markdown。
你会收到 previous_steps，里面包含前面步骤的 plan 和 tool_result；如果已有观察足够回答，就停止继续调工具。

可用技能：
{skill_text}

规则：
1. 优先遵循 Skill 合约中的 trigger、preferred_tools、planner_hint。
2. 如果某个 Skill 提供了解析脚本或声明式工具定义，优先使用它，而不是自行编造调用方式。
3. 如果某个 Skill 只有脚本没有专用工具，可以先使用 skill.scripts.list，再使用 skill.python.run 执行明确脚本。
4. 如果没有合适工具，直接说明无需工具即可。
5. 不要编造工具结果，不要调用未注册工具。
""".strip()

    def _planning_messages(
        self,
        message: str,
        history: list[dict[str, str]],
        skills: list[SkillDescriptor],
        prior_steps: list[dict] | None = None,
        step_no: int = 1,
    ) -> list[dict[str, str]]:
        payload = {
            "user_message": message,
            "step_index": step_no,
            "previous_steps": prior_steps or [],
        }
        return [
            {"role": "system", "content": self._planning_prompt(skills)},
            *history,
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    def _answer_prompt(self, skills: list[SkillDescriptor]) -> str:
        skill_text = "\n\n".join(_skill_prompt(skill) for skill in skills) or "No selected skills."
        return f"""
你是一个中文聊天智能体。

请根据用户问题、行动计划和工具结果回答。

已选技能：
{skill_text}

要求：
1. 不要编造工具结果中不存在的数据。
2. 工具失败时说明失败原因，并给出下一步建议。
3. 回答要简洁，但保留关键事实。
4. 如果没有工具结果，就按普通聊天回答。
5. 如果存在多步执行，按步骤消化工具观察，但最终回答不要机械复述整个账本。
""".strip()

    def _answer_messages(
        self,
        message: str,
        history: list[dict[str, str]],
        skills: list[SkillDescriptor],
        plan: dict,
        tool_result: ToolResult | None,
        completed_steps: list[dict] | None = None,
    ) -> list[dict[str, str]]:
        payload = {
            "user_message": message,
            "plan": plan,
            "tool_result": _tool_result_to_dict(tool_result) if tool_result else None,
            "completed_steps": completed_steps or [],
        }
        return [
            {"role": "system", "content": self._answer_prompt(skills)},
            *history,
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    def _fallback_plan(
        self,
        message: str,
        skills: list[SkillDescriptor],
        step_no: int = 1,
        prior_steps: list[dict] | None = None,
    ) -> dict:
        if step_no > 1:
            return {
                "action": "answer",
                "arguments": {},
                "reason": f"fallback planner stops after {len(prior_steps or [])} observed step(s)",
            }
        resolved = self._resolve_skill_plan(message, skills)
        if resolved:
            return resolved
        return {"action": "answer", "arguments": {}, "reason": "fallback planner found no required tool"}

    def _guard_plan(self, message: str, skills: list[SkillDescriptor], parsed: dict, step_no: int = 1) -> dict | None:
        if step_no > 1:
            return None
        resolved = self._resolve_skill_plan(message, skills)
        if not resolved:
            return None
        if parsed.get("action") != "tool":
            resolved["reason"] = "skill contract resolver replaced a non-tool model plan"
            return resolved
        parsed_tool = str(parsed.get("tool_name") or "")
        if not self.tool_registry.get(parsed_tool):
            resolved["reason"] = "skill contract resolver replaced an unknown model tool"
            return resolved
        if self._should_prefer_resolved_plan(parsed, resolved, skills):
            resolved["reason"] = "skill contract resolver normalized the model tool call"
            return resolved
        return None

    def _compact_history(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        return history[-self.max_history_messages:]

    def _create_run(
        self,
        session_id: str,
        message: str,
        history_snapshot: list[dict[str, str]],
        selected_skill_names: list[str],
        max_steps: int,
        auto_approve_tools: bool,
    ) -> ExecutionRun:
        run = ExecutionRun(
            run_id=uuid4().hex,
            session_id=session_id,
            message=message,
            history_snapshot=[dict(item) for item in history_snapshot],
            selected_skill_names=list(selected_skill_names),
            max_steps=max_steps,
            auto_approve_tools=auto_approve_tools,
        )
        self._runs[run.run_id] = run
        return run

    def _selected_skills_from_names(self, skill_names: list[str]) -> list[SkillDescriptor]:
        selected: list[SkillDescriptor] = []
        for name in skill_names:
            skill = self.skill_registry.get_skill(name)
            if skill:
                selected.append(skill)
        return selected

    def _resolve_skill_plan(self, message: str, skills: list[SkillDescriptor]) -> dict | None:
        available_tools = [tool.name for tool in self.tool_registry.list_tools()]
        selected_names = [skill.name for skill in skills]
        for skill in skills:
            try:
                resolved = self.tool_registry.skill_runtime_adapter.resolve_plan(
                    skill_name=skill.name,
                    message=message,
                    available_tools=available_tools,
                    selected_skills=selected_names,
                )
            except Exception:
                continue
            if self._is_valid_skill_plan(resolved):
                return resolved
        return None

    def _is_valid_skill_plan(self, plan: dict | None) -> bool:
        if not isinstance(plan, dict):
            return False
        action = plan.get("action")
        if action == "answer":
            return True
        if action != "tool":
            return False
        tool_name = str(plan.get("tool_name") or "")
        if not tool_name or self.tool_registry.get(tool_name) is None:
            return False
        return isinstance(plan.get("arguments"), dict)

    def _should_prefer_resolved_plan(
        self,
        parsed: dict,
        resolved: dict,
        skills: list[SkillDescriptor],
    ) -> bool:
        if parsed.get("action") != "tool" or resolved.get("action") != "tool":
            return False
        parsed_tool = str(parsed.get("tool_name") or "")
        resolved_tool = str(resolved.get("tool_name") or "")
        if parsed_tool == resolved_tool:
            parsed_args = parsed.get("arguments") if isinstance(parsed.get("arguments"), dict) else {}
            resolved_args = resolved.get("arguments") if isinstance(resolved.get("arguments"), dict) else {}
            return len(resolved_args) > len(parsed_args)
        preferred_tools = {
            tool_name
            for skill in skills
            for tool_name in skill.contract.routing.preferred_tools
        }
        if resolved_tool in preferred_tools and parsed_tool not in preferred_tools:
            return True
        return False

    def _next_model_call_id(self, run: ExecutionRun, stage: str) -> str:
        call_id = f"{run.run_id}:model:{run.next_model_call_index:02d}:{stage}"
        run.next_model_call_index += 1
        return call_id

    def _model_name(self) -> str | None:
        return getattr(self.model_client, "model", None)

    def _model_request_payload(
        self,
        run: ExecutionRun,
        call_id: str,
        stage: str,
        transport: str,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
    ) -> dict:
        payload = {
            "run_id": run.run_id,
            "call_id": call_id,
            "stage": stage,
            "transport": transport,
            "model": self._model_name(),
            "message_count": len(messages),
            "messages": messages,
        }
        if tools is not None:
            payload["tools"] = tools
        return payload

    def _model_response_payload(
        self,
        run: ExecutionRun,
        call_id: str,
        stage: str,
        transport: str,
        output_text: str | None,
        source: str,
        error: str | None,
        parsed: dict | None = None,
        final: dict | None = None,
        tool_calls: list[dict] | None = None,
    ) -> dict:
        payload = {
            "run_id": run.run_id,
            "call_id": call_id,
            "stage": stage,
            "transport": transport,
            "model": self._model_name(),
            "source": source,
            "error": error,
            "output_text": output_text,
            "parsed": parsed,
            "final": final,
        }
        if tool_calls is not None:
            payload["tool_calls"] = tool_calls
        return payload

    def _append_session_history(self, session_id: str, message: str, answer: str) -> None:
        history = self._sessions.setdefault(session_id, [])
        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ])
        self._sessions[session_id] = self._compact_history(history)

    def _remember_plan(self, run: ExecutionRun, step_no: int, plan: dict) -> None:
        step = self._ensure_completed_step(run, step_no)
        step["plan"] = dict(plan)

    def _remember_step_result(self, run: ExecutionRun, step_no: int, tool_result: ToolResult | None) -> None:
        step = self._ensure_completed_step(run, step_no)
        step["tool_result"] = _tool_result_to_dict(tool_result) if tool_result else None

    def _latest_tool_result_payload(self, run: ExecutionRun) -> dict | None:
        for step in reversed(run.completed_steps):
            tool_result = step.get("tool_result")
            if isinstance(tool_result, dict):
                return tool_result
        return None

    def _ensure_completed_step(self, run: ExecutionRun, step_no: int) -> dict:
        for step in run.completed_steps:
            if step.get("step_no") == step_no:
                return step
        created = {"step_no": step_no, "plan": None, "tool_result": None}
        run.completed_steps.append(created)
        run.completed_steps.sort(key=lambda item: int(item.get("step_no") or 0))
        return created

    def _record(
        self,
        run: ExecutionRun,
        step: str,
        state: AgentState,
        status: str,
        detail: str,
        data: dict | None = None,
        parent_step_id: str | None = None,
    ) -> LedgerEntry:
        entry = LedgerEntry(
            run_id=run.run_id,
            step_id=f"{run.run_id}:{run.next_step_index:04d}",
            step=step,
            state=state.value,
            status=status,
            detail=detail,
            parent_step_id=parent_step_id,
            data=data or {},
        )
        run.next_step_index += 1
        run.ledger.append(entry)
        return entry

    def _build_response(
        self,
        run: ExecutionRun,
        answer: str,
        tool_result: ToolResult | None,
        needs_approval: bool,
        pending_approval: ApprovalTicket | None,
        key_point: str,
    ) -> dict:
        return {
            "run_id": run.run_id,
            "session_id": run.session_id,
            "status": run.status,
            "answer": answer,
            "selected_skills": list(run.selected_skill_names),
            "plan": run.plan,
            "tool_result": _tool_result_to_dict(tool_result) if tool_result else None,
            "needs_approval": needs_approval,
            "pending_approval": _approval_to_dict(pending_approval) if pending_approval else None,
            "ledger": [_ledger_to_dict(entry) for entry in run.ledger],
            "key_point": key_point,
        }

    def _stream_answer_and_done(
        self,
        run: ExecutionRun,
        selected_skills: list[SkillDescriptor],
        tool_result: ToolResult | None,
        phase_detail: str,
        answer_detail: str,
        done_detail: str,
        key_point: str,
    ):
        yield _stream_event(
            "phase",
            {
                "name": "answering",
                "detail": phase_detail,
                "run_id": run.run_id,
                "has_tool_result": tool_result is not None,
                "needs_approval": False,
                "completed_tool_steps": len(run.completed_steps),
            },
        )
        answer_messages = self._answer_messages(
            message=run.message,
            history=run.history_snapshot,
            skills=selected_skills,
            plan=run.plan,
            tool_result=tool_result,
            completed_steps=run.completed_steps,
        )
        answer_call_id = self._next_model_call_id(run, "answering")
        yield _stream_event(
            "model_request",
            self._model_request_payload(
                run=run,
                call_id=answer_call_id,
                stage="answering",
                transport="stream",
                messages=answer_messages,
            ),
        )
        answer_parts: list[str] = []
        answer_source = "model"
        answer_error: str | None = None
        delta_index = 0
        for chunk in self._answer_stream(
            messages=answer_messages,
            tool_result=tool_result,
            needs_approval=False,
        ):
            delta = chunk.get("text", "")
            if not delta:
                continue
            answer_parts.append(delta)
            if chunk.get("kind") == "delta":
                delta_index += 1
                yield _stream_event(
                    "model_delta",
                    {
                        "run_id": run.run_id,
                        "call_id": answer_call_id,
                        "stage": "answering",
                        "index": delta_index,
                        "text": delta,
                    },
                )
            else:
                answer_source = str(chunk.get("source") or "fallback")
                answer_error = chunk.get("error")
            yield _stream_event("answer_delta", {"text": delta, "run_id": run.run_id})

        answer = "".join(answer_parts)
        yield _stream_event(
            "model_response",
            self._model_response_payload(
                run=run,
                call_id=answer_call_id,
                stage="answering",
                transport="stream",
                output_text=answer,
                source=answer_source,
                error=answer_error,
            ),
        )
        self._append_session_history(run.session_id, run.message, answer)
        run.status = "completed"
        answer_entry = self._record(
            run,
            "answer",
            AgentState.ANSWERING,
            "completed",
            answer_detail,
            {"answer_length": len(answer), "completed_steps": len(run.completed_steps)},
        )
        yield _stream_event("ledger", _ledger_to_dict(answer_entry))
        done_entry = self._record(
            run,
            "done",
            AgentState.DONE,
            "completed",
            done_detail,
            {"session_id": run.session_id},
        )
        yield _stream_event("ledger", _ledger_to_dict(done_entry))
        yield _stream_event(
            "done",
            self._build_response(
                run=run,
                answer=answer,
                tool_result=tool_result,
                needs_approval=False,
                pending_approval=None,
                key_point=key_point,
            ),
        )

    def _consume_done_event(self, events) -> dict:
        final_payload: dict | None = None
        for event in events:
            if event.get("event") == "done":
                final_payload = event.get("data")
        if final_payload is None:
            raise RuntimeError("Harness stream ended without a done payload")
        return final_payload


def _skill_prompt(skill: SkillDescriptor) -> str:
    parts = [
        f"Skill: {skill.name}",
        f"Description: {skill.description}",
    ]
    if skill.contract.category:
        parts.append(f"Category: {skill.contract.category}")
    if skill.contract.trigger.keywords:
        parts.append(f"Trigger keywords: {', '.join(skill.contract.trigger.keywords[:16])}")
    if skill.contract.routing.preferred_tools:
        parts.append(f"Preferred tools: {', '.join(skill.contract.routing.preferred_tools)}")
    if skill.contract.routing.planner_hint:
        parts.append(f"Planner hint: {skill.contract.routing.planner_hint}")
    if skill.contract.routing.answer_hint:
        parts.append(f"Answer hint: {skill.contract.routing.answer_hint}")
    if skill.contract.routing.resolver:
        parts.append(f"Resolver script: {skill.contract.routing.resolver.script}")
    if skill.default_prompt:
        parts.append(f"Default prompt: {skill.default_prompt}")
    preview = skill.instructions[:1200]
    parts.append(f"Instructions preview:\n{preview}")
    return "\n".join(parts)


def _plan_from_model_response(response: dict) -> dict:
    tool_calls = response.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        return {
            "action": "tool",
            "tool_name": str(first.get("name") or ""),
            "arguments": first.get("arguments") if isinstance(first.get("arguments"), dict) else {},
            "reason": str(response.get("content") or "model selected a registered tool"),
        }

    content = str(response.get("content") or "").strip()
    if not content:
        content = "model determined no tool was required"
    return {
        "action": "answer",
        "arguments": {},
        "reason": content,
    }


def _tool_call_from_plan(plan: dict) -> ToolCall:
    return ToolCall(
        name=str(plan.get("tool_name") or ""),
        arguments=plan.get("arguments") if isinstance(plan.get("arguments"), dict) else {},
    )


def _tool_result_to_dict(result: ToolResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "ok": result.ok,
        "tool_name": result.tool_name,
        "result": result.result,
        "error": result.error,
    }


def _dict_to_tool_result(payload: dict | None) -> ToolResult | None:
    if not isinstance(payload, dict):
        return None
    return ToolResult(
        ok=bool(payload.get("ok")),
        tool_name=str(payload.get("tool_name") or ""),
        result=payload.get("result") if isinstance(payload.get("result"), dict) else payload.get("result"),
        error=str(payload.get("error")) if payload.get("error") is not None else None,
    )


def _approval_to_dict(ticket: ApprovalTicket | None) -> dict | None:
    if ticket is None:
        return None
    return {
        "approval_id": ticket.approval_id,
        "run_id": ticket.run_id,
        "step_id": ticket.step_id,
        "loop_step": ticket.loop_step_no,
        "status": ticket.status,
        "tool_name": ticket.tool_call.name,
        "arguments": ticket.tool_call.arguments,
        "requested_at": ticket.requested_at,
        "resolved_at": ticket.resolved_at,
        "decision": ticket.decision,
    }


def _ledger_to_dict(entry: LedgerEntry) -> dict:
    return {
        "run_id": entry.run_id,
        "step_id": entry.step_id,
        "step": entry.step,
        "state": entry.state,
        "status": entry.status,
        "detail": entry.detail,
        "parent_step_id": entry.parent_step_id,
        "timestamp": entry.timestamp,
        "data": entry.data,
    }


def _stream_event(event: str, data: dict) -> dict:
    return {"event": event, "data": data}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
