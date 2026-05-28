import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from uuid import uuid4

from app.agents.model_client import ModelClient, OpenAICompatibleChatClient
from app.agents.subagents import (
    ImplementationSubAgent,
    ResearchSubAgent,
    SubAgentPolicy,
    SubAgentResult,
    SubAgentTask,
    SynthesisResult,
    VerificationSubAgent,
)
from app.agents.skills import SkillRegistry, project_root
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
        research_subagent: ResearchSubAgent | None = None,
        verification_subagent: VerificationSubAgent | None = None,
        implementation_subagent: ImplementationSubAgent | None = None,
        subagent_policy: SubAgentPolicy | None = None,
        max_history_messages: int = 12,
    ):
        self.model_client = model_client or OpenAICompatibleChatClient()
        self.skill_registry = skill_registry or SkillRegistry()
        self.tool_registry = tool_registry or ToolRegistry()
        self.research_subagent = research_subagent or ResearchSubAgent()
        self.verification_subagent = verification_subagent or VerificationSubAgent()
        self.implementation_subagent = implementation_subagent or ImplementationSubAgent()
        self.subagent_policy = subagent_policy or SubAgentPolicy()
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

        is_subagent_approval = ticket.tool_call.name.startswith("subagent.")
        if not approved:
            answer = "已拒绝执行该 Subagent 委派，本轮到此结束。" if is_subagent_approval else "已拒绝执行该工具调用，本轮到此结束。"
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

        if is_subagent_approval:
            task_payload = ticket.tool_call.arguments.get("task")
            if not isinstance(task_payload, dict):
                raise ValueError(f"Subagent approval ticket is missing task payload: {approval_id}")
            task = _subagent_task_from_payload(task_payload)
            result = yield from self._execute_approved_subagent_stream(
                run=run,
                task=task,
                plan=ticket.tool_call.arguments,
                loop_step_no=ticket.loop_step_no,
                parent_step_id=ticket.step_id,
                resumed=True,
            )
            synthesis = self._synthesize_subagent_result(task, result)
            self._remember_subagent_result(run, ticket.loop_step_no, result, synthesis)
            yield from self._record_synthesis_stream(run, ticket.loop_step_no, synthesis)
            run.current_loop_step = ticket.loop_step_no + 1
            run.status = "running"

            loop_result = yield from self._run_loop_stream(run=run, selected_skills=selected_skills)
            if loop_result["needs_approval"]:
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
                        tool_result=loop_result["tool_result"],
                        needs_approval=True,
                        pending_approval=loop_result["pending_approval"],
                        key_point="审批恢复后，Harness 会继续进入多步循环；若下一步仍需审批，会再次保存新的检查点。",
                    ),
                )
                return

            yield from self._stream_answer_and_done(
                run=run,
                selected_skills=selected_skills,
                tool_result=loop_result["tool_result"],
                phase_detail="Subagent 审批通过，正在综合执行和验证结果生成最终回答",
                answer_detail="Subagent 审批恢复后的最终回答已生成",
                done_detail="Subagent 审批恢复执行已完成并写回会话状态",
                key_point="Implementation Subagent 审批通过后会执行受控写入，并由 Verification Subagent 独立检查。",
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
            pre_plan = self._pre_plan_route(run.message, step_no=step_no, prior_steps=run.completed_steps)
            if pre_plan:
                plan = pre_plan
                planning_trace = _pre_plan_trace(plan)
            else:
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
            run.plan = plan
            self._remember_plan(run, step_no, plan)
            plan_detail = "Harness 预规划路由生成行动计划" if planning_trace["source"] == "pre_plan_guard" else "模型生成行动计划"
            plan_entry = self._record(
                run,
                f"plan-{step_no}",
                AgentState.PLANNING,
                "completed",
                plan_detail,
                {"loop_step": step_no, **plan},
            )
            yield _stream_event("ledger", _ledger_to_dict(plan_entry))
            yield _stream_event("plan", {"loop_step": step_no, **plan})

            if plan.get("action") == "delegate_batch":
                delegation = yield from self._execute_delegation_batch_stream(
                    run=run,
                    plan=plan,
                    selected_skills=selected_skills,
                    loop_step_no=step_no,
                )
                if not delegation["ok"]:
                    run.current_loop_step = step_no + 1
                    continue
                run.current_loop_step = step_no + 1
                continue

            if plan.get("action") == "delegate":
                delegation = yield from self._execute_delegation_stream(
                    run=run,
                    plan=plan,
                    selected_skills=selected_skills,
                    loop_step_no=step_no,
                )
                if delegation.get("needs_approval"):
                    return delegation
                if not delegation["ok"]:
                    run.current_loop_step = step_no + 1
                    continue
                run.current_loop_step = step_no + 1
                continue

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

    def _execute_delegation_stream(
        self,
        run: ExecutionRun,
        plan: dict,
        selected_skills: list[SkillDescriptor],
        loop_step_no: int,
    ):
        task = self._subagent_task_from_plan(run=run, plan=plan, selected_skills=selected_skills)
        decision = self.subagent_policy.decide(task)
        if decision == "ask" and run.auto_approve_tools:
            decision = "allow"
        delegate_status = "completed" if decision == "allow" else ("pending" if decision == "ask" else "failed")
        delegate_entry = self._record(
            run,
            f"delegate-{loop_step_no}",
            AgentState.PLANNING,
            delegate_status,
            "完成 Subagent 委派裁决",
            {
                "loop_step": loop_step_no,
                "decision": decision,
                "task": task.to_dict(),
            },
        )
        yield _stream_event("ledger", _ledger_to_dict(delegate_entry))
        yield _stream_event("delegate", delegate_entry.data)

        if decision == "ask":
            run.status = "pending_approval"
            tool_call = ToolCall(
                name=f"subagent.{task.role}",
                arguments={**plan, "task": task.to_dict()},
            )
            ticket = ApprovalTicket(
                approval_id=uuid4().hex,
                run_id=run.run_id,
                step_id=delegate_entry.step_id,
                tool_call=tool_call,
                loop_step_no=loop_step_no,
            )
            self._pending_approvals[ticket.approval_id] = ticket
            run.pending_approval_id = ticket.approval_id
            approval_entry = self._record(
                run,
                f"subagent-approval-{loop_step_no}",
                AgentState.PENDING_APPROVAL,
                "pending",
                "Subagent 委派等待用户审批",
                _approval_to_dict(ticket),
                parent_step_id=delegate_entry.step_id,
            )
            yield _stream_event("ledger", _ledger_to_dict(approval_entry))
            yield _stream_event("approval_required", _approval_to_dict(ticket))
            tool_result = ToolResult(
                ok=False,
                tool_name=tool_call.name,
                error="Subagent delegation requires approval",
            )
            yield _stream_event("tool_result", _tool_result_to_dict(tool_result))
            return {
                "ok": False,
                "tool_result": tool_result,
                "needs_approval": True,
                "pending_approval": ticket,
            }

        if decision == "deny":
            result = SubAgentResult(
                task_id=task.task_id,
                parent_run_id=run.run_id,
                role=task.role,
                ok=False,
                summary="Subagent 委派未执行",
                risks=[f"subagent policy decision: {decision}"],
                missing_evidence=["委派未被允许，未产生 worker 证据"],
                proposed_next_actions=["coordinator 应缩小任务边界或改用普通回答"],
            )
            synthesis = self._synthesize_subagent_result(task, result)
            self._remember_subagent_result(run, loop_step_no, result, synthesis)
            yield from self._record_synthesis_stream(run, loop_step_no, synthesis)
            return {"ok": False, "result": result, "synthesis": synthesis, "needs_approval": False}

        result = yield from self._execute_approved_subagent_stream(
            run=run,
            task=task,
            plan=plan,
            loop_step_no=loop_step_no,
            parent_step_id=delegate_entry.step_id,
            resumed=False,
        )
        synthesis = self._synthesize_subagent_result(task, result)
        self._remember_subagent_result(run, loop_step_no, result, synthesis)
        yield from self._record_synthesis_stream(run, loop_step_no, synthesis)
        return {"ok": result.ok, "result": result, "synthesis": synthesis, "needs_approval": False}

    def _execute_delegation_batch_stream(
        self,
        run: ExecutionRun,
        plan: dict,
        selected_skills: list[SkillDescriptor],
        loop_step_no: int,
    ):
        tasks = self._subagent_tasks_from_batch_plan(run=run, plan=plan, selected_skills=selected_skills)
        rejected: list[SubAgentResult] = []
        allowed: list[SubAgentTask] = []
        for task in tasks:
            decision = self.subagent_policy.decide(task)
            if decision == "allow" and task.role == "research":
                allowed.append(task)
                continue
            rejected.append(
                SubAgentResult(
                    task_id=task.task_id,
                    parent_run_id=run.run_id,
                    role=task.role,
                    ok=False,
                    summary="Subagent batch item 未执行",
                    risks=[f"batch policy decision: {decision}", "batch 只允许并行 research task"],
                    missing_evidence=["该 batch item 未产生 worker 证据"],
                    proposed_next_actions=["coordinator 应拆成单独 delegate 或缩小任务边界"],
                )
            )

        batch_entry = self._record(
            run,
            f"delegate-batch-{loop_step_no}",
            AgentState.PLANNING,
            "completed" if allowed else "failed",
            "完成 Subagent 批量委派裁决",
            {
                "loop_step": loop_step_no,
                "allowed_count": len(allowed),
                "rejected_count": len(rejected),
                "tasks": [task.to_dict() for task in tasks],
            },
        )
        yield _stream_event("ledger", _ledger_to_dict(batch_entry))
        yield _stream_event("delegate_batch", batch_entry.data)

        start_step_ids: dict[str, str] = {}
        for task in allowed:
            start_entry = self._record(
                run,
                f"subagent-start-{loop_step_no}-{task.task_id}",
                AgentState.SUBAGENT_RUNNING,
                "running",
                "Research Subagent 并行任务开始执行",
                {
                    "loop_step": loop_step_no,
                    "task_id": task.task_id,
                    "role": task.role,
                    "objective": task.objective,
                    "allowed_tools": task.allowed_tools,
                    "allowed_paths": task.allowed_paths,
                },
                parent_step_id=batch_entry.step_id,
            )
            start_step_ids[task.task_id] = start_entry.step_id
            yield _stream_event("ledger", _ledger_to_dict(start_entry))
            yield _stream_event("subagent_start", start_entry.data)

        results: list[SubAgentResult] = list(rejected)
        if allowed:
            max_workers = min(4, len(allowed))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {executor.submit(self.research_subagent.run, task): task for task in allowed}
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = SubAgentResult(
                            task_id=task.task_id,
                            parent_run_id=run.run_id,
                            role=task.role,
                            ok=False,
                            summary="Research Subagent 并行任务执行失败",
                            risks=[str(exc)],
                            missing_evidence=["worker 执行异常，未产生完整证据"],
                            proposed_next_actions=["coordinator 应回退到串行 research 或缩小任务"],
                        )
                    results.append(result)
                    result_entry = self._record(
                        run,
                        f"subagent-result-{loop_step_no}-{task.task_id}",
                        AgentState.SUBAGENT_RUNNING,
                        "completed" if result.ok else "failed",
                        "Research Subagent 并行任务返回结构化结果",
                        {
                            "loop_step": loop_step_no,
                            "task_id": result.task_id,
                            "role": result.role,
                            "ok": result.ok,
                            "summary": result.summary,
                            "findings_count": len(result.findings),
                            "evidence_count": len(result.evidence),
                            "risk_count": len(result.risks),
                            "missing_evidence_count": len(result.missing_evidence),
                            "result": result.to_dict(),
                        },
                        parent_step_id=start_step_ids.get(task.task_id),
                    )
                    yield _stream_event("ledger", _ledger_to_dict(result_entry))
                    yield _stream_event("subagent_result", result_entry.data)

        synthesis = self._synthesize_subagent_batch_results(results)
        self._remember_subagent_batch_results(run, loop_step_no, results, synthesis)
        yield from self._record_synthesis_stream(run, loop_step_no, synthesis)
        return {
            "ok": bool(allowed) and all(result.ok for result in results),
            "results": results,
            "synthesis": synthesis,
            "needs_approval": False,
        }

    def _execute_approved_subagent_stream(
        self,
        run: ExecutionRun,
        task: SubAgentTask,
        plan: dict,
        loop_step_no: int,
        parent_step_id: str | None,
        resumed: bool,
    ):
        start_step = "subagent-resume" if resumed else "subagent-start"
        start_detail = "审批已通过，恢复执行 Subagent" if resumed else "Subagent 开始执行"
        start_entry = self._record(
            run,
            f"{start_step}-{loop_step_no}",
            AgentState.SUBAGENT_RUNNING,
            "running",
            start_detail,
            {
                "loop_step": loop_step_no,
                "task_id": task.task_id,
                "role": task.role,
                "objective": task.objective,
                "allowed_tools": task.allowed_tools,
                "allowed_paths": task.allowed_paths,
            },
            parent_step_id=parent_step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(start_entry))
        yield _stream_event("subagent_start", start_entry.data)

        try:
            if task.role == "research":
                result = self.research_subagent.run(task)
            elif task.role == "verification":
                result = self.verification_subagent.run(task)
            elif task.role == "implementation":
                files = plan.get("files") if isinstance(plan.get("files"), list) else []
                result = self.implementation_subagent.run(task, files=files)
            else:
                raise ValueError(f"Unsupported subagent role: {task.role}")
        except Exception as exc:
            result = SubAgentResult(
                task_id=task.task_id,
                parent_run_id=run.run_id,
                role=task.role,
                ok=False,
                summary="Subagent 执行失败",
                risks=[str(exc)],
                missing_evidence=["worker 执行异常，未产生完整证据"],
                proposed_next_actions=["coordinator 应回退到普通回答或重新委派更小任务"],
            )

        if task.role == "implementation":
            verification = yield from self._run_post_implementation_verification_stream(
                run=run,
                implementation_task=task,
                implementation_result=result,
                loop_step_no=loop_step_no,
                parent_step_id=start_entry.step_id,
            )
            result.evidence.append(
                {
                    "type": "verification_result",
                    "ok": verification.ok,
                    "summary": verification.summary,
                    "missing_evidence": verification.missing_evidence,
                    "risks": verification.risks,
                }
            )
            if not verification.ok:
                result.ok = False
                result.risks.extend(verification.risks)
                result.missing_evidence.extend(verification.missing_evidence)

        result_entry = self._record(
            run,
            f"subagent-result-{loop_step_no}",
            AgentState.SUBAGENT_RUNNING,
            "completed" if result.ok else "failed",
            "Subagent 返回结构化结果",
            {
                "loop_step": loop_step_no,
                "task_id": result.task_id,
                "role": result.role,
                "ok": result.ok,
                "summary": result.summary,
                "findings_count": len(result.findings),
                "evidence_count": len(result.evidence),
                "risk_count": len(result.risks),
                "missing_evidence_count": len(result.missing_evidence),
                "result": result.to_dict(),
            },
            parent_step_id=start_entry.step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(result_entry))
        yield _stream_event("subagent_result", result_entry.data)

        return result

    def _run_post_implementation_verification_stream(
        self,
        run: ExecutionRun,
        implementation_task: SubAgentTask,
        implementation_result: SubAgentResult,
        loop_step_no: int,
        parent_step_id: str | None,
    ):
        verification_task = SubAgentTask.create(
            parent_run_id=run.run_id,
            role="verification",
            objective=f"独立验证 implementation subagent 的结果: {implementation_task.objective}",
            user_message=run.message,
            relevant_history=run.history_snapshot[-4:],
            selected_skill_summaries=[],
            prior_observations=[
                *run.completed_steps,
                {
                    "step_no": loop_step_no,
                    "subagent_result": implementation_result.to_dict(),
                },
            ],
            allowed_tools=["repo.search", "repo.read"],
            allowed_paths=implementation_task.allowed_paths,
            constraints=["不共享 implementation worker 的 scratchpad，只验证 coordinator 可见证据"],
            max_steps=2,
        )
        verify_entry = self._record(
            run,
            f"verification-{loop_step_no}",
            AgentState.SUBAGENT_RUNNING,
            "running",
            "Verification Subagent 开始独立验证",
            {
                "loop_step": loop_step_no,
                "task_id": verification_task.task_id,
                "role": verification_task.role,
                "objective": verification_task.objective,
                "allowed_paths": verification_task.allowed_paths,
            },
            parent_step_id=parent_step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(verify_entry))
        yield _stream_event("verification", verify_entry.data)
        verification_result = self.verification_subagent.run(verification_task)
        result_entry = self._record(
            run,
            f"verification-result-{loop_step_no}",
            AgentState.SUBAGENT_RUNNING,
            "completed" if verification_result.ok else "failed",
            "Verification Subagent 返回独立验证结果",
            {
                "loop_step": loop_step_no,
                "task_id": verification_result.task_id,
                "ok": verification_result.ok,
                "summary": verification_result.summary,
                "findings_count": len(verification_result.findings),
                "evidence_count": len(verification_result.evidence),
                "risk_count": len(verification_result.risks),
                "missing_evidence_count": len(verification_result.missing_evidence),
                "result": verification_result.to_dict(),
            },
            parent_step_id=verify_entry.step_id,
        )
        yield _stream_event("ledger", _ledger_to_dict(result_entry))
        yield _stream_event("verification", result_entry.data)
        return verification_result

    def _record_synthesis_stream(
        self,
        run: ExecutionRun,
        loop_step_no: int,
        synthesis: SynthesisResult,
    ):
        synthesis_entry = self._record(
            run,
            f"synthesis-{loop_step_no}",
            AgentState.SYNTHESIZING,
            "completed",
            "Coordinator 综合 Subagent 结果",
            {"loop_step": loop_step_no, **synthesis.to_dict()},
        )
        yield _stream_event("ledger", _ledger_to_dict(synthesis_entry))
        yield _stream_event("synthesis", synthesis_entry.data)

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
        pre_plan = self._pre_plan_route(message, step_no=step_no, prior_steps=prior_steps)
        if pre_plan:
            return pre_plan, _pre_plan_trace(pre_plan)

        request_messages = messages or self._planning_messages(message, history, skills)
        planning_tools = tools or self.tool_registry.list_openai_tools()
        try:
            raw_response = self.model_client.plan(request_messages, planning_tools)
            parsed = _plan_from_model_response(raw_response)
            if _should_answer_after_research_delegate(message, prior_steps) and parsed.get("action") != "answer":
                guarded_answer = {
                    "action": "answer",
                    "arguments": {},
                    "reason": "research subagent already produced evidence; synthesize instead of calling another tool",
                }
                return guarded_answer, {
                    "raw_output": str(raw_response.get("content") or ""),
                    "parsed_plan": parsed,
                    "source": "guarded_research_synthesis",
                    "error": None,
                    "tool_calls": raw_response.get("tool_calls") or [],
                }
            if parsed.get("action") in {"answer", "tool", "delegate", "delegate_batch"}:
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

    def _pre_plan_route(self, message: str, step_no: int = 1, prior_steps: list[dict] | None = None) -> dict | None:
        if step_no == 1 and not prior_steps:
            return _research_delegate_plan_from_message(message)
        if _should_answer_after_research_delegate(message, prior_steps):
            return {
                "action": "answer",
                "arguments": {},
                "reason": "research subagent already produced evidence; synthesize instead of calling planner again",
            }
        return None

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
本轮计划最终会被 Harness 归一化为四种 action：answer、tool、delegate、delegate_batch。
你不需要总是手写 JSON：
- answer：如果无需外部能力，直接用自然语言简短说明原因；Harness 会把它归一化为 answer。
- tool：如果需要外部能力，优先发起系统注册的 tool call；Harness 会把 tool call 归一化为 tool。
- delegate：如果需要 subagent，请输出合法 JSON delegate 计划。
- delegate_batch：如果需要多个并行只读 research subagent，请输出合法 JSON delegate_batch 计划。
如果需要外部能力，请发起 tool call。
如果问题需要先做只读代码/文档调查，可以输出 JSON 形式的 delegate 计划，请求 research subagent。
如果需要独立检查已有观察或执行结果，可以请求 verification subagent。
如果确实需要受控写入文件，可以请求 implementation subagent；必须给 allowed_paths 和 files，是否执行由 Harness 审批决定。
如果有多个互相独立的只读调查任务，可以输出 delegate_batch；batch 只允许 research，不允许 implementation。
如果不需要工具，请直接用自然语言简短说明原因，不要输出 Markdown。
你会收到 previous_steps，里面包含前面步骤的 plan 和 tool_result；如果已有观察足够回答，就停止继续调工具。

可用技能：
{skill_text}

规则：
1. 优先遵循 Skill 合约中的 trigger、preferred_tools、planner_hint。
2. 如果某个 Skill 提供了解析脚本或声明式工具定义，优先使用它，而不是自行编造调用方式。
3. 如果某个 Skill 只有脚本没有专用工具，可以先使用 skill.scripts.list，再使用 skill.python.run 执行明确脚本。
4. delegate role 只能是 research、verification、implementation；delegate_batch 只能包含 research；不要假装 subagent 已经执行。
5. 如果 previous_steps 已经包含 subagent_result 和 synthesis，必须先消化这些观察，再决定是否继续。
6. implementation 必须提供明确 files: [{{"path": "...", "content": "..."}}]，并限制 allowed_paths。
7. 如果没有合适工具或安全边界不清楚，直接说明无需工具或需要用户补充。
8. 不要编造工具结果，不要调用未注册工具。

delegate JSON 示例：
{{"action":"delegate","role":"research","objective":"检查聊天智能体当前 query loop 的实现位置","allowed_tools":["repo.search","repo.read"],"allowed_paths":["app/agents","tests"],"reason":"需要先隔离做只读调查"}}

delegate_batch JSON 示例：
{{"action":"delegate_batch","tasks":[{{"role":"research","objective":"调查 app/agents 目录","allowed_tools":["repo.search","repo.read"],"allowed_paths":["app/agents"]}},{{"role":"research","objective":"调查 tests 目录","allowed_tools":["repo.search","repo.read"],"allowed_paths":["tests"]}}],"reason":"两个只读调查互相独立，可以并行执行"}}
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
        research_plan = _research_delegate_plan_from_message(message)
        if research_plan and parsed.get("action") in {"answer", "tool"}:
            return research_plan
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

    def _subagent_task_from_plan(
        self,
        run: ExecutionRun,
        plan: dict,
        selected_skills: list[SkillDescriptor],
    ) -> SubAgentTask:
        role = str(plan.get("role") or "research")
        objective = str(plan.get("objective") or plan.get("reason") or run.message)
        allowed_tools = plan.get("allowed_tools")
        allowed_paths = plan.get("allowed_paths")
        constraints = plan.get("constraints")
        default_tools = ["repo.write"] if role == "implementation" else ["repo.search", "repo.read"]
        try:
            max_steps = int(plan.get("max_steps") or 2)
        except (TypeError, ValueError):
            max_steps = 2
        return SubAgentTask.create(
            parent_run_id=run.run_id,
            role=role,
            objective=objective,
            user_message=run.message,
            relevant_history=run.history_snapshot[-4:],
            selected_skill_summaries=self._skill_summaries(selected_skills),
            prior_observations=run.completed_steps,
            allowed_tools=allowed_tools if isinstance(allowed_tools, list) else default_tools,
            allowed_paths=allowed_paths if isinstance(allowed_paths, list) else ["app/agents", "tests"],
            constraints=constraints if isinstance(constraints, list) else [],
            max_steps=max_steps,
        )

    def _subagent_tasks_from_batch_plan(
        self,
        run: ExecutionRun,
        plan: dict,
        selected_skills: list[SkillDescriptor],
    ) -> list[SubAgentTask]:
        raw_tasks = plan.get("tasks")
        if not isinstance(raw_tasks, list):
            return []
        tasks: list[SubAgentTask] = []
        for raw in raw_tasks[:6]:
            if not isinstance(raw, dict):
                continue
            role = str(raw.get("role") or "research")
            objective = str(raw.get("objective") or raw.get("reason") or run.message)
            allowed_tools = raw.get("allowed_tools")
            allowed_paths = raw.get("allowed_paths")
            constraints = raw.get("constraints")
            try:
                max_steps = int(raw.get("max_steps") or 2)
            except (TypeError, ValueError):
                max_steps = 2
            tasks.append(
                SubAgentTask.create(
                    parent_run_id=run.run_id,
                    role=role,
                    objective=objective,
                    user_message=run.message,
                    relevant_history=run.history_snapshot[-4:],
                    selected_skill_summaries=self._skill_summaries(selected_skills),
                    prior_observations=run.completed_steps,
                    allowed_tools=allowed_tools if isinstance(allowed_tools, list) else ["repo.search", "repo.read"],
                    allowed_paths=allowed_paths if isinstance(allowed_paths, list) else ["app/agents", "tests"],
                    constraints=constraints if isinstance(constraints, list) else ["parallel_safe_research_only"],
                    max_steps=max_steps,
                )
            )
        return tasks

    def _skill_summaries(self, skills: list[SkillDescriptor]) -> list[dict]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "source": skill.source,
                "preferred_tools": list(skill.contract.routing.preferred_tools),
            }
            for skill in skills
        ]

    def _synthesize_subagent_result(self, task: SubAgentTask, result: SubAgentResult) -> SynthesisResult:
        accepted = list(result.findings) if result.ok else []
        rejected = list(result.risks) if result.risks else []
        if result.ok:
            reason = "research 结果已压缩为 coordinator 可使用的证据，继续进入下一轮规划"
            next_action = "answer"
        else:
            reason = "subagent 未产生可靠证据，coordinator 应回退或缩小任务"
            next_action = "ask_user" if result.missing_evidence else "answer"
        return SynthesisResult(
            accepted_findings=accepted,
            rejected_findings=rejected,
            conflicts=[],
            next_action=next_action,
            reason=reason,
        )

    def _synthesize_subagent_batch_results(self, results: list[SubAgentResult]) -> SynthesisResult:
        accepted: list[str] = []
        rejected: list[str] = []
        missing_count = 0
        for result in results:
            if result.ok:
                accepted.extend(result.findings)
            else:
                rejected.extend(result.risks)
                missing_count += len(result.missing_evidence)
        ok_count = sum(1 for result in results if result.ok)
        reason = f"并行 research 完成：{ok_count}/{len(results)} 个任务产生可靠结果"
        if missing_count:
            reason += f"，另有 {missing_count} 条证据缺口"
        return SynthesisResult(
            accepted_findings=accepted,
            rejected_findings=rejected,
            conflicts=[],
            next_action="answer",
            reason=reason,
        )

    def _remember_subagent_result(
        self,
        run: ExecutionRun,
        step_no: int,
        result: SubAgentResult,
        synthesis: SynthesisResult,
    ) -> None:
        step = self._ensure_completed_step(run, step_no)
        step["subagent_result"] = result.to_dict()
        step["synthesis"] = synthesis.to_dict()

    def _remember_subagent_batch_results(
        self,
        run: ExecutionRun,
        step_no: int,
        results: list[SubAgentResult],
        synthesis: SynthesisResult,
    ) -> None:
        step = self._ensure_completed_step(run, step_no)
        step["subagent_results"] = [result.to_dict() for result in results]
        step["synthesis"] = synthesis.to_dict()

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
    parsed_content = _json_plan_from_text(content)
    if parsed_content and parsed_content.get("action") in {"answer", "tool", "delegate", "delegate_batch"}:
        return parsed_content
    if not content:
        content = "model determined no tool was required"
    return {
        "action": "answer",
        "arguments": {},
        "reason": content,
    }


def _json_plan_from_text(content: str) -> dict | None:
    if not content:
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    action = parsed.get("action")
    if action not in {"answer", "tool", "delegate", "delegate_batch"}:
        return None
    if action == "tool":
        parsed.setdefault("arguments", {})
    if action == "answer":
        parsed.setdefault("arguments", {})
    if action == "delegate":
        parsed.setdefault("role", "research")
        default_tools = ["repo.write"] if parsed.get("role") == "implementation" else ["repo.search", "repo.read"]
        parsed.setdefault("allowed_tools", default_tools)
        parsed.setdefault("allowed_paths", ["app/agents", "tests"])
    if action == "delegate_batch":
        parsed.setdefault("tasks", [])
    return parsed


def _research_delegate_plan_from_message(message: str) -> dict | None:
    paths = _extract_research_paths(message)
    if not paths:
        return None
    return {
        "action": "delegate",
        "role": "research",
        "objective": message,
        "allowed_tools": ["repo.search", "repo.read"],
        "allowed_paths": paths,
        "reason": "Harness guard detected a code/file research request with explicit paths",
    }


def _pre_plan_trace(plan: dict) -> dict:
    return {
        "raw_output": None,
        "parsed_plan": None,
        "source": "pre_plan_guard",
        "error": None,
        "tool_calls": [],
        "final_plan": plan,
    }


def _should_answer_after_research_delegate(message: str, prior_steps: list[dict] | None) -> bool:
    if not _extract_research_paths(message):
        return False
    for step in prior_steps or []:
        if not isinstance(step, dict):
            continue
        if isinstance(step.get("subagent_result"), dict):
            return True
        if isinstance(step.get("subagent_results"), list):
            return True
    return False


def _extract_research_paths(message: str) -> list[str]:
    paths: list[str] = []
    root = project_root().resolve()
    pattern = r"(?<![\w./-])([A-Za-z0-9_./-]+(?:\.(?:py|md|json|ya?ml|txt|ipynb))?)(?![\w./-])"
    for match in re.finditer(pattern, message):
        path = match.group(1).strip("`'\"，,。.;；:：)）]")
        if "/" not in path:
            continue
        if path.startswith("/") or ".." in path.split("/"):
            continue
        try:
            resolved = (root / path).resolve()
        except OSError:
            continue
        if resolved != root and root not in resolved.parents:
            continue
        if not resolved.exists():
            continue
        if path not in paths:
            paths.append(path)
    return paths[:6]


def _subagent_task_from_payload(payload: dict) -> SubAgentTask:
    return SubAgentTask(
        task_id=str(payload.get("task_id") or f"restored-{uuid4().hex[:8]}"),
        parent_run_id=str(payload.get("parent_run_id") or ""),
        role=str(payload.get("role") or "research"),  # type: ignore[arg-type]
        objective=str(payload.get("objective") or ""),
        user_message=str(payload.get("user_message") or ""),
        relevant_history=payload.get("relevant_history") if isinstance(payload.get("relevant_history"), list) else [],
        selected_skill_summaries=payload.get("selected_skill_summaries") if isinstance(payload.get("selected_skill_summaries"), list) else [],
        prior_observations=payload.get("prior_observations") if isinstance(payload.get("prior_observations"), list) else [],
        allowed_tools=payload.get("allowed_tools") if isinstance(payload.get("allowed_tools"), list) else [],
        allowed_paths=payload.get("allowed_paths") if isinstance(payload.get("allowed_paths"), list) else [],
        constraints=payload.get("constraints") if isinstance(payload.get("constraints"), list) else [],
        max_steps=int(payload.get("max_steps") or 2),
    )


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
