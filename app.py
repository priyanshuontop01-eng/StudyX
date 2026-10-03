"""
AI Study Assistant  -  Streamlit + Google Gemini (free tier)
-------------------------------------------------------------
Upload a PDF  ->  get summary notes, a 10-question MCQ quiz, and a practice paper.

Run locally:   streamlit run app.py
"""

import json
import re

import pdfplumber
import streamlit as st
from google import genai
from google.genai import types

# --------------------------------------------------------------------------
# 1. PAGE CONFIG + STYLING
# --------------------------------------------------------------------------
st.set_page_config(page_title="AI Study Assistant", page_icon="📚", layout="wide")

st.image("studyx_banner.png", use_container_width=True)
# --------------------------------------------------------------------------
# 1. PAGE CONFIG & BANNER
# --------------------------------------------------------------------------
st.set_page_config(page_title="AI Study Assistant", page_icon="📚", layout="wide")

# Custom CSS: Hide Streamlit default header/footer
st.markdown(
    """
    <style>
        .block#MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .main .block-container {padding-top: 1rem; max-width: 1000px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Centered & Compact Banner
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
  
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# 2. SETTINGS (API key, model, text limit)
# --------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-2.5-flash"  # free-tier friendly; change here if Google renames models


def get_api_key() -> str:
    """Use the key from Streamlit Secrets if present, otherwise the sidebar box."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # no secrets file locally - that's fine
    return st.session_state.get("manual_key", "")


with st.sidebar:
    st.header("⚙️ Settings")
    secrets_has_key = False
    try:
        secrets_has_key = "GEMINI_API_KEY" in st.secrets
    except Exception:
        pass

    if secrets_has_key:
        st.success("API key loaded from secrets ✅")
    else:
        st.text_input(
            "Gemini API key",
            type="password",
            key="manual_key",
            help="Get a free key at https://aistudio.google.com/app/apikey",
        )
    model_name = st.text_input("Model", value=DEFAULT_MODEL)
    max_chars = st.slider(
        "Max characters read from PDF",
        10_000, 150_000, 60_000, step=5_000,
        help="Longer = more complete, but slower and uses more of your free quota.",
    )
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1)
    st.caption("Free tier has rate limits. If you see an error, wait a minute and retry.")

# --------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# --------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def extract_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Extract text from every page of the PDF. Returns (text, page_count)."""
    import io

    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
        count = len(pdf.pages)
    return "\n\n".join(pages).strip(), count


def call_gemini(prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to Gemini and return the text reply."""
    api_key = get_api_key()
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar first.")
        st.stop()

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=0.4,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    response = client.models.generate_content(
        model=model_name, contents=prompt, config=config
    )
    return response.text or ""


def parse_quiz_json(raw: str) -> list[dict]:
    """Turn the model's JSON reply into a validated list of questions."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)
    if isinstance(data, dict):  # sometimes wrapped as {"questions": [...]}
        data = data.get("questions", [])
    quiz = []
    for q in data:
        if (
            isinstance(q.get("options"), list)
            and len(q["options"]) == 4
            and isinstance(q.get("answer_index"), int)
            and 0 <= q["answer_index"] < 4
        ):
            quiz.append(q)
    if not quiz:
        raise ValueError("The AI returned no usable questions.")
    return quiz


# ---- Prompts ----------------------------------------------------------------

def notes_prompt(text: str) -> str:
    return f"""You are an expert teacher. Create concise study notes from the material below.

Format in Markdown with these sections:
## Key Concepts  (bullet points)
## Important Definitions  (term: definition)
## Main Takeaways  (5-8 bullets)
## Quick Revision Checklist  (short bullets)

Use simple language for students. Use only information from the material.

MATERIAL:
{text}"""


def quiz_prompt(text: str) -> str:
    return f"""You are an expert exam setter. Write exactly 10 {difficulty.lower()}-level
multiple-choice questions based ONLY on the material below.

Return ONLY a JSON array. Each item must look like:
{{"question": "...", "options": ["A text", "B text", "C text", "D text"],
  "answer_index": 0, "explanation": "why this answer is correct"}}

Rules: exactly 4 options, answer_index is 0-3, only one correct option, no letter prefixes
inside the option text, vary which position is correct.

MATERIAL:
{text}"""


def paper_prompt(text: str) -> str:
    return f"""You are a university examiner. Create a {difficulty.lower()}-level sample practice paper
based ONLY on the material below. Use Markdown.

Structure:
# Sample Practice Paper
## Section A - Short Answer (8 questions, 2 marks each)
## Section B - Long Answer (4 questions, 8 marks each)
## Marking Scheme & Model Answer Points
(for every question, give 2-5 bullet points a good answer should contain)

MATERIAL:
{text}"""


# --------------------------------------------------------------------------
# 4. UPLOAD + GENERATE
# --------------------------------------------------------------------------
uploaded = st.file_uploader("📄 Upload your study material (PDF)", type=["pdf"])

if uploaded:
    try:
        full_text, n_pages = extract_text(uploaded.getvalue())
    except Exception as e:
        st.error(f"Couldn't read this PDF: {e}")
        st.stop()

    if len(full_text) < 200:
        st.warning(
            "Almost no text was found. This looks like a scanned/image-only PDF, "
            "which this app can't read. Try a PDF with selectable text."
        )
        st.stop()

    text = full_text[:max_chars]
    c1, c2, c3 = st.columns(3)
    c1.metric("Pages", n_pages)
    c2.metric("Characters found", f"{len(full_text):,}")
    c3.metric("Characters used", f"{len(text):,}")
    if len(full_text) > max_chars:
        st.info("The PDF is longer than the limit, so only the first part is used. "
                "Raise the limit in the sidebar if needed.")

    # A new file resets old results
    if st.session_state.get("file_id") != (uploaded.name, uploaded.size):
        st.session_state.update(file_id=(uploaded.name, uploaded.size),
                                notes=None, quiz=None, paper=None)

    tab_notes, tab_quiz, tab_paper = st.tabs(["📝 Notes", "❓ MCQ Quiz", "📄 Practice Paper"])

    # ---- Notes ----
    with tab_notes:
        if st.button("Generate Notes", type="primary", key="b_notes"):
            with st.spinner("Writing your notes..."):
                try:
                    st.session_state.notes = call_gemini(notes_prompt(text))
                except Exception as e:
                    st.error(f"Gemini error: {e}")
        if st.session_state.get("notes"):
            st.markdown(st.session_state.notes)
            st.download_button("⬇️ Download notes", st.session_state.notes,
                               file_name="study_notes.md")

    # ---- Quiz ----
    with tab_quiz:
        if st.button("Generate 10 MCQs", type="primary", key="b_quiz"):
            with st.spinner("Creating your quiz..."):
                try:
                    st.session_state.quiz = parse_quiz_json(
                        call_gemini(quiz_prompt(text), json_mode=True)
                    )
                    st.session_state.pop("submitted", None)
                except Exception as e:
                    st.error(f"Couldn't build the quiz ({e}). Please click Generate again.")

        quiz = st.session_state.get("quiz")
        if quiz:
            with st.form("quiz_form"):
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i + 1}. {q['question']}**")
                    st.radio("Choose one:", q["options"], index=None,
                             key=f"ans_{i}", label_visibility="collapsed")
                    st.write("")
                submitted = st.form_submit_button("✅ Submit answers", type="primary")
            if submitted:
                st.session_state.submitted = True

            if st.session_state.get("submitted"):
                score = 0
                for i, q in enumerate(quiz):
                    if st.session_state.get(f"ans_{i}") == q["options"][q["answer_index"]]:
                        score += 1
                st.markdown(f'<div class="score-box">Your score: {score} / {len(quiz)}</div>',
                            unsafe_allow_html=True)
                st.subheader("Answer key & explanations")
                for i, q in enumerate(quiz):
                    chosen = st.session_state.get(f"ans_{i}")
                    correct = q["options"][q["answer_index"]]
                    icon = "✅" if chosen == correct else "❌"
                    with st.expander(f"{icon} Q{i + 1}. {q['question']}"):
                        st.write(f"**Your answer:** {chosen or 'Not answered'}")
                        st.write(f"**Correct answer:** {correct}")
                        st.write(f"**Why:** {q.get('explanation', '')}")

    # ---- Practice paper ----
    with tab_paper:
        if st.button("Generate Practice Paper", type="primary", key="b_paper"):
            with st.spinner("Setting your paper..."):
                try:
                    st.session_state.paper = call_gemini(paper_prompt(text))
                except Exception as e:
                    st.error(f"Gemini error: {e}")
        if st.session_state.get("paper"):
            st.markdown(st.session_state.paper)
            st.download_button("⬇️ Download paper", st.session_state.paper,
                               file_name="practice_paper.md")
else:
    st.info("👆 Upload a PDF to get started. Add your free Gemini API key in the sidebar.")
