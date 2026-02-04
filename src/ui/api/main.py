"""FastAPI application for Resume RAG Platform - Production Ready"""

import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time

from .config import get_settings
from .routers import chat_router, settings_router, analyze_router, interview_router, email_router, jobs_router, job_list_router

# Get settings
settings = get_settings()

# Configure logging based on environment
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Pre-initialize RAG if in production
    if settings.is_production:
        try:
            from .dependencies import get_rag
            rag = get_rag()
            doc_count = rag.retriever.vector_store.collection.count()
            logger.info(f"RAG initialized with {doc_count} documents")
        except Exception as e:
            logger.warning(f"RAG pre-initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Resume RAG Platform API")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Resume RAG Platform API - Production Ready

    A RAG-powered system for resume-based Q&A, job matching, interview preparation,
    and application email generation.

    ## Features
    - **Chat**: Conversational interface to query resume content
    - **Job Matching**: Match resume against job descriptions with detailed scoring
    - **Job Analysis**: Analyze job descriptions against resume
    - **Interview Prep**: Practice questions with AI feedback
    - **Email Generation**: Generate tailored application emails

    ## RAG Capabilities
    - Hybrid Search (BM25 + Vector)
    - Cross-Encoder Reranking
    - HyDE Query Enhancement
    - Citation Grounding
    """,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing and logging middleware
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = f"{int(start_time * 1000)}"

    # Log request (only in debug mode to avoid log spam)
    if settings.debug:
        logger.debug(f"[{request_id}] {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add timing headers
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        response.headers["X-Request-ID"] = request_id

        # Log response time for slow requests (> 2s)
        if process_time > 2.0:
            logger.warning(
                f"[{request_id}] Slow request: {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )

        return response

    except Exception as e:
        logger.error(f"[{request_id}] Request failed: {e}", exc_info=True)
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Return different detail level based on environment
    detail = str(exc) if settings.debug else "An unexpected error occurred"

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": detail,
            "path": str(request.url.path),
        },
    )


# Include routers
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(analyze_router)
app.include_router(interview_router)
app.include_router(email_router)
app.include_router(jobs_router)
app.include_router(job_list_router)


# Health check endpoint (always available, even in production)
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    try:
        from .dependencies import get_rag
        rag = get_rag()
        doc_count = rag.retriever.vector_store.collection.count()
        rag_status = "healthy" if doc_count > 0 else "empty"
    except Exception:
        rag_status = "unavailable"

    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "rag_status": rag_status,
    }


# Readiness check (for Kubernetes)
@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check - returns 200 only when app is ready to serve traffic"""
    try:
        from .dependencies import get_rag
        rag = get_rag()
        doc_count = rag.retriever.vector_store.collection.count()
        if doc_count == 0:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "No documents indexed"}
            )
        return {"status": "ready", "documents": doc_count}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": str(e)}
        )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API info"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health",
        "ready": "/ready",
    }


# Run with: python -m src.ui.api.main
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.ui.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level,
        access_log=settings.debug,
    )
