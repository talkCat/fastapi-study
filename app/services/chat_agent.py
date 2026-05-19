from app.agents.harness import HarnessChatAgent
from app.agents.skill_runtime import SkillRuntimeAdapter
from app.agents.skills import SkillRegistry
from app.agents.tools import ToolRegistry
from app.core.exceptions import AlreadyExistsException, ValidationException
from app.schemas.chat_agent import (
    ChatAgentApprovalRequest,
    ChatAgentMessageRequest,
    ChatAgentSkillInfo,
    ChatAgentSkillInstallResponse,
    ChatAgentToolInfo,
)


class ChatAgentService:
    def __init__(self):
        self.skill_registry = SkillRegistry()
        self.tool_registry = ToolRegistry(skill_runtime_adapter=SkillRuntimeAdapter(self.skill_registry))
        self.agent = HarnessChatAgent(
            skill_registry=self.skill_registry,
            tool_registry=self.tool_registry,
        )

    def chat(self, payload: ChatAgentMessageRequest) -> dict:
        return self.agent.chat(
            message=payload.message,
            session_id=payload.session_id,
            skill_names=payload.skill_names,
            auto_approve_tools=payload.auto_approve_tools,
            max_steps=payload.max_steps,
        )

    def stream_chat(self, payload: ChatAgentMessageRequest):
        yield from self.agent.stream_chat(
            message=payload.message,
            session_id=payload.session_id,
            skill_names=payload.skill_names,
            auto_approve_tools=payload.auto_approve_tools,
            max_steps=payload.max_steps,
        )

    def approve(self, payload: ChatAgentApprovalRequest) -> dict:
        try:
            return self.agent.resume_approval(
                approval_id=payload.approval_id,
                approved=payload.approved,
            )
        except ValueError as exc:
            raise ValidationException(str(exc)) from exc

    def stream_approve(self, payload: ChatAgentApprovalRequest):
        try:
            yield from self.agent.stream_resume_approval(
                approval_id=payload.approval_id,
                approved=payload.approved,
            )
        except ValueError as exc:
            raise ValidationException(str(exc)) from exc

    def list_skills(self) -> list[ChatAgentSkillInfo]:
        return [_skill_to_schema(skill) for skill in self.skill_registry.list_skills()]

    def list_tools(self) -> list[ChatAgentToolInfo]:
        return [
            ChatAgentToolInfo(
                name=tool.name,
                description=tool.description,
                risk_level=tool.risk_level,
                parallel_safe=tool.parallel_safe,
            )
            for tool in self.tool_registry.list_tools()
        ]

    def install_skill(self, source_path: str, overwrite: bool = False) -> ChatAgentSkillInstallResponse:
        try:
            skill = self.skill_registry.install_unpacked_skill(source_path, overwrite=overwrite)
        except FileExistsError as exc:
            raise AlreadyExistsException(str(exc)) from exc
        except ValueError as exc:
            raise ValidationException(str(exc)) from exc

        return ChatAgentSkillInstallResponse(
            installed=True,
            skill=_skill_to_schema(skill),
            key_point="技能安装只复制已解压且通过校验的 Skill 包；运行时工具仍应放在独立 Tool 目录。",
        )


def _skill_to_schema(skill) -> ChatAgentSkillInfo:
    return ChatAgentSkillInfo(
        name=skill.name,
        description=skill.description,
        source=skill.source,
        path=str(skill.path),
        has_default_prompt=bool(skill.default_prompt),
    )


chat_agent_service = ChatAgentService()
