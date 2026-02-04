# Resume RAG Assistant - Complete Setup Guide

## Project Overview

This is an AI-powered resume assistant that uses RAG (Retrieval-Augmented Generation) to:
- Draft job application emails
- Tailor resumes for specific jobs
- Answer questions about your experience
- Prepare for interviews
- Search the web for company/job info

### LLM Backends Available
| Backend | Cost | Notes |
|---------|------|-------|
| **Groq** | FREE | Recommended - Fast, free tier |
| **Ollama** | FREE | Local, private, needs 8GB+ RAM |
| **OpenAI** | PAID | Best quality, ~$0.01/1K tokens |
| **ChatGPT Web** | FREE* | Uses browser automation - RISKY, may violate ToS |

---

## Quick Setup (5 minutes)

### Step 1: Open Terminal in Project Directory
```bash
cd D:\Projects\resume-rag
```

### Step 2: Create Virtual Environment (Recommended)
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Install Playwright (for ChatGPT Web - optional)
```bash
playwright install chromium
```

### Step 5: Create .env File
```bash
copy .env.example .env
```

### Step 6: Add API Key
Edit `.env` and add at least ONE of these:

**Option A: Groq (FREE - Recommended)**
```
GROQ_API_KEY=your_groq_api_key_here
```
Get free key at: https://console.groq.com/keys

**Option B: Ollama (FREE - Local)**
```bash
# Install Ollama from https://ollama.ai/download
# Then run:
ollama pull llama3.1
```
No API key needed - just install and run Ollama.

**Option C: OpenAI (PAID)**
```
OPENAI_API_KEY=your_openai_api_key_here
```

### Step 7: Copy Your Resumes
```bash
# Copy LaTeX resumes to data/resumes/
copy "C:\Users\karas\OneDrive\Desktop\tes\bullet\W2\resumes_latex\*.tex" "D:\Projects\resume-rag\data\resumes\"

# Or copy entire folder
xcopy "C:\Users\karas\OneDrive\Desktop\tes\bullet\W2\resumes_latex" "D:\Projects\resume-rag\data\resumes\" /E /I
```

### Step 8: Index Resumes
```bash
python main.py index
```

### Step 9: Start the Assistant
```bash
# Web UI (recommended)
python main.py web

# Or CLI
python main.py cli
```

---

## Usage

### Web Interface
After running `python main.py web`, open http://localhost:8501

Features:
- Chat with your resume knowledge base
- Draft emails for job applications
- Get resume tailoring suggestions
- Search your resume or the web

### CLI Commands
```bash
# Interactive mode
python main.py cli

# Quick chat
python main.py chat "What are my Python skills?"

# Check status
python main.py status

# Index specific directory
python main.py index "C:\path\to\resumes"
```

### CLI Subcommands
```bash
python -m src.ui.cli chat "message"
python -m src.ui.cli email --job "job description"
python -m src.ui.cli tailor --job "job description"
python -m src.ui.cli interview "Tell me about yourself"
python -m src.ui.cli search "query"
python -m src.ui.cli backends
python -m src.ui.cli status
```

### Interactive CLI Commands
When in interactive mode (`python main.py cli`):
- `/email <job>` - Draft an email
- `/tailor <job>` - Get resume suggestions
- `/search <query>` - Search resumes
- `/web <query>` - Search the web
- `/backend <name>` - Switch LLM (groq/ollama/openai/chatgpt_web)
- `/clear` - Clear chat history
- `/quit` - Exit

---

## Project Files Reference

```
D:\Projects\resume-rag\
├── config/
│   └── settings.py           # All configuration options
├── data/
│   ├── resumes/              # PUT YOUR RESUME FILES HERE
│   └── chroma_db/            # Vector database (auto-created)
├── src/
│   ├── llm_backends/
│   │   ├── base.py           # Base LLM interface
│   │   ├── groq_backend.py   # Groq implementation
│   │   ├── ollama_backend.py # Ollama implementation
│   │   ├── openai_backend.py # OpenAI implementation
│   │   ├── chatgpt_web_backend.py  # ChatGPT browser automation
│   │   └── router.py         # LLM switching logic
│   ├── rag/
│   │   ├── vector_store.py   # ChromaDB wrapper
│   │   ├── retriever.py      # Resume parsing & search
│   │   └── rag_chain.py      # Main RAG logic
│   ├── web_search/
│   │   └── search.py         # DuckDuckGo search
│   └── ui/
│       ├── cli.py            # Typer CLI app
│       └── web.py            # Streamlit web app
├── main.py                   # Main entry point
├── setup.py                  # Auto-setup script
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .env                      # Your API keys (create this)
└── README.md                 # Documentation
```

---

## Configuration Options (.env)

```env
# LLM Selection (groq | ollama | openai | chatgpt_web)
DEFAULT_LLM=groq

# Groq (FREE)
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.1-70b-versatile

# Ollama (LOCAL)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# OpenAI (PAID)
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4-turbo-preview

# ChatGPT Web (RISKY)
CHATGPT_EMAIL=your_email
CHATGPT_PASSWORD=your_password

# Embedding Model (FREE, local)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Web Search
WEB_SEARCH_ENABLED=true
WEB_SEARCH_MAX_RESULTS=5
```

---

## Troubleshooting

### "No LLM backends available"
- Make sure you have at least one backend configured in `.env`
- For Groq: Get free API key from https://console.groq.com/keys
- For Ollama: Install from https://ollama.ai and run `ollama pull llama3.1`

### "Ollama not available"
- Make sure Ollama is running: `ollama serve`
- Check if model is pulled: `ollama list`
- Pull model if needed: `ollama pull llama3.1`

### "No documents indexed"
- Copy resume files to `data/resumes/`
- Run `python main.py index`
- Supported formats: .tex, .txt

### Import errors
- Make sure you're in the project directory: `cd D:\Projects\resume-rag`
- Activate virtual environment: `venv\Scripts\activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### Streamlit not found
```bash
pip install streamlit
```

---

## Resume Locations

Your existing resumes are at:
```
C:\Users\karas\OneDrive\Desktop\tes\bullet\W2\resumes_latex\
├── Software_Engineer\
├── Security_Engineer\
├── DevOps_SRE\
├── Data_AI\
└── Specialized\
```

Copy to project:
```bash
xcopy "C:\Users\karas\OneDrive\Desktop\tes\bullet\W2\resumes_latex" "D:\Projects\resume-rag\data\resumes\" /E /I
python main.py index
```

---

## Extending the Project

### Add New LLM Backend
1. Create `src/llm_backends/new_backend.py`
2. Inherit from `BaseLLM`
3. Implement `generate()` and `stream()` methods
4. Register in `src/llm_backends/router.py`

### Add New Features
- Edit `src/rag/rag_chain.py` for new chat capabilities
- Edit `src/ui/web.py` for new UI features
- Edit `src/ui/cli.py` for new CLI commands

### Customize Prompts
Edit `SYSTEM_PROMPTS` in `src/rag/rag_chain.py`

---

## Contact & Credits

Built for Naveen Karasu's resume management workflow.

Technologies:
- LangChain for RAG
- ChromaDB for vectors
- Sentence-Transformers for embeddings
- Streamlit for web UI
- Typer for CLI
- Groq/Ollama/OpenAI for LLMs
