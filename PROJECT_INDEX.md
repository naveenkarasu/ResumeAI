# Project Index: Resume RAG

**Generated**: 2026-02-03
**Type**: AI-powered Resume Assistant with RAG
**Status**: Active Development (Web Platform Phase)

---

## Project Structure

```
resume-rag/
├── src/                      # Python source code
│   ├── rag/                  # RAG components (9 files)
│   ├── llm_backends/         # LLM integrations (8 files)
│   ├── web_search/           # Web search (2 files)
│   └── ui/                   # User interfaces
│       ├── cli.py            # CLI interface
│       ├── web.py            # Streamlit interface
│       └── api/              # FastAPI backend (12 files)
├── config/                   # Configuration
├── data/                     # ChromaDB + sample data
├── docs/                     # Documentation
│   ├── architecture/         # System designs
│   ├── requirements/         # Feature specs
│   └── workflow/             # Implementation plans
└── frontend/                 # React + TypeScript app (31 files)
    ├── src/
    │   ├── api/              # API client
    │   ├── components/       # React components
    │   ├── hooks/            # Custom hooks
    │   ├── pages/            # Page components
    │   └── types/            # TypeScript types
    └── package.json
```

---

## Entry Points

| Entry | Path | Command |
|-------|------|---------|
| **CLI** | `src/ui/cli.py` | `python -m src.ui.cli` |
| **Web (Streamlit)** | `src/ui/web.py` | `streamlit run src/ui/web.py` |
| **API** | `src/ui/api/main.py` | `uvicorn src.ui.api.main:app --reload` |
| **Frontend** | `frontend/` | `cd frontend && npm run dev` |

---

## Core Modules

### `src/rag/` - RAG Pipeline
| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `rag_chain.py` | Main RAG interface | `ResumeRAG`, `VerifiedResponse` |
| `retriever.py` | Document retrieval | `ResumeRetriever` |
| `vector_store.py` | ChromaDB wrapper | `VectorStore` |
| `reranker.py` | Cross-encoder reranking | `Reranker`, `RankedDocument` |
| `hybrid_search.py` | BM25 + Vector fusion | `HybridSearcher`, `SearchResult` |
| `query_enhancer.py` | HyDE implementation | `QueryEnhancer`, `QueryComplexity` |
| `grounding.py` | Citation verification | `ResponseGrounder`, `GroundingReport` |
| `evaluation.py` | RAGAS metrics | `RAGEvaluator`, `EvaluationScores` |

### `src/llm_backends/` - LLM Integrations
| Backend | Model | Free Tier |
|---------|-------|-----------|
| `groq_backend.py` | Llama 3.3 70B | Yes |
| `gemini_backend.py` | Gemini 1.5 | Yes |
| `openai_backend.py` | GPT-4o | No |
| `claude_backend.py` | Claude 3.5 | No |
| `ollama_backend.py` | Local models | Yes (local) |

### `src/web_search/` - External Search
- `search.py`: DuckDuckGo integration for company research

---

## RAG Features

| Feature | Status | Impact |
|---------|--------|--------|
| Vector Search (ChromaDB) | Done | Baseline |
| Hybrid Search (BM25+Vector) | Done | +15-25% accuracy |
| Cross-Encoder Reranking | Done | +10-20% relevance |
| HyDE Query Enhancement | Done | +10-15% complex queries |
| Citation Grounding | Done | -42-68% hallucinations |
| RAGAS Evaluation | Done | Quality measurement |
| Chunk Overlap | Done | Better context |

---

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| chromadb | >=0.4.0 | Vector database |
| sentence-transformers | >=2.2.0 | Embeddings + reranking |
| rank-bm25 | >=0.2.2 | BM25 keyword search |
| groq | >=0.4.0 | Fast LLM inference |
| typer | >=0.9.0 | CLI framework |
| fastapi | >=0.109.0 | API backend |
| react | ^18.2.0 | Web frontend |
| @tanstack/react-query | ^5.17.0 | Server state |
| tailwindcss | ^3.4.0 | Styling |

---

## Configuration

| File | Purpose |
|------|---------|
| `config/settings.py` | App settings (Pydantic) |
| `.env` | API keys (not committed) |
| `requirements.txt` | Python dependencies |

**Required Environment Variables:**
```
GROQ_API_KEY=        # Free tier available
GEMINI_API_KEY=      # Free tier available
OPENAI_API_KEY=      # Optional (paid)
CLAUDE_API_KEY=      # Optional (paid)
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/architecture/SYSTEM_ARCHITECTURE.md` | Overall system design |
| `docs/architecture/RAG_IMPROVEMENTS_DESIGN.md` | RAG enhancement specs |
| `docs/architecture/WEB_PLATFORM_ARCHITECTURE.md` | React+FastAPI design |
| `docs/requirements/PLATFORM_REQUIREMENTS.md` | Feature requirements |
| `docs/workflow/IMPLEMENTATION_PLAN.md` | 6-week build plan |
| `claudedocs/research_rag_best_practices_2026-02-03.md` | RAG research |

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Index resumes
python -m src.ui.cli index --path ./resumes

# 4. Run CLI
python -m src.ui.cli interactive

# 5. Or run Streamlit web UI
streamlit run src/ui/web.py

# 6. Or run React + FastAPI web platform
# Terminal 1: Backend
uvicorn src.ui.api.main:app --reload --port 8000

# Terminal 2: Frontend (first time: npm install)
cd frontend && npm install && npm run dev
# Access: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

---

## CLI Commands

```bash
python -m src.ui.cli <command>

Commands:
  chat <message>       Chat with resume assistant
  email --job <desc>   Generate application email
  tailor --job <desc>  Get resume suggestions
  interview <question> Interview prep
  search <query>       Search resume content
  index --path <dir>   Index resumes
  status               Show system status
  backends             List LLM backends
  interactive          Start interactive mode
```

---

## Current Development Phase

**Phase**: Web Platform (React + FastAPI)
**Timeline**: 6 weeks

```
Week 1-2: Foundation     [DONE]
├── FastAPI backend      ✓ 18 files
├── React frontend       ✓ 29 files
└── Chat page            ✓ Working

Week 3-4: Core Features  [DONE]
├── Job Analyzer         ✓ Full analysis UI
├── Interview Prep       ✓ Questions + STAR + Practice
└── Email Generator      ✓ 3 email types

Week 5-6: Polish         [DONE]
├── Mobile responsive    ✓ Hamburger menu + layouts
├── Toast notifications  ✓ Success/error feedback
├── Error boundaries     ✓ Graceful error handling
├── Keyboard shortcuts   ✓ Ctrl+K, Ctrl+1-4
└── Copy buttons         ✓ All outputs copyable
```

---

## File Counts

| Category | Count |
|----------|-------|
| Python source | 36 files |
| Frontend (TS/React) | 31 files |
| Documentation | 12 files |
| Configuration | 8 files |
| **Total** | 87 files |

---

## Usage for Claude

**To understand this project, read:**
1. This file (PROJECT_INDEX.md)
2. `src/rag/__init__.py` for RAG exports
3. `src/llm_backends/__init__.py` for LLM exports

**To work on features:**
- RAG improvements → `src/rag/`
- New LLM backend → `src/llm_backends/`
- CLI commands → `src/ui/cli.py`
- API endpoints → `src/ui/api/routers/`
- API services → `src/ui/api/services/`
- Frontend pages → `frontend/src/pages/`
- Frontend components → `frontend/src/components/`

---

*Index generated by /sc:index-repo*
*Token savings: ~55,000 tokens per session*
