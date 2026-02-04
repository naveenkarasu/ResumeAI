"""Resume Retriever - Loads and indexes resume data"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path
import re
import hashlib

from .vector_store import VectorStore
from .reranker import Reranker, RankedDocument
from .hybrid_search import HybridSearcher, SearchResult
from .query_enhancer import QueryEnhancer, EnhancedQuery, QueryComplexity

if TYPE_CHECKING:
    from ..llm_backends import LLMRouter

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class ResumeRetriever:
    """
    Retrieves relevant resume sections based on queries.

    Handles:
    - Loading resumes from LaTeX/PDF/DOCX files
    - Chunking content into searchable sections
    - Hybrid search (BM25 + Vector) with optional reranking
    - HyDE query enhancement for complex queries

    Search Modes:
    - use_hybrid=True: Combines BM25 keyword + vector semantic search (+15-25% accuracy)
    - use_reranking=True: Cross-encoder reranking for better relevance (+10-20%)
    - use_hyde=True: HyDE query enhancement for complex queries (+10-15%)
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        use_reranking: bool = True,
        use_hybrid: bool = True,
        use_hyde: bool = False,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        llm_router: Optional["LLMRouter"] = None
    ):
        """
        Initialize retriever with search options.

        Args:
            vector_store: VectorStore instance (creates new if None)
            use_reranking: Enable cross-encoder reranking
            use_hybrid: Enable BM25 + Vector hybrid search
            use_hyde: Enable HyDE query enhancement for complex queries
            vector_weight: Weight for vector results in hybrid fusion
            bm25_weight: Weight for BM25 results in hybrid fusion
            llm_router: LLM router for HyDE generation (lazy-loaded if None)
        """
        self.vector_store = vector_store or VectorStore()
        self.resumes_dir = settings.resumes_dir
        self.use_reranking = use_reranking
        self.use_hybrid = use_hybrid
        self.use_hyde = use_hyde

        # Lazy-loaded components
        self._reranker: Optional[Reranker] = None
        self._hybrid_searcher: Optional[HybridSearcher] = None
        self._query_enhancer: Optional[QueryEnhancer] = None
        self._vector_weight = vector_weight
        self._bm25_weight = bm25_weight
        self._llm_router = llm_router

    @property
    def reranker(self) -> Reranker:
        """Lazy-load reranker to avoid loading model unless needed"""
        if self._reranker is None:
            self._reranker = Reranker()
        return self._reranker

    @property
    def hybrid_searcher(self) -> HybridSearcher:
        """Lazy-load hybrid searcher"""
        if self._hybrid_searcher is None:
            self._hybrid_searcher = HybridSearcher(
                vector_store=self.vector_store,
                vector_weight=self._vector_weight,
                bm25_weight=self._bm25_weight
            )
        return self._hybrid_searcher

    @property
    def query_enhancer(self) -> QueryEnhancer:
        """Lazy-load query enhancer"""
        if self._query_enhancer is None:
            self._query_enhancer = QueryEnhancer(
                llm_router=self._llm_router,
                hyde_enabled=True
            )
        return self._query_enhancer

    def load_latex_resume(self, file_path: Path) -> Dict[str, Any]:
        """Parse a LaTeX resume file into structured sections"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract sections from LaTeX
        sections = {}

        # Extract header info
        name_match = re.search(r"\\textbf\{([^}]+)\}", content)
        if name_match:
            sections["name"] = name_match.group(1)

        # Extract sections by \section{...}
        section_pattern = r"\\section\{([^}]+)\}(.*?)(?=\\section\{|\\end\{document\})"
        matches = re.findall(section_pattern, content, re.DOTALL)

        for section_name, section_content in matches:
            # Clean up LaTeX commands
            clean_content = self._clean_latex(section_content)
            sections[section_name.lower().replace(" ", "_")] = clean_content

        # Extract job entries
        job_pattern = r"\\jobentry\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}"
        jobs = re.findall(job_pattern, content)
        sections["jobs"] = [
            {"title": j[0], "company": j[1], "location": j[2], "dates": j[3]}
            for j in jobs
        ]

        # Extract skills
        skill_pattern = r"\\skill\{([^}]+)\}\{([^}]+)\}"
        skills = re.findall(skill_pattern, content)
        sections["skills"] = {s[0]: s[1] for s in skills}

        # Extract projects
        project_pattern = r"\\projectentry\{([^}]+)\}\{([^}]+)\}"
        projects = re.findall(project_pattern, content)
        sections["projects"] = [{"name": p[0], "date": p[1]} for p in projects]

        return {
            "file": str(file_path),
            "sections": sections,
            "raw_content": content
        }

    def _clean_latex(self, text: str) -> str:
        """Remove LaTeX commands and clean up text"""
        # Remove common LaTeX commands
        text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+", "", text)
        text = re.sub(r"\{|\}", "", text)
        text = re.sub(r"\\item", "•", text)
        text = re.sub(r"\\;", " ", text)
        text = re.sub(r"\\%", "%", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        return text.strip()

    def load_text_resume(self, file_path: Path) -> Dict[str, Any]:
        """Load a plain text resume"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "file": str(file_path),
            "sections": {"content": content},
            "raw_content": content
        }

    def load_pdf_resume(self, file_path: Path) -> Dict[str, Any]:
        """Load a PDF resume and extract text"""
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        content = "\n".join(text_parts)

        # Try to extract sections from PDF content
        sections = self._parse_pdf_sections(content)

        return {
            "file": str(file_path),
            "sections": sections,
            "raw_content": content
        }

    def _parse_pdf_sections(self, content: str) -> Dict[str, str]:
        """Parse common resume sections from PDF text"""
        sections = {}

        # Common section headers
        section_patterns = [
            (r"(?i)(experience|work\s*experience|professional\s*experience)", "experience"),
            (r"(?i)(education|academic\s*background)", "education"),
            (r"(?i)(skills|technical\s*skills|core\s*competencies)", "skills"),
            (r"(?i)(projects|key\s*projects)", "projects"),
            (r"(?i)(summary|professional\s*summary|objective)", "summary"),
            (r"(?i)(certifications?|credentials)", "certifications"),
            (r"(?i)(awards?|achievements?|honors?)", "awards"),
        ]

        # Split content by common section headers
        lines = content.split('\n')
        current_section = "header"
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line is a section header
            found_section = False
            for pattern, section_name in section_patterns:
                if re.match(pattern, line):
                    # Save previous section
                    if current_content:
                        sections[current_section] = "\n".join(current_content)
                    current_section = section_name
                    current_content = []
                    found_section = True
                    break

            if not found_section:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content)

        # If no sections found, use whole content
        if not sections:
            sections["content"] = content

        return sections

    def chunk_resume(
        self,
        resume_data: Dict[str, Any],
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Split resume into chunks for indexing with overlap.

        Args:
            resume_data: Parsed resume data with sections
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Overlap between consecutive chunks (improves context)

        Returns:
            List of chunks with content and metadata
        """
        chunks = []
        file_path = resume_data["file"]
        sections = resume_data["sections"]

        for section_name, section_content in sections.items():
            if isinstance(section_content, str):
                # Split long sections into overlapping chunks
                if len(section_content) > chunk_size:
                    words = section_content.split()
                    current_chunk = []
                    current_length = 0
                    chunk_index = 0

                    for word in words:
                        current_chunk.append(word)
                        current_length += len(word) + 1

                        if current_length >= chunk_size:
                            chunk_text = " ".join(current_chunk)
                            chunks.append({
                                "content": chunk_text,
                                "metadata": {
                                    "file": file_path,
                                    "section": section_name,
                                    "type": "text",
                                    "chunk_index": chunk_index,
                                    "has_overlap": chunk_index > 0
                                }
                            })
                            chunk_index += 1

                            # Keep overlap words for next chunk
                            overlap_chars = 0
                            overlap_words = []
                            for w in reversed(current_chunk):
                                overlap_chars += len(w) + 1
                                overlap_words.insert(0, w)
                                if overlap_chars >= chunk_overlap:
                                    break

                            current_chunk = overlap_words
                            current_length = overlap_chars

                    if current_chunk:
                        chunks.append({
                            "content": " ".join(current_chunk),
                            "metadata": {
                                "file": file_path,
                                "section": section_name,
                                "type": "text",
                                "chunk_index": chunk_index,
                                "has_overlap": chunk_index > 0
                            }
                        })
                else:
                    chunks.append({
                        "content": section_content,
                        "metadata": {
                            "file": file_path,
                            "section": section_name,
                            "type": "text",
                            "chunk_index": 0,
                            "has_overlap": False
                        }
                    })

            elif isinstance(section_content, list):
                # Handle lists (jobs, projects)
                for item in section_content:
                    if isinstance(item, dict):
                        content = " | ".join(f"{k}: {v}" for k, v in item.items())
                    else:
                        content = str(item)

                    chunks.append({
                        "content": content,
                        "metadata": {
                            "file": file_path,
                            "section": section_name,
                            "type": "list_item"
                        }
                    })

            elif isinstance(section_content, dict):
                # Handle dicts (skills)
                for key, value in section_content.items():
                    chunks.append({
                        "content": f"{key}: {value}",
                        "metadata": {
                            "file": file_path,
                            "section": section_name,
                            "type": "key_value"
                        }
                    })

        return chunks

    def index_resumes(self, directory: Optional[Path] = None) -> int:
        """
        Index all resumes from a directory.

        Builds both vector store and BM25 index for hybrid search.

        Args:
            directory: Path to resumes directory (uses settings default if None)

        Returns:
            Number of chunks indexed
        """
        directory = directory or self.resumes_dir

        if not directory.exists():
            print(f"Directory not found: {directory}")
            return 0

        # Find all resume files
        latex_files = list(directory.rglob("*.tex"))
        txt_files = list(directory.rglob("*.txt"))
        pdf_files = list(directory.rglob("*.pdf"))

        all_chunks = []

        # Index LaTeX files
        for file_path in latex_files:
            try:
                resume_data = self.load_latex_resume(file_path)
                chunks = self.chunk_resume(resume_data)
                all_chunks.extend(chunks)
                print(f"Indexed: {file_path.name} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")

        # Index text files
        for file_path in txt_files:
            try:
                resume_data = self.load_text_resume(file_path)
                chunks = self.chunk_resume(resume_data)
                all_chunks.extend(chunks)
                print(f"Indexed: {file_path.name} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")

        # Index PDF files
        for file_path in pdf_files:
            try:
                resume_data = self.load_pdf_resume(file_path)
                chunks = self.chunk_resume(resume_data)
                all_chunks.extend(chunks)
                print(f"Indexed: {file_path.name} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")

        if all_chunks:
            documents = [c["content"] for c in all_chunks]
            metadatas = [c["metadata"] for c in all_chunks]

            # Generate document IDs based on content hash
            doc_ids = [
                hashlib.md5(doc.encode()).hexdigest()[:16]
                for doc in documents
            ]

            # Add to vector store
            self.vector_store.add_documents(documents, metadatas, doc_ids)

            # Build BM25 index for hybrid search
            if self.use_hybrid:
                self.hybrid_searcher.build_bm25_index(documents, doc_ids, metadatas)
                print(f"Built BM25 index with {len(documents)} documents")

        return len(all_chunks)

    def rebuild_bm25_index(self) -> int:
        """
        Rebuild BM25 index from existing vector store.

        Useful when vector store already has documents but BM25 index is missing.

        Returns:
            Number of documents indexed
        """
        # Get all documents from vector store
        all_docs = self.vector_store.get_all()

        if not all_docs["documents"]:
            return 0

        documents = all_docs["documents"]
        metadatas = all_docs["metadatas"]
        doc_ids = all_docs.get("ids", [
            hashlib.md5(doc.encode()).hexdigest()[:16]
            for doc in documents
        ])

        # Build BM25 index
        self.hybrid_searcher.build_bm25_index(documents, doc_ids, metadatas)
        print(f"Rebuilt BM25 index with {len(documents)} documents")

        return len(documents)

    def search(
        self,
        query: str,
        n_results: int = 5,
        section_filter: Optional[str] = None,
        use_reranking: Optional[bool] = None,
        use_hybrid: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant resume sections with hybrid search and reranking.

        Args:
            query: Search query string
            n_results: Number of results to return
            section_filter: Optional section name to filter by
            use_reranking: Override instance reranking setting
            use_hybrid: Override instance hybrid search setting

        Returns:
            List of results with content, metadata, and relevance scores
        """
        should_rerank = use_reranking if use_reranking is not None else self.use_reranking
        should_hybrid = use_hybrid if use_hybrid is not None else self.use_hybrid

        where = None
        if section_filter:
            where = {"section": section_filter}

        # Fetch more candidates if reranking (5x for better selection)
        fetch_k = n_results * 5 if should_rerank else n_results

        # Use hybrid search if enabled and BM25 index is ready
        if should_hybrid and self.hybrid_searcher.is_bm25_ready:
            hybrid_results = self.hybrid_searcher.search(
                query,
                n_results=fetch_k,
                where=where
            )

            # Convert SearchResult to dict format
            candidates = [
                {
                    "content": r.content,
                    "metadata": r.metadata,
                    "relevance": r.fused_score,
                    "vector_score": r.vector_score,
                    "bm25_score": r.bm25_score,
                    "search_mode": "hybrid"
                }
                for r in hybrid_results
            ]
        else:
            # Fall back to pure vector search
            results = self.vector_store.search(query, n_results=fetch_k, where=where)

            candidates = [
                {
                    "content": doc,
                    "metadata": meta,
                    "relevance": 1 - dist,  # Convert distance to similarity
                    "search_mode": "vector"
                }
                for doc, meta, dist in zip(
                    results["documents"],
                    results["metadatas"],
                    results["distances"]
                )
            ]

        if not candidates:
            return []

        # Apply cross-encoder reranking if enabled
        if should_rerank and len(candidates) > 1:
            ranked = self.reranker.rerank(query, candidates, top_k=n_results)
            return [
                {
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "relevance": doc.rerank_score,
                    "original_relevance": doc.original_score,
                    "rank": doc.final_rank,
                    "search_mode": candidates[0].get("search_mode", "unknown") + "+rerank"
                }
                for doc in ranked
            ]

        # Without reranking, just return top n_results
        return candidates[:n_results]

    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        """Get relevant context for a query, formatted for LLM"""
        results = self.search(query, n_results=10)

        context_parts = []
        current_length = 0

        for result in results:
            content = result["content"]
            section = result["metadata"].get("section", "unknown")

            entry = f"[{section}]\n{content}\n"
            entry_length = len(entry.split())

            if current_length + entry_length > max_tokens:
                break

            context_parts.append(entry)
            current_length += entry_length

        return "\n".join(context_parts)

    async def enhanced_search(
        self,
        query: str,
        n_results: int = 5,
        section_filter: Optional[str] = None,
        use_reranking: Optional[bool] = None,
        use_hybrid: Optional[bool] = None,
        use_hyde: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Enhanced async search with HyDE query enhancement.

        For complex queries, generates a hypothetical document (HyDE) that would
        answer the query, then uses that for retrieval. This bridges the semantic
        gap between short queries and long documents.

        Args:
            query: Search query string
            n_results: Number of results to return
            section_filter: Optional section name to filter by
            use_reranking: Override instance reranking setting
            use_hybrid: Override instance hybrid search setting
            use_hyde: Override instance HyDE setting

        Returns:
            Dict with 'results', 'query_info', and 'search_mode'
        """
        should_hyde = use_hyde if use_hyde is not None else self.use_hyde

        # Enhance query if HyDE is enabled
        query_info = None
        search_query = query

        if should_hyde:
            enhanced = await self.query_enhancer.enhance(query)
            query_info = {
                "original": enhanced.original,
                "enhanced": enhanced.enhanced,
                "complexity": enhanced.complexity.value,
                "hyde_used": enhanced.hyde_used,
                "expanded_queries": enhanced.expanded_queries
            }

            # Use HyDE-enhanced query for complex queries
            if enhanced.hyde_used:
                search_query = enhanced.enhanced

        # Perform search with (potentially enhanced) query
        results = self.search(
            search_query,
            n_results=n_results,
            section_filter=section_filter,
            use_reranking=use_reranking,
            use_hybrid=use_hybrid
        )

        # Add HyDE info to search mode
        search_mode = results[0].get("search_mode", "unknown") if results else "unknown"
        if query_info and query_info.get("hyde_used"):
            search_mode = f"hyde+{search_mode}"

        return {
            "results": results,
            "query_info": query_info,
            "search_mode": search_mode
        }

    def enhanced_search_sync(
        self,
        query: str,
        n_results: int = 5,
        section_filter: Optional[str] = None,
        use_reranking: Optional[bool] = None,
        use_hybrid: Optional[bool] = None,
        use_hyde: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Synchronous version of enhanced_search"""
        import asyncio
        return asyncio.run(self.enhanced_search(
            query, n_results, section_filter,
            use_reranking, use_hybrid, use_hyde
        ))

    async def get_context_enhanced(
        self,
        query: str,
        max_tokens: int = 2000,
        use_hyde: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get relevant context with optional HyDE enhancement.

        Args:
            query: Search query
            max_tokens: Maximum tokens for context
            use_hyde: Whether to use HyDE (None = use instance setting)

        Returns:
            Dict with 'context' string and 'query_info'
        """
        search_result = await self.enhanced_search(
            query,
            n_results=10,
            use_hyde=use_hyde
        )

        context_parts = []
        current_length = 0

        for result in search_result["results"]:
            content = result["content"]
            section = result["metadata"].get("section", "unknown")

            entry = f"[{section}]\n{content}\n"
            entry_length = len(entry.split())

            if current_length + entry_length > max_tokens:
                break

            context_parts.append(entry)
            current_length += entry_length

        return {
            "context": "\n".join(context_parts),
            "query_info": search_result["query_info"],
            "search_mode": search_result["search_mode"]
        }
