"""Email Generator service for creating application emails"""

import logging
from typing import Optional

from src.rag import ResumeRAG
from ..models.requests import EmailTone, EmailLength, EmailType
from ..models.responses import EmailResponse

logger = logging.getLogger(__name__)


class EmailService:
    """Service for generating application emails"""

    # Email templates and guidelines
    TONE_GUIDELINES = {
        EmailTone.professional: "Use formal language, avoid contractions, maintain respectful distance",
        EmailTone.conversational: "Use friendly but professional tone, some contractions OK, show personality",
        EmailTone.enthusiastic: "Show genuine excitement, use dynamic language, express passion for the role",
    }

    LENGTH_GUIDELINES = {
        EmailLength.brief: "Keep it to 3-4 sentences, focus only on key points",
        EmailLength.standard: "Use 2-3 short paragraphs, cover qualifications and interest",
        EmailLength.detailed: "Use 3-4 paragraphs, include specific examples and achievements",
    }

    def __init__(self, rag: ResumeRAG):
        self.rag = rag

    async def generate_email(
        self,
        email_type: EmailType,
        job_description: str,
        company_name: Optional[str] = None,
        recipient_name: Optional[str] = None,
        tone: EmailTone = EmailTone.professional,
        length: EmailLength = EmailLength.standard,
        focus: Optional[str] = None,
    ) -> EmailResponse:
        """Generate an email based on type and parameters"""

        # Get relevant resume context
        if focus == "technical":
            query = "technical skills programming languages frameworks projects"
        elif focus == "leadership":
            query = "leadership management team mentoring experience"
        elif focus == "culture":
            query = "collaboration teamwork values achievements"
        else:
            query = "skills experience achievements summary"

        resume_context = self.rag.retriever.get_context(query, n_results=5)

        # Generate based on email type
        if email_type == EmailType.application:
            return await self._generate_application_email(
                job_description, resume_context, company_name,
                recipient_name, tone, length, focus
            )
        elif email_type == EmailType.followup:
            return await self._generate_followup_email(
                job_description, resume_context, company_name,
                recipient_name, tone, length
            )
        elif email_type == EmailType.thankyou:
            return await self._generate_thankyou_email(
                job_description, resume_context, company_name,
                recipient_name, tone, length
            )
        else:
            return await self._generate_application_email(
                job_description, resume_context, company_name,
                recipient_name, tone, length, focus
            )

    async def _generate_application_email(
        self,
        job_description: str,
        resume_context: str,
        company_name: Optional[str],
        recipient_name: Optional[str],
        tone: EmailTone,
        length: EmailLength,
        focus: Optional[str],
    ) -> EmailResponse:
        """Generate a job application email"""

        company = company_name or "your company"
        greeting = f"Dear {recipient_name}," if recipient_name else "Dear Hiring Manager,"

        prompt = f"""Write a job application email based on the following:

Job Description:
{job_description[:2000]}

My Background (from resume):
{resume_context[:1500]}

Requirements:
- Tone: {self.TONE_GUIDELINES[tone]}
- Length: {self.LENGTH_GUIDELINES[length]}
- Company: {company}
- Greeting: {greeting}
{f"- Focus area: {focus}" if focus else ""}

Structure:
1. Opening: Express interest in the specific role
2. Body: Highlight 2-3 most relevant qualifications/experiences that match the job
3. Closing: Express enthusiasm and call to action

Do NOT include a subject line in the body. Just write the email body starting with the greeting.
Make it specific to this job, not generic. Use concrete examples from the resume context."""

        try:
            body = self.rag.llm_backend.generate(prompt)

            # Generate subject line separately
            subject_prompt = f"Write a professional email subject line for a job application to {company}. Just the subject line, nothing else."
            subject = self.rag.llm_backend.generate(subject_prompt).strip()
            # Clean up subject
            subject = subject.replace("Subject:", "").replace("subject:", "").strip()
            if not subject or len(subject) > 100:
                subject = f"Application for Position at {company}"

            # Generate an alternative version
            alt_prompt = f"""Write a shorter, more direct version of this application email.
Keep the same tone ({tone.value}) but make it more concise.
Original resume context: {resume_context[:500]}
Job highlights: {job_description[:500]}

Start directly with the greeting: {greeting}"""

            alternative = self.rag.llm_backend.generate(alt_prompt)

            return EmailResponse(
                subject=subject,
                body=body.strip(),
                email_type=EmailType.application.value,
                variations=[alternative.strip()],
            )

        except Exception as e:
            logger.error(f"Failed to generate application email: {e}")
            return self._fallback_application_email(company, recipient_name)

    async def _generate_followup_email(
        self,
        job_description: str,
        resume_context: str,
        company_name: Optional[str],
        recipient_name: Optional[str],
        tone: EmailTone,
        length: EmailLength,
    ) -> EmailResponse:
        """Generate a follow-up email"""

        company = company_name or "your company"
        greeting = f"Dear {recipient_name}," if recipient_name else "Dear Hiring Manager,"

        prompt = f"""Write a follow-up email after submitting a job application.

Context:
- Company: {company}
- Role details: {job_description[:1000]}
- Tone: {self.TONE_GUIDELINES[tone]}

The email should:
1. Reference the previous application
2. Reiterate interest in the role
3. Add one new point of value (skill, achievement, or insight)
4. Ask about next steps professionally

Start with: {greeting}
Keep it brief and professional. Do not include a subject line in the body."""

        try:
            body = self.rag.llm_backend.generate(prompt)

            return EmailResponse(
                subject=f"Following Up on My Application - {company}",
                body=body.strip(),
                email_type=EmailType.followup.value,
                variations=None,
            )

        except Exception as e:
            logger.error(f"Failed to generate followup email: {e}")
            return EmailResponse(
                subject=f"Following Up on My Application",
                body=f"""{greeting}

I hope this message finds you well. I wanted to follow up on my recent application for the position at {company}.

I remain very interested in this opportunity and would welcome the chance to discuss how my background aligns with your needs.

Please let me know if there's any additional information I can provide. I look forward to hearing from you.

Best regards""",
                email_type=EmailType.followup.value,
            )

    async def _generate_thankyou_email(
        self,
        job_description: str,
        resume_context: str,
        company_name: Optional[str],
        recipient_name: Optional[str],
        tone: EmailTone,
        length: EmailLength,
    ) -> EmailResponse:
        """Generate a thank you email after interview"""

        company = company_name or "your company"
        greeting = f"Dear {recipient_name}," if recipient_name else "Dear Hiring Team,"

        prompt = f"""Write a thank you email to send after a job interview.

Context:
- Company: {company}
- Role: {job_description[:500]}
- Tone: {self.TONE_GUIDELINES[tone]}

The email should:
1. Thank them for their time
2. Reference something specific from the conversation (use a placeholder like [specific topic discussed])
3. Reiterate enthusiasm for the role
4. Briefly reinforce your fit

Start with: {greeting}
Keep it sincere and concise. Do not include a subject line in the body."""

        try:
            body = self.rag.llm_backend.generate(prompt)

            return EmailResponse(
                subject=f"Thank You - {company} Interview",
                body=body.strip(),
                email_type=EmailType.thankyou.value,
                variations=None,
            )

        except Exception as e:
            logger.error(f"Failed to generate thankyou email: {e}")
            return EmailResponse(
                subject=f"Thank You for the Interview",
                body=f"""{greeting}

Thank you so much for taking the time to meet with me today. I really enjoyed learning more about the role and the team at {company}.

Our conversation reinforced my enthusiasm for this opportunity. I'm excited about the possibility of contributing to [specific area discussed].

Please don't hesitate to reach out if you need any additional information from me.

Thank you again, and I look forward to the next steps.

Best regards""",
                email_type=EmailType.thankyou.value,
            )

    def _fallback_application_email(
        self,
        company: str,
        recipient_name: Optional[str],
    ) -> EmailResponse:
        """Fallback application email when generation fails"""
        greeting = f"Dear {recipient_name}," if recipient_name else "Dear Hiring Manager,"

        return EmailResponse(
            subject=f"Application for Position at {company}",
            body=f"""{greeting}

I am writing to express my strong interest in the position at {company}. With my background in software engineering and passion for building impactful products, I believe I would be a valuable addition to your team.

Throughout my career, I have developed expertise in [key skills] and have a proven track record of [key achievements]. I am particularly drawn to {company} because of [company values/mission].

I would welcome the opportunity to discuss how my experience aligns with your needs. Thank you for considering my application.

Best regards""",
            email_type=EmailType.application.value,
        )
