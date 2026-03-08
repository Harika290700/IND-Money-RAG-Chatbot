"""
Streamlit deployment: INDMoney RAG Chatbot UI.
Uses the same phase2 RAG + chat logic; no FastAPI required.
Run: streamlit run streamlit_app.py
Deploy: push to GitHub, then connect repo at share.streamlit.io and set GROQ_API_KEY in Secrets.
"""
from pathlib import Path
import os
import sys

# Ensure project root is on path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="INDMoney FAQ Assistant",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Inject Streamlit secrets into env so phase2.config / rag_service see GROQ_API_KEY on Streamlit Cloud
try:
    if getattr(st, "secrets", None):
        for key in ("GROQ_API_KEY", "GROQ_MODEL"):
            val = st.secrets.get(key)
            if val:
                os.environ[key] = str(val).strip()
except Exception:
    pass

# Import RAG service (requires ChromaDB; fails on Python 3.14 with Pydantic error)
try:
    from phase2.rag_service import chat
    from phase6 import record_feedback
except Exception as e:
    err_msg = str(e).lower()
    if "3.14" in str(sys.version) or "configerror" in err_msg or "infer type" in err_msg:
        st.error(
            "**This app requires Python 3.11 or 3.12 on Streamlit Cloud.**\n\n"
            "You're currently running Python 3.14, which is not compatible with ChromaDB.\n\n"
            "**Fix:** Delete this app, then create a new app from the same repo. "
            "In **Advanced settings**, set **Python version** to **3.11** or **3.12**, then deploy. "
            "Re-add your Secrets (e.g. `GROQ_API_KEY`) after redeploying."
        )
        st.stop()
    raise

# Custom CSS for a cleaner chat look
st.markdown("""
<style>
    .stChatMessage { padding: 0.75rem 1rem; }
    .source-link a { color: #1f77b4; text-decoration: none; }
    .source-link a:hover { text-decoration: underline; }
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stChatMessage"]) { margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# Session state: chat history and optional "ask for fund" state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_prompt_template" not in st.session_state:
    st.session_state.pending_prompt_template = None
if "pending_label" not in st.session_state:
    st.session_state.pending_label = None

# Header
st.title("INDMoney FAQ Assistant")
st.caption("Get factual details about SBI, HDFC, ICICI, Motilal Oswal, and Canara Robeco funds. No investment or personal advice.")

# Sidebar: suggested questions (full questions) and new chat
with st.sidebar:
    st.subheader("Suggested questions")
    sidebar_prompts = [
        "What is the NAV of HDFC Mid Cap Fund today?",
        "What expense ratio does SBI Contra Fund charge?",
        "Is there an exit load for Canara Robeco Mutual Fund?",
    ]
    for prompt in sidebar_prompts:
        if st.button(prompt, key=f"side_{hash(prompt) % 10**8}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    st.divider()
    if st.button("New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_prompt_template = None
        st.session_state.pending_label = None
        st.rerun()

    # Last updated (optional)
    try:
        from phase5.metadata import get_last_updated
        last = get_last_updated()
        if last:
            st.caption(f"Data last updated: {last}")
    except Exception:
        pass

# Welcome + 4 topic buttons (ask for fund then send)
if not st.session_state.messages and st.session_state.pending_prompt_template is None:
    st.markdown("**What can I help you with?**")
    cols = st.columns(2)
    templates = [
        ("What expense ratio does {fund} charge?", "Expense ratio & fund details"),
        ("What is the minimum SIP for {fund}?", "Minimum SIP & investment"),
        ("What is the exit load for {fund}?", "Exit load & charges"),
        ("Does {fund} have a lock-in? How many years?", "ELSS lock-in & tax"),
    ]
    for i, (template, label) in enumerate(templates):
        with cols[i % 2]:
            if st.button(label, key=f"welcome_{i}", use_container_width=True):
                st.session_state.pending_prompt_template = template
                st.session_state.pending_label = label
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "What is the fund you want to know about?",
                    "sources": [],
                    "question_for_feedback": None,
                })
                st.rerun()

# Chat history
for idx, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    content = msg.get("content", "")
    with st.chat_message(role):
        st.markdown(content)
        sources = msg.get("sources", [])
        if sources and role == "assistant":
            s = sources[0]
            url = s.get("url", "")
            title = s.get("title") or url
            if url:
                st.markdown(f'<p class="source-link"><a href="{url}" target="_blank" rel="noopener">{title if len(title) < 80 else url}</a></p>', unsafe_allow_html=True)
        # Feedback for assistant messages (only last one to avoid clutter)
        if role == "assistant" and idx == len(st.session_state.messages) - 1:
            q = msg.get("question_for_feedback")
            if q:
                c1, c2, _ = st.columns([1, 1, 4])
                with c1:
                    if st.button("👍", key=f"fb_up_{idx}"):
                        try:
                            record_feedback(q, "up")
                            st.toast("Thanks for your feedback!")
                        except Exception:
                            pass
                with c2:
                    if st.button("👎", key=f"fb_down_{idx}"):
                        try:
                            record_feedback(q, "down")
                            st.toast("Thanks for your feedback!")
                        except Exception:
                            pass

# Input: either "fund name" (when pending) or normal message
prompt_label = "Enter fund name" if st.session_state.pending_prompt_template else "Ask about a fund…"
user_input = st.chat_input(prompt_label)

if user_input:
    user_input = user_input.strip()
    if not user_input:
        st.stop()

    # If we were waiting for fund name, build the full question
    if st.session_state.pending_prompt_template:
        full_question = st.session_state.pending_prompt_template.replace("{fund}", user_input)
        display_label = f"{st.session_state.pending_label} – {user_input}"
        st.session_state.pending_prompt_template = None
        st.session_state.pending_label = None
        user_input = full_question
    else:
        display_label = user_input

    # Append user message
    st.session_state.messages.append({"role": "user", "content": display_label})

    # Get reply from RAG
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = chat(user_input)
        answer = result.get("answer", "No response.")
        sources = result.get("sources", [])[:1]
        scraped = result.get("scraped_data", [])

        st.markdown(answer)
        if sources:
            s = sources[0]
            url = s.get("url", "")
            title = s.get("title") or url
            if url:
                st.markdown(f'<p class="source-link"><a href="{url}" target="_blank" rel="noopener">{title if len(title) < 80 else url}</a></p>', unsafe_allow_html=True)

    # Append assistant message to history so it persists
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "question_for_feedback": user_input,
    })

    st.rerun()
