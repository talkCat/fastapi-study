import json
import re
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

        yield _stream_event(
            "phase",
            {
                "name": "planning",
                "detail": "正在调用模型生成行动计划",
                "run_id": run.run_id,
                "selected_skills": run.selected_skill_names,
            },
        )
        planning_messages = self._planning_messages(message, compact_history, selected_skills)
        planning_call_id = self._next_model_call_id(run, "planning")
        yield _stream_event(
            "model_request",
            self._model_request_payload(
                run=run,
                call_id=planning_call_id,
                stage="planning",
                transport="chat",
                messages=planning_messages,
            ),
        )
        plan, planning_trace = self._plan(message, compact_history, selected_skills, messages=planning_messages)
        run.plan = plan
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
            ),
        )
        plan_entry = self._record(run, "plan", AgentState.PLANNING, "completed", "模型生成行动计划", plan)
        yield _stream_event("ledger", _ledger_to_dict(plan_entry))
        yield _stream_event("plan", plan)

        result = yield from self._execute_plan_stream(
            run=run,
            selected_skills=selected_skills,
            auto_approve_tools=auto_approve_tools,
            max_steps=max_steps,
        )

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

        yield _stream_event(
            "phase",
            {
                "name": "answering",
                "detail": "正在根据计划和工具结果生成最终回答",
                "run_id": run.run_id,
                "has_tool_result": result["tool_result"] is not None,
                "needs_approval": False,
            },
        )
        answer_messages = self._answer_messages(
            message=message,
            history=compact_history,
            skills=selected_skills,
            plan=run.plan,
            tool_result=result["tool_result"],
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
            tool_result=result["tool_result"],
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
        self._append_session_history(active_session_id, message, answer)
        run.status = "completed"
        answer_entry = self._record(
            run,
            "answer",
            AgentState.ANSWERING,
            "completed",
            "完成最终回答",
            {"answer_length": len(answer)},
        )
        yield _stream_event("ledger", _ledger_to_dict(answer_entry))
        done_entry = self._record(
            run,
            "done",
            AgentState.DONE,
            "completed",
            "会话状态已更新",
            {"session_id": active_session_id},
        )
        yield _stream_event("ledger", _ledger_to_dict(done_entry))
        yield _stream_event(
            "done",
            self._build_response(
                run=run,
                answer=answer,
                tool_result=result["tool_result"],
                needs_approval=False,
                pending_approval=None,
                key_point="Harness 先治理上下文、权限和执行账本，再让模型组织最终回答。",
            ),
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

        tool_entry = self._record(
            run,
            "tool-resume",
            AgentState.TOOL_RUNNING,
            "running",
            "审批已通过，恢复执行工具",
            {"tool_name": ticket.tool_call.name, "arguments": ticket.tool_call.arguments},
            parent_step_id=ticket.step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(tool_entry))
        yield _stream_event("tool_start", tool_entry.data)

        tool_result = self.tool_registry.execute(ticket.tool_call)
        tool_result_entry = self._record(
            run,
            "tool-result-resume",
            AgentState.TOOL_RUNNING,
            "completed" if tool_result.ok else "failed",
            "恢复后的工具执行完成",
            _tool_result_to_dict(tool_result),
            parent_step_id=tool_entry.step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(tool_result_entry))
        yield _stream_event("tool_result", _tool_result_to_dict(tool_result))

        yield _stream_event(
            "phase",
            {
                "name": "answering",
                "detail": "审批已通过，正在从执行账本检查点继续生成最终回答",
                "run_id": run.run_id,
                "has_tool_result": True,
                "needs_approval": False,
            },
        )
        answer_messages = self._answer_messages(
            message=run.message,
            history=run.history_snapshot,
            skills=selected_skills,
            plan=run.plan,
            tool_result=tool_result,
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
            "恢复后的最终回答已生成",
            {"answer_length": len(answer)},
        )
        yield _stream_event("ledger", _ledger_to_dict(answer_entry))
        done_entry = self._record(
            run,
            "done",
            AgentState.DONE,
            "completed",
            "审批恢复执行已完成并写回会话状态",
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
                key_point="审批恢复会直接从保存的 plan 和待执行 tool_call 继续，而不是重新规划整轮对话。",
            ),
        )

    def _execute_plan_stream(
        self,
        run: ExecutionRun,
        selected_skills: list[SkillDescriptor],
        auto_approve_tools: bool,
        max_steps: int,
    ):
        tool_result: ToolResult | None = None
        for step_no in range(max_steps):
            if run.plan.get("action") != "tool":
                break
            tool_call = _tool_call_from_plan(run.plan)
            decision = self.tool_registry.decide_permission(tool_call, auto_approve=auto_approve_tools)
            permission_status = "completed" if decision == "allow" else ("pending" if decision == "ask" else "failed")
            permission_entry = self._record(
                run,
                f"permission-{step_no + 1}",
                AgentState.TOOL_PERMISSION,
                permission_status,
                "完成工具权限裁决",
                {"tool_name": tool_call.name, "decision": decision},
            )
            yield _stream_event("ledger", _ledger_to_dict(permission_entry))
            yield _stream_event("permission", permission_entry.data)

            if decision == "deny":
                run.status = "failed"
                tool_result = ToolResult(ok=False, tool_name=tool_call.name, error="Tool call denied")
                yield _stream_event("tool_result", _tool_result_to_dict(tool_result))
                return {"tool_result": tool_result, "needs_approval": False, "pending_approval": None}

            if decision == "ask":
                run.status = "pending_approval"
                ticket = ApprovalTicket(
                    approval_id=uuid4().hex,
                    run_id=run.run_id,
                    step_id=permission_entry.step_id,
                    tool_call=tool_call,
                )
                self._pending_approvals[ticket.approval_id] = ticket
                run.pending_approval_id = ticket.approval_id
                approval_entry = self._record(
                    run,
                    f"approval-{step_no + 1}",
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

            tool_entry = self._record(
                run,
                f"tool-{step_no + 1}",
                AgentState.TOOL_RUNNING,
                "running",
                "开始执行工具",
                {"tool_name": tool_call.name, "arguments": tool_call.arguments},
                parent_step_id=permission_entry.step_id,
            )
            yield _stream_event("ledger", _ledger_to_dict(tool_entry))
            yield _stream_event("tool_start", tool_entry.data)

            tool_result = self.tool_registry.execute(tool_call)
            tool_result_entry = self._record(
                run,
                f"tool-result-{step_no + 1}",
                AgentState.TOOL_RUNNING,
                "completed" if tool_result.ok else "failed",
                "工具执行完成",
                _tool_result_to_dict(tool_result),
                parent_step_id=tool_entry.step_id,
            )
            yield _stream_event("ledger", _ledger_to_dict(tool_result_entry))
            yield _stream_event("tool_result", _tool_result_to_dict(tool_result))
            break

        return {"tool_result": tool_result, "needs_approval": False, "pending_approval": None}

    def _plan(
        self,
        message: str,
        history: list[dict[str, str]],
        skills: list[SkillDescriptor],
        messages: list[dict[str, str]] | None = None,
    ) -> tuple[dict, dict]:
        request_messages = messages or self._planning_messages(message, history, skills)
        try:
            raw = self.model_client.chat(request_messages)
            parsed = _extract_json(raw)
            if parsed.get("action") in {"answer", "tool"}:
                guarded_plan = self._guard_plan(message, skills, parsed)
                if guarded_plan:
                    return guarded_plan, {
                        "raw_output": raw,
                        "parsed_plan": parsed,
                        "source": "guarded_model",
                        "error": None,
                    }
                return parsed, {
                    "raw_output": raw,
                    "parsed_plan": parsed,
                    "source": "model",
                    "error": None,
                }
            return self._fallback_plan(message, skills), {
                "raw_output": raw,
                "parsed_plan": parsed,
                "source": "fallback_invalid_plan",
                "error": None,
            }
        except Exception as exc:
            plan = self._fallback_plan(message, skills)
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
        tool_text = "\n".join(
            f"- {tool.name}: {tool.description}; risk={tool.risk_level}"
            for tool in self.tool_registry.list_tools()
        )
        return f"""
你是一个 Harness 风格聊天智能体的规划器。

你只能输出 JSON，不要输出 Markdown。

可用技能：
{skill_text}

可用工具：
{tool_text}

输出格式：
{{
  "action": "answer" 或 "tool",
  "tool_name": "工具名，action=tool 时必填",
  "arguments": {{}},
  "reason": "为什么这样做"
}}

规则：
1. 优先遵循 Skill 合约中的 trigger、preferred_tools、planner_hint。
2. 如果某个 Skill 提供了解析脚本或声明式工具定义，优先使用它，而不是自行编造调用方式。
3. 如果某个 Skill 只有脚本没有专用工具，可以先使用 skill.scripts.list，再使用 skill.python.run 执行明确脚本。
4. 如果没有合适工具，action=answer。
5. 不要编造工具结果，不要输出协议外字段。
""".strip()

    def _planning_messages(
        self,
        message: str,
        history: list[dict[str, str]],
        skills: list[SkillDescriptor],
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._planning_prompt(skills)},
            *history,
            {"role": "user", "content": message},
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
""".strip()

    def _answer_messages(
        self,
        message: str,
        history: list[dict[str, str]],
        skills: list[SkillDescriptor],
        plan: dict,
        tool_result: ToolResult | None,
    ) -> list[dict[str, str]]:
        payload = {
            "user_message": message,
            "plan": plan,
            "tool_result": _tool_result_to_dict(tool_result) if tool_result else None,
        }
        return [
            {"role": "system", "content": self._answer_prompt(skills)},
            *history,
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    def _fallback_plan(self, message: str, skills: list[SkillDescriptor]) -> dict:
        resolved = self._resolve_skill_plan(message, skills)
        if resolved:
            return resolved
        return {"action": "answer", "arguments": {}, "reason": "fallback planner found no required tool"}

    def _guard_plan(self, message: str, skills: list[SkillDescriptor], parsed: dict) -> dict | None:
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
    ) -> ExecutionRun:
        run = ExecutionRun(
            run_id=uuid4().hex,
            session_id=session_id,
            message=message,
            history_snapshot=[dict(item) for item in history_snapshot],
            selected_skill_names=list(selected_skill_names),
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
    ) -> dict:
        return {
            "run_id": run.run_id,
            "call_id": call_id,
            "stage": stage,
            "transport": transport,
            "model": self._model_name(),
            "message_count": len(messages),
            "messages": messages,
        }

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
    ) -> dict:
        return {
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

    def _append_session_history(self, session_id: str, message: str, answer: str) -> None:
        history = self._sessions.setdefault(session_id, [])
        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ])
        self._sessions[session_id] = self._compact_history(history)

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


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


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


def _approval_to_dict(ticket: ApprovalTicket | None) -> dict | None:
    if ticket is None:
        return None
    return {
        "approval_id": ticket.approval_id,
        "run_id": ticket.run_id,
        "step_id": ticket.step_id,
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
