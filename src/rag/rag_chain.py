"""
ResumeAI RAG Chain - Combines retrieval with LLM generation
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

from .retriever import ResumeRetriever
from .vector_store import VectorStore
from .grounding import ResponseGrounder, GroundingReport
from .evaluation import RAGEvaluator, EvaluationScores
from ..llm_backends import LLMRouter, Message

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


@dataclass
class VerifiedResponse:
    """Response with grounding verification"""
    content: str
    grounding_report: Optional[GroundingReport]
    grounding_score: float
    is_verified: bool
    context_used: str


# System prompts for different tasks with citation requirements
SYSTEM_PROMPTS = {
    "default": """You are an AI assistant helping with resume-related tasks. You have access to the user's resume information.

CRITICAL RULES FOR ACCURACY:
1. ONLY use information from the Resume Context below - never invent details
2. For EVERY factual claim, cite the source section in brackets: [Experience], [Skills], [Education], [Projects], etc.
3. If information is NOT in the context, clearly state: "This is not mentioned in my resume."
4. Never invent dates, company names, job titles, or skills

You can help with:
- Answering questions about experience and skills
- Drafting job application emails
- Tailoring resumes for specific job descriptions
- Suggesting improvements to resume content

Example response format:
"I have 5 years of Python experience [Experience] including Django and FastAPI frameworks [Skills]."

Resume Context:
{context}""",

    "email_draft": """You are an expert at writing professional job application emails. Your task is to draft compelling, personalized emails based on the user's resume.

CRITICAL RULES FOR ACCURACY:
1. ONLY reference experience and skills from the Resume Context below
2. Cite sources for key claims: [Experience], [Skills], [Education]
3. If a required qualification isn't in the resume, acknowledge it honestly
4. Never invent or exaggerate qualifications

Guidelines:
- Keep emails concise (150-250 words)
- Highlight relevant experience from the resume with citations
- Match tone to the company culture
- Include a clear call to action
- Be professional but personable

Resume Context:
{context}""",

    "resume_tailor": """You are an expert resume writer. Your task is to help tailor resume content for specific job descriptions.

CRITICAL RULES FOR ACCURACY:
1. ONLY suggest modifications based on actual content in the Resume Context
2. Cite which sections contain the relevant experience: [Experience], [Skills], [Projects]
3. If the resume lacks a required skill/experience, note it as a gap to address
4. Never suggest adding skills or experience the candidate doesn't have

Guidelines:
- Match keywords from the job description to existing resume content
- Quantify achievements where data exists in the resume
- Highlight relevant experience with section citations
- Use action verbs
- Keep content concise and impactful

Resume Context:
{context}""",

    "interview_prep": """You are an interview preparation coach. Help the user prepare for interviews using their actual experience.

CRITICAL RULES FOR ACCURACY:
1. ONLY suggest answers based on real experience from the Resume Context
2. Cite the source of each example: [Experience: Company Name], [Projects], [Skills]
3. If there's no relevant experience for a question, help them think about transferable skills
4. Never fabricate stories or experiences

Help the user by:
- Suggesting answers based on their documented experience
- Identifying relevant stories from specific roles [Experience]
- Practicing common interview questions with real examples
- Providing feedback on responses

Resume Context:
{context}""",
}


class ResumeRAG:
    """
    Main RAG interface for resume-related tasks.

    Combines:
    - Vector store for semantic search
    - Resume retriever for context (with hybrid search + reranking)
    - LLM router for generation
    - Response grounding for hallucination prevention
    - Evaluation framework for quality measurement

    Features:
    - Hybrid search (BM25 + Vector) for +15-25% accuracy
    - Cross-encoder reranking for +10-20% relevance
    - HyDE query enhancement for complex queries
    - Citation-required prompts to reduce hallucinations
    - Response verification against source context
    """

    def __init__(
        self,
        llm_backend: Optional[str] = None,
        resumes_dir: Optional[Path] = None,
        use_hybrid: bool = True,
        use_reranking: bool = True,
        use_hyde: bool = False,
        enable_grounding: bool = True,
        enable_verification: bool = False
    ):
        """
        Initialize RAG system.

        Args:
            llm_backend: Default LLM backend to use
            resumes_dir: Directory containing resume files
            use_hybrid: Enable hybrid search (BM25 + Vector)
            use_reranking: Enable cross-encoder reranking
            use_hyde: Enable HyDE query enhancement
            enable_grounding: Use citation-required prompts
            enable_verification: Verify responses against context (adds latency)
        """
        self.llm_router = LLMRouter(default_backend=llm_backend)
        self.vector_store = VectorStore()
        self.retriever = ResumeRetriever(
            self.vector_store,
            use_reranking=use_reranking,
            use_hybrid=use_hybrid,
            use_hyde=use_hyde,
            llm_router=self.llm_router
        )
        self.resumes_dir = resumes_dir or settings.resumes_dir
        self.chat_history: List[Message] = []

        # Grounding and evaluation settings
        self.enable_grounding = enable_grounding
        self.enable_verification = enable_verification

        # Lazy-loaded components
        self._grounder: Optional[ResponseGrounder] = None
        self._evaluator: Optional[RAGEvaluator] = None

    @property
    def grounder(self) -> ResponseGrounder:
        """Lazy-load response grounder"""
        if self._grounder is None:
            self._grounder = ResponseGrounder(
                llm_router=self.llm_router,
                require_citations=self.enable_grounding,
                verify_claims=self.enable_verification
            )
        return self._grounder

    @property
    def evaluator(self) -> RAGEvaluator:
        """Lazy-load RAG evaluator"""
        if self._evaluator is None:
            self._evaluator = RAGEvaluator(llm_router=self.llm_router)
        return self._evaluator

    def index_resumes(self, directory: Optional[Path] = None) -> int:
        """Index resumes from a directory"""
        directory = directory or self.resumes_dir
        return self.retriever.index_resumes(directory)

    def clear_index(self):
        """Clear the vector store"""
        self.vector_store.clear()

    def get_relevant_context(self, query: str, max_tokens: int = 2000) -> str:
        """Get relevant resume context for a query"""
        return self.retriever.get_context(query, max_tokens)

    async def chat(
        self,
        user_message: str,
        task_type: str = "default",
        include_history: bool = True,
        backend: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Chat with the RAG system.

        Args:
            user_message: The user's message/query
            task_type: Type of task (default, email_draft, resume_tailor, interview_prep)
            include_history: Whether to include chat history
            backend: LLM backend to use (groq, ollama, openai, chatgpt_web)

        Returns:
            The assistant's response
        """
        # Get relevant context from resume
        context = self.get_relevant_context(user_message)

        # Select system prompt based on task type
        system_template = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["default"])
        system_prompt = system_template.format(context=context)

        # Build message history
        history = self.chat_history if include_history else None

        # Generate response
        response = await self.llm_router.achat(
            user_message=user_message,
            system_prompt=system_prompt,
            history=history,
            backend=backend,
            **kwargs
        )

        # Update chat history
        self.chat_history.append(Message(role="user", content=user_message))
        self.chat_history.append(Message(role="assistant", content=response.content))

        # Keep history manageable
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

        return response.content

    def chat_sync(
        self,
        user_message: str,
        task_type: str = "default",
        include_history: bool = True,
        backend: Optional[str] = None,
        **kwargs
    ) -> str:
        """Synchronous version of chat"""
        import asyncio
        return asyncio.run(self.chat(
            user_message, task_type, include_history, backend, **kwargs
        ))

    async def draft_email(
        self,
        job_description: str,
        recipient: Optional[str] = None,
        tone: str = "professional",
        backend: Optional[str] = None
    ) -> str:
        """Draft a job application email"""
        prompt = f"""Draft an email for this job opportunity:

Job Description:
{job_description}

{"Recipient: " + recipient if recipient else ""}
Tone: {tone}

Write a compelling application email highlighting relevant experience from my resume."""

        return await self.chat(prompt, task_type="email_draft", backend=backend)

    async def tailor_resume(
        self,
        job_description: str,
        section: Optional[str] = None,
        backend: Optional[str] = None
    ) -> str:
        """Suggest resume tailoring for a job"""
        prompt = f"""Help me tailor my resume for this job:

Job Description:
{job_description}

{f"Focus on the {section} section." if section else "Suggest improvements across all sections."}

Provide specific suggestions to better match this job, including:
1. Keywords to add
2. Experience to highlight
3. Skills to emphasize
4. Bullet points to modify"""

        return await self.chat(prompt, task_type="resume_tailor", backend=backend)

    async def answer_question(
        self,
        question: str,
        backend: Optional[str] = None
    ) -> str:
        """Answer a question about the resume/experience"""
        return await self.chat(question, task_type="default", backend=backend)

    async def interview_prep(
        self,
        question: str,
        company: Optional[str] = None,
        backend: Optional[str] = None
    ) -> str:
        """Help prepare for an interview question"""
        prompt = f"""Help me prepare to answer this interview question:

Question: {question}
{f"Company: {company}" if company else ""}

Provide:
1. A suggested answer based on my experience
2. Key points to emphasize
3. A relevant story or example from my background"""

        return await self.chat(prompt, task_type="interview_prep", backend=backend)

    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []

    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "indexed_documents": self.vector_store.count(),
            "chat_history_length": len(self.chat_history),
            "available_backends": self.llm_router.get_available_backends(),
            "current_backend": self.llm_router.default_backend,
            "resumes_directory": str(self.resumes_dir),
            "features": {
                "hybrid_search": self.retriever.use_hybrid,
                "reranking": self.retriever.use_reranking,
                "hyde": self.retriever.use_hyde,
                "grounding": self.enable_grounding,
                "verification": self.enable_verification
            }
        }

    async def chat_with_verification(
        self,
        user_message: str,
        task_type: str = "default",
        include_history: bool = True,
        backend: Optional[str] = None,
        **kwargs
    ) -> VerifiedResponse:
        """
        Chat with response verification.

        Generates a response and verifies it against the source context
        to detect potential hallucinations.

        Args:
            user_message: The user's message/query
            task_type: Type of task
            include_history: Whether to include chat history
            backend: LLM backend to use

        Returns:
            VerifiedResponse with content and grounding report
        """
        # Get relevant context from resume
        context = self.get_relevant_context(user_message)

        # Generate response using grounded prompt
        if self.enable_grounding:
            system_template = self.grounder.get_grounded_prompt(task_type)
        else:
            system_template = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["default"])

        system_prompt = system_template.format(context=context)

        # Build message history
        history = self.chat_history if include_history else None

        # Generate response
        response = await self.llm_router.achat(
            user_message=user_message,
            system_prompt=system_prompt,
            history=history,
            backend=backend,
            **kwargs
        )

        # Update chat history
        self.chat_history.append(Message(role="user", content=user_message))
        self.chat_history.append(Message(role="assistant", content=response.content))

        # Keep history manageable
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

        # Verify response if enabled
        grounding_report = None
        grounding_score = 1.0
        is_verified = True

        if self.enable_verification:
            grounding_report = self.grounder.verify_response(response.content, context)
            grounding_score = grounding_report.grounding_score
            is_verified = grounding_score >= 0.7  # 70% threshold

        return VerifiedResponse(
            content=response.content,
            grounding_report=grounding_report,
            grounding_score=grounding_score,
            is_verified=is_verified,
            context_used=context
        )

    def chat_with_verification_sync(
        self,
        user_message: str,
        task_type: str = "default",
        include_history: bool = True,
        backend: Optional[str] = None,
        **kwargs
    ) -> VerifiedResponse:
        """Synchronous version of chat_with_verification"""
        import asyncio
        return asyncio.run(self.chat_with_verification(
            user_message, task_type, include_history, backend, **kwargs
        ))

    def evaluate_response(
        self,
        question: str,
        answer: str,
        contexts: Optional[List[str]] = None,
        ground_truth: Optional[str] = None
    ) -> EvaluationScores:
        """
        Evaluate a RAG response using RAGAS-style metrics.

        Args:
            question: The question that was asked
            answer: The generated answer
            contexts: Retrieved context chunks (fetched if not provided)
            ground_truth: Expected answer (optional)

        Returns:
            EvaluationScores with faithfulness, relevancy, precision, recall
        """
        # Get contexts if not provided
        if contexts is None:
            results = self.retriever.search(question, n_results=5)
            contexts = [r["content"] for r in results]

        return self.evaluator.evaluate_single(
            question=question,
            answer=answer,
            contexts=contexts,
            ground_truth=ground_truth
        )

    def get_retrieval_debug(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Get debug information about retrieval for a query.

        Useful for understanding why certain results were returned.

        Args:
            query: Search query
            n_results: Number of results

        Returns:
            Dict with search results and metadata
        """
        results = self.retriever.search(query, n_results=n_results)

        return {
            "query": query,
            "n_results": len(results),
            "search_mode": results[0].get("search_mode") if results else "unknown",
            "results": [
                {
                    "section": r["metadata"].get("section", "unknown"),
                    "relevance": r.get("relevance", 0),
                    "content_preview": r["content"][:100] + "..."
                }
                for r in results
            ],
            "hybrid_ready": self.retriever.hybrid_searcher.is_bm25_ready,
            "total_indexed": self.vector_store.count()
        }
