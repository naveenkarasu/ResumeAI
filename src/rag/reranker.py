"""Cross-Encoder Reranker for improved relevance scoring"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from functools import lru_cache


# Module-level singleton for reranker model (expensive to load)
_reranker_model_cache: Dict[str, Any] = {}


def get_reranker_model(model_name: str):
    """Get or create reranker model singleton (avoids ~2-3s reload per instance)"""
    if model_name not in _reranker_model_cache:
        from sentence_transformers import CrossEncoder
        _reranker_model_cache[model_name] = CrossEncoder(model_name)
    return _reranker_model_cache[model_name]


@dataclass
class RankedDocument:
    """Document with reranking scores"""
    content: str
    metadata: Dict[str, Any]
    original_score: float      # From vector search (similarity)
    rerank_score: float        # From cross-encoder
    final_rank: int


class Reranker:
    """
    Cross-Encoder Reranker for two-stage retrieval.

    Uses sentence-transformers CrossEncoder to score query-document pairs
    for more accurate relevance ranking than bi-encoder similarity.

    Benefits:
    - Examines full query-document pair (not just embeddings)
    - +10-20% relevance improvement
    - Solves "lost in the middle" problem
    """

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize reranker with cross-encoder model.

        Args:
            model_name: HuggingFace model name for cross-encoder.
                       Default: cross-encoder/ms-marco-MiniLM-L-6-v2
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None

    @property
    def model(self):
        """Lazy-load model from singleton cache"""
        if self._model is None:
            self._model = get_reranker_model(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[RankedDocument]:
        """
        Rerank documents using cross-encoder.

        Args:
            query: User query string
            documents: List of dicts with 'content', 'metadata', and optionally 'relevance'
            top_k: Number of top documents to return

        Returns:
            List of RankedDocument sorted by rerank_score (highest first)
        """
        if not documents:
            return []

        # Prepare query-document pairs for cross-encoder
        pairs = [(query, doc.get("content", "")) for doc in documents]

        # Get cross-encoder scores
        scores = self.model.predict(pairs)

        # Create ranked documents
        ranked_docs = []
        for i, (doc, score) in enumerate(zip(documents, scores)):
            original_score = doc.get("relevance", doc.get("score", 0.0))
            ranked_docs.append(RankedDocument(
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
                original_score=float(original_score),
                rerank_score=float(score),
                final_rank=0  # Will be set after sorting
            ))

        # Sort by rerank score (highest first)
        ranked_docs.sort(key=lambda x: x.rerank_score, reverse=True)

        # Assign final ranks and limit to top_k
        result = []
        for rank, doc in enumerate(ranked_docs[:top_k]):
            doc.final_rank = rank + 1
            result.append(doc)

        return result

    def score_pair(self, query: str, document: str) -> float:
        """
        Score a single query-document pair.

        Args:
            query: User query
            document: Document text

        Returns:
            Relevance score (higher is more relevant)
        """
        return float(self.model.predict([(query, document)])[0])

    def batch_rerank(
        self,
        queries: List[str],
        documents_list: List[List[Dict[str, Any]]],
        top_k: int = 5
    ) -> List[List[RankedDocument]]:
        """
        Batch rerank multiple query-document sets.

        Args:
            queries: List of query strings
            documents_list: List of document lists (one per query)
            top_k: Number of top documents per query

        Returns:
            List of ranked document lists
        """
        return [
            self.rerank(query, docs, top_k)
            for query, docs in zip(queries, documents_list)
        ]

    def __repr__(self) -> str:
        return f"Reranker(model={self.model_name})"
