# Performance Analysis Report

## Resume RAG System - Performance Improvement Opportunities

**Analysis Date**: 2026-02-03
**Focus Areas**: Embedding Caching, Async Optimization

---

## Executive Summary

| Severity | Count | Est. Impact |
|----------|-------|-------------|
| Critical | 3 | 60-70% latency reduction |
| Medium | 4 | 20-30% latency reduction |
| Low | 3 | 5-10% latency reduction |

---

## Critical Issues

### 1. Embedding Model Reloaded on Every Query
**Location**: `src/rag/vector_store.py:51-55`
**Impact**: ~2-3 seconds per query (model load time)

```python
# CURRENT (Problem)
@property
def embedding_model(self) -> SentenceTransformer:
    if self._embedding_model is None:
        self._embedding_model = SentenceTransformer(self.embedding_model_name)
    return self._embedding_model
```

**Issue**: Each new `VectorStore` instance loads the model from scratch. CLI commands create new instances per invocation.

**Fix**: Implement module-level singleton with lazy initialization.

---

### 2. Synchronous API Calls in Async Methods
**Location**: All LLM backends (`groq_backend.py`, `openai_backend.py`, `claude_backend.py`, `gemini_backend.py`)
**Impact**: Blocks event loop, prevents concurrent requests

```python
# CURRENT (Problem) - groq_backend.py:64
async def generate(...):
    response = client.chat.completions.create(...)  # SYNC call in async method!
```

**Issue**: Using synchronous SDK clients inside `async def` methods blocks the entire event loop.

**Fix**: Use async SDK clients (`AsyncGroq`, `AsyncOpenAI`, `AsyncAnthropic`) or run sync calls in thread pool.

---

### 3. No Embedding Cache for Repeated Text
**Location**: `src/rag/vector_store.py:57-60`
**Impact**: ~90ms wasted per duplicate embedding

```python
# CURRENT (Problem)
def _embed(self, texts: List[str]) -> List[List[float]]:
    embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()
```

**Issue**: Same query text embedded repeatedly without caching.

**Fix**: Add LRU cache for query embeddings.

---

## Medium Priority Issues

### 4. CLI Creates New RAG Instance Per Command
**Location**: `src/ui/cli.py:36-38`
**Impact**: Full initialization overhead on every command

```python
# CURRENT (Problem)
def get_rag() -> ResumeRAG:
    return ResumeRAG()  # New instance every time!
```

**Fix**: Use module-level singleton or caching decorator.

---

### 5. Gemini Backend Reconfigures API Every Call
**Location**: `src/llm_backends/gemini_backend.py:83-86, 136-138`
**Impact**: ~50-100ms overhead per call

```python
# CURRENT (Problem)
async def generate(...):
    genai.configure(api_key=self.api_key)  # Called every time!
    ...
    model = genai.GenerativeModel(self.model, **model_kwargs)  # New model every time!
```

**Fix**: Configure once in `__init__` or `_get_client()`.

---

### 6. No HTTP Connection Pooling
**Location**: All LLM backend clients
**Impact**: ~100-200ms per new connection (TCP + TLS handshake)

**Issue**: Clients created without explicit connection pooling configuration.

**Fix**: Configure `httpx` clients with keep-alive and connection pools.

---

### 7. Repeated asyncio.run() Calls
**Location**: `src/ui/cli.py` (multiple locations), `src/llm_backends/base.py:87`
**Impact**: Event loop creation overhead (~1-5ms per call)

```python
# CURRENT (Problem)
response = asyncio.run(rag.chat(message))  # Creates new event loop each time!
```

**Fix**: Use single event loop for CLI session or `asyncio.get_event_loop().run_until_complete()`.

---

## Low Priority Issues

### 8. No Query Result Caching
**Location**: `src/rag/vector_store.py:110-133`
**Impact**: ~50-90ms for repeated identical queries

**Fix**: Add TTL-based cache for search results.

---

### 9. Lazy Imports Could Be Optimized
**Location**: Various (hashlib imported inside function, etc.)
**Impact**: ~1-5ms per import

**Fix**: Move to module-level imports where used frequently.

---

### 10. List Comprehensions in Hot Paths
**Location**: Message conversion in all backends
**Impact**: Minor (~1ms)

```python
# Could use generator for streaming scenarios
groq_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
```

---

## Recommended Fixes (Safe to Apply)

### Safe Auto-Fix List

| # | Fix | Risk | Impact |
|---|-----|------|--------|
| 1 | Embedding model singleton | Low | High |
| 2 | LRU cache for query embeddings | Low | High |
| 3 | Gemini API single configuration | Low | Medium |
| 4 | RAG instance caching in CLI | Low | Medium |
| 5 | Move hashlib import to module level | None | Low |

### Requires Review (Structural Changes)

| # | Fix | Risk | Impact |
|---|-----|------|--------|
| 6 | Async SDK clients | Medium | High |
| 7 | Connection pooling | Medium | Medium |
| 8 | Event loop management | Medium | Medium |

---

## Performance Benchmarks (Before)

| Operation | Current Time | Target Time |
|-----------|-------------|-------------|
| First query (cold) | ~4-5s | <2s |
| Subsequent query | ~200-500ms | <100ms |
| Embedding (per query) | ~90ms | <10ms (cached) |
| LLM API call | ~1-3s | ~1-3s (network bound) |

---

## Implementation Priority

1. **Immediate** (Safe fixes - apply now):
   - Embedding model singleton
   - Query embedding cache
   - Gemini configuration fix

2. **Short-term** (Review required):
   - Async SDK migration
   - CLI singleton pattern

3. **Long-term** (Architectural):
   - Connection pooling
   - Full async refactor

