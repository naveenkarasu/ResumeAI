"""Chat API router"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

from ..dependencies import get_rag
from ..services.chat_service import ChatService
from ..models.requests import ChatRequest
from ..models.responses import ChatResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Service instance (created once per app lifecycle)
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create chat service instance"""
    global _chat_service
    if _chat_service is None:
        rag = get_rag()
        _chat_service = ChatService(rag)
    return _chat_service


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Send a chat message",
    description="Send a message to the RAG system and get a response with citations",
)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Process a chat message"""
    try:
        response = await service.chat(
            message=request.message,
            mode=request.mode,
            job_description=request.job_description,
            use_verification=request.use_verification,
        )
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/suggestions",
    response_model=list[str],
    summary="Get suggested prompts",
    description="Get suggested prompts for the given mode",
)
async def get_suggestions(
    mode: str = "chat",
    service: ChatService = Depends(get_chat_service),
) -> list[str]:
    """Get suggested prompts for a mode"""
    return service.get_suggestions(mode)


@router.get(
    "/history",
    response_model=list[dict],
    summary="Get chat history",
    description="Get chat history for the current session",
)
async def get_history(
    session_id: str = "default",
    service: ChatService = Depends(get_chat_service),
) -> list[dict]:
    """Get chat history for a session"""
    return service.get_history(session_id)


@router.delete(
    "/history",
    summary="Clear chat history",
    description="Clear chat history for the current session",
)
async def clear_history(
    session_id: str = "default",
    service: ChatService = Depends(get_chat_service),
) -> dict:
    """Clear chat history for a session"""
    success = service.clear_history(session_id)
    return {"success": success, "message": "History cleared" if success else "No history found"}
