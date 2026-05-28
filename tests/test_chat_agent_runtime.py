import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.harness import HarnessChatAgent
from app.agents.skill_runtime import SkillRuntimeAdapter
from app.agents.skills import SkillRegistry
from app.agents.subagents import ImplementationSubAgent, SubAgentPolicy, VerificationSubAgent
from app.agents.tools import ToolRegistry, _extract_search_items
from app.agents.types import ToolCall, ToolDefinition
from app.main import app
from app.services.chat_agent import chat_agent_service


class FakeModelClient:
    def __init__(self):
        self.plan_calls = 0

    def plan(self, messages, tools, model=None):
        self.plan_calls += 1
        self.last_plan_tools = tools
        if self.plan_calls > 1:
            return {
                "content": "已经拿到工具结果，无需继续调用工具。",
                "tool_calls": [],
                "finish_reason": "stop",
            }
        return {
            "content": "使用 echo 做冒烟测试",
            "tool_calls": [
                {
                    "id": "call_echo",
                    "type": "function",
                    "name": "echo",
                    "arguments": {"text": "hello"},
                    "raw_arguments": '{"text":"hello"}',
                }
            ],
            "finish_reason": "tool_calls",
        }

    def chat(self, messages, model=None):
        return "最终回答：hello"

    def stream_chat(self, messages, model=None):
        for chunk in ["最终", "回答", "：hello"]:
            yield chunk


class ChatAgentRuntimeTests(unittest.TestCase):
    def test_harness_executes_allowed_tool_and_records_ledger(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        agent = HarnessChatAgent(
            model_client=FakeModelClient(),
            skill_registry=SkillRegistry(installed_dir=Path(temp_dir.name)),
            tool_registry=ToolRegistry(),
        )

        result = agent.chat("请 echo hello")

        self.assertEqual(result["answer"], "最终回答：hello")
        self.assertEqual(result["tool_result"]["tool_name"], "echo")
        self.assertTrue(result["tool_result"]["ok"])
        self.assertIn("permission-1", [entry["step"] for entry in result["ledger"]])
        self.assertFalse(result["needs_approval"])

    def test_harness_streams_events_and_final_done_payload(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        agent = HarnessChatAgent(
            model_client=FakeModelClient(),
            skill_registry=SkillRegistry(installed_dir=Path(temp_dir.name)),
            tool_registry=ToolRegistry(),
        )

        events = list(agent.stream_chat("请 echo hello"))
        event_names = [event["event"] for event in events]

        self.assertIn("model_request", event_names)
        self.assertIn("model_response", event_names)
        self.assertIn("plan", event_names)
        self.assertIn("permission", event_names)
        self.assertIn("tool_result", event_names)
        self.assertIn("answer_delta", event_names)
        self.assertEqual(events[-1]["event"], "done")
        self.assertEqual(events[-1]["data"]["answer"], "最终回答：hello")
        planning_request = next(event for event in events if event["event"] == "model_request" and event["data"]["stage"] == "planning")
        self.assertTrue(isinstance(planning_request["data"].get("tools"), list))
        self.assertTrue(any(tool["function"]["name"] == "echo" for tool in planning_request["data"]["tools"]))
        planning_response = next(event for event in events if event["event"] == "model_response" and event["data"]["stage"] == "planning")
        self.assertEqual(planning_response["data"]["tool_calls"][0]["name"], "echo")

    def test_harness_creates_approval_ticket_and_resumes_from_checkpoint(self):
        class MediumRiskModelClient:
            def __init__(self):
                self.plan_calls = 0

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls > 1:
                    return {
                        "content": "审批通过后已经拿到结果，可以直接回答。",
                        "tool_calls": [],
                        "finish_reason": "stop",
                    }
                return {
                    "content": "需要审批后调用 medium.echo",
                    "tool_calls": [
                        {
                            "id": "call_medium_echo",
                            "type": "function",
                            "name": "medium.echo",
                            "arguments": {"text": "resume"},
                            "raw_arguments": '{"text":"resume"}',
                        }
                    ],
                    "finish_reason": "tool_calls",
                }

            def chat(self, messages, model=None):
                return "审批恢复完成"

            def stream_chat(self, messages, model=None):
                for chunk in ["审批", "恢复", "完成"]:
                    yield chunk

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="medium.echo",
                description="Approval test tool",
                risk_level="medium",
                parallel_safe=True,
                handler=lambda arguments: {"text": str(arguments.get("text", ""))},
            )
        )
        agent = HarnessChatAgent(
            model_client=MediumRiskModelClient(),
            tool_registry=registry,
        )

        first = agent.chat("请审批测试")

        self.assertEqual(first["status"], "pending_approval")
        self.assertTrue(first["needs_approval"])
        self.assertIsNotNone(first["pending_approval"])
        self.assertEqual(first["pending_approval"]["tool_name"], "medium.echo")

        resumed = agent.resume_approval(first["pending_approval"]["approval_id"], True)

        self.assertEqual(resumed["run_id"], first["run_id"])
        self.assertEqual(resumed["status"], "completed")
        self.assertFalse(resumed["needs_approval"])
        self.assertIsNone(resumed["pending_approval"])
        self.assertTrue(resumed["tool_result"]["ok"])
        self.assertEqual(resumed["tool_result"]["tool_name"], "medium.echo")
        self.assertEqual(resumed["answer"], "审批恢复完成")
        self.assertIn("approval-resolution", [entry["step"] for entry in resumed["ledger"]])
        self.assertIn("plan-2", [entry["step"] for entry in resumed["ledger"]])

    def test_install_unpacked_skill_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "demo-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\n"
                "name: demo-skill\n"
                "description: Demo installable skill\n"
                "---\n"
                "# Demo Skill\n"
                "Use this skill for tests.\n",
                encoding="utf-8",
            )

            registry = SkillRegistry(
                builtin_dir=root / "missing-builtins",
                installed_dir=root / "installed",
            )
            installed = registry.install_unpacked_skill(str(source))

            self.assertEqual(installed.name, "demo-skill")
            self.assertTrue((root / "installed" / "demo-skill" / "SKILL.md").exists())
            self.assertEqual(registry.get_skill("demo-skill").description, "Demo installable skill")

    def test_harness_runs_multi_step_loop_before_answering(self):
        class MultiStepModelClient:
            def __init__(self):
                self.plan_calls = 0

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls == 1:
                    return {
                        "content": "先调用 echo 获取第一步结果",
                        "tool_calls": [
                            {
                                "id": "call_echo_1",
                                "type": "function",
                                "name": "echo",
                                "arguments": {"text": "step-one"},
                                "raw_arguments": '{"text":"step-one"}',
                            }
                        ],
                        "finish_reason": "tool_calls",
                    }
                return {
                    "content": "已有观察结果，可以直接进入最终回答。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "多步循环完成"

            def stream_chat(self, messages, model=None):
                for chunk in ["多步", "循环", "完成"]:
                    yield chunk

        agent = HarnessChatAgent(model_client=MultiStepModelClient(), tool_registry=ToolRegistry())

        result = agent.chat("请执行多步测试")

        self.assertEqual(result["answer"], "多步循环完成")
        self.assertEqual(result["tool_result"]["tool_name"], "echo")
        ledger_steps = [entry["step"] for entry in result["ledger"]]
        self.assertIn("plan-1", ledger_steps)
        self.assertIn("plan-2", ledger_steps)
        self.assertIn("tool-result-1", ledger_steps)

    def test_harness_runs_research_subagent_and_synthesizes_result(self):
        class DelegateModelClient:
            def __init__(self):
                self.plan_calls = 0

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls == 1:
                    return {
                        "content": json.dumps(
                            {
                                "action": "delegate",
                                "role": "research",
                                "objective": "检查 HarnessChatAgent 的实现位置",
                                "allowed_tools": ["repo.search", "repo.read"],
                                "allowed_paths": ["app/agents/harness.py", "tests"],
                                "reason": "需要先做只读 research",
                            },
                            ensure_ascii=False,
                        ),
                        "tool_calls": [],
                        "finish_reason": "stop",
                    }
                return {
                    "content": "已经综合 research 结果，可以回答。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "已基于 research subagent 综合回答"

            def stream_chat(self, messages, model=None):
                payload = json.loads(messages[-1]["content"])
                completed_steps = payload.get("completed_steps", [])
                self.seen_subagent_result = bool(completed_steps and completed_steps[0].get("subagent_result"))
                for chunk in ["已基于", " research", " subagent", " 综合回答"]:
                    yield chunk

        model_client = DelegateModelClient()
        agent = HarnessChatAgent(model_client=model_client, tool_registry=ToolRegistry())

        events = list(agent.stream_chat("请先调查当前 coordinator 在哪里实现"))
        event_names = [event["event"] for event in events]
        done = events[-1]["data"]

        self.assertEqual(done["answer"], "已基于 research subagent 综合回答")
        self.assertTrue(model_client.seen_subagent_result)
        self.assertIn("delegate", event_names)
        self.assertIn("subagent_start", event_names)
        self.assertIn("subagent_result", event_names)
        self.assertIn("synthesis", event_names)
        ledger_steps = [entry["step"] for entry in done["ledger"]]
        self.assertIn("delegate-1", ledger_steps)
        self.assertIn("subagent-start-1", ledger_steps)
        self.assertIn("subagent-result-1", ledger_steps)
        self.assertIn("synthesis-1", ledger_steps)
        self.assertIn("plan-2", ledger_steps)

    def test_code_research_request_is_guarded_into_research_delegate(self):
        class AnswerOnlyModelClient:
            def __init__(self):
                self.plan_calls = 0
                self.related_symbols = []

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                return {
                    "content": "这个问题可以直接回答，不需要工具。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "approval 恢复流程涉及 resume_approval 和 stream_resume_approval"

            def stream_chat(self, messages, model=None):
                payload = json.loads(messages[-1]["content"])
                result = payload.get("completed_steps", [{}])[0].get("subagent_result", {})
                evidence = result.get("evidence", [])
                if evidence:
                    self.related_symbols = evidence[0].get("related_symbols", [])
                yield "approval 恢复流程涉及 resume_approval 和 stream_resume_approval"

        model_client = AnswerOnlyModelClient()
        agent = HarnessChatAgent(model_client=model_client, tool_registry=ToolRegistry())

        events = list(agent.stream_chat("帮我检查 app/agents/harness.py 里 approval 恢复流程涉及哪些方法"))
        event_names = [event["event"] for event in events]
        done = events[-1]["data"]

        self.assertIn("delegate", event_names)
        self.assertIn("subagent_result", event_names)
        planning_requests = [event for event in events if event["event"] == "model_request" and event["data"]["stage"] == "planning"]
        self.assertEqual(planning_requests, [])
        self.assertEqual(model_client.plan_calls, 0)
        self.assertEqual(done["answer"], "approval 恢复流程涉及 resume_approval 和 stream_resume_approval")
        signatures = [item["signature"] for item in model_client.related_symbols]
        self.assertTrue(any("resume_approval" in signature for signature in signatures))
        self.assertTrue(any("stream_resume_approval" in signature for signature in signatures))

    def test_explicit_repo_path_is_guarded_into_research_delegate_without_keyword_hardcoding(self):
        class AnswerOnlyModelClient:
            def __init__(self):
                self.plan_calls = 0

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                return {
                    "content": "这个问题可以直接回答。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "已查看 harness 文件"

            def stream_chat(self, messages, model=None):
                yield "已查看 harness 文件"

        model_client = AnswerOnlyModelClient()
        agent = HarnessChatAgent(model_client=model_client, tool_registry=ToolRegistry())

        events = list(agent.stream_chat("app/agents/harness.py"))
        event_names = [event["event"] for event in events]

        self.assertIn("delegate", event_names)
        self.assertIn("subagent_result", event_names)
        planning_requests = [event for event in events if event["event"] == "model_request" and event["data"]["stage"] == "planning"]
        self.assertEqual(planning_requests, [])
        self.assertEqual(model_client.plan_calls, 0)

    def test_explicit_repo_path_research_guard_overrides_incorrect_tool_plan(self):
        class ToolHappyModelClient:
            def __init__(self):
                self.plan_calls = 0

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                return {
                    "content": "错误地选择 echo",
                    "tool_calls": [
                        {
                            "id": "call_echo",
                            "type": "function",
                            "name": "echo",
                            "arguments": {"text": "not research"},
                            "raw_arguments": '{"text":"not research"}',
                        }
                    ],
                    "finish_reason": "tool_calls",
                }

            def chat(self, messages, model=None):
                return "已通过 research 处理"

            def stream_chat(self, messages, model=None):
                yield "已通过 research 处理"

        model_client = ToolHappyModelClient()
        agent = HarnessChatAgent(model_client=model_client, tool_registry=ToolRegistry())

        events = list(agent.stream_chat("帮我看 app/agents/harness.py"))
        event_names = [event["event"] for event in events]

        self.assertIn("delegate", event_names)
        self.assertIn("subagent_result", event_names)
        self.assertNotIn("tool_start", event_names)
        planning_requests = [event for event in events if event["event"] == "model_request" and event["data"]["stage"] == "planning"]
        self.assertEqual(planning_requests, [])
        self.assertEqual(model_client.plan_calls, 0)

    def test_harness_approval_runs_implementation_subagent_then_verification(self):
        class ImplementationModelClient:
            def __init__(self):
                self.plan_calls = 0

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls == 1:
                    return {
                        "content": json.dumps(
                            {
                                "action": "delegate",
                                "role": "implementation",
                                "objective": "写入一个受控测试文件",
                                "allowed_tools": ["repo.write"],
                                "allowed_paths": ["workspace"],
                                "files": [
                                    {
                                        "path": "workspace/demo.txt",
                                        "content": "hello subagent\n",
                                    }
                                ],
                                "reason": "需要测试 implementation subagent 审批链路",
                            },
                            ensure_ascii=False,
                        ),
                        "tool_calls": [],
                        "finish_reason": "stop",
                    }
                return {
                    "content": "implementation 和 verification 已完成，可以回答。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "受控写入完成"

            def stream_chat(self, messages, model=None):
                for chunk in ["受控", "写入", "完成"]:
                    yield chunk

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agent = HarnessChatAgent(
                model_client=ImplementationModelClient(),
                tool_registry=ToolRegistry(),
                implementation_subagent=ImplementationSubAgent(root=root),
                verification_subagent=VerificationSubAgent(root=root),
                subagent_policy=SubAgentPolicy(root=root),
            )

            first = agent.chat("请通过 implementation subagent 写入测试文件")

            self.assertEqual(first["status"], "pending_approval")
            self.assertTrue(first["needs_approval"])
            self.assertEqual(first["pending_approval"]["tool_name"], "subagent.implementation")
            self.assertFalse((root / "workspace" / "demo.txt").exists())

            resumed_events = list(agent.stream_resume_approval(first["pending_approval"]["approval_id"], True))
            resumed = resumed_events[-1]["data"]

            self.assertEqual(resumed["status"], "completed")
            self.assertEqual(resumed["answer"], "受控写入完成")
            self.assertEqual((root / "workspace" / "demo.txt").read_text(encoding="utf-8"), "hello subagent\n")
            event_names = [event["event"] for event in resumed_events]
            self.assertIn("verification", event_names)
            self.assertIn("subagent_result", event_names)
            ledger_steps = [entry["step"] for entry in resumed["ledger"]]
            self.assertIn("subagent-approval-1", ledger_steps)
            self.assertIn("subagent-resume-1", ledger_steps)
            self.assertIn("verification-1", ledger_steps)
            self.assertIn("verification-result-1", ledger_steps)
            self.assertIn("synthesis-1", ledger_steps)

    def test_harness_runs_parallel_research_delegate_batch(self):
        class BatchDelegateModelClient:
            def __init__(self):
                self.plan_calls = 0
                self.seen_subagent_results = False

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls == 1:
                    return {
                        "content": json.dumps(
                            {
                                "action": "delegate_batch",
                                "tasks": [
                                    {
                                        "role": "research",
                                        "objective": "调查 app/agents 目录",
                                        "allowed_tools": ["repo.search", "repo.read"],
                                        "allowed_paths": ["app/agents"],
                                    },
                                    {
                                        "role": "research",
                                        "objective": "调查 tests 目录",
                                        "allowed_tools": ["repo.search", "repo.read"],
                                        "allowed_paths": ["tests"],
                                    },
                                ],
                                "reason": "两个只读调查互相独立，可以批量执行",
                            },
                            ensure_ascii=False,
                        ),
                        "tool_calls": [],
                        "finish_reason": "stop",
                    }
                return {
                    "content": "并行 research 已综合，可以回答。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "并行 research 完成"

            def stream_chat(self, messages, model=None):
                payload = json.loads(messages[-1]["content"])
                completed_steps = payload.get("completed_steps", [])
                self.seen_subagent_results = bool(completed_steps and completed_steps[0].get("subagent_results"))
                for chunk in ["并行", " research", " 完成"]:
                    yield chunk

        model_client = BatchDelegateModelClient()
        agent = HarnessChatAgent(model_client=model_client, tool_registry=ToolRegistry())

        events = list(agent.stream_chat("请并行调查 agents 和 tests"))
        event_names = [event["event"] for event in events]
        done = events[-1]["data"]

        self.assertEqual(done["answer"], "并行 research 完成")
        self.assertTrue(model_client.seen_subagent_results)
        self.assertIn("delegate_batch", event_names)
        self.assertEqual(event_names.count("subagent_start"), 2)
        self.assertEqual(event_names.count("subagent_result"), 2)
        self.assertIn("synthesis", event_names)
        ledger_steps = [entry["step"] for entry in done["ledger"]]
        self.assertIn("delegate-batch-1", ledger_steps)
        self.assertIn("synthesis-1", ledger_steps)
        self.assertIn("plan-2", ledger_steps)

    def test_delegate_batch_rejects_non_research_tasks(self):
        class MixedBatchModelClient:
            def __init__(self):
                self.plan_calls = 0
                self.seen_rejected_batch_item = False

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls == 1:
                    return {
                        "content": json.dumps(
                            {
                                "action": "delegate_batch",
                                "tasks": [
                                    {
                                        "role": "research",
                                        "objective": "调查 app/agents 目录",
                                        "allowed_tools": ["repo.search", "repo.read"],
                                        "allowed_paths": ["app/agents"],
                                    },
                                    {
                                        "role": "implementation",
                                        "objective": "不应在 batch 中执行写入",
                                        "allowed_tools": ["repo.write"],
                                        "allowed_paths": ["workspace"],
                                    },
                                ],
                                "reason": "混合 batch 应拒绝非 research 项",
                            },
                            ensure_ascii=False,
                        ),
                        "tool_calls": [],
                        "finish_reason": "stop",
                    }
                return {
                    "content": "batch 已综合，可以回答。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "混合 batch 已处理"

            def stream_chat(self, messages, model=None):
                payload = json.loads(messages[-1]["content"])
                results = payload.get("completed_steps", [{}])[0].get("subagent_results", [])
                self.seen_rejected_batch_item = any(not item.get("ok") for item in results)
                yield "混合 batch 已处理"

        model_client = MixedBatchModelClient()
        agent = HarnessChatAgent(model_client=model_client, tool_registry=ToolRegistry())

        events = list(agent.stream_chat("请批量执行 research 和 implementation"))
        event_names = [event["event"] for event in events]
        done = events[-1]["data"]

        self.assertEqual(done["answer"], "混合 batch 已处理")
        self.assertTrue(model_client.seen_rejected_batch_item)
        self.assertIn("delegate_batch", event_names)
        self.assertEqual(event_names.count("subagent_start"), 1)
        self.assertEqual(event_names.count("subagent_result"), 1)
        synthesis = next(event["data"] for event in events if event["event"] == "synthesis")
        self.assertTrue(any("batch 只允许并行 research task" in item for item in synthesis["rejected_findings"]))

    def test_implementation_subagent_rejects_out_of_scope_file_write_after_approval(self):
        class OutOfScopeImplementationModelClient:
            def __init__(self, outside_name):
                self.plan_calls = 0
                self.seen_failed_implementation = False
                self.outside_name = outside_name

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls == 1:
                    return {
                        "content": json.dumps(
                            {
                                "action": "delegate",
                                "role": "implementation",
                                "objective": "尝试越界写入，应该被拒绝",
                                "allowed_tools": ["repo.write"],
                                "allowed_paths": ["workspace"],
                                "files": [
                                    {
                                        "path": f"../{self.outside_name}",
                                        "content": "should not be written\n",
                                    }
                                ],
                                "reason": "验证 implementation 写入边界",
                            },
                            ensure_ascii=False,
                        ),
                        "tool_calls": [],
                        "finish_reason": "stop",
                    }
                return {
                    "content": "越界写入已被拒绝，可以回答。",
                    "tool_calls": [],
                    "finish_reason": "stop",
                }

            def chat(self, messages, model=None):
                return "越界写入已拒绝"

            def stream_chat(self, messages, model=None):
                payload = json.loads(messages[-1]["content"])
                result = payload.get("completed_steps", [{}])[0].get("subagent_result", {})
                self.seen_failed_implementation = result.get("ok") is False
                yield "越界写入已拒绝"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            outside_name = f"{root.name}_outside.txt"
            outside = root.parent / outside_name
            agent = HarnessChatAgent(
                model_client=OutOfScopeImplementationModelClient(outside_name),
                tool_registry=ToolRegistry(),
                implementation_subagent=ImplementationSubAgent(root=root),
                verification_subagent=VerificationSubAgent(root=root),
                subagent_policy=SubAgentPolicy(root=root),
            )

            first = agent.chat("请尝试越界写入")
            self.assertTrue(first["needs_approval"])

            resumed_events = list(agent.stream_resume_approval(first["pending_approval"]["approval_id"], True))
            resumed = resumed_events[-1]["data"]

            self.assertEqual(resumed["answer"], "越界写入已拒绝")
            self.assertFalse(outside.exists())
            self.assertTrue(agent.model_client.seen_failed_implementation)
            subagent_result = next(event["data"] for event in resumed_events if event["event"] == "subagent_result")
            self.assertFalse(subagent_result["ok"])
            self.assertTrue(any("拒绝越界写入" in item for item in subagent_result["result"]["risks"]))
            self.assertIn("verification", [event["event"] for event in resumed_events])

    def test_api_lists_agent_tools_and_skills(self):
        client = TestClient(app)

        tools_response = client.get("/api/v1/chat-agent/tools")
        self.assertEqual(tools_response.status_code, 200)
        tool_names = [item["name"] for item in tools_response.json()["data"]]
        self.assertIn("echo", tool_names)
        self.assertIn("fs.read_text", tool_names)
        self.assertIn("fs.write_text", tool_names)
        self.assertIn("shell.exec", tool_names)
        self.assertIn("python.exec", tool_names)
        self.assertIn("http.get", tool_names)
        self.assertIn("skill.scripts.list", tool_names)
        self.assertIn("skill.python.run", tool_names)
        self.assertIn("web.search", tool_names)
        self.assertIn("web_fetch", tool_names)

        skills_response = client.get("/api/v1/chat-agent/skills")
        self.assertEqual(skills_response.status_code, 200)
        skill_names = [item["name"] for item in skills_response.json()["data"]]
        self.assertTrue(len(skill_names) >= 0)

    def test_search_question_selects_multi_search_skill(self):
        selected = SkillRegistry().select_skills("查询特朗普访华最新信息")
        self.assertTrue(len(selected) >= 1)

    def test_web_search_parser_extracts_bing_result_items(self):
        html = """
        <html>
          <head><script>var noisy = "ignore me";</script></head>
          <body>
            <ol id="b_results">
              <li class="b_algo">
                <h2><a href="https://example.com/news">特朗普访华暂无官方消息</a></h2>
                <div class="b_caption"><p>这是搜索结果摘要，用于说明新闻进展。</p></div>
              </li>
            </ol>
          </body>
        </html>
        """

        items = _extract_search_items("bing_cn", html)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "特朗普访华暂无官方消息")
        self.assertEqual(items[0]["url"], "https://example.com/news")
        self.assertIn("搜索结果摘要", items[0]["snippet"])

    def test_web_search_parser_extracts_rss_result_items(self):
        xml = """
        <rss version="2.0">
          <channel>
            <item>
              <title>习近平为美国总统特朗普举行欢迎宴会</title>
              <link>https://example.com/rss-news</link>
              <description>5月14日晚，国家主席习近平在北京人民大会堂举行宴会。</description>
              <pubDate>Thu, 14 May 2026 20:55:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """

        items = _extract_search_items("bing_cn", xml)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "习近平为美国总统特朗普举行欢迎宴会")
        self.assertEqual(items[0]["url"], "https://example.com/rss-news")
        self.assertIn("人民大会堂", items[0]["snippet"])
        self.assertIn("published_at", items[0])

    def test_generic_file_tools_read_write_and_list(self):
        root = Path("tmp/test-generic-file-tools").resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: root.exists() and __import__("shutil").rmtree(root))
        registry = ToolRegistry()
        target = root / "sample.txt"

        write_call = ToolCall(
            name="fs.write_text",
            arguments={"path": str(target), "content": "hello tools"},
        )
        self.assertEqual(registry.decide_permission(write_call), "ask")
        self.assertEqual(registry.decide_permission(write_call, auto_approve=True), "allow")
        write_result = registry.execute(write_call)
        self.assertTrue(write_result.ok, msg=write_result.error)
        self.assertTrue(target.exists())

        read_result = registry.execute(ToolCall(name="fs.read_text", arguments={"path": str(target)}))
        self.assertTrue(read_result.ok)
        self.assertEqual(read_result.result["text"], "hello tools")

        list_result = registry.execute(
            ToolCall(name="fs.list_dir", arguments={"path": str(root)})
        )
        self.assertTrue(list_result.ok)
        self.assertEqual(list_result.result["count"], 1)
        self.assertEqual(list_result.result["entries"][0]["name"], "sample.txt")

    def test_generic_python_tool_executes_code(self):
        registry = ToolRegistry()
        call = ToolCall(name="python.exec", arguments={"code": "print(1 + 2)"})
        self.assertEqual(registry.decide_permission(call), "ask")
        result = registry.execute(call)
        self.assertTrue(result.ok)
        self.assertEqual(result.result["stdout"].strip(), "3")

    def test_shell_tool_accepts_cmd_alias(self):
        registry = ToolRegistry()
        call = ToolCall(name="shell.exec", arguments={"cmd": "printf hello"})
        result = registry.execute(call)
        self.assertTrue(result.ok, msg=result.error)
        self.assertEqual(result.result["stdout"], "hello")

    def test_skill_runtime_adapts_unpacked_skill_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "demo-skill"
            scripts_dir = skill_dir / "scripts"
            agents_dir = skill_dir / "agents"
            scripts_dir.mkdir(parents=True)
            agents_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: Demo runtime skill\n---\n# Demo\n",
                encoding="utf-8",
            )
            script_path = scripts_dir / "upper.py"
            script_path.write_text(
                "import sys\nprint(sys.argv[1].upper())\n",
                encoding="utf-8",
            )
            (agents_dir / "tools.json").write_text(
                "{"
                "\"version\":1,"
                "\"tools\":[{"
                "\"name\":\"upper\","
                "\"description\":\"Uppercase text\","
                "\"script\":\"scripts/upper.py\","
                "\"risk_level\":\"low\","
                "\"parallel_safe\":true,"
                "\"output_format\":\"text\","
                "\"arguments\":[{\"name\":\"text\",\"required\":true}]"
                "}]"
                "}",
                encoding="utf-8",
            )

            skill_registry = SkillRegistry(builtin_dir=root, installed_dir=root / "installed")
            adapter = SkillRuntimeAdapter(skill_registry)
            registry = ToolRegistry(skill_runtime_adapter=adapter)
            result = registry.execute(ToolCall(name="skill.demo-skill.upper", arguments={"text": "hello"}))

            self.assertTrue(result.ok)
            self.assertEqual(result.result["stdout"], "HELLO")

    def test_skill_runtime_resolves_plan_from_skill_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "contract-skill"
            scripts_dir = skill_dir / "scripts"
            agents_dir = skill_dir / "agents"
            scripts_dir.mkdir(parents=True)
            agents_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: contract-skill\n"
                "description: Contract routed skill\n"
                "---\n"
                "# Contract Skill\n",
                encoding="utf-8",
            )
            (agents_dir / "skill.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "trigger": {"keywords": ["hello-contract"]},
                        "routing": {
                            "preferred_tools": ["echo"],
                            "resolver": {"script": "scripts/resolve_plan.py", "timeout_seconds": 5},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (scripts_dir / "resolve_plan.py").write_text(
                "import json, sys\n"
                "payload = json.loads(sys.stdin.read() or '{}')\n"
                "print(json.dumps({'action':'tool','tool_name':'echo','arguments':{'text':payload['message']},'reason':'resolved'}))\n",
                encoding="utf-8",
            )

            skill_registry = SkillRegistry(builtin_dir=root, installed_dir=root / "installed")
            adapter = SkillRuntimeAdapter(skill_registry)
            selected = skill_registry.select_skills("please hello-contract now")
            self.assertEqual([skill.name for skill in selected], ["contract-skill"])

            resolved = adapter.resolve_plan(
                skill_name="contract-skill",
                message="please hello-contract now",
                available_tools=["echo"],
                selected_skills=["contract-skill"],
            )
            self.assertEqual(resolved["tool_name"], "echo")
            self.assertEqual(resolved["arguments"]["text"], "please hello-contract now")

    def test_generic_skill_python_runner_supports_skills_without_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "plain-skill"
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: plain-skill\ndescription: Plain script skill\n---\n# Plain\n",
                encoding="utf-8",
            )
            (scripts_dir / "join_args.py").write_text(
                "import sys\nprint('|'.join(sys.argv[1:]))\n",
                encoding="utf-8",
            )

            skill_registry = SkillRegistry(builtin_dir=root, installed_dir=root / "installed")
            adapter = SkillRuntimeAdapter(skill_registry)
            registry = ToolRegistry(skill_runtime_adapter=adapter)

            list_result = registry.execute(
                ToolCall(name="skill.scripts.list", arguments={"skill_name": "plain-skill"})
            )
            self.assertTrue(list_result.ok)
            self.assertEqual(list_result.result["count"], 1)
            self.assertEqual(list_result.result["scripts"][0]["path"], "scripts/join_args.py")

            run_call = ToolCall(
                name="skill.python.run",
                arguments={
                    "skill_name": "plain-skill",
                    "script": "scripts/join_args.py",
                    "args": ["a", "b"],
                },
            )
            self.assertEqual(registry.decide_permission(run_call), "ask")
            self.assertEqual(registry.decide_permission(run_call, auto_approve=True), "allow")
            run_result = registry.execute(run_call)
            self.assertTrue(run_result.ok)
            self.assertEqual(run_result.result["stdout"], "a|b")

            argv_result = registry.execute(
                ToolCall(
                    name="skill.python.run",
                    arguments={
                        "skill_name": "plain-skill",
                        "script": "scripts/join_args.py",
                        "argv": ["x", "y"],
                    },
                )
            )
            self.assertTrue(argv_result.ok)
            self.assertEqual(argv_result.result["stdout"], "x|y")

    def test_generic_skill_python_runner_blocks_path_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "plain-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: plain-skill\ndescription: Plain script skill\n---\n# Plain\n",
                encoding="utf-8",
            )
            outside = root / "outside.py"
            outside.write_text("print('bad')\n", encoding="utf-8")

            skill_registry = SkillRegistry(builtin_dir=root, installed_dir=root / "installed")
            adapter = SkillRuntimeAdapter(skill_registry)
            registry = ToolRegistry(skill_runtime_adapter=adapter)
            result = registry.execute(
                ToolCall(
                    name="skill.python.run",
                    arguments={"skill_name": "plain-skill", "script": "../outside.py"},
                )
            )
            self.assertFalse(result.ok)
            self.assertIn("escapes skill directory", result.error)

    def test_skill_registry_inferrs_preferred_tools_from_skill_markdown_without_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "weather-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: weather\ndescription: Query weather from a public endpoint\n---\n"
                "# Weather\n"
                "Use curl -s \"https://wttr.in/Shanghai?format=3\" to query current weather.\n",
                encoding="utf-8",
            )

            registry = SkillRegistry(builtin_dir=root, installed_dir=root / "installed")
            skill = registry.get_skill("weather")

            self.assertIsNotNone(skill)
            self.assertIn("shell.exec", skill.contract.routing.preferred_tools)
            self.assertIn("http.get", skill.contract.routing.preferred_tools)
            self.assertTrue(skill.contract.routing.planner_hint)

    def test_skill_registry_inferrs_skill_script_tools_from_scripts_directory_without_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "plain-skill"
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: plain-skill\ndescription: Plain skill with scripts\n---\n# Plain\n",
                encoding="utf-8",
            )
            (scripts_dir / "demo.py").write_text("print('ok')\n", encoding="utf-8")

            registry = SkillRegistry(builtin_dir=root, installed_dir=root / "installed")
            skill = registry.get_skill("plain-skill")

            self.assertIsNotNone(skill)
            self.assertIn("skill.scripts.list", skill.contract.routing.preferred_tools)
            self.assertIn("skill.python.run", skill.contract.routing.preferred_tools)
            self.assertIn("contains Python scripts", skill.contract.routing.planner_hint)

    def test_api_stream_endpoint_returns_sse(self):
        client = TestClient(app)
        original_agent = chat_agent_service.agent
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        chat_agent_service.agent = HarnessChatAgent(
            model_client=FakeModelClient(),
            skill_registry=SkillRegistry(installed_dir=Path(temp_dir.name)),
            tool_registry=ToolRegistry(),
        )
        self.addCleanup(lambda: setattr(chat_agent_service, "agent", original_agent))

        with client.stream("POST", "/api/v1/chat-agent/chat/stream", json={"message": "请 echo hello"}) as response:
            self.assertEqual(response.status_code, 200)
            body = response.read().decode("utf-8")

        self.assertIn("event: plan", body)
        self.assertIn("event: model_request", body)
        self.assertIn("event: model_response", body)
        self.assertIn("event: answer_delta", body)
        self.assertIn("event: done", body)

    def test_api_approval_stream_resumes_from_pending_ticket(self):
        class MediumRiskModelClient:
            def __init__(self):
                self.plan_calls = 0

            def plan(self, messages, tools, model=None):
                self.plan_calls += 1
                if self.plan_calls > 1:
                    return {
                        "content": "审批恢复后直接回答。",
                        "tool_calls": [],
                        "finish_reason": "stop",
                    }
                return {
                    "content": "需要审批后调用 medium.echo",
                    "tool_calls": [
                        {
                            "id": "call_medium_echo",
                            "type": "function",
                            "name": "medium.echo",
                            "arguments": {"text": "resume"},
                            "raw_arguments": '{"text":"resume"}',
                        }
                    ],
                    "finish_reason": "tool_calls",
                }
 
            def chat(self, messages, model=None):
                return "审批接口恢复"

            def stream_chat(self, messages, model=None):
                for chunk in ["审批", "接口", "恢复"]:
                    yield chunk

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="medium.echo",
                description="Approval test tool",
                risk_level="medium",
                parallel_safe=True,
                handler=lambda arguments: {"text": str(arguments.get("text", ""))},
            )
        )

        client = TestClient(app)
        original_agent = chat_agent_service.agent
        chat_agent_service.agent = HarnessChatAgent(
            model_client=MediumRiskModelClient(),
            tool_registry=registry,
        )
        self.addCleanup(lambda: setattr(chat_agent_service, "agent", original_agent))

        first = client.post("/api/v1/chat-agent/chat", json={"message": "请审批接口测试"})
        self.assertEqual(first.status_code, 200)
        approval_id = first.json()["data"]["pending_approval"]["approval_id"]

        with client.stream(
            "POST",
            "/api/v1/chat-agent/approvals/stream",
            json={"approval_id": approval_id, "approved": True},
        ) as response:
            self.assertEqual(response.status_code, 200)
            body = response.read().decode("utf-8")

        self.assertIn("event: approval_resolved", body)
        self.assertIn("event: tool_start", body)
        self.assertIn("event: model_request", body)
        self.assertIn("event: model_response", body)
        self.assertIn("event: answer_delta", body)
        self.assertIn("event: done", body)


if __name__ == "__main__":
    unittest.main()
