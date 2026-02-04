# ResumeAI

AI-powered resume management and job search platform with intelligent matching, multi-source scraping, and automated cover letter generation.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

### Core Features
- **Multi-LLM Support**: Groq, Gemini, OpenAI, Claude, DeepSeek, OpenRouter, Ollama (local)
- **Smart Resume Search**: Your resumes as a searchable knowledge base with vector embeddings
- **Smart Chat**: Context-aware conversations about your experience and skills

### Job Search & Tracking
- **Multi-Source Job Scraping**: Aggregates jobs from 10+ sources
  - GitHub Jobs, Simplify, Jobright, RemoteOK, Hacker News, WeWorkRemotely
  - Indeed, LinkedIn, Wellfound, Dice, Y Combinator, BuiltIn
- **Google Dorking**: Advanced web search to find hidden job listings using dork operators
- **Resume Matching**: AI-powered job-resume match scoring with skill gap analysis
- **Application Tracker**: Kanban-style tracking with status timeline
- **Timeline Filtering**: Filter jobs by posting time (1h, 6h, 24h, 7d)

### AI-Powered Tools
- **Cover Letter Generation**: Tailored cover letters based on job + resume match
- **Email Drafting**: Generate personalized job application emails
- **Resume Tailoring**: Suggestions to optimize your resume for specific jobs
- **Interview Prep**: Practice answers based on your experience

### User Interface
- **Modern React Frontend**: Responsive UI with card/table/kanban views
- **Real-time Search**: Instant job search with smart filters
- **Match Visualization**: Progress bars and skill badges for job fit

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/naveenkarasu/ResumeAI.git
cd ResumeAI
python setup.py
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required: At least one LLM API key (Groq is free and recommended)

### 3. Install Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 4. Index Your Resumes

Place your resume files in `data/resumes/` then:

```bash
python main.py index
```

### 5. Start the Platform

```bash
# Start backend API
python main.py api

# In another terminal, start frontend
cd frontend && npm run dev
```

Open http://localhost:5173

## LLM Backends

| Backend | Cost | Best For |
|---------|------|----------|
| **Groq** | FREE | Fast inference, development |
| **DeepSeek** | FREE | Coding tasks, reasoning |
| **Gemini** | FREE* | Multimodal, long context |
| **OpenRouter** | PAID | Access to 100+ models |
| **OpenAI** | PAID | GPT-4, best quality |
| **Claude** | PAID | Best reasoning, safety |
| **Ollama** | FREE | Local, private, offline |

*Free tier available

## Project Structure

```
resume-rag/
├── frontend/                 # React + TypeScript frontend
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # React components
│   │   └── pages/           # Page components
│   └── package.json
├── src/
│   ├── llm_backends/        # LLM integrations
│   ├── rag/                 # RAG components
│   ├── ui/
│   │   └── api/
│   │       ├── routers/     # FastAPI routers
│   │       ├── scrapers/    # Job scrapers
│   │       ├── models/      # Pydantic models
│   │       └── services/    # Business logic
│   └── resume/              # Resume parsing
├── data/
│   ├── resumes/             # Your resume files
│   └── chroma/              # Vector database
├── main.py                  # Entry point
├── requirements.txt
├── .env.example             # Environment template
└── README.md
```

## Job Sources

### Tier 1: Fast & Reliable (API/JSON)
- GitHub Jobs
- Simplify
- Jobright
- RemoteOK
- Hacker News (Who's Hiring)
- WeWorkRemotely

### Tier 2: HTTP Scraping
- BuiltIn
- Y Combinator

### Tier 3: Google Dorking
Advanced web search using operators like:
- `site:greenhouse.io` - Target ATS platforms
- `intitle:"security engineer"` - Search job titles
- `filetype:pdf "job description"` - Find PDF job listings

### Categories
- Cybersecurity, Software Engineering, Data/ML, DevOps
- Startups, Remote-First, Big Tech, Government, Education

## API Endpoints

### Job Search
- `POST /api/job-list/search` - Search jobs with NLP query
- `GET /api/job-list/jobs` - List cached jobs
- `GET /api/job-list/jobs/{id}` - Job details with match score

### Applications
- `GET /api/job-list/applications` - List tracked applications
- `POST /api/job-list/applications` - Track new application
- `PUT /api/job-list/applications/{id}` - Update status

### AI Features
- `POST /api/job-list/jobs/{id}/cover-letter` - Generate cover letter
- `GET /api/job-list/recommendations` - AI job recommendations
- `GET /api/job-list/dork-strategies` - Google dork templates

### Chat & Resume
- `POST /api/chat` - Chat with resume context
- `POST /api/analyze/job` - Analyze job fit
- `POST /api/email/draft` - Draft application email

## Environment Variables

See `.env.example` for all available options:

```env
# Required: At least one LLM API key
GROQ_API_KEY=           # Free: https://console.groq.com
GEMINI_API_KEY=         # Free: https://makersuite.google.com
OPENAI_API_KEY=         # Paid: https://platform.openai.com
ANTHROPIC_API_KEY=      # Paid: https://console.anthropic.com
DEEPSEEK_API_KEY=       # Free: https://platform.deepseek.com
OPENROUTER_API_KEY=     # Paid: https://openrouter.ai

# Application settings
ENVIRONMENT=development
DEFAULT_BACKEND=groq
API_PORT=8000
```

## Supported Resume Formats

- `.tex` - LaTeX (recommended, best parsing)
- `.pdf` - PDF documents
- `.docx` - Word documents
- `.txt` - Plain text

## Requirements

- Python 3.10+
- Node.js 18+
- 8GB+ RAM (for local Ollama)

## Development

```bash
# Run backend with auto-reload
uvicorn src.ui.api.main:app --reload --port 8000

# Run frontend dev server
cd frontend && npm run dev

# Run tests
pytest

# Type checking
mypy src/
```

## License

MIT License - Free for personal and commercial use.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Security

- Never commit `.env` files
- API keys are stored locally only
- No data is sent to external servers except LLM APIs
