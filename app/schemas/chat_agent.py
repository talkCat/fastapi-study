from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatAgentMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")
    session_id: str | None = Field(default=None, description="会话 ID；不传则自动创建")
    skill_names: list[str] | None = Field(default=None, description="指定启用的技能名；不传则自动选择")
    auto_approve_tools: bool = Field(False, description="是否自动批准中高风险工具；低风险工具默认允许")
    max_steps: int = Field(4, ge=1, le=8, description="单轮最大工具执行步数")


class ChatAgentSkillInstallRequest(BaseModel):
    source_path: str = Field(..., min_length=1, description="已解压技能包目录路径，目录内必须有 SKILL.md")
    overwrite: bool = Field(False, description="同名技能已存在时是否覆盖")


class ChatAgentSkillInfo(BaseModel):
    name: str
    description: str
    source: str
    path: str
    has_default_prompt: bool


class ChatAgentToolInfo(BaseModel):
    name: str
    description: str
    risk_level: Literal["low", "medium", "high"]
    parallel_safe: bool


class ChatAgentLedgerEntry(BaseModel):
    run_id: str
    step_id: str
    step: str
    state: str
    status: str
    detail: str
    parent_step_id: str | None = None
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)


class ChatAgentApprovalInfo(BaseModel):
    approval_id: str
    run_id: str
    step_id: str
    status: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    requested_at: str
    resolved_at: str | None = None
    decision: str | None = None


class ChatAgentMessageResponse(BaseModel):
    run_id: str
    session_id: str
    status: str
    answer: str
    selected_skills: list[str]
    plan: dict[str, Any]
    tool_result: dict[str, Any] | None = None
    needs_approval: bool
    pending_approval: ChatAgentApprovalInfo | None = None
    ledger: list[ChatAgentLedgerEntry]
    key_point: str


class ChatAgentSkillInstallResponse(BaseModel):
    installed: bool
    skill: ChatAgentSkillInfo
    key_point: str


class ChatAgentApprovalRequest(BaseModel):
    approval_id: str = Field(..., min_length=1, description="待审批票据 ID")
    approved: bool = Field(..., description="是否批准执行该工具调用")
