"""Query Enhancement with HyDE (Hypothetical Document Embeddings)"""

from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import re

if TYPE_CHECKING:
    from ..llm_backends import LLMRouter


class QueryComplexity(Enum):
    """Query complexity levels for enhancement decisions"""
    SIMPLE = "simple"      # Direct keyword match likely (1-3 words)
    MODERATE = "moderate"  # Some expansion helpful (4-6 words)
    COMPLEX = "complex"    # HyDE recommended (7+ words or semantic)


@dataclass
class EnhancedQuery:
    """Result of query enhancement"""
    original: str
    enhanced: str                          # HyDE output or original
    complexity: QueryComplexity
    expanded_queries: List[str] = field(default_factory=list)
    hyde_used: bool = False


class QueryEnhancer:
    """
    Query Enhancement using HyDE (Hypothetical Document Embeddings).

    HyDE generates a hypothetical document that would answer the query,
    then uses that document's embedding for retrieval. This bridges the
    semantic gap between short queries and long documents.

    Benefits:
    - +10-15% improvement on complex queries
    - Better semantic matching for abstract questions
    - Handles vocabulary mismatch (query uses different words than document)

    Example:
        Query: "Python skills"
        HyDE: "The candidate has 6+ years of Python experience including
               Django, FastAPI, Flask for web development, Pandas and
               NumPy for data processing, and pytest for testing..."

    The HyDE embedding is closer to actual resume content than "Python skills".
    """

    # HyDE prompt template for resume context
    HYDE_PROMPT = """You are generating a hypothetical resume section that would perfectly answer the following query.

Query: {query}

Write a detailed, realistic resume section (2-3 sentences) that would contain the answer to this query. Include specific technologies, years of experience, company types, and achievements that would be relevant. Write as if this is actual resume content, not a response to the query.

Resume section:"""

    # Keywords that suggest simple queries (direct matches work well)
    SIMPLE_KEYWORDS = {
        "email", "phone", "name", "address", "linkedin", "github",
        "education", "degree", "university", "gpa", "graduation"
    }

    # Keywords that suggest complex queries (HyDE helps)
    COMPLEX_INDICATORS = {
        "experience", "skills", "projects", "achievements", "responsibilities",
        "how", "what", "describe", "tell", "explain", "background",
        "qualifications", "expertise", "proficiency", "years"
    }

    def __init__(
        self,
        llm_router: Optional["LLMRouter"] = None,
        hyde_enabled: bool = True,
        complexity_threshold: int = 5,
        hyde_backend: Optional[str] = None
    ):
        """
        Initialize query enhancer.

        Args:
            llm_router: LLM router for HyDE generation (lazy-loaded if None)
            hyde_enabled: Whether to use HyDE for complex queries
            complexity_threshold: Word count threshold for complexity (default: 5)
            hyde_backend: Specific backend for HyDE generation (uses default if None)
        """
        self._llm_router = llm_router
        self.hyde_enabled = hyde_enabled
        self.complexity_threshold = complexity_threshold
        self.hyde_backend = hyde_backend

    @property
    def llm_router(self) -> "LLMRouter":
        """Lazy-load LLM router"""
        if self._llm_router is None:
            from ..llm_backends import LLMRouter
            self._llm_router = LLMRouter()
        return self._llm_router

    def detect_complexity(self, query: str) -> QueryComplexity:
        """
        Detect query complexity to decide enhancement strategy.

        Args:
            query: User's search query

        Returns:
            QueryComplexity level (SIMPLE, MODERATE, COMPLEX)
        """
        query_lower = query.lower()
        words = query_lower.split()
        word_count = len(words)

        # Check for simple keyword queries
        if word_count <= 2:
            return QueryComplexity.SIMPLE

        # Check if query contains simple keywords (likely direct match)
        if any(kw in query_lower for kw in self.SIMPLE_KEYWORDS):
            return QueryComplexity.SIMPLE

        # Check for complex indicators
        has_complex_indicator = any(
            ind in query_lower for ind in self.COMPLEX_INDICATORS
        )

        # Question words suggest semantic queries
        is_question = any(
            query_lower.startswith(qw)
            for qw in ["what", "how", "describe", "tell", "explain", "list"]
        )

        if is_question or (has_complex_indicator and word_count >= self.complexity_threshold):
            return QueryComplexity.COMPLEX

        if word_count >= self.complexity_threshold:
            return QueryComplexity.MODERATE

        return QueryComplexity.SIMPLE

    async def generate_hyde(self, query: str) -> str:
        """
        Generate hypothetical document using HyDE.

        Args:
            query: User's search query

        Returns:
            Hypothetical resume section that would answer the query
        """
        prompt = self.HYDE_PROMPT.format(query=query)

        response = await self.llm_router.achat(
            user_message=prompt,
            system_prompt="You are a resume content generator. Generate realistic resume content.",
            backend=self.hyde_backend,
            temperature=0.7,
            max_tokens=200
        )

        # Clean up the response
        hyde_text = response.content.strip()

        # Remove any preamble like "Here's a resume section:"
        hyde_text = re.sub(
            r'^(here\'?s?|the following|resume section:?)[\s:]*',
            '',
            hyde_text,
            flags=re.IGNORECASE
        ).strip()

        return hyde_text

    def generate_hyde_sync(self, query: str) -> str:
        """Synchronous version of generate_hyde"""
        return asyncio.run(self.generate_hyde(query))

    def expand_query(self, query: str) -> List[str]:
        """
        Expand query into multiple related queries.

        Useful for multi-query retrieval where results from multiple
        query variations are combined.

        Args:
            query: Original query

        Returns:
            List of expanded queries (including original)
        """
        expanded = [query]

        # Add variations based on query structure
        query_lower = query.lower()

        # If asking about skills, also search for experience
        if "skill" in query_lower:
            expanded.append(query.replace("skill", "experience").replace("skills", "experience"))

        # If asking about experience, also search for projects
        if "experience" in query_lower:
            expanded.append(query.replace("experience", "projects"))

        # If asking about a technology, search for related terms
        tech_synonyms = {
            "python": ["django", "fastapi", "flask"],
            "javascript": ["react", "node", "typescript"],
            "database": ["sql", "postgresql", "mongodb"],
            "cloud": ["aws", "azure", "gcp"],
            "ml": ["machine learning", "deep learning", "ai"],
        }

        for tech, synonyms in tech_synonyms.items():
            if tech in query_lower:
                for syn in synonyms[:2]:  # Add up to 2 synonyms
                    expanded.append(f"{query} {syn}")

        return expanded[:4]  # Limit to 4 queries max

    async def enhance(self, query: str) -> EnhancedQuery:
        """
        Enhance query based on complexity.

        Simple queries: Pass through unchanged
        Moderate queries: Add query expansion
        Complex queries: Generate HyDE hypothetical document

        Args:
            query: User's search query

        Returns:
            EnhancedQuery with enhancement details
        """
        complexity = self.detect_complexity(query)
        expanded = []
        enhanced = query
        hyde_used = False

        if complexity == QueryComplexity.SIMPLE:
            # Simple queries work well with direct search
            pass

        elif complexity == QueryComplexity.MODERATE:
            # Moderate queries benefit from expansion
            expanded = self.expand_query(query)

        elif complexity == QueryComplexity.COMPLEX and self.hyde_enabled:
            # Complex queries benefit from HyDE
            try:
                enhanced = await self.generate_hyde(query)
                hyde_used = True
                # Also add expansion for fallback
                expanded = self.expand_query(query)
            except Exception as e:
                # Fall back to expansion if HyDE fails
                print(f"HyDE generation failed: {e}")
                expanded = self.expand_query(query)

        return EnhancedQuery(
            original=query,
            enhanced=enhanced,
            complexity=complexity,
            expanded_queries=expanded,
            hyde_used=hyde_used
        )

    def enhance_sync(self, query: str) -> EnhancedQuery:
        """Synchronous version of enhance"""
        return asyncio.run(self.enhance(query))

    def __repr__(self) -> str:
        return f"QueryEnhancer(hyde_enabled={self.hyde_enabled}, threshold={self.complexity_threshold})"
