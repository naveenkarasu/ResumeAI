"""Dependency injection for FastAPI"""

from functools import lru_cache
from typing import Optional
import logging

from src.rag import ResumeRAG, VectorStore
from .config import get_settings

logger = logging.getLogger(__name__)

# Global RAG instance (singleton)
_rag_instance: Optional[ResumeRAG] = None


def get_rag() -> ResumeRAG:
    """Get or create the RAG instance (singleton pattern)"""
    global _rag_instance

    if _rag_instance is None:
        settings = get_settings()
        logger.info(f"Initializing RAG with backend: {settings.default_backend}")

        try:
            # Initialize RAG with backend name (string)
            _rag_instance = ResumeRAG(
                llm_backend=settings.default_backend
            )
            logger.info("RAG instance initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}")
            raise

    return _rag_instance


def reset_rag(backend_name: Optional[str] = None) -> ResumeRAG:
    """Reset the RAG instance with a new backend"""
    global _rag_instance

    settings = get_settings()
    backend = backend_name or settings.default_backend

    logger.info(f"Resetting RAG with backend: {backend}")

    try:
        _rag_instance = ResumeRAG(
            llm_backend=backend
        )
        logger.info("RAG instance reset successfully")
        return _rag_instance
    except Exception as e:
        logger.error(f"Failed to reset RAG: {e}")
        raise


def get_vector_store() -> VectorStore:
    """Get the vector store from the RAG instance"""
    rag = get_rag()
    return rag.retriever.vector_store


def get_available_backends() -> list[dict]:
    """Get list of available LLM backends with their status"""
    from src.llm_backends import BACKENDS

    available = []
    for name, backend_class in BACKENDS.items():
        try:
            # Try to instantiate to check if API key is available
            backend = backend_class()
            status = "available"
        except Exception as e:
            status = f"unavailable: {str(e)[:50]}"

        available.append({
            "name": name,
            "status": status,
            "model": getattr(backend_class, "DEFAULT_MODEL", "unknown")
        })

    return available
