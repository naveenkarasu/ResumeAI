"""Chat service for handling RAG interactions"""

import time
import logging
from typing import Optional
from dataclasses import dataclass

from src.rag import ResumeRAG, VerifiedResponse
from ..models.responses import ChatResponse, Citation

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    """Context for a chat session"""
    history: list[dict]
    job_description: Optional[str] = None


class ChatService:
    """Service for handling chat interactions with the RAG system"""

    def __init__(self, rag: ResumeRAG):
        self.rag = rag
        self._sessions: dict[str, ChatContext] = {}

    async def chat(
        self,
        message: str,
        mode: str = "chat",
        job_description: Optional[str] = None,
        use_verification: bool = False,
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        """Process a chat message and return response"""
        start_time = time.time()

        try:
            # Build the query based on mode
            if mode == "email" and job_description:
                query = f"Generate an application email for this job: {job_description}\n\nFocus: {message}"
            elif mode == "tailor" and job_description:
                query = f"How should I tailor my resume for this job: {job_description}\n\nSpecific question: {message}"
            elif mode == "interview":
                query = f"Interview preparation question: {message}"
            else:
                query = message

            # Get response from RAG
            if use_verification:
                result = await self._chat_with_verification(query)
            else:
                result = await self._chat_simple(query)

            processing_time = int((time.time() - start_time) * 1000)

            # Build citations from context
            citations = self._extract_citations(result)

            # Get search mode info
            search_mode = self._get_search_mode()

            return ChatResponse(
                response=result.get("response", ""),
                citations=citations,
                mode=mode,
                grounding_score=result.get("grounding_score"),
                search_mode=search_mode,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise

    async def _chat_simple(self, query: str) -> dict:
        """Simple chat without verification"""
        response = await self.rag.chat(query)
        return {
            "response": response,
            "grounding_score": None,
            "contexts": self.rag.get_retrieval_debug(query).get("contexts", []),
        }

    async def _chat_with_verification(self, query: str) -> dict:
        """Chat with grounding verification"""
        verified: VerifiedResponse = await self.rag.chat_with_verification(query)
        return {
            "response": verified.content,
            "grounding_score": verified.grounding_score,
            "contexts": [verified.context_used] if verified.context_used else [],
            "verification_details": verified.grounding_report,
        }

    def _extract_citations(self, result: dict) -> list[Citation]:
        """Extract citations from RAG result contexts"""
        citations = []
        contexts = result.get("contexts", [])

        for ctx in contexts[:5]:  # Limit to top 5 citations
            if isinstance(ctx, dict):
                citations.append(Citation(
                    section=ctx.get("metadata", {}).get("section", "Unknown"),
                    text=ctx.get("content", "")[:200] + "...",
                    relevance_score=ctx.get("score", 0.0),
                ))
            elif isinstance(ctx, str):
                # Infer section from content
                section = self._infer_section(ctx)
                citations.append(Citation(
                    section=section,
                    text=ctx[:200] + "..." if len(ctx) > 200 else ctx,
                    relevance_score=0.5,
                ))

        return citations

    def _infer_section(self, text: str) -> str:
        """Infer the resume section from text content"""
        text_lower = text.lower()

        section_keywords = {
            "Experience": ["worked", "developed", "led", "managed", "built"],
            "Skills": ["proficient", "experience with", "skilled in", "technologies"],
            "Education": ["degree", "university", "bachelor", "master", "graduated"],
            "Projects": ["project", "implemented", "created", "github"],
            "Summary": ["passionate", "years of experience", "seeking"],
        }

        for section, keywords in section_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return section

        return "Content"

    def _get_search_mode(self) -> str:
        """Get the current search mode from RAG settings"""
        modes = []

        if hasattr(self.rag.retriever, "use_hybrid") and self.rag.retriever.use_hybrid:
            modes.append("hybrid")
        else:
            modes.append("vector")

        if hasattr(self.rag.retriever, "reranker") and self.rag.retriever.reranker:
            modes.append("rerank")

        return "+".join(modes) if modes else "vector"

    def get_suggestions(self, mode: str = "chat") -> list[str]:
        """Get suggested prompts for the given mode"""
        suggestions = {
            "chat": [
                "What are my main technical skills?",
                "Summarize my work experience",
                "What leadership experience do I have?",
                "What are my most impressive achievements?",
                "What industries have I worked in?",
            ],
            "email": [
                "Write a brief introduction focusing on my technical skills",
                "Emphasize my leadership experience",
                "Highlight my relevant project work",
                "Focus on my problem-solving abilities",
            ],
            "tailor": [
                "What skills should I emphasize for this role?",
                "Which experiences are most relevant?",
                "What keywords should I add?",
                "How can I address the requirements I'm missing?",
            ],
            "interview": [
                "What technical questions should I prepare for?",
                "Give me common behavioral interview questions",
                "How can I explain my career transitions?",
                "What achievements should I highlight?",
            ],
        }

        return suggestions.get(mode, suggestions["chat"])

    def clear_history(self, session_id: str) -> bool:
        """Clear chat history for a session"""
        if session_id in self._sessions:
            self._sessions[session_id] = ChatContext(history=[])
            return True
        return False

    def get_history(self, session_id: str) -> list[dict]:
        """Get chat history for a session"""
        if session_id in self._sessions:
            return self._sessions[session_id].history
        return []
