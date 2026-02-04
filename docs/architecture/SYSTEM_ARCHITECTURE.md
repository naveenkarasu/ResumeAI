# Resume RAG System Architecture

## Document Information
- **Version**: 1.0
- **Date**: 2026-02-03
- **Status**: Design Specification

---

## 1. Executive Summary

The Resume RAG (Retrieval-Augmented Generation) Assistant is an AI-powered system that enables intelligent resume management and job application assistance. It combines semantic search over personal resume data with multiple LLM backends to provide personalized assistance for job seekers.

### Key Capabilities
- Multi-format resume parsing (PDF, LaTeX, TXT)
- Semantic search over resume content
- Multi-LLM backend support (6 providers)
- Job application email drafting
- Resume tailoring suggestions
- Interview preparation assistance
- Web research integration

---

## 2. System Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                              RESUME RAG SYSTEM                                     |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +------------------+     +------------------+     +------------------+           |
|  |   PRESENTATION   |     |    APPLICATION   |     |      DATA        |           |
|  |      LAYER       |     |      LAYER       |     |      LAYER       |           |
|  +------------------+     +------------------+     +------------------+           |
|                                                                                   |
|  +--------+--------+     +------------------+     +------------------+           |
|  | Web UI | CLI UI |     |   ResumeRAG      |     |  Vector Store    |           |
|  |Streamlit| Typer |     |   (Orchestrator) |     |  (ChromaDB)      |           |
|  +--------+--------+     +------------------+     +------------------+           |
|         |                        |                        |                       |
|         v                        v                        v                       |
|  +------------------+     +------------------+     +------------------+           |
|  |  User Session    |     |   LLM Router     |     |  Embedding Model |           |
|  |  Management      |     |   (Multi-Backend)|     |  (MiniLM-L6)     |           |
|  +------------------+     +------------------+     +------------------+           |
|                                  |                                                |
|                                  v                                                |
|  +------------------+     +------------------+     +------------------+           |
|  |   Web Search     |     |   LLM Backends   |     |  Resume Retriever|           |
|  |   (DuckDuckGo)   |     |   (6 Providers)  |     |  (Parser + Index)|           |
|  +------------------+     +------------------+     +------------------+           |
|                                                                                   |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                            EXTERNAL SERVICES                                       |
+-----------------------------------------------------------------------------------+
|  +--------+  +--------+  +--------+  +--------+  +--------+  +--------+          |
|  |  Groq  |  | Ollama |  | OpenAI |  | Gemini |  | Claude |  |ChatGPT |          |
|  |  API   |  | Local  |  |  API   |  |  API   |  |  API   |  |  Web   |          |
|  | (FREE) |  | (FREE) |  | (PAID) |  | (FREE*)|  | (PAID) |  |(RISKY) |          |
|  +--------+  +--------+  +--------+  +--------+  +--------+  +--------+          |
+-----------------------------------------------------------------------------------+
```

---

## 3. Component Architecture

### 3.1 Layer Diagram

```
+===============================================================================+
|                           PRESENTATION LAYER                                   |
+===============================================================================+
|                                                                               |
|   +---------------------------+       +---------------------------+           |
|   |      Web Interface        |       |      CLI Interface        |           |
|   |      (Streamlit)          |       |        (Typer)            |           |
|   +---------------------------+       +---------------------------+           |
|   | - Chat interface          |       | - Interactive mode        |           |
|   | - Resume upload           |       | - Quick commands          |           |
|   | - Backend selection       |       | - Batch processing        |           |
|   | - History management      |       | - Status reporting        |           |
|   +---------------------------+       +---------------------------+           |
|                                                                               |
+===============================================================================+
                                    |
                                    v
+===============================================================================+
|                           APPLICATION LAYER                                    |
+===============================================================================+
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |                         ResumeRAG (Orchestrator)                      |   |
|   +-----------------------------------------------------------------------+   |
|   | - chat()              : Main conversation interface                   |   |
|   | - draft_email()       : Generate job application emails               |   |
|   | - tailor_resume()     : Resume optimization suggestions               |   |
|   | - interview_prep()    : Interview answer preparation                  |   |
|   | - index_resumes()     : Trigger resume indexing                       |   |
|   | - get_status()        : System health and statistics                  |   |
|   +-----------------------------------------------------------------------+   |
|                |                    |                    |                    |
|                v                    v                    v                    |
|   +-------------------+  +-------------------+  +-------------------+         |
|   |    LLM Router     |  | Resume Retriever  |  |    Web Search     |         |
|   +-------------------+  +-------------------+  +-------------------+         |
|   | - Backend mgmt    |  | - Document loader |  | - General search  |         |
|   | - Auto-fallback   |  | - Text chunking   |  | - News search     |         |
|   | - Load balancing  |  | - Context builder |  | - Company research|         |
|   +-------------------+  +-------------------+  +-------------------+         |
|                                                                               |
+===============================================================================+
                                    |
                                    v
+===============================================================================+
|                              DATA LAYER                                        |
+===============================================================================+
|                                                                               |
|   +---------------------------+       +---------------------------+           |
|   |      Vector Store         |       |    Embedding Model        |           |
|   |      (ChromaDB)           |       |    (MiniLM-L6-v2)         |           |
|   +---------------------------+       +---------------------------+           |
|   | - Persistent storage      |       | - 384-dim embeddings      |           |
|   | - Cosine similarity       |       | - Local execution         |           |
|   | - Metadata filtering      |       | - ~90ms/query             |           |
|   | - HNSW indexing           |       | - FREE (no API)           |           |
|   +---------------------------+       +---------------------------+           |
|                                                                               |
+===============================================================================+
```

### 3.2 LLM Backend Architecture

```
+===============================================================================+
|                            LLM ROUTER                                          |
+===============================================================================+
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |                         LLMRouter                                      |   |
|   +-----------------------------------------------------------------------+   |
|   |  - default_backend: str                                               |   |
|   |  - _backends: Dict[str, BaseLLM]                                      |   |
|   |  + get_backend(name) -> BaseLLM                                       |   |
|   |  + set_backend(name) -> void                                          |   |
|   |  + achat(message, system, history) -> LLMResponse                     |   |
|   |  + stream(messages) -> AsyncGenerator[str]                            |   |
|   |  + get_available_backends() -> List[str]                              |   |
|   +-----------------------------------------------------------------------+   |
|                                    |                                          |
|                                    | implements                               |
|                                    v                                          |
|   +-----------------------------------------------------------------------+   |
|   |                      BaseLLM (Abstract)                                |   |
|   +-----------------------------------------------------------------------+   |
|   |  <<abstract>>                                                          |   |
|   |  + model: str                                                          |   |
|   |  + backend_type: LLMType                                               |   |
|   |  + is_available: bool                                                  |   |
|   |  + generate(messages) -> LLMResponse                                   |   |
|   |  + stream(messages) -> AsyncGenerator[str]                             |   |
|   |  + achat(message, system, history) -> LLMResponse                      |   |
|   +-----------------------------------------------------------------------+   |
|                                    ^                                          |
|                                    | extends                                  |
|        +------------+------------+-+----------+------------+----------+       |
|        |            |            |            |            |          |       |
|   +--------+   +--------+   +--------+   +--------+   +--------+  +--------+ |
|   | Groq   |   | Ollama |   | OpenAI |   | Gemini |   | Claude |  |ChatGPT | |
|   |  LLM   |   |  LLM   |   |  LLM   |   |  LLM   |   |  LLM   |  |WebLLM  | |
|   +--------+   +--------+   +--------+   +--------+   +--------+  +--------+ |
|   |llama3.1|   |llama3.1|   |gpt-4   |   |gemini  |   |claude  |  |gpt-4   | |
|   | 70b    |   | local  |   |turbo   |   | 1.5pro |   | 3.5    |  | via web| |
|   | FREE   |   | FREE   |   | PAID   |   | FREE*  |   | PAID   |  | RISKY  | |
|   +--------+   +--------+   +--------+   +--------+   +--------+  +--------+ |
|                                                                               |
+===============================================================================+
```

### 3.3 RAG Pipeline Architecture

```
+===============================================================================+
|                         RAG PIPELINE DATA FLOW                                 |
+===============================================================================+

  INDEXING PIPELINE (Offline)
  ===========================

  +----------+     +------------+     +----------+     +----------+
  | Resume   | --> | Document   | --> | Text     | --> | Embedding|
  | Files    |     | Parser     |     | Chunker  |     | Model    |
  +----------+     +------------+     +----------+     +----------+
   .pdf .tex           |                   |               |
   .txt                v                   v               v
                  +----------+        +----------+    +----------+
                  | Section  |        | Metadata |    | Vector   |
                  | Extract  |        | Attach   |    | Store    |
                  +----------+        +----------+    +----------+
                       |                   |               |
                       +-------------------+---------------+
                                           |
                                           v
                                    +-------------+
                                    |  ChromaDB   |
                                    | (Persisted) |
                                    +-------------+


  QUERY PIPELINE (Online)
  =======================

  +----------+     +----------+     +-------------+     +----------+
  | User     | --> | Query    | --> | Vector      | --> | Top-K    |
  | Query    |     | Embed    |     | Similarity  |     | Results  |
  +----------+     +----------+     +-------------+     +----------+
                       |                                     |
                       v                                     v
                  +----------+                         +----------+
                  | MiniLM   |                         | Context  |
                  | Encoder  |                         | Builder  |
                  +----------+                         +----------+
                                                            |
                                                            v
  +----------+     +----------+     +-------------+     +----------+
  | Response | <-- | LLM      | <-- | System      | <-- | Prompt   |
  |          |     | Backend  |     | Prompt +    |     | Template |
  +----------+     +----------+     | Context     |     +----------+
                                    +-------------+

```

---

## 4. Data Models

### 4.1 Core Data Structures

```
+===============================================================================+
|                            DATA MODELS                                         |
+===============================================================================+

  Message
  +------------------+
  | role: str        |  # "user" | "assistant" | "system"
  | content: str     |
  +------------------+

  LLMResponse
  +------------------+
  | content: str     |
  | model: str       |
  | usage: Dict      |  # tokens_in, tokens_out
  | raw_response: Any|
  +------------------+

  ResumeChunk
  +------------------+
  | content: str     |
  | metadata: Dict   |
  |   - file: str    |
  |   - section: str |
  |   - type: str    |
  +------------------+

  SearchResult
  +------------------+
  | content: str     |
  | metadata: Dict   |
  | relevance: float |  # 0.0 - 1.0 (cosine similarity)
  +------------------+

  Settings
  +------------------+
  | project_root     |
  | data_dir         |
  | resumes_dir      |
  | chroma_dir       |
  | default_llm      |
  | *_api_key        |
  | *_model          |
  +------------------+
```

### 4.2 Vector Store Schema

```
  ChromaDB Collection: "resumes"
  +============================================================+
  | id          | document      | embedding   | metadata       |
  |-------------|---------------|-------------|----------------|
  | md5[:16]    | chunk_text    | [384 dims]  | {file,         |
  |             |               |             |  section,      |
  |             |               |             |  type}         |
  +============================================================+

  Index: HNSW (Hierarchical Navigable Small World)
  Distance: Cosine Similarity
  Dimensions: 384 (MiniLM-L6-v2)
```

---

## 5. Component Specifications

### 5.1 VectorStore Component

| Attribute | Specification |
|-----------|---------------|
| **Storage** | ChromaDB (PersistentClient) |
| **Embedding** | all-MiniLM-L6-v2 (384 dimensions) |
| **Distance Metric** | Cosine Similarity |
| **Index Type** | HNSW |
| **Deduplication** | Content-hash based (MD5) |

**Interface:**
```python
class VectorStore:
    def add_documents(documents, metadatas, ids) -> List[str]
    def search(query, n_results, where, where_document) -> Dict
    def get_all() -> Dict
    def delete(ids) -> None
    def clear() -> None
    def count() -> int
```

### 5.2 ResumeRetriever Component

| Attribute | Specification |
|-----------|---------------|
| **Supported Formats** | PDF, LaTeX (.tex), Plain Text (.txt) |
| **Chunk Size** | 500 characters (configurable) |
| **Section Detection** | Regex-based (Experience, Education, Skills, etc.) |
| **Metadata Extraction** | File path, Section name, Content type |

**Interface:**
```python
class ResumeRetriever:
    def load_pdf_resume(file_path) -> Dict[str, Any]
    def load_latex_resume(file_path) -> Dict[str, Any]
    def load_text_resume(file_path) -> Dict[str, Any]
    def chunk_resume(resume_data, chunk_size) -> List[Dict]
    def index_resumes(directory) -> int
    def search(query, n_results, section_filter) -> List[Dict]
    def get_context(query, max_tokens) -> str
```

### 5.3 LLMRouter Component

| Attribute | Specification |
|-----------|---------------|
| **Backends** | 6 (Groq, Ollama, OpenAI, Gemini, Claude, ChatGPT Web) |
| **Fallback** | Automatic to first available backend |
| **Streaming** | Supported (async generator) |
| **Rate Limiting** | Per-backend configuration |

**Interface:**
```python
class LLMRouter:
    def get_backend(name) -> BaseLLM
    def set_backend(name) -> None
    def list_backends() -> Dict[str, Dict]
    def get_available_backends() -> List[str]
    async def achat(message, system, history, backend) -> LLMResponse
    async def stream(messages, backend) -> AsyncGenerator[str, None]
```

### 5.4 ResumeRAG Orchestrator

| Attribute | Specification |
|-----------|---------------|
| **Task Types** | default, email_draft, resume_tailor, interview_prep |
| **History Limit** | 20 messages (sliding window) |
| **Context Limit** | 2000 tokens (configurable) |

**Interface:**
```python
class ResumeRAG:
    async def chat(message, task_type, include_history, backend) -> str
    async def draft_email(job_description, recipient, tone) -> str
    async def tailor_resume(job_description, section) -> str
    async def interview_prep(question, company) -> str
    def index_resumes(directory) -> int
    def get_status() -> Dict[str, Any]
```

---

## 6. Sequence Diagrams

### 6.1 Chat Flow

```
User        WebUI       ResumeRAG    Retriever    VectorStore    LLMRouter    LLM
 |            |             |            |             |             |          |
 |--message-->|             |            |             |             |          |
 |            |--chat()---->|            |             |             |          |
 |            |             |--get_context()---------->|             |          |
 |            |             |            |--search()-->|             |          |
 |            |             |            |<--results---|             |          |
 |            |             |<--context--|             |             |          |
 |            |             |                          |             |          |
 |            |             |--------build_prompt------|             |          |
 |            |             |                          |             |          |
 |            |             |--achat(prompt)-----------|------------>|          |
 |            |             |                          |             |--call--->|
 |            |             |                          |             |<-response|
 |            |             |<---------LLMResponse-----|-------------|          |
 |            |<--response--|                          |             |          |
 |<--display--|             |                          |             |          |
 |            |             |                          |             |          |
```

### 6.2 Indexing Flow

```
User        CLI         ResumeRAG    Retriever    VectorStore    EmbeddingModel
 |           |              |            |             |               |
 |--index--->|              |            |             |               |
 |           |--index_resumes()--------->|             |               |
 |           |              |            |--scan_dir-->|               |
 |           |              |            |             |               |
 |           |              |            |  for each file:             |
 |           |              |            |--load_*()-->|               |
 |           |              |            |--chunk()--->|               |
 |           |              |            |             |               |
 |           |              |            |--add_documents()----------->|
 |           |              |            |             |--encode()---->|
 |           |              |            |             |<--embeddings--|
 |           |              |            |             |--upsert()     |
 |           |              |            |<--count-----|               |
 |           |<--count------|------------|             |               |
 |<--done----|              |            |             |               |
```

---

## 7. Deployment Architecture

### 7.1 Single-Node Deployment (Current)

```
+===============================================================================+
|                         LOCAL MACHINE                                          |
+===============================================================================+
|                                                                               |
|   +-------------------------------------------------------------------+       |
|   |                    Python Runtime (3.10+)                         |       |
|   +-------------------------------------------------------------------+       |
|   |                                                                   |       |
|   |   +-----------------------+     +-----------------------+         |       |
|   |   |   Streamlit Server    |     |    CLI Application    |         |       |
|   |   |   (Port 8501)         |     |    (Terminal)         |         |       |
|   |   +-----------------------+     +-----------------------+         |       |
|   |              |                             |                      |       |
|   |              +-------------+---------------+                      |       |
|   |                            |                                      |       |
|   |                            v                                      |       |
|   |   +---------------------------------------------------+          |       |
|   |   |              Resume RAG Application               |          |       |
|   |   +---------------------------------------------------+          |       |
|   |                            |                                      |       |
|   |              +-------------+---------------+                      |       |
|   |              |                             |                      |       |
|   |              v                             v                      |       |
|   |   +-----------------------+     +-----------------------+         |       |
|   |   |  ChromaDB (SQLite)    |     |  Sentence Transformer |         |       |
|   |   |  ./data/chroma_db/    |     |  (MiniLM-L6-v2)       |         |       |
|   |   +-----------------------+     +-----------------------+         |       |
|   |                                                                   |       |
|   +-------------------------------------------------------------------+       |
|                                                                               |
+===============================================================================+
                         |
                         | HTTPS
                         v
+===============================================================================+
|                       EXTERNAL APIS                                            |
+===============================================================================+
|   Groq API | OpenAI API | Gemini API | Claude API | Ollama (localhost:11434)  |
+===============================================================================+
```

### 7.2 Production Deployment (Recommended)

```
+===============================================================================+
|                         PRODUCTION ARCHITECTURE                                |
+===============================================================================+

                            +------------------+
                            |   Load Balancer  |
                            |   (nginx/ALB)    |
                            +------------------+
                                     |
                 +-------------------+-------------------+
                 |                                       |
                 v                                       v
        +------------------+                   +------------------+
        |  Web Server 1    |                   |  Web Server 2    |
        |  (Streamlit)     |                   |  (Streamlit)     |
        +------------------+                   +------------------+
                 |                                       |
                 +-------------------+-------------------+
                                     |
                                     v
                          +------------------+
                          |   API Gateway    |
                          |   (FastAPI)      |
                          +------------------+
                                     |
                 +-------------------+-------------------+
                 |                   |                   |
                 v                   v                   v
        +-------------+     +-------------+     +-------------+
        | RAG Worker 1|     | RAG Worker 2|     | RAG Worker N|
        | (Celery)    |     | (Celery)    |     | (Celery)    |
        +-------------+     +-------------+     +-------------+
                 |                   |                   |
                 +-------------------+-------------------+
                                     |
                                     v
                          +------------------+
                          |   Redis Queue    |
                          | (Task Broker)    |
                          +------------------+
                                     |
                 +-------------------+-------------------+
                 |                                       |
                 v                                       v
        +------------------+                   +------------------+
        |  ChromaDB Server |                   |  PostgreSQL      |
        |  (Persistent)    |                   |  (User Data)     |
        +------------------+                   +------------------+

```

---

## 8. Security Considerations

### 8.1 API Key Management

| Concern | Mitigation |
|---------|------------|
| Key Exposure | Environment variables via `.env` (gitignored) |
| Key Rotation | Support for runtime key updates |
| Minimal Permissions | Per-backend key isolation |

### 8.2 Data Privacy

| Concern | Mitigation |
|---------|------------|
| Resume Data | Local storage only (no cloud sync) |
| Vector DB | Local ChromaDB with file-based persistence |
| LLM Transmission | HTTPS only, no resume caching on provider side |

### 8.3 Input Validation

| Concern | Mitigation |
|---------|------------|
| Prompt Injection | System prompt isolation |
| File Upload | Extension whitelist (.pdf, .tex, .txt) |
| Query Length | Token limits on context windows |

---

## 9. Scalability Considerations

### 9.1 Current Limitations

| Component | Limitation | Impact |
|-----------|------------|--------|
| ChromaDB | Single-file SQLite | ~100K documents max |
| Embedding | CPU-only | ~90ms per query |
| LLM Router | Sequential requests | No parallelism |
| Chat History | In-memory | Lost on restart |

### 9.2 Scaling Strategies

| Component | Strategy | Implementation |
|-----------|----------|----------------|
| Vector Store | ChromaDB Server Mode | Client-server architecture |
| Embedding | GPU acceleration | CUDA/MPS support |
| LLM Calls | Connection pooling | httpx with keep-alive |
| History | Redis/PostgreSQL | Persistent sessions |

---

## 10. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **UI** | Streamlit | 1.30+ | Web interface |
| **CLI** | Typer | 0.9+ | Command-line interface |
| **Orchestration** | Python | 3.10+ | Core runtime |
| **Vector DB** | ChromaDB | 0.4+ | Embedding storage |
| **Embeddings** | Sentence-Transformers | 2.2+ | Text encoding |
| **LLM SDKs** | groq, openai, anthropic, google-generativeai | Latest | API clients |
| **Config** | Pydantic-Settings | 2.0+ | Environment management |
| **PDF** | pypdf | 3.0+ | PDF parsing |
| **Web Search** | duckduckgo-search | 4.0+ | Search integration |

---

## 11. File Structure

```
resume-rag/
├── config/
│   └── settings.py              # Pydantic settings configuration
├── data/
│   ├── resumes/                 # User resume files
│   └── chroma_db/               # Vector database storage
├── docs/
│   └── architecture/
│       └── SYSTEM_ARCHITECTURE.md  # This document
├── src/
│   ├── __init__.py
│   ├── llm_backends/
│   │   ├── __init__.py          # Package exports
│   │   ├── base.py              # BaseLLM abstract class
│   │   ├── router.py            # LLMRouter implementation
│   │   ├── groq_backend.py      # Groq LLM backend
│   │   ├── ollama_backend.py    # Ollama LLM backend
│   │   ├── openai_backend.py    # OpenAI LLM backend
│   │   ├── gemini_backend.py    # Google Gemini backend
│   │   ├── claude_backend.py    # Anthropic Claude backend
│   │   └── chatgpt_web_backend.py  # ChatGPT Web backend
│   ├── rag/
│   │   ├── __init__.py          # Package exports
│   │   ├── vector_store.py      # ChromaDB wrapper
│   │   ├── retriever.py         # Resume parsing & retrieval
│   │   └── rag_chain.py         # Main RAG orchestrator
│   ├── web_search/
│   │   ├── __init__.py
│   │   └── search.py            # DuckDuckGo search integration
│   └── ui/
│       ├── __init__.py
│       ├── cli.py               # Typer CLI application
│       └── web.py               # Streamlit web application
├── main.py                      # Application entry point
├── setup.py                     # Installation script
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Environment template
└── README.md                    # Project documentation
```

---

## 12. Next Steps

### Immediate (Phase 1)
- [ ] Add unit tests for core components
- [ ] Implement session persistence
- [ ] Add logging and monitoring

### Short-term (Phase 2)
- [ ] Add FastAPI REST endpoint
- [ ] Implement user authentication
- [ ] Add DOCX format support

### Long-term (Phase 3)
- [ ] Multi-user support with PostgreSQL
- [ ] ChromaDB server mode deployment
- [ ] GPU-accelerated embeddings
- [ ] Job board integration APIs

---

## Appendix A: LLM Backend Comparison

| Backend | Cost | Latency | Quality | Privacy | Availability |
|---------|------|---------|---------|---------|--------------|
| Groq | FREE | ~200ms | High | Cloud | 99.9% |
| Ollama | FREE | ~2-5s | High | Local | 100% (local) |
| OpenAI | $$$$ | ~1-3s | Highest | Cloud | 99.9% |
| Gemini | FREE* | ~1-2s | High | Cloud | 99% |
| Claude | $$$ | ~2-4s | Highest | Cloud | 99.9% |
| ChatGPT Web | FREE** | ~3-5s | Highest | Cloud | Unstable |

*Free tier with limits
**May violate ToS

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation - combining search with LLM |
| **Embedding** | Dense vector representation of text |
| **Chunking** | Splitting documents into smaller searchable pieces |
| **HNSW** | Hierarchical Navigable Small World - efficient ANN index |
| **ANN** | Approximate Nearest Neighbors - fast similarity search |
| **Context Window** | Maximum tokens an LLM can process at once |

---

*Document generated by /sc:design command*
*For implementation, use `/sc:implement` with specific components*
