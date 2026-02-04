# Resume RAG Platform - Rust/Go Backend Architecture

## Overview

This document describes the architecture for a complete backend rewrite using **Go** for the API gateway and scraping services, and **Rust** for performance-critical ML/embedding operations.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + Vite)                            │
│                              Port: 5173                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP/REST
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GO API GATEWAY (Fiber)                               │
│                              Port: 8080                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   /chat     │  │   /jobs     │  │  /analyze   │  │  /settings  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ /interview  │  │   /email    │  │  /job-list  │  │   /health   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  Middleware: CORS, Compression, Logging, Rate Limiting, Request ID          │
└─────────────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          │ gRPC               │ HTTP               │ SQL
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐
│  RUST ML SERVICE│  │  GO SCRAPER SVC │  │         DATABASES               │
│    Port: 50051  │  │    Port: 8081   │  │                                 │
│                 │  │                 │  │  ┌─────────────┐ ┌───────────┐  │
│  - Embeddings   │  │  - chromedp     │  │  │ PostgreSQL  │ │  Qdrant   │  │
│  - Reranking    │  │  - Indeed       │  │  │   :5432     │ │   :6333   │  │
│  - BM25 Index   │  │  - Dice         │  │  │             │ │           │  │
│  - Skills NER   │  │  - Wellfound    │  │  │  - Jobs     │ │  - Vectors│  │
│                 │  │  - YCombinator  │  │  │  - Apps     │ │  - Index  │  │
│  Model: ONNX    │  │  - BuiltIn      │  │  │  - Users    │ │           │  │
└─────────────────┘  └─────────────────┘  │  └─────────────┘ └───────────┘  │
          │                    │          └─────────────────────────────────┘
          │                    │
          │ gRPC               │ gRPC
          ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL LLM APIs                                      │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│    │  Groq   │  │ OpenAI  │  │ Claude  │  │ Gemini  │  │ Ollama  │        │
│    └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Breakdown

### 1. Go API Gateway (`cmd/api/`)

**Framework**: Fiber v2 (fastest Go web framework)

**Responsibilities**:
- REST API routing and request handling
- Authentication and authorization
- Rate limiting (token bucket)
- Request validation
- Response caching
- LLM API orchestration
- Session management

**Directory Structure**:
```
backend-go/
├── cmd/
│   ├── api/              # API gateway entry point
│   │   └── main.go
│   └── scraper/          # Scraper service entry point
│       └── main.go
├── internal/
│   ├── api/
│   │   ├── handlers/     # HTTP handlers
│   │   │   ├── chat.go
│   │   │   ├── jobs.go
│   │   │   ├── analyze.go
│   │   │   ├── interview.go
│   │   │   ├── email.go
│   │   │   ├── joblist.go
│   │   │   └── settings.go
│   │   ├── middleware/   # HTTP middleware
│   │   │   ├── cors.go
│   │   │   ├── logging.go
│   │   │   ├── ratelimit.go
│   │   │   └── recovery.go
│   │   └── router.go     # Route definitions
│   ├── config/           # Configuration
│   │   └── config.go
│   ├── domain/           # Domain models
│   │   ├── job.go
│   │   ├── application.go
│   │   ├── chat.go
│   │   └── resume.go
│   ├── llm/              # LLM client abstraction
│   │   ├── client.go     # Interface
│   │   ├── groq.go
│   │   ├── openai.go
│   │   ├── claude.go
│   │   └── router.go     # Backend selection
│   ├── repository/       # Data access
│   │   ├── postgres/
│   │   │   ├── job.go
│   │   │   ├── application.go
│   │   │   └── search.go
│   │   └── qdrant/
│   │       └── vector.go
│   ├── scraper/          # Scraping logic
│   │   ├── scraper.go    # Interface
│   │   ├── indeed.go
│   │   ├── dice.go
│   │   ├── wellfound.go
│   │   ├── ycombinator.go
│   │   └── builtin.go
│   └── service/          # Business logic
│       ├── chat.go
│       ├── analyzer.go
│       ├── jobmatch.go
│       ├── interview.go
│       ├── email.go
│       └── joblist.go
├── pkg/                  # Shared utilities
│   ├── cache/
│   ├── logger/
│   └── validator/
├── proto/                # gRPC definitions
│   └── ml/
│       └── ml.proto
├── go.mod
└── go.sum
```

### 2. Rust ML Service (`ml-service/`)

**Framework**: Axum + Tonic (gRPC)

**Responsibilities**:
- Text embedding generation (ONNX models)
- Cross-encoder reranking
- BM25 index management
- Skills/entity extraction (NER)
- Hybrid search fusion

**Directory Structure**:
```
ml-service/
├── src/
│   ├── main.rs
│   ├── config.rs
│   ├── grpc/
│   │   ├── mod.rs
│   │   └── service.rs    # gRPC handlers
│   ├── embedding/
│   │   ├── mod.rs
│   │   ├── model.rs      # ONNX model wrapper
│   │   └── tokenizer.rs
│   ├── reranker/
│   │   ├── mod.rs
│   │   └── cross_encoder.rs
│   ├── search/
│   │   ├── mod.rs
│   │   ├── bm25.rs       # BM25 index
│   │   ├── hybrid.rs     # RRF fusion
│   │   └── qdrant.rs     # Vector DB client
│   ├── ner/
│   │   ├── mod.rs
│   │   └── skills.rs     # Skills extraction
│   └── proto/
│       └── ml.rs         # Generated from .proto
├── models/               # ONNX model files
│   ├── all-MiniLM-L6-v2/
│   └── ms-marco-MiniLM-L-6-v2/
├── Cargo.toml
└── Cargo.lock
```

### 3. Go Scraper Service (`cmd/scraper/`)

**Framework**: chromedp (headless Chrome)

**Responsibilities**:
- Parallel job scraping from multiple sources
- Rate limiting per source
- Job deduplication
- Data normalization
- Scrape task management

**Key Features**:
- Worker pool with configurable concurrency
- Per-site rate limiting
- Automatic retry with backoff
- Cookie/session management
- Proxy rotation support

## Database Schema (PostgreSQL)

```sql
-- Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    logo_url TEXT,
    website TEXT,
    industry VARCHAR(100),
    size VARCHAR(20), -- startup, small, medium, large, enterprise
    rating DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(normalized_name)
);

CREATE INDEX idx_companies_normalized ON companies(normalized_name);

-- Jobs
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    company_id UUID REFERENCES companies(id),
    location VARCHAR(255),
    location_type VARCHAR(20), -- remote, hybrid, onsite
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'USD',
    salary_text VARCHAR(100),
    description TEXT NOT NULL,
    requirements JSONB DEFAULT '[]',
    posted_date DATE,
    scraped_at TIMESTAMP DEFAULT NOW(),
    source VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    embedding_id UUID,
    content_hash VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_location_type ON jobs(location_type);
CREATE INDEX idx_jobs_salary ON jobs(salary_min, salary_max);
CREATE INDEX idx_jobs_posted ON jobs(posted_date DESC);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_active ON jobs(is_active);
CREATE INDEX idx_jobs_content_hash ON jobs(content_hash);

-- Applications
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'saved',
    applied_date DATE,
    notes TEXT,
    resume_version VARCHAR(100),
    cover_letter TEXT,
    reminder_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_reminder ON applications(reminder_date);

-- Application Timeline (audit)
CREATE TABLE application_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX idx_timeline_app ON application_timeline(application_id);

-- Saved Searches
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    query TEXT,
    filters JSONB DEFAULT '{}',
    notification_enabled BOOLEAN DEFAULT FALSE,
    last_run_at TIMESTAMP,
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Search Cache
CREATE TABLE search_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    filters JSONB,
    result_job_ids UUID[] NOT NULL,
    total_results INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cache_hash ON search_cache(query_hash);
CREATE INDEX idx_cache_expires ON search_cache(expires_at);

-- Job Match Scores (pre-calculated)
CREATE TABLE job_match_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    resume_hash VARCHAR(64) NOT NULL,
    overall_score INTEGER NOT NULL,
    skills_score INTEGER,
    experience_score INTEGER,
    education_score INTEGER,
    matched_skills JSONB DEFAULT '[]',
    missing_skills JSONB DEFAULT '[]',
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(job_id, resume_hash)
);

CREATE INDEX idx_match_job ON job_match_scores(job_id);
CREATE INDEX idx_match_score ON job_match_scores(overall_score DESC);

-- Chat Sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode VARCHAR(20) NOT NULL DEFAULT 'chat',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat Messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- user, assistant
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    grounding_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON chat_messages(session_id);
```

## Qdrant Collections

```json
{
  "collections": [
    {
      "name": "resume_chunks",
      "vectors": {
        "size": 384,
        "distance": "Cosine"
      },
      "payload_schema": {
        "section": "keyword",
        "doc_type": "keyword",
        "content": "text"
      }
    },
    {
      "name": "job_embeddings",
      "vectors": {
        "size": 384,
        "distance": "Cosine"
      },
      "payload_schema": {
        "job_id": "uuid",
        "title": "text",
        "company": "keyword",
        "source": "keyword"
      }
    }
  ]
}
```

## gRPC Service Definition

```protobuf
syntax = "proto3";

package ml;

option go_package = "github.com/user/resume-rag/proto/ml";

service MLService {
    // Embedding operations
    rpc Embed(EmbedRequest) returns (EmbedResponse);
    rpc EmbedBatch(EmbedBatchRequest) returns (EmbedBatchResponse);

    // Reranking
    rpc Rerank(RerankRequest) returns (RerankResponse);

    // Hybrid search
    rpc Search(SearchRequest) returns (SearchResponse);

    // Skills extraction
    rpc ExtractSkills(ExtractSkillsRequest) returns (ExtractSkillsResponse);

    // BM25 index management
    rpc IndexDocuments(IndexRequest) returns (IndexResponse);
    rpc ClearIndex(ClearIndexRequest) returns (ClearIndexResponse);
}

message EmbedRequest {
    string text = 1;
}

message EmbedResponse {
    repeated float embedding = 1;
}

message EmbedBatchRequest {
    repeated string texts = 1;
}

message EmbedBatchResponse {
    repeated Embedding embeddings = 1;
}

message Embedding {
    repeated float vector = 1;
}

message RerankRequest {
    string query = 1;
    repeated Document documents = 2;
    int32 top_k = 3;
}

message RerankResponse {
    repeated RankedDocument documents = 1;
}

message Document {
    string id = 1;
    string content = 2;
    float score = 3;
}

message RankedDocument {
    string id = 1;
    string content = 2;
    float score = 3;
    int32 rank = 4;
}

message SearchRequest {
    string query = 1;
    int32 top_k = 2;
    string collection = 3;
    map<string, string> filters = 4;
    bool use_hybrid = 5;
    float vector_weight = 6;
}

message SearchResponse {
    repeated SearchResult results = 1;
    string search_mode = 2;
}

message SearchResult {
    string id = 1;
    string content = 2;
    float score = 3;
    map<string, string> metadata = 4;
}

message ExtractSkillsRequest {
    string text = 1;
}

message ExtractSkillsResponse {
    repeated string technical_skills = 1;
    repeated string soft_skills = 2;
    repeated string tools = 3;
}

message IndexRequest {
    repeated IndexDocument documents = 1;
    string collection = 2;
}

message IndexDocument {
    string id = 1;
    string content = 2;
    map<string, string> metadata = 3;
}

message IndexResponse {
    int32 indexed_count = 1;
}

message ClearIndexRequest {
    string collection = 1;
}

message ClearIndexResponse {
    bool success = 1;
}
```

## API Endpoints Specification

### Chat API (`/api/chat`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Send chat message |
| GET | `/suggestions` | Get prompt suggestions |
| GET | `/history` | Get chat history |
| DELETE | `/history` | Clear chat history |

**POST /api/chat**
```json
// Request
{
    "message": "string",
    "mode": "chat|email|tailor|interview",
    "job_description": "string?",
    "use_verification": "boolean"
}

// Response
{
    "response": "string",
    "citations": [
        {"section": "string", "text": "string", "relevance": 0.95}
    ],
    "mode": "string",
    "grounding_score": 0.92,
    "search_mode": "hybrid|vector",
    "processing_time_ms": 245
}
```

### Job List API (`/api/job-list`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/search` | Search jobs |
| GET | `/jobs` | List cached jobs |
| GET | `/jobs/:id` | Get job details |
| GET | `/recommendations` | Get AI recommendations |
| GET | `/applications` | List applications |
| POST | `/applications` | Create application |
| PUT | `/applications/:id` | Update application |
| DELETE | `/applications/:id` | Delete application |
| POST | `/jobs/:id/cover-letter` | Generate cover letter |
| POST | `/scrape` | Trigger scraping |
| GET | `/scrape/status/:id` | Get scrape status |

**POST /api/job-list/search**
```json
// Request
{
    "query": "remote ML engineer $150k+ startups",
    "filters": {
        "location_type": ["remote"],
        "salary_min": 150000,
        "company_size": ["startup", "small"],
        "sources": ["indeed", "ycombinator"]
    },
    "include_match_scores": true,
    "page": 1,
    "limit": 20,
    "sort_by": "match_score",
    "sort_order": "desc"
}

// Response
{
    "jobs": [...],
    "total": 156,
    "page": 1,
    "pages": 8,
    "cached": false,
    "scrape_status": "completed"
}
```

## Configuration

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 8080
  read_timeout: 30s
  write_timeout: 30s

database:
  postgres:
    host: "localhost"
    port: 5432
    user: "resume_rag"
    password: "${POSTGRES_PASSWORD}"
    database: "resume_rag"
    pool_size: 25
  qdrant:
    host: "localhost"
    port: 6333
    collection_prefix: "resume_rag"

ml_service:
  host: "localhost"
  port: 50051
  timeout: 10s

scraper:
  concurrency: 10
  rate_limit:
    indeed: 5s
    dice: 4s
    wellfound: 4s
    ycombinator: 3s
    builtin: 4s
  retry:
    max_attempts: 3
    backoff: 2s

llm:
  default_backend: "groq"
  groq:
    api_key: "${GROQ_API_KEY}"
    model: "llama-3.3-70b-versatile"
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4o-mini"
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-sonnet-4-20250514"

cache:
  enabled: true
  ttl: 1h
  max_size: 10000

rate_limit:
  enabled: true
  requests_per_minute: 60
  burst: 10

cors:
  allowed_origins:
    - "http://localhost:5173"
    - "http://localhost:3000"
  allowed_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  allowed_headers: ["*"]
  max_age: 600
```

## Docker Compose

```yaml
version: '3.8'

services:
  api:
    build:
      context: ./backend-go
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://resume_rag:password@postgres:5432/resume_rag
      - QDRANT_URL=http://qdrant:6333
      - ML_SERVICE_URL=ml-service:50051
      - GROQ_API_KEY=${GROQ_API_KEY}
    depends_on:
      - postgres
      - qdrant
      - ml-service

  ml-service:
    build:
      context: ./ml-service
      dockerfile: Dockerfile
    ports:
      - "50051:50051"
    environment:
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./models:/app/models

  scraper:
    build:
      context: ./backend-go
      dockerfile: Dockerfile.scraper
    environment:
      - DATABASE_URL=postgres://resume_rag:password@postgres:5432/resume_rag
      - API_URL=http://api:8080
    depends_on:
      - api
      - postgres

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=resume_rag
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=resume_rag
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - api

volumes:
  postgres_data:
  qdrant_data:
```

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| API Response (cached) | <50ms p95 | In-memory cache + connection pooling |
| API Response (search) | <300ms p95 | Hybrid search with reranking |
| Scraping throughput | 100+ jobs/min | 10 concurrent browser instances |
| Embedding generation | <10ms per text | ONNX with batch processing |
| Memory (API) | <200MB | Go's efficient memory management |
| Memory (ML) | <1GB | Model loading + inference buffers |
| Memory (Scraper) | <500MB | Per 10 browser instances |

## Migration Plan

### Phase 1: Foundation (2-3 weeks)
1. Set up Go project structure
2. Set up Rust ML service structure
3. Configure PostgreSQL and Qdrant
4. Implement gRPC communication
5. Create Docker Compose setup

### Phase 2: Core Services (3-4 weeks)
1. Implement Go API handlers (all routes)
2. Implement Rust embedding service
3. Implement Rust reranking service
4. Implement Rust BM25 + hybrid search
5. Port LLM router logic to Go

### Phase 3: Scraping (2-3 weeks)
1. Port scrapers to Go with chromedp
2. Implement worker pool and rate limiting
3. Add job deduplication
4. Test against all sources

### Phase 4: Integration (2 weeks)
1. Connect frontend to new backend
2. End-to-end testing
3. Performance benchmarking
4. Bug fixes and optimization

### Phase 5: Production (1-2 weeks)
1. Production Docker builds
2. CI/CD pipeline
3. Monitoring and logging
4. Documentation updates

## Technology Choices Rationale

### Why Go for API/Scraping?
- **Fiber**: Fastest Go web framework, Express-like syntax
- **chromedp**: Native Chrome DevTools Protocol, no external deps
- **sqlx**: Type-safe SQL with compile-time checks
- **Simple concurrency**: goroutines + channels for parallel scraping
- **Fast compilation**: Quick iteration during development
- **Single binary**: Easy deployment

### Why Rust for ML?
- **ONNX Runtime**: Production-grade inference, SIMD optimization
- **Qdrant client**: Native Rust, excellent performance
- **Memory safety**: No GC pauses during inference
- **Tonic/Axum**: Async gRPC with high throughput
- **bm25 crate**: Efficient BM25 implementation
- **Tokenizers**: HuggingFace tokenizers in Rust

### Why PostgreSQL over SQLite?
- **Concurrency**: Multiple writers without lock contention
- **pgvector**: Alternative to Qdrant if needed
- **JSONB**: Efficient JSON storage and querying
- **Connection pooling**: Better for web workloads
- **Full-text search**: Built-in FTS for fallback

### Why Qdrant over ChromaDB?
- **Production-ready**: Designed for scale
- **Rust native**: Excellent performance
- **Filtering**: Advanced payload filtering
- **Snapshots**: Built-in backup/restore
- **gRPC API**: Low latency from Rust service
