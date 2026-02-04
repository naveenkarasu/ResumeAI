# RAG Improvements Architecture Design

## Design Specification for Enhanced Resume RAG System

**Version**: 2.0
**Date**: 2026-02-03
**Status**: Design Specification (Pending Approval)

---

## 1. Executive Summary

This document specifies the architecture for upgrading the Resume RAG system from a basic implementation (Score: 6/10) to a production-ready system (Target: 9/10) by implementing 6 key improvements identified in the research phase.

### Target Improvements

| # | Feature | Expected Impact | Priority |
|---|---------|-----------------|----------|
| 1 | Cross-Encoder Reranking | +10-20% relevance | Critical |
| 2 | Hybrid Search (BM25 + Vector) | +15-25% accuracy | Critical |
| 3 | Semantic Chunking with Overlap | +10-15% recall | High |
| 4 | HyDE Query Enhancement | +10-15% complex queries | High |
| 5 | Citation Grounding | -42-68% hallucinations | High |
| 6 | RAGAS Evaluation Framework | Enables measurement | High |

---

## 2. Current vs. Target Architecture

### 2.1 Current Architecture (v1.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURRENT RAG PIPELINE                        │
└─────────────────────────────────────────────────────────────────┘

  User Query
      │
      ▼
  ┌─────────────────┐
  │  Direct Embed   │  ◄── No query enhancement
  │  (MiniLM-L6)    │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Vector Search  │  ◄── Single retrieval method
  │  (ChromaDB)     │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Top-K Results  │  ◄── No reranking
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Context Build  │  ◄── Simple concatenation
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  LLM Generate   │  ◄── No citation requirements
  └────────┬────────┘
           │
           ▼
  Response (Unverified)
```

### 2.2 Target Architecture (v2.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENHANCED RAG PIPELINE                         │
└─────────────────────────────────────────────────────────────────┘

  User Query
      │
      ▼
  ┌─────────────────┐
  │  Query Analyzer │  ◄── NEW: Complexity detection
  └────────┬────────┘
           │
      ┌────┴────┐
      │         │
      ▼         ▼
  Simple    Complex
  Query     Query
      │         │
      │    ┌────┴────┐
      │    │  HyDE   │  ◄── NEW: Hypothetical doc generation
      │    │ Expand  │
      │    └────┬────┘
      │         │
      └────┬────┘
           │
           ▼
  ┌─────────────────────────────────────────┐
  │           HYBRID RETRIEVAL               │  ◄── NEW
  │  ┌─────────────┐    ┌─────────────┐     │
  │  │   BM25      │    │   Vector    │     │
  │  │  (Keyword)  │    │ (Semantic)  │     │
  │  └──────┬──────┘    └──────┬──────┘     │
  │         │                  │            │
  │         └────────┬─────────┘            │
  │                  ▼                      │
  │         ┌─────────────┐                 │
  │         │     RRF     │  ◄── Reciprocal Rank Fusion
  │         │   Fusion    │                 │
  │         └─────────────┘                 │
  └───────────────────┬─────────────────────┘
                      │
                      ▼
  ┌─────────────────────────────────────────┐
  │         CROSS-ENCODER RERANKING          │  ◄── NEW
  │  ┌─────────────────────────────────┐    │
  │  │  ms-marco-MiniLM-L-6-v2         │    │
  │  │  Top 25 → Top 5                 │    │
  │  └─────────────────────────────────┘    │
  └───────────────────┬─────────────────────┘
                      │
                      ▼
  ┌─────────────────────────────────────────┐
  │         CONTEXT CONSTRUCTION             │
  │  ┌─────────────────────────────────┐    │
  │  │  Parent-Child Chunk Expansion   │    │  ◄── NEW
  │  │  + Section Labels               │    │
  │  │  + Relevance Scores             │    │
  │  └─────────────────────────────────┘    │
  └───────────────────┬─────────────────────┘
                      │
                      ▼
  ┌─────────────────────────────────────────┐
  │         GROUNDED GENERATION              │  ◄── NEW
  │  ┌─────────────────────────────────┐    │
  │  │  Citation-Required Prompts      │    │
  │  │  Section References [Experience]│    │
  │  └─────────────────────────────────┘    │
  └───────────────────┬─────────────────────┘
                      │
                      ▼
  ┌─────────────────────────────────────────┐
  │         RESPONSE VERIFICATION            │  ◄── NEW
  │  ┌─────────────────────────────────┐    │
  │  │  Claim Extraction & Validation  │    │
  │  │  Hallucination Detection        │    │
  │  └─────────────────────────────────┘    │
  └───────────────────┬─────────────────────┘
                      │
                      ▼
  Verified Response with Citations
```

---

## 3. Component Design

### 3.1 New Components Overview

```
src/rag/
├── __init__.py              # Updated exports
├── vector_store.py          # Existing (minor updates)
├── retriever.py             # MAJOR UPDATES
├── rag_chain.py             # MAJOR UPDATES
├── reranker.py              # NEW: Cross-encoder reranking
├── hybrid_search.py         # NEW: BM25 + Vector fusion
├── query_enhancer.py        # NEW: HyDE implementation
├── chunker.py               # NEW: Semantic chunking
├── grounding.py             # NEW: Citation & verification
└── evaluation.py            # NEW: RAGAS integration
```

### 3.2 Component Specifications

---

#### 3.2.1 Reranker Component (NEW)

**File**: `src/rag/reranker.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                        Reranker                                  │
├─────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│  - model: CrossEncoder                                           │
│  - model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"     │
│  - _model_cache: Dict[str, CrossEncoder]  (singleton)           │
├─────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│  + rerank(query, documents, top_k=5) -> List[RankedDocument]    │
│  + score_pair(query, document) -> float                         │
│  + batch_rerank(queries, documents_list) -> List[List[...]]     │
├─────────────────────────────────────────────────────────────────┤
│  Performance:                                                    │
│  - Latency: ~50-100ms for 25 documents                          │
│  - Memory: ~100MB model                                          │
└─────────────────────────────────────────────────────────────────┘
```

**Interface**:
```python
@dataclass
class RankedDocument:
    content: str
    metadata: Dict[str, Any]
    original_score: float      # From vector/BM25
    rerank_score: float        # From cross-encoder
    final_rank: int

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        ...

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[RankedDocument]:
        """
        Rerank documents using cross-encoder.

        Args:
            query: User query
            documents: List of {content, metadata, score}
            top_k: Number of documents to return

        Returns:
            Top-k documents reranked by relevance
        """
        ...
```

---

#### 3.2.2 Hybrid Search Component (NEW)

**File**: `src/rag/hybrid_search.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                      HybridSearcher                              │
├─────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│  - vector_store: VectorStore                                     │
│  - bm25_index: BM25Okapi                                         │
│  - documents: List[str]  (for BM25)                              │
│  - doc_ids: List[str]                                            │
│  - vector_weight: float = 0.7                                    │
│  - bm25_weight: float = 0.3                                      │
├─────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│  + search(query, n_results=25) -> List[SearchResult]            │
│  + build_bm25_index(documents, ids) -> None                      │
│  + vector_search(query, n) -> List[SearchResult]                 │
│  + bm25_search(query, n) -> List[SearchResult]                   │
│  + rrf_fusion(results_a, results_b, k=60) -> List[SearchResult] │
├─────────────────────────────────────────────────────────────────┤
│  Algorithm: Reciprocal Rank Fusion (RRF)                         │
│  score(d) = Σ 1/(k + rank_i(d)) for each retriever i            │
└─────────────────────────────────────────────────────────────────┘
```

**Interface**:
```python
@dataclass
class SearchResult:
    content: str
    metadata: Dict[str, Any]
    vector_score: Optional[float]
    bm25_score: Optional[float]
    fused_score: float
    doc_id: str

class HybridSearcher:
    def __init__(
        self,
        vector_store: VectorStore,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ):
        ...

    def build_bm25_index(self, documents: List[str], ids: List[str]) -> None:
        """Build BM25 index from documents."""
        ...

    def search(
        self,
        query: str,
        n_results: int = 25,
        where: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Hybrid search combining BM25 and vector similarity.
        Uses Reciprocal Rank Fusion to combine results.
        """
        ...
```

**Dependency**: `pip install rank-bm25`

---

#### 3.2.3 Query Enhancer Component (NEW)

**File**: `src/rag/query_enhancer.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                      QueryEnhancer                               │
├─────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│  - llm_router: LLMRouter                                         │
│  - complexity_threshold: int = 5  (word count)                   │
│  - hyde_enabled: bool = True                                     │
├─────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│  + enhance(query) -> EnhancedQuery                               │
│  + detect_complexity(query) -> QueryComplexity                   │
│  + generate_hyde(query) -> str                                   │
│  + expand_query(query) -> List[str]                              │
├─────────────────────────────────────────────────────────────────┤
│  HyDE Prompt Template:                                           │
│  "Write a detailed resume section that would answer: {query}"    │
└─────────────────────────────────────────────────────────────────┘
```

**Interface**:
```python
class QueryComplexity(Enum):
    SIMPLE = "simple"      # Direct keyword match likely
    MODERATE = "moderate"  # Some expansion helpful
    COMPLEX = "complex"    # HyDE recommended

@dataclass
class EnhancedQuery:
    original: str
    enhanced: str              # HyDE output or original
    complexity: QueryComplexity
    expanded_queries: List[str]  # For multi-query

class QueryEnhancer:
    def __init__(
        self,
        llm_router: LLMRouter,
        hyde_enabled: bool = True,
        complexity_threshold: int = 5
    ):
        ...

    async def enhance(self, query: str) -> EnhancedQuery:
        """
        Enhance query based on complexity.

        Simple queries: Pass through
        Complex queries: Generate HyDE hypothetical document
        """
        ...
```

---

#### 3.2.4 Semantic Chunker Component (NEW)

**File**: `src/rag/chunker.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                      SemanticChunker                             │
├─────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│  - chunk_size: int = 512                                         │
│  - chunk_overlap: int = 50                                       │
│  - separators: List[str] = ["\n\n", "\n", ". ", " "]            │
│  - preserve_sections: bool = True                                │
├─────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│  + chunk_document(text, metadata) -> List[Chunk]                 │
│  + chunk_with_hierarchy(text, metadata) -> List[HierarchicalChunk]│
│  + add_overlap(chunks) -> List[Chunk]                            │
│  + extract_section_context(chunk) -> str                         │
├─────────────────────────────────────────────────────────────────┤
│  Chunk Metadata:                                                 │
│  - chunk_index: int                                              │
│  - parent_id: Optional[str]                                      │
│  - section: str                                                  │
│  - has_overlap: bool                                             │
└─────────────────────────────────────────────────────────────────┘
```

**Interface**:
```python
@dataclass
class Chunk:
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    start_char: int
    end_char: int

@dataclass
class HierarchicalChunk:
    child_chunk: Chunk           # Small chunk for retrieval
    parent_content: str          # Larger context for LLM
    parent_id: str
    siblings: List[str]          # Adjacent chunk IDs

class SemanticChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        ...

    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Split document into overlapping chunks.
        Respects sentence and paragraph boundaries.
        """
        ...
```

---

#### 3.2.5 Grounding Component (NEW)

**File**: `src/rag/grounding.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                      ResponseGrounder                            │
├─────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│  - require_citations: bool = True                                │
│  - verify_claims: bool = True                                    │
│  - llm_router: LLMRouter (for claim extraction)                  │
├─────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│  + build_grounded_prompt(context, task) -> str                   │
│  + extract_claims(response) -> List[Claim]                       │
│  + verify_claim(claim, context) -> VerificationResult            │
│  + add_citations(response, context) -> str                       │
│  + get_grounding_score(response, context) -> float               │
├─────────────────────────────────────────────────────────────────┤
│  Citation Format:                                                │
│  "[Experience: TechCorp]" or "[Skills]"                          │
└─────────────────────────────────────────────────────────────────┘
```

**Interface**:
```python
@dataclass
class Claim:
    text: str
    claim_type: str  # "factual", "temporal", "quantitative"
    source_section: Optional[str]

@dataclass
class VerificationResult:
    claim: Claim
    is_grounded: bool
    confidence: float
    source_text: Optional[str]

class ResponseGrounder:
    def __init__(
        self,
        llm_router: LLMRouter,
        require_citations: bool = True,
        verify_claims: bool = True
    ):
        ...

    def build_grounded_prompt(
        self,
        context: str,
        task_type: str
    ) -> str:
        """
        Build system prompt that requires citations.
        """
        ...

    async def verify_response(
        self,
        response: str,
        context: str
    ) -> Tuple[bool, List[VerificationResult]]:
        """
        Verify all claims in response are grounded in context.
        Returns (is_valid, verification_results)
        """
        ...
```

**Updated System Prompts**:
```python
GROUNDED_SYSTEM_PROMPTS = {
    "default": """You are an AI assistant helping with resume-related tasks.

CRITICAL RULES:
1. ONLY use information from the Resume Context below
2. For EVERY claim, cite the source section: [Experience], [Skills], [Education], etc.
3. If information is NOT in the context, say: "This is not mentioned in my resume."
4. Never invent dates, companies, or skills

Resume Context:
{context}

Example response format:
"I have 5 years of Python experience [Experience: TechCorp] including Django and FastAPI [Skills]."
""",
    # ... other task-specific prompts with citation requirements
}
```

---

#### 3.2.6 Evaluation Component (NEW)

**File**: `src/rag/evaluation.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAGEvaluator                                │
├─────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│  - metrics: List[str] = ["faithfulness", "relevancy", ...]       │
│  - test_dataset: Optional[Dataset]                               │
├─────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│  + evaluate_single(question, answer, contexts, truth) -> Scores  │
│  + evaluate_batch(dataset) -> EvaluationReport                   │
│  + generate_test_questions() -> List[TestCase]                   │
│  + benchmark(rag_system) -> BenchmarkResult                      │
│  + compare_configurations(configs) -> ComparisonReport           │
├─────────────────────────────────────────────────────────────────┤
│  RAGAS Metrics:                                                  │
│  - Faithfulness: Is answer grounded in context?                  │
│  - Answer Relevancy: Does answer address the question?           │
│  - Context Precision: Is retrieved context relevant?             │
│  - Context Recall: Is all needed info retrieved?                 │
└─────────────────────────────────────────────────────────────────┘
```

**Interface**:
```python
@dataclass
class EvaluationScores:
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    overall: float

@dataclass
class TestCase:
    question: str
    ground_truth: str
    expected_sections: List[str]

class RAGEvaluator:
    def __init__(self, metrics: List[str] = None):
        ...

    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationScores:
        """Evaluate a single RAG response."""
        ...

    def generate_test_questions(
        self,
        resume_content: str,
        n_questions: int = 20
    ) -> List[TestCase]:
        """Auto-generate test questions from resume content."""
        ...
```

**Dependency**: `pip install ragas datasets`

---

## 4. Updated Retriever Design

### 4.1 Enhanced ResumeRetriever

**File**: `src/rag/retriever.py` (UPDATED)

```
┌─────────────────────────────────────────────────────────────────┐
│                  ResumeRetriever (Enhanced)                      │
├─────────────────────────────────────────────────────────────────┤
│  NEW Attributes:                                                 │
│  + hybrid_searcher: HybridSearcher                               │
│  + reranker: Reranker                                            │
│  + chunker: SemanticChunker                                      │
│  + query_enhancer: QueryEnhancer                                 │
│  + use_hybrid: bool = True                                       │
│  + use_reranking: bool = True                                    │
│  + use_hyde: bool = True                                         │
├─────────────────────────────────────────────────────────────────┤
│  UPDATED Methods:                                                │
│  + search(query, n_results, ...) -> List[SearchResult]           │
│    - Now uses hybrid search + reranking                          │
│  + index_resumes(directory) -> int                               │
│    - Now uses semantic chunking                                  │
│    - Builds BM25 index alongside vector store                    │
│  + get_context(query, max_tokens) -> ContextResult               │
│    - Returns structured context with sources                     │
├─────────────────────────────────────────────────────────────────┤
│  NEW Methods:                                                    │
│  + async enhanced_search(query, n_results) -> List[SearchResult] │
│  + get_parent_context(chunk_ids) -> str                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Updated RAG Chain Design

### 5.1 Enhanced ResumeRAG

**File**: `src/rag/rag_chain.py` (UPDATED)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ResumeRAG (Enhanced)                          │
├─────────────────────────────────────────────────────────────────┤
│  NEW Attributes:                                                 │
│  + grounder: ResponseGrounder                                    │
│  + evaluator: RAGEvaluator                                       │
│  + enable_grounding: bool = True                                 │
│  + enable_verification: bool = True                              │
├─────────────────────────────────────────────────────────────────┤
│  UPDATED Methods:                                                │
│  + async chat(...) -> RAGResponse                                │
│    - Uses grounded prompts                                       │
│    - Optionally verifies response                                │
│    - Returns structured response with citations                  │
│  + get_relevant_context(query) -> ContextResult                  │
│    - Uses enhanced retrieval pipeline                            │
├─────────────────────────────────────────────────────────────────┤
│  NEW Methods:                                                    │
│  + async chat_with_verification(...) -> VerifiedResponse         │
│  + evaluate_response(response, context) -> EvaluationScores      │
│  + get_retrieval_debug(query) -> RetrievalDebugInfo              │
└─────────────────────────────────────────────────────────────────┘
```

**New Response Types**:
```python
@dataclass
class RAGResponse:
    content: str
    citations: List[Citation]
    context_used: List[str]
    retrieval_scores: Dict[str, float]

@dataclass
class VerifiedResponse(RAGResponse):
    is_verified: bool
    verification_results: List[VerificationResult]
    grounding_score: float

@dataclass
class Citation:
    section: str
    text_snippet: str
    relevance: float
```

---

## 6. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENHANCED RAG DATA FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

INDEXING FLOW (One-time)
========================

Resume Files (.pdf, .tex, .txt)
         │
         ▼
┌─────────────────┐
│ SemanticChunker │───► Chunks with overlap
└────────┬────────┘     + Section metadata
         │              + Parent IDs
         ▼
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│Vector │ │ BM25  │
│ Store │ │ Index │
│ChromaDB│ │(rank-bm25)│
└───────┘ └───────┘


QUERY FLOW (Per Request)
========================

User Query: "What Python frameworks have I used?"
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: QUERY ENHANCEMENT                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  QueryEnhancer.detect_complexity("What Python frameworks have I used?")     │
│         │                                                                   │
│         ▼                                                                   │
│  Complexity: MODERATE (6 words, specific domain)                            │
│         │                                                                   │
│         ▼                                                                   │
│  QueryEnhancer.generate_hyde(query)                                         │
│         │                                                                   │
│         ▼                                                                   │
│  HyDE Output: "The candidate has extensive experience with Python web       │
│  frameworks including Django for backend development, FastAPI for high-     │
│  performance APIs, and Flask for microservices. They have used these        │
│  frameworks in production environments handling millions of requests..."    │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: HYBRID RETRIEVAL                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐     ┌─────────────────────┐                        │
│  │   Vector Search     │     │    BM25 Search      │                        │
│  │   (HyDE embedding)  │     │  (Original query)   │                        │
│  └──────────┬──────────┘     └──────────┬──────────┘                        │
│             │                           │                                   │
│             │  Top 25                   │  Top 25                           │
│             │                           │                                   │
│             └───────────┬───────────────┘                                   │
│                         ▼                                                   │
│              ┌─────────────────────┐                                        │
│              │   RRF Fusion        │                                        │
│              │   k=60              │                                        │
│              └──────────┬──────────┘                                        │
│                         │                                                   │
│                         ▼                                                   │
│              Top 25 Fused Results                                           │
│              [Django experience..., FastAPI APIs..., Python skills...]      │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: RERANKING                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Reranker.rerank(query="What Python frameworks...", docs=25, top_k=5)       │
│         │                                                                   │
│         ▼                                                                   │
│  Cross-Encoder Scoring:                                                     │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ Doc 1: "Django, FastAPI for REST APIs..." │ Score: 0.92         │      │
│  │ Doc 2: "Python web frameworks at TechCorp" │ Score: 0.88         │      │
│  │ Doc 3: "Flask microservices architecture"  │ Score: 0.85         │      │
│  │ Doc 4: "Python skills include Django..."   │ Score: 0.82         │      │
│  │ Doc 5: "Backend development with Python"   │ Score: 0.78         │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: CONTEXT CONSTRUCTION                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Experience: TechCorp]                                                     │
│  Led development of REST APIs using Django and FastAPI, serving 1M+ users. │
│  Implemented microservices with Flask for high-throughput data processing. │
│                                                                             │
│  [Skills]                                                                   │
│  Python Frameworks: Django, FastAPI, Flask, Celery                          │
│  Web Development: REST APIs, GraphQL, WebSockets                            │
│                                                                             │
│  [Experience: StartupXYZ]                                                   │
│  Built backend services using Django REST Framework...                      │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: GROUNDED GENERATION                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  System Prompt (with citation requirements) + Context + User Query          │
│         │                                                                   │
│         ▼                                                                   │
│  LLM Generation                                                             │
│         │                                                                   │
│         ▼                                                                   │
│  Response: "Based on my resume, I have worked extensively with Python       │
│  frameworks including:                                                      │
│                                                                             │
│  - **Django** and **FastAPI** for REST API development at TechCorp          │
│    [Experience: TechCorp], serving over 1 million users                     │
│  - **Flask** for microservices architecture [Experience: TechCorp]          │
│  - **Django REST Framework** at StartupXYZ [Experience: StartupXYZ]         │
│                                                                             │
│  My skills section also lists Django, FastAPI, Flask, and Celery [Skills]"  │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 6: VERIFICATION (Optional)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ResponseGrounder.verify_response(response, context)                        │
│         │                                                                   │
│         ▼                                                                   │
│  Claims Extracted:                                                          │
│  ├─ "Django and FastAPI for REST API" ✓ Found in context                   │
│  ├─ "serving over 1 million users" ✓ Found: "1M+ users"                    │
│  ├─ "Flask for microservices" ✓ Found in context                           │
│  └─ "Django, FastAPI, Flask, Celery in skills" ✓ Found in [Skills]         │
│                                                                             │
│  Grounding Score: 1.0 (all claims verified)                                 │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
                    VerifiedResponse with Citations
```

---

## 7. Configuration

### 7.1 Settings Updates

**File**: `config/settings.py` (ADDITIONS)

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # RAG Enhancement Settings
    use_hybrid_search: bool = True
    use_reranking: bool = True
    use_hyde: bool = True
    use_grounding: bool = True

    # Retrieval Settings
    hybrid_vector_weight: float = 0.7
    hybrid_bm25_weight: float = 0.3
    initial_retrieval_k: int = 25
    final_top_k: int = 5

    # Chunking Settings
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Reranking Settings
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Query Enhancement Settings
    hyde_complexity_threshold: int = 5

    # Grounding Settings
    require_citations: bool = True
    verify_responses: bool = False  # Optional, adds latency
```

---

## 8. Dependencies

### 8.1 New Requirements

Add to `requirements.txt`:

```
# RAG Enhancements
rank-bm25>=0.2.2          # BM25 implementation
ragas>=0.1.0              # RAG evaluation
datasets>=2.14.0          # For RAGAS

# Already have sentence-transformers for CrossEncoder
```

### 8.2 Optional Dependencies

```
# For advanced chunking (optional)
langchain>=0.1.0
langchain-text-splitters>=0.0.1
```

---

## 9. Implementation Phases

### Phase 1: Quick Wins (Week 1)
1. **Reranker** - Add cross-encoder reranking
2. **Chunk Overlap** - Update chunker with 50-char overlap
3. **Citation Prompts** - Update system prompts

### Phase 2: Hybrid Search (Week 2)
1. **HybridSearcher** - Implement BM25 + Vector fusion
2. **Update Indexing** - Build BM25 index during resume indexing
3. **Integration** - Wire into retriever

### Phase 3: Query Enhancement (Week 3)
1. **QueryEnhancer** - Implement HyDE
2. **Complexity Detection** - Add query analysis
3. **Integration** - Optional enhancement in retriever

### Phase 4: Grounding & Evaluation (Week 4)
1. **ResponseGrounder** - Citation requirements and verification
2. **RAGEvaluator** - RAGAS integration
3. **Test Dataset** - Generate evaluation questions

---

## 10. Testing Strategy

### 10.1 Unit Tests

```
tests/
├── test_reranker.py
├── test_hybrid_search.py
├── test_query_enhancer.py
├── test_chunker.py
├── test_grounding.py
└── test_evaluation.py
```

### 10.2 Integration Tests

```python
def test_full_pipeline():
    """Test complete enhanced RAG pipeline."""
    rag = ResumeRAG()

    # Index test resume
    rag.index_resumes(Path("tests/fixtures/resumes"))

    # Query
    response = await rag.chat("What Python frameworks have I used?")

    # Verify
    assert "[Experience" in response.content or "[Skills]" in response.content
    assert response.grounding_score > 0.8
```

### 10.3 Benchmark Tests

```python
def test_retrieval_improvement():
    """Measure improvement from enhancements."""
    baseline_scores = evaluate_baseline()
    enhanced_scores = evaluate_enhanced()

    assert enhanced_scores.context_precision > baseline_scores.context_precision * 1.15
    assert enhanced_scores.faithfulness > 0.9
```

---

## 11. Rollback Strategy

Each enhancement is **independently toggleable**:

```python
rag = ResumeRAG(
    use_hybrid_search=False,   # Disable hybrid, use vector only
    use_reranking=True,        # Keep reranking
    use_hyde=False,            # Disable HyDE
    enable_grounding=True      # Keep citation requirements
)
```

---

## 12. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Context Precision | ~60% | 80% | RAGAS evaluation |
| Answer Relevancy | ~70% | 85% | RAGAS evaluation |
| Faithfulness | Unknown | 90% | RAGAS evaluation |
| Query Latency | ~100ms | <200ms | Benchmark |
| Hallucination Rate | Unknown | <10% | Claim verification |

---

## 13. Next Steps

1. **Review this design** for approval
2. **Use `/sc:implement`** to build Phase 1 components
3. **Run benchmarks** after each phase
4. **Iterate** based on evaluation results

---

*Design document generated by /sc:design command*
*For implementation, use `/sc:implement` with specific component names*
