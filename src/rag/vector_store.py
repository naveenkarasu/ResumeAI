"""Vector Store using ChromaDB for resume embeddings"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from functools import lru_cache
import hashlib
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


# Module-level singleton for embedding model (expensive to load)
_embedding_model_cache: Dict[str, SentenceTransformer] = {}


def get_embedding_model(model_name: str) -> SentenceTransformer:
    """Get or create embedding model singleton (avoids reloading ~2-3s per instance)"""
    if model_name not in _embedding_model_cache:
        _embedding_model_cache[model_name] = SentenceTransformer(model_name)
    return _embedding_model_cache[model_name]


# LRU cache for query embeddings (avoids re-embedding same text)
@lru_cache(maxsize=1000)
def _cached_embed_single(text: str, model_name: str) -> tuple:
    """Cache embeddings for repeated queries (returns tuple for hashability)"""
    model = get_embedding_model(model_name)
    embedding = model.encode([text], convert_to_numpy=True)[0]
    return tuple(embedding.tolist())


class VectorStore:
    """
    ChromaDB-based vector store for resume data.

    Stores embeddings of resume sections for semantic search.
    Uses sentence-transformers for FREE local embeddings.
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[Path] = None,
        embedding_model: Optional[str] = None
    ):
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_directory = persist_directory or settings.chroma_dir
        self.embedding_model_name = embedding_model or settings.embedding_model

        # Initialize embedding model (FREE, local)
        self._embedding_model = None

        # Initialize ChromaDB
        self._client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    @property
    def embedding_model(self) -> SentenceTransformer:
        """Get embedding model from singleton cache (avoids ~2-3s reload per instance)"""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model(self.embedding_model_name)
        return self._embedding_model

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts with caching for repeated queries"""
        # For single text queries, use cache (common case for search)
        if len(texts) == 1:
            cached = _cached_embed_single(texts[0], self.embedding_model_name)
            return [list(cached)]

        # For batch operations (indexing), skip cache to avoid memory bloat
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to the vector store, skipping duplicates"""
        if ids is None:
            # Generate IDs based on content hash
            ids = [
                hashlib.md5(doc.encode()).hexdigest()[:16]
                for doc in documents
            ]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        # Deduplicate by ID (keep first occurrence)
        seen_ids = set()
        unique_docs = []
        unique_metas = []
        unique_ids = []

        for doc, meta, doc_id in zip(documents, metadatas, ids):
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append(doc)
                unique_metas.append(meta)
                unique_ids.append(doc_id)

        if not unique_docs:
            return []

        # Generate embeddings
        embeddings = self._embed(unique_docs)

        # Add to ChromaDB (use upsert to handle any remaining duplicates)
        self._collection.upsert(
            documents=unique_docs,
            embeddings=embeddings,
            metadatas=unique_metas,
            ids=unique_ids
        )

        return unique_ids

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search for similar documents"""
        query_embedding = self._embed([query])[0]

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"]
        )

        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "ids": results["ids"][0] if results["ids"] else []
        }

    def get_all(self) -> Dict[str, Any]:
        """Get all documents in the collection"""
        return self._collection.get(include=["documents", "metadatas"])

    def delete(self, ids: List[str]):
        """Delete documents by IDs"""
        self._collection.delete(ids=ids)

    def clear(self):
        """Clear all documents from the collection"""
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        """Get number of documents in the collection"""
        return self._collection.count()

    def __repr__(self) -> str:
        return f"VectorStore(collection={self.collection_name}, documents={self.count()})"
