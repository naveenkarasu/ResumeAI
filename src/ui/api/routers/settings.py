"""Settings and status API router"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import time
import logging
import os
from pathlib import Path

from ..dependencies import get_rag, get_available_backends, reset_rag
from ..config import get_settings
from ..models.requests import SettingsUpdateRequest
from ..models.responses import SettingsResponse, StatusResponse, BackendInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])

# Track app start time for uptime
_start_time = time.time()


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Get system status",
    description="Get the current status of the RAG system",
)
async def get_status() -> StatusResponse:
    """Get system status"""
    settings = get_settings()

    try:
        rag = get_rag()
        rag_initialized = True
        active_backend = rag.llm_router.default_backend or "groq"
        indexed_documents = rag.vector_store.count()
    except Exception as e:
        logger.warning(f"RAG not initialized: {e}")
        rag_initialized = False
        active_backend = "none"
        indexed_documents = 0

    # Check component status
    components = {
        "rag": "healthy" if rag_initialized else "unhealthy",
        "vector_store": "healthy" if indexed_documents > 0 else "empty",
        "llm_backend": "healthy" if rag_initialized else "unavailable",
    }

    overall_status = "healthy"
    if not rag_initialized:
        overall_status = "unhealthy"
    elif indexed_documents == 0:
        overall_status = "degraded"

    return StatusResponse(
        status=overall_status,
        version=settings.app_version,
        uptime_seconds=int(time.time() - _start_time),
        rag_initialized=rag_initialized,
        active_backend=active_backend,
        indexed_documents=indexed_documents,
        last_index_time=None,  # TODO: Track this
        components=components,
    )


@router.get(
    "/settings",
    response_model=SettingsResponse,
    summary="Get current settings",
    description="Get the current RAG settings and available backends",
)
async def get_current_settings() -> SettingsResponse:
    """Get current settings"""
    try:
        rag = get_rag()
        current_backend = rag.llm_router.default_backend or "groq"
        indexed_documents = rag.vector_store.count()

        # Get RAG settings
        use_hybrid = getattr(rag.retriever, "use_hybrid", True)
        use_hyde = getattr(rag.retriever, "use_hyde", False)
        use_reranking = hasattr(rag.retriever, "reranker") and rag.retriever.reranker is not None
        use_grounding = True  # Default enabled

        # Count chunks (same as documents for now)
        total_chunks = indexed_documents

    except Exception as e:
        logger.warning(f"Could not get RAG settings: {e}")
        current_backend = "none"
        indexed_documents = 0
        total_chunks = 0
        use_hybrid = True
        use_hyde = False
        use_reranking = True
        use_grounding = True

    # Get available backends
    backends = get_available_backends()
    backend_infos = [
        BackendInfo(
            name=b["name"],
            status=b["status"],
            model=b["model"],
            is_active=(b["name"] == current_backend),
        )
        for b in backends
    ]

    return SettingsResponse(
        backend=current_backend,
        available_backends=backend_infos,
        use_hybrid_search=use_hybrid,
        use_hyde=use_hyde,
        use_reranking=use_reranking,
        use_grounding=use_grounding,
        indexed_documents=indexed_documents,
        total_chunks=total_chunks,
    )


@router.put(
    "/settings",
    response_model=SettingsResponse,
    summary="Update settings",
    description="Update RAG settings including LLM backend",
)
async def update_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    """Update settings"""
    try:
        # If backend is being changed, reset RAG
        if request.backend:
            logger.info(f"Switching backend to: {request.backend}")
            reset_rag(request.backend)

        # Get current RAG and update settings
        rag = get_rag()

        if request.use_hybrid_search is not None:
            rag.retriever.use_hybrid = request.use_hybrid_search

        if request.use_hyde is not None:
            rag.retriever.use_hyde = request.use_hyde

        if request.use_reranking is not None:
            if request.use_reranking and not rag.retriever.reranker:
                from src.rag import Reranker
                rag.retriever.reranker = Reranker()
            elif not request.use_reranking:
                rag.retriever.reranker = None

        # Return updated settings
        return await get_current_settings()

    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/settings/backends",
    response_model=list[BackendInfo],
    summary="Get available backends",
    description="Get list of available LLM backends with their status",
)
async def list_backends() -> list[BackendInfo]:
    """List available LLM backends"""
    backends = get_available_backends()
    return [
        BackendInfo(
            name=b["name"],
            status=b["status"],
            model=b["model"],
            is_active=False,
        )
        for b in backends
    ]


@router.post(
    "/restart",
    summary="Restart server (development only)",
    description="Triggers a server reload when running with --reload flag",
)
async def restart_server():
    """
    Restart the server by touching main.py to trigger uvicorn's file watcher.
    Only works when running with --reload flag.
    """
    settings = get_settings()

    if settings.is_production:
        raise HTTPException(
            status_code=403,
            detail="Server restart is only available in development mode"
        )

    try:
        # Touch main.py to trigger uvicorn reload
        main_file = Path(__file__).parent.parent / "main.py"
        if main_file.exists():
            main_file.touch()
            logger.info("Server restart triggered - touching main.py")
            return {"status": "restarting", "message": "Server will reload shortly"}
        else:
            raise HTTPException(status_code=500, detail="Could not find main.py")
    except Exception as e:
        logger.error(f"Failed to trigger restart: {e}")
        raise HTTPException(status_code=500, detail=str(e))
