"""
Streamlit Web Interface for ResumeAI

Run with: streamlit run src/ui/web.py
"""

import streamlit as st
import asyncio
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.rag import ResumeRAG
from src.llm_backends import LLMRouter
from src.web_search import WebSearch
from config.settings import settings


# Page config
st.set_page_config(
    page_title="ResumeAI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initialize session state
if "rag" not in st.session_state:
    st.session_state.rag = ResumeRAG()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_backend" not in st.session_state:
    st.session_state.current_backend = settings.default_llm


def get_rag() -> ResumeRAG:
    return st.session_state.rag


# Sidebar
with st.sidebar:
    st.title("⚙️ Settings")

    # LLM Backend Selection
    st.subheader("LLM Backend")
    router = LLMRouter()
    backends = router.list_backends()
    available = [name for name, info in backends.items() if info["available"]]

    if available:
        selected_backend = st.selectbox(
            "Select Backend",
            available,
            index=available.index(st.session_state.current_backend) if st.session_state.current_backend in available else 0
        )
        st.session_state.current_backend = selected_backend
        get_rag().llm_router.set_backend(selected_backend)

        # Show backend info
        backend_info = backends[selected_backend]
        st.caption(f"Model: {backend_info['model']}")
    else:
        st.error("No LLM backends available! Configure at least one in .env")

    st.divider()

    # Index Management
    st.subheader("📁 Resume Index")

    status = get_rag().get_status()
    st.metric("Indexed Chunks", status["indexed_documents"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Re-index", use_container_width=True):
            with st.spinner("Indexing resumes..."):
                count = get_rag().index_resumes()
            st.success(f"Indexed {count} chunks")
            st.rerun()

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            get_rag().clear_index()
            st.success("Index cleared")
            st.rerun()

    st.divider()

    # Task Type
    st.subheader("📋 Task Type")
    task_type = st.radio(
        "Select task",
        ["General Chat", "Email Drafting", "Resume Tailoring", "Interview Prep"],
        label_visibility="collapsed"
    )

    task_map = {
        "General Chat": "default",
        "Email Drafting": "email_draft",
        "Resume Tailoring": "resume_tailor",
        "Interview Prep": "interview_prep"
    }

    st.divider()

    # Clear chat
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        get_rag().clear_history()
        st.rerun()


# Main content
st.title("📄 ResumeAI")
st.caption("AI-powered resume management and job application helper")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "✉️ Email Draft", "🎯 Tailor Resume", "🔍 Search"])

with tab1:
    # Chat interface
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything about your resume..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = asyncio.run(get_rag().chat(
                    prompt,
                    task_type=task_map[task_type],
                    backend=st.session_state.current_backend
                ))
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

with tab2:
    st.subheader("✉️ Draft Application Email")

    col1, col2 = st.columns([2, 1])

    with col1:
        job_description = st.text_area(
            "Job Description",
            height=200,
            placeholder="Paste the job description here..."
        )

    with col2:
        recipient = st.text_input("Recipient Name (optional)")
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Formal", "Enthusiastic"])

    if st.button("📧 Generate Email", type="primary", use_container_width=True):
        if job_description:
            with st.spinner("Drafting email..."):
                email = asyncio.run(get_rag().draft_email(
                    job_description,
                    recipient,
                    tone.lower(),
                    st.session_state.current_backend
                ))

            st.subheader("Generated Email")
            st.text_area("", email, height=300, label_visibility="collapsed")

            # Copy button
            st.button("📋 Copy to Clipboard", on_click=lambda: st.write("Copied!"))
        else:
            st.warning("Please enter a job description")

with tab3:
    st.subheader("🎯 Tailor Resume for Job")

    job_for_tailoring = st.text_area(
        "Job Description",
        height=200,
        placeholder="Paste the job description to get tailoring suggestions...",
        key="tailor_job"
    )

    section_focus = st.selectbox(
        "Focus Section (optional)",
        ["All Sections", "Summary", "Skills", "Experience", "Projects"]
    )

    if st.button("🔧 Get Suggestions", type="primary", use_container_width=True):
        if job_for_tailoring:
            section = None if section_focus == "All Sections" else section_focus.lower()

            with st.spinner("Analyzing..."):
                suggestions = asyncio.run(get_rag().tailor_resume(
                    job_for_tailoring,
                    section,
                    st.session_state.current_backend
                ))

            st.subheader("Tailoring Suggestions")
            st.markdown(suggestions)
        else:
            st.warning("Please enter a job description")

with tab4:
    st.subheader("🔍 Search")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input("Search query", placeholder="Search your resume or the web...")

    with col2:
        search_type = st.radio("Type", ["Resume", "Web"], horizontal=True)

    if st.button("🔎 Search", use_container_width=True):
        if search_query:
            if search_type == "Resume":
                results = get_rag().retriever.search(search_query, n_results=5)

                st.subheader("Resume Search Results")
                for i, r in enumerate(results, 1):
                    with st.expander(f"{i}. {r['metadata'].get('section', 'Unknown')} (Relevance: {r['relevance']:.2f})"):
                        st.write(r["content"])
            else:
                ws = WebSearch()
                results = ws.search(search_query)

                st.subheader("Web Search Results")
                for r in results:
                    st.markdown(f"**[{r['title']}]({r['link']})**")
                    st.caption(r["snippet"])
                    st.divider()
        else:
            st.warning("Please enter a search query")


# Footer
st.divider()
st.caption("ResumeAI | Powered by Groq/Ollama/OpenAI | Built with Streamlit")
