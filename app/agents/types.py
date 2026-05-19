from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Literal


PermissionDecision = Literal["allow", "deny", "ask"]


class AgentState(str, Enum):
    READY = "ready"
    PLANNING = "planning"
    TOOL_PERMISSION = "tool_permission"
    PENDING_APPROVAL = "pending_approval"
    TOOL_RUNNING = "tool_running"
    ANSWERING = "answering"
    DONE = "done"
    FAILED = "failed"


RunStatus = Literal["running", "pending_approval", "completed", "failed"]
ApprovalStatus = Literal["pending", "approved", "denied", "expired"]


@dataclass
class SkillTrigger:
    keywords: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


@dataclass
class SkillResolver:
    script: str
    timeout_seconds: int = 10
    output_format: Literal["json"] = "json"


@dataclass
class SkillRouting:
    preferred_tools: list[str] = field(default_factory=list)
    planner_hint: str | None = None
    answer_hint: str | None = None
    resolver: SkillResolver | None = None


@dataclass
class SkillContract:
    schema_version: str = "1.0"
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    trigger: SkillTrigger = field(default_factory=SkillTrigger)
    routing: SkillRouting = field(default_factory=SkillRouting)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillDescriptor:
    name: str
    description: str
    path: Path
    source: str
    instructions: str
    default_prompt: str | None = None
    contract: SkillContract = field(default_factory=SkillContract)


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    risk_level: Literal["low", "medium", "high"]
    parallel_safe: bool
    handler: Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class LedgerEntry:
    run_id: str
    step_id: str
    step: str
    state: str
    status: str
    detail: str
    parent_step_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalTicket:
    approval_id: str
    run_id: str
    step_id: str
    tool_call: ToolCall
    status: ApprovalStatus = "pending"
    requested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    decision: Literal["approved", "denied"] | None = None


@dataclass
class ExecutionRun:
    run_id: str
    session_id: str
    message: str
    history_snapshot: list[dict[str, str]]
    selected_skill_names: list[str]
    ledger: list[LedgerEntry] = field(default_factory=list)
    status: RunStatus = "running"
    plan: dict[str, Any] = field(default_factory=dict)
    next_step_index: int = 1
    next_model_call_index: int = 1
    pending_approval_id: str | None = None
