"""Email Generator API router"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

from ..dependencies import get_rag
from ..services.email_service import EmailService
from ..models.requests import EmailRequest
from ..models.responses import EmailResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])

# Service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance"""
    global _email_service
    if _email_service is None:
        rag = get_rag()
        _email_service = EmailService(rag)
    return _email_service


@router.post(
    "/generate",
    response_model=EmailResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate email",
    description="Generate an application, follow-up, or thank you email",
)
async def generate_email(
    request: EmailRequest,
    service: EmailService = Depends(get_email_service),
) -> EmailResponse:
    """Generate an email"""
    try:
        return await service.generate_email(
            email_type=request.email_type,
            job_description=request.job_description,
            company_name=request.company_name,
            recipient_name=request.recipient_name,
            tone=request.tone,
            length=request.length,
            focus=request.focus,
        )
    except Exception as e:
        logger.error(f"Email generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/application",
    response_model=EmailResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate application email",
    description="Generate a job application email",
)
async def generate_application_email(
    request: EmailRequest,
    service: EmailService = Depends(get_email_service),
) -> EmailResponse:
    """Generate application email (convenience endpoint)"""
    request.email_type = "application"
    return await generate_email(request, service)


@router.post(
    "/followup",
    response_model=EmailResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate follow-up email",
    description="Generate a follow-up email after application",
)
async def generate_followup_email(
    request: EmailRequest,
    service: EmailService = Depends(get_email_service),
) -> EmailResponse:
    """Generate follow-up email (convenience endpoint)"""
    request.email_type = "followup"
    return await generate_email(request, service)


@router.post(
    "/thankyou",
    response_model=EmailResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate thank you email",
    description="Generate a thank you email after interview",
)
async def generate_thankyou_email(
    request: EmailRequest,
    service: EmailService = Depends(get_email_service),
) -> EmailResponse:
    """Generate thank you email (convenience endpoint)"""
    request.email_type = "thankyou"
    return await generate_email(request, service)
