"""API Routers"""

from .chat import router as chat_router
from .settings import router as settings_router
from .analyze import router as analyze_router
from .interview import router as interview_router
from .email import router as email_router
from .jobs import router as jobs_router
from .job_list import router as job_list_router

__all__ = [
    "chat_router",
    "settings_router",
    "analyze_router",
    "interview_router",
    "email_router",
    "jobs_router",
    "job_list_router",
]
