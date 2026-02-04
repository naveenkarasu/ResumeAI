# Resume RAG Web Platform - System Architecture

**Version**: 1.0
**Date**: 2026-02-03
**Status**: Design Specification

---

## 1. System Overview

### 1.1 Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RESUME RAG PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        FRONTEND (React + TypeScript)                 │   │
│   │                                                                     │   │
│   │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│   │   │   Chat   │  │   Job    │  │Interview │  │  Email   │          │   │
│   │   │   Page   │  │ Analyzer │  │   Prep   │  │Generator │          │   │
│   │   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │   │
│   │        │              │              │              │               │   │
│   │        └──────────────┴──────────────┴──────────────┘               │   │
│   │                              │                                       │   │
│   │                    ┌─────────┴─────────┐                            │   │
│   │                    │   React Query     │                            │   │
│   │                    │   (API Client)    │                            │   │
│   │                    └─────────┬─────────┘                            │   │
│   └──────────────────────────────┼──────────────────────────────────────┘   │
│                                  │                                           │
│                          HTTP/REST API                                       │
│                                  │                                           │
│   ┌──────────────────────────────┼──────────────────────────────────────┐   │
│   │                     BACKEND (FastAPI)                                │   │
│   │                              │                                       │   │
│   │   ┌──────────────────────────┴───────────────────────────────┐      │   │
│   │   │                    API Router                             │      │   │
│   │   │  /chat  /analyze  /interview  /email  /settings  /health │      │   │
│   │   └──────────────────────────┬───────────────────────────────┘      │   │
│   │                              │                                       │   │
│   │   ┌──────────────────────────┴───────────────────────────────┐      │   │
│   │   │                   Service Layer                           │      │   │
│   │   │  ChatService  AnalyzerService  InterviewService  ...     │      │   │
│   │   └──────────────────────────┬───────────────────────────────┘      │   │
│   │                              │                                       │   │
│   │   ┌──────────────────────────┴───────────────────────────────┐      │   │
│   │   │                    RAG Core                               │      │   │
│   │   │  ResumeRAG  Retriever  Reranker  HybridSearch  Grounder  │      │   │
│   │   └──────────────────────────┬───────────────────────────────┘      │   │
│   │                              │                                       │   │
│   │   ┌────────────┬─────────────┼─────────────┬────────────────┐       │   │
│   │   │            │             │             │                │       │   │
│   │   ▼            ▼             ▼             ▼                ▼       │   │
│   │ ChromaDB   LLM Router   Embedding    Question DB    Web Search     │   │
│   │ (Vector)   (Multi-LLM)   Model       (JSON/SQLite)  (Optional)     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React 18 + TypeScript | Type safety, component ecosystem |
| Styling | Tailwind CSS | Rapid UI development, utility-first |
| State | React Query + Zustand | Server state + local state |
| Routing | React Router v6 | Standard routing solution |
| Backend | FastAPI | Async, fast, auto-docs, Python native |
| API Docs | OpenAPI/Swagger | Auto-generated from FastAPI |
| RAG | Existing src/rag | Reuse all implemented components |
| Database | SQLite (optional) | Simple, file-based, no setup |
| Vector DB | ChromaDB | Already implemented |

---

## 2. Directory Structure

```
resume-rag/
├── src/                          # Existing Python source
│   ├── rag/                      # RAG components (unchanged)
│   ├── llm_backends/             # LLM backends (unchanged)
│   ├── web_search/               # Web search (unchanged)
│   ├── ui/
│   │   ├── cli.py                # Existing CLI (unchanged)
│   │   └── api/                  # NEW: FastAPI backend
│   │       ├── __init__.py
│   │       ├── main.py           # FastAPI app entry
│   │       ├── config.py         # API configuration
│   │       ├── dependencies.py   # Dependency injection
│   │       ├── routers/
│   │       │   ├── __init__.py
│   │       │   ├── chat.py       # /api/chat endpoints
│   │       │   ├── analyze.py    # /api/analyze endpoints
│   │       │   ├── interview.py  # /api/interview endpoints
│   │       │   ├── email.py      # /api/email endpoints
│   │       │   └── settings.py   # /api/settings endpoints
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── chat_service.py
│   │       │   ├── analyzer_service.py
│   │       │   ├── interview_service.py
│   │       │   └── email_service.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── requests.py   # Pydantic request models
│   │       │   └── responses.py  # Pydantic response models
│   │       └── data/
│   │           └── questions.json # Interview question bank
│
├── frontend/                     # NEW: React frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx              # App entry
│   │   ├── App.tsx               # Root component
│   │   ├── api/
│   │   │   ├── client.ts         # API client setup
│   │   │   ├── chat.ts           # Chat API hooks
│   │   │   ├── analyze.ts        # Analyzer API hooks
│   │   │   ├── interview.ts      # Interview API hooks
│   │   │   └── email.ts          # Email API hooks
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── chat/
│   │   │   │   ├── ChatInput.tsx
│   │   │   │   ├── ChatMessage.tsx
│   │   │   │   └── ChatHistory.tsx
│   │   │   ├── analyzer/
│   │   │   │   ├── JobInput.tsx
│   │   │   │   ├── MatchScore.tsx
│   │   │   │   └── GapAnalysis.tsx
│   │   │   ├── interview/
│   │   │   │   ├── QuestionList.tsx
│   │   │   │   ├── StarGenerator.tsx
│   │   │   │   └── PracticeMode.tsx
│   │   │   └── email/
│   │   │       ├── EmailForm.tsx
│   │   │       └── EmailPreview.tsx
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx
│   │   │   ├── AnalyzerPage.tsx
│   │   │   ├── InterviewPage.tsx
│   │   │   ├── EmailPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   └── useLocalStorage.ts
│   │   ├── store/
│   │   │   └── appStore.ts       # Zustand store
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript types
│   │   └── utils/
│   │       └── markdown.ts       # Markdown rendering
│   └── public/
│       └── favicon.ico
│
├── config/                       # Existing config
├── data/                         # ChromaDB, etc.
├── resumes/                      # Resume files
└── docs/                         # Documentation
```

---

## 3. API Design

### 3.1 API Endpoints

```
BASE URL: http://localhost:8000/api

┌─────────────────────────────────────────────────────────────────────────────┐
│                              API ENDPOINTS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CHAT                                                                       │
│  ─────                                                                      │
│  POST   /api/chat                    Send message, get response             │
│  GET    /api/chat/history            Get chat history                       │
│  DELETE /api/chat/history            Clear chat history                     │
│  GET    /api/chat/suggestions        Get suggested questions                │
│                                                                             │
│  JOB ANALYZER                                                               │
│  ────────────                                                               │
│  POST   /api/analyze/job             Analyze job description                │
│  POST   /api/analyze/match           Get match score                        │
│  POST   /api/analyze/gaps            Get gap analysis                       │
│  POST   /api/analyze/keywords        Extract keywords                       │
│                                                                             │
│  INTERVIEW PREP                                                             │
│  ──────────────                                                             │
│  GET    /api/interview/questions     Get question bank (with filters)       │
│  POST   /api/interview/star          Generate STAR story                    │
│  POST   /api/interview/practice      Submit answer, get feedback            │
│  POST   /api/interview/company       Research company                       │
│                                                                             │
│  EMAIL GENERATOR                                                            │
│  ───────────────                                                            │
│  POST   /api/email/application       Generate application email             │
│  POST   /api/email/followup          Generate follow-up email               │
│  POST   /api/email/thankyou          Generate thank you email               │
│                                                                             │
│  SETTINGS                                                                   │
│  ────────                                                                   │
│  GET    /api/settings                Get current settings                   │
│  PUT    /api/settings                Update settings                        │
│  GET    /api/settings/backends       List available LLM backends            │
│                                                                             │
│  SYSTEM                                                                     │
│  ──────                                                                     │
│  GET    /api/health                  Health check                           │
│  GET    /api/status                  System status                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Request/Response Models

```python
# ============= CHAT =============

class ChatRequest(BaseModel):
    message: str
    task_type: str = "default"  # default, email_draft, resume_tailor, interview_prep
    include_history: bool = True

class ChatResponse(BaseModel):
    response: str
    citations: List[str]
    grounding_score: Optional[float]
    sources: List[SourceReference]

class SourceReference(BaseModel):
    section: str
    content: str
    relevance: float

# ============= JOB ANALYZER =============

class AnalyzeJobRequest(BaseModel):
    job_description: str
    focus_areas: Optional[List[str]] = None  # skills, experience, education

class AnalyzeJobResponse(BaseModel):
    match_score: float  # 0-100
    matching_skills: List[SkillMatch]
    missing_requirements: List[str]
    keyword_suggestions: List[str]
    resume_suggestions: List[ResumeSuggestion]

class SkillMatch(BaseModel):
    skill: str
    source_section: str
    relevance: float

class ResumeSuggestion(BaseModel):
    section: str
    current: str
    suggested: str
    reason: str

# ============= INTERVIEW PREP =============

class QuestionFilter(BaseModel):
    category: Optional[str] = None  # behavioral, technical, system_design, leadership
    role: Optional[str] = None      # swe, data_ml, devops, em
    difficulty: Optional[str] = None  # easy, medium, hard

class InterviewQuestion(BaseModel):
    id: str
    question: str
    category: str
    role: List[str]
    difficulty: str
    tips: List[str]

class StarRequest(BaseModel):
    achievement: str  # From resume
    target_question: Optional[str] = None

class StarResponse(BaseModel):
    situation: str
    task: str
    action: str
    result: str
    full_story: str

class PracticeRequest(BaseModel):
    question_id: str
    answer: str

class PracticeFeedback(BaseModel):
    score: float  # 0-100
    relevance: str
    structure: str
    specificity: str
    improvements: List[str]
    example_answer: str

# ============= EMAIL =============

class EmailRequest(BaseModel):
    job_description: str
    recipient: Optional[str] = None
    tone: str = "professional"  # professional, conversational, enthusiastic
    length: str = "standard"    # brief, standard, detailed
    focus: str = "balanced"     # technical, leadership, culture_fit, balanced

class EmailResponse(BaseModel):
    subject: str
    body: str
    variations: List[EmailVariation]

class EmailVariation(BaseModel):
    label: str  # "More Formal", "More Personal", etc.
    subject: str
    body: str
```

---

## 4. Frontend Architecture

### 4.1 Component Hierarchy

```
App
├── Layout
│   ├── Sidebar
│   │   ├── NavItem (Chat)
│   │   ├── NavItem (Job Analyzer)
│   │   ├── NavItem (Interview Prep)
│   │   ├── NavItem (Email Generator)
│   │   └── NavItem (Settings)
│   └── MainContent
│       └── <Outlet /> (React Router)
│
├── ChatPage
│   ├── ChatHistory
│   │   └── ChatMessage (multiple)
│   ├── SuggestedQuestions
│   └── ChatInput
│
├── AnalyzerPage
│   ├── JobInput (textarea)
│   ├── AnalyzeButton
│   └── AnalysisResults
│       ├── MatchScore (circular progress)
│       ├── MatchingSkills (list)
│       ├── MissingRequirements (list)
│       └── Suggestions (accordion)
│
├── InterviewPage
│   ├── TabNavigation
│   │   ├── Questions Tab
│   │   ├── STAR Generator Tab
│   │   └── Practice Tab
│   ├── QuestionsPanel
│   │   ├── FilterBar
│   │   └── QuestionList
│   ├── StarGeneratorPanel
│   │   ├── AchievementInput
│   │   └── StarOutput
│   └── PracticePanel
│       ├── QuestionDisplay
│       ├── AnswerInput
│       └── FeedbackDisplay
│
├── EmailPage
│   ├── EmailForm
│   │   ├── JobDescriptionInput
│   │   ├── ToneSelector
│   │   ├── LengthSelector
│   │   └── FocusSelector
│   └── EmailPreview
│       ├── EmailCard (main)
│       └── VariationCards
│
└── SettingsPage
    ├── BackendSelector
    ├── PreferencesForm
    └── SystemStatus
```

### 4.2 State Management

```typescript
// Zustand store for app-wide state
interface AppState {
  // Settings
  selectedBackend: string;
  theme: 'light' | 'dark';

  // Chat
  chatHistory: ChatMessage[];
  addMessage: (msg: ChatMessage) => void;
  clearHistory: () => void;

  // Saved Items (optional)
  savedJobs: SavedJob[];
  practiceHistory: PracticeSession[];
}

// React Query for server state
// - useChat() - chat mutations
// - useAnalyzeJob() - job analysis
// - useQuestions() - interview questions
// - useGenerateEmail() - email generation
```

### 4.3 API Client Setup

```typescript
// api/client.ts
import { QueryClient } from '@tanstack/react-query';

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

// Generic fetch wrapper
export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}
```

---

## 5. Backend Architecture

### 5.1 FastAPI Application Structure

```python
# src/ui/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import chat, analyze, interview, email, settings
from .dependencies import get_rag_instance

app = FastAPI(
    title="Resume RAG API",
    description="AI-powered resume assistant API",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["Analyzer"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])
app.include_router(email.router, prefix="/api/email", tags=["Email"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
```

### 5.2 Dependency Injection

```python
# src/ui/api/dependencies.py
from functools import lru_cache
from src.rag import ResumeRAG

@lru_cache(maxsize=1)
def get_rag_instance() -> ResumeRAG:
    """Singleton RAG instance"""
    return ResumeRAG(
        use_hybrid=True,
        use_reranking=True,
        enable_grounding=True
    )

def get_rag() -> ResumeRAG:
    """Dependency for route handlers"""
    return get_rag_instance()
```

### 5.3 Service Layer Example

```python
# src/ui/api/services/analyzer_service.py
from typing import List
from src.rag import ResumeRAG

class AnalyzerService:
    def __init__(self, rag: ResumeRAG):
        self.rag = rag

    async def analyze_job(self, job_description: str) -> dict:
        """Analyze job description against resume"""

        # Get relevant context
        context = self.rag.get_relevant_context(job_description)

        # Generate analysis
        prompt = f"""Analyze this job description against my resume.

Job Description:
{job_description}

Provide:
1. Match score (0-100%)
2. Matching skills and experience
3. Missing requirements
4. Keywords to add to resume
5. Specific suggestions for each resume section

Format as structured JSON."""

        response = await self.rag.chat(prompt, task_type="resume_tailor")

        # Parse and return structured response
        return self._parse_analysis(response)

    def _parse_analysis(self, response: str) -> dict:
        # Parse LLM response into structured format
        ...
```

---

## 6. Data Flow Diagrams

### 6.1 Chat Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   User     │────▶│  React     │────▶│  FastAPI   │────▶│  ResumeRAG │
│   Types    │     │  ChatInput │     │  /api/chat │     │  .chat()   │
└────────────┘     └────────────┘     └────────────┘     └─────┬──────┘
                                                               │
                   ┌───────────────────────────────────────────┘
                   │
                   ▼
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│  Display   │◀────│  Format    │◀────│  Response  │◀────│  LLM +     │
│  Message   │     │  Markdown  │     │  JSON      │     │  Grounding │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
```

### 6.2 Job Analysis Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JOB ANALYSIS FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

     User Input                    Backend Processing                 Output
     ──────────                    ──────────────────                 ──────

┌──────────────┐            ┌──────────────────────┐          ┌──────────────┐
│ Job          │            │ 1. Extract Keywords  │          │ Match Score  │
│ Description  │───────────▶│    from JD           │─────────▶│ (0-100%)     │
│ (textarea)   │            └──────────┬───────────┘          └──────────────┘
└──────────────┘                       │
                                       ▼
                            ┌──────────────────────┐          ┌──────────────┐
                            │ 2. Search Resume     │          │ Matching     │
                            │    (Hybrid + Rerank) │─────────▶│ Skills       │
                            └──────────┬───────────┘          └──────────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐          ┌──────────────┐
                            │ 3. Compare           │          │ Missing      │
                            │    Requirements      │─────────▶│ Requirements │
                            └──────────┬───────────┘          └──────────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐          ┌──────────────┐
                            │ 4. Generate          │          │ Resume       │
                            │    Suggestions (LLM) │─────────▶│ Suggestions  │
                            └──────────────────────┘          └──────────────┘
```

---

## 7. Interview Question Bank Schema

```json
// src/ui/api/data/questions.json
{
  "questions": [
    {
      "id": "beh-001",
      "question": "Tell me about a time you had to deal with a difficult team member.",
      "category": "behavioral",
      "roles": ["swe", "data_ml", "devops", "em"],
      "difficulty": "medium",
      "tips": [
        "Focus on the resolution, not the conflict",
        "Show empathy and communication skills",
        "Quantify the positive outcome if possible"
      ],
      "star_prompts": {
        "situation": "Describe the team dynamic and the specific challenge",
        "task": "What was your responsibility in resolving this?",
        "action": "What specific steps did you take?",
        "result": "What was the outcome? How did the relationship improve?"
      }
    },
    {
      "id": "tech-swe-001",
      "question": "Explain a complex technical concept to a non-technical stakeholder.",
      "category": "technical",
      "roles": ["swe", "data_ml"],
      "difficulty": "medium",
      "tips": [
        "Use analogies and simple language",
        "Focus on the business impact",
        "Check for understanding"
      ]
    },
    {
      "id": "sys-001",
      "question": "Design a URL shortener system.",
      "category": "system_design",
      "roles": ["swe", "devops"],
      "difficulty": "medium",
      "tips": [
        "Start with requirements clarification",
        "Discuss scale: reads vs writes ratio",
        "Consider: hashing, database choice, caching"
      ]
    }
    // ... 50+ questions
  ]
}
```

---

## 8. Deployment Architecture

### 8.1 Local Development

```
┌─────────────────────────────────────────────────────────────────┐
│                     LOCAL DEVELOPMENT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Terminal 1: Backend                Terminal 2: Frontend       │
│   ─────────────────────              ────────────────────       │
│   $ uvicorn src.ui.api.main:app      $ cd frontend              │
│     --reload --port 8000             $ npm run dev              │
│                                        (Vite @ :5173)           │
│                                                                 │
│   Browser: http://localhost:5173                                │
│   API Docs: http://localhost:8000/docs                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Production (Optional)

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRODUCTION DEPLOYMENT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Option A: Single Server (Railway/Render)                      │
│   ─────────────────────────────────────────                     │
│   - FastAPI serves built React static files                     │
│   - Single process, simple deployment                           │
│   - Cost: ~$5-10/month                                          │
│                                                                 │
│   Option B: Separate Services (Vercel + Railway)                │
│   ────────────────────────────────────────────                  │
│   - Frontend: Vercel (free tier)                                │
│   - Backend: Railway ($5/month)                                 │
│   - Better for scaling                                          │
│                                                                 │
│   Option C: Local Only                                          │
│   ────────────────────                                          │
│   - Run on your machine                                         │
│   - No hosting costs                                            │
│   - Access via localhost                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Security Considerations

| Concern | Mitigation |
|---------|------------|
| API Keys | Environment variables only, never in code |
| CORS | Restrict to known origins |
| Rate Limiting | Add FastAPI middleware (optional for personal use) |
| Input Validation | Pydantic models validate all input |
| No Auth | Personal use only - add auth if deploying publicly |

---

## 10. Implementation Checklist

### Phase 1: Foundation (Week 1-2)
- [ ] Set up FastAPI project structure
- [ ] Create API models (Pydantic)
- [ ] Implement /api/chat endpoint
- [ ] Implement /api/health endpoint
- [ ] Set up React + Vite + TypeScript
- [ ] Configure Tailwind CSS
- [ ] Create Layout component with Sidebar
- [ ] Implement ChatPage with basic functionality
- [ ] Set up React Query

### Phase 2: Core Features (Week 3-4)
- [ ] Implement /api/analyze/* endpoints
- [ ] Implement /api/interview/* endpoints
- [ ] Implement /api/email/* endpoints
- [ ] Create AnalyzerPage
- [ ] Create InterviewPage (Questions + STAR)
- [ ] Create EmailPage

### Phase 3: Polish (Week 5-6)
- [ ] Interview Practice mode
- [ ] Company research feature
- [ ] Mobile responsive design
- [ ] Loading states and error handling
- [ ] Keyboard shortcuts
- [ ] Settings page

---

## 11. Next Steps

1. Review this architecture document
2. Run `/sc:workflow` to generate detailed task breakdown
3. Run `/sc:implement` to start Phase 1

---

*Architecture designed for Resume RAG Platform v1.0*
