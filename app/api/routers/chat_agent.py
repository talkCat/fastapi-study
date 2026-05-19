import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.responses import success_response
from app.schemas.chat_agent import (
    ChatAgentApprovalRequest,
    ChatAgentMessageRequest,
    ChatAgentMessageResponse,
    ChatAgentSkillInfo,
    ChatAgentSkillInstallRequest,
    ChatAgentSkillInstallResponse,
    ChatAgentToolInfo,
)
from app.schemas.common import ApiResponse
from app.services.chat_agent import chat_agent_service

router = APIRouter(prefix="/chat-agent", tags=["Harness 聊天智能体"])


@router.post("/chat", response_model=ApiResponse[ChatAgentMessageResponse])
def chat_with_agent(payload: ChatAgentMessageRequest):
    return success_response(chat_agent_service.chat(payload), message="执行成功")


@router.post("/chat/stream")
def stream_chat_with_agent(payload: ChatAgentMessageRequest):
    return StreamingResponse(
        _sse_events(chat_agent_service.stream_chat(payload)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/approvals", response_model=ApiResponse[ChatAgentMessageResponse])
def approve_chat_agent_tool(payload: ChatAgentApprovalRequest):
    return success_response(chat_agent_service.approve(payload), message="审批执行成功")


@router.post("/approvals/stream")
def approve_chat_agent_tool_stream(payload: ChatAgentApprovalRequest):
    return StreamingResponse(
        _sse_events(chat_agent_service.stream_approve(payload)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/skills", response_model=ApiResponse[list[ChatAgentSkillInfo]])
def list_agent_skills():
    return success_response(chat_agent_service.list_skills(), message="查询成功")


@router.post("/skills/install", response_model=ApiResponse[ChatAgentSkillInstallResponse])
def install_agent_skill(payload: ChatAgentSkillInstallRequest):
    return success_response(
        chat_agent_service.install_skill(
            source_path=payload.source_path,
            overwrite=payload.overwrite,
        ),
        message="安装成功",
    )


@router.get("/tools", response_model=ApiResponse[list[ChatAgentToolInfo]])
def list_agent_tools():
    return success_response(chat_agent_service.list_tools(), message="查询成功")


def _sse_events(events):
    for item in events:
        event = item.get("event", "message")
        data = json.dumps(item.get("data", {}), ensure_ascii=False)
        yield f"event: {event}\ndata: {data}\n\n"
