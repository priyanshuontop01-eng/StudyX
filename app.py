"""
StudyX - AI Study Assistant (Streamlit + Google Gemini)
-------------------------------------------------------------
- Professional CSS with UI animations and smooth hover transitions
- Compact Banner & clean header layout
- Sidebar configuration (API key and settings)
- Full features: Notes, MCQ Quiz, Sample Practice Paper
"""

import json
import re
import io
import pdfplumber
import streamlit as st
from google import genai
from google.genai import types

# --------------------------------------------------------------------------
# 1. PAGE CONFIG & ADVANCED PROFESSIONAL STYLING
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="StudyX - AI Assistant", 
    page_icon="📚", 
    layout="wide"
)

# Professional CSS animations & micro-interactions
st.markdown(
    """
    <style>
        /* Hide unnecessary UI elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Container layout */
        .main .block-container {
            padding-top: 1.5rem;
            max-width: 900px;
        }

        /* Smooth page fade-in animation */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(15px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .element-container, .stMarkdown, .stButton, div[data-testid="stFileUploader"] {
            animation: fadeInUp 0.5s ease-out forwards;
        }

        /* Compact Banner Styling */
        .banner-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .banner-wrapper img {
            max-height: 120px;
            border-radius: 12px;
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.12);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .banner-wrapper img:hover {
            transform: scale(1.02);
            box-shadow: 0px 12px 28px rgba(0, 0, 0, 0.18);
        }

        /* Professional Interactive Buttons */
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.6rem 1.2rem;
            transition: all 0.25s ease-in-out;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(13, 110, 253, 0.3);
        }

        div.stButton > button:active {
            transform: translateY(0px);
            box-shadow: 0 2px 10px rgba(13, 110, 253, 0.2);
        }

        /* Metric Box animations */
        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px;
            border-radius: 10px;
            transition: transform 0.2s ease;
        }
        
        [data-testid="stMetric"]:hover {
            transform: translateY(-3px);
        }

        /* Tab styling & transitions */
        button[data-baseweb="tab"] {
            font-size: 1.05rem;
            font-weight: 500;
            padding: 10px 20px;
            transition: all 0.2s ease;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Render Banner
st.markdown('<div class="banner-wrapper">', unsafe_allow_html=True)
st.image("studyx_banner.png", use_container_width=False)
st.markdown('</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------
# 2. CONFIGURATION & SIDEBAR
# --------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-2.5-flash"

def get_api_key() -> str:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return st.session_state.get("manual_key", "")

with st.sidebar:
    st.title("⚙️ StudyX Settings")
    if "GEMINI_API_KEY" not in st.secrets:
        st.text_input(
            "Gemini API Key",
            type="password",
            key="manual_key",
            help="Enter your API key here."
        )
    model_name = st.text_input("Model", value=DEFAULT_MODEL)
    max_chars = st.slider(
        "Max Characters from PDF",
        10_000, 150_000, 60_000, step=5_000,
    )
    difficulty = st.selectbox("Quiz/Paper Difficulty", ["Easy", "Medium", "Hard"], index=1)

# --------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def extract_text(pdf_bytes: bytes) -> tuple[str, int]:
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                pages.append(extracted)
        count = len(pdf.pages)
    return "\n\n".join(pages).strip(), count

def call_gemini(prompt: str, json_mode: bool = False) -> str:
    api_key = .Ab8RN6KJcurjcCQRpxPnH_FdkAhmLAzokPj7T-bYalI2rA-yHQ
    if not api_key:
        st.error("Gemini API key is required. Please provide it in sidebar secrets or input field.")
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
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)
    if isinstance(data, dict):
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
        raise ValueError("Could not parse valid quiz questions from AI output.")
    return quiz

# Prompt Generators
def notes_prompt(text: str) -> str:
    return f"""You are an expert tutor. Create structured study notes from the following material.

Format in Markdown:
## 📌 Key Concepts
## 📖 Definitions & Key Terms
## 💡 Main Takeaways
## ⚡ Quick Revision Checklist

MATERIAL:
{text}"""

def quiz_prompt(text: str) -> str:
    return f"""Create exactly 10 {difficulty.lower()}-level multiple-choice questions based ONLY on the text below.

Return ONLY a JSON array with objects matching:
{{"question": "...", "options": ["Option A", "Option B", "Option C", "Option D"], "answer_index": 0, "explanation": "..."}}

MATERIAL:
{text}"""

def paper_prompt(text: str) -> str:
    return f"""Generate a {difficulty.lower()}-level sample exam paper based ONLY on the material provided.

Structure:
# Practice Exam Paper
## Section A: Short Answer Questions (2 Marks Each)
## Section B: Long Answer Questions (8 Marks Each)
## Model Answers & Marking Scheme

MATERIAL:
{text}"""

# --------------------------------------------------------------------------
# 4. MAIN APP INTERFACE
# --------------------------------------------------------------------------
uploaded_file = st.file_uploader("Upload a PDF to get started", type=["pdf"])

if uploaded_file:
    try:
        full_text, n_pages = extract_text(uploaded_file.getvalue())
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
        st.stop()

    if len(full_text) < 100:
        st.warning("No readable text found in this PDF file.")
        st.stop()

    text = full_text[:max_chars]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pages", n_pages)
    col2.metric("Extracted Characters", f"{len(full_text):,}")
    col3.metric("Processed Characters", f"{len(text):,}")

    if st.session_state.get("file_id") != (uploaded_file.name, uploaded_file.size):
        st.session_state.update(
            file_id=(uploaded_file.name, uploaded_file.size), 
            notes=None, quiz=None, paper=None, submitted=False
        )

    st.write("")
    tab_notes, tab_quiz, tab_paper = st.tabs(["📝 Notes", "❓ Quiz", "📄 Practice Paper"])

    # --- TAB 1: NOTES ---
    with tab_notes:
        if st.button("Generate Study Notes", type="primary", key="btn_notes"):
            with st.spinner("Generating summary notes..."):
                try:
                    st.session_state.notes = call_gemini(notes_prompt(text))
                except Exception as err:
                    st.error(f"API Error: {err}")

        if st.session_state.get("notes"):
            st.markdown(st.session_state.notes)
            st.download_button(
                "📥 Download Notes (.md)", 
                st.session_state.notes, 
                file_name="StudyX_Notes.md"
            )

    # --- TAB 2: QUIZ ---
    with tab_quiz:
        if st.button("Generate MCQ Quiz", type="primary", key="btn_quiz"):
            with st.spinner("Creating 10 practice questions..."):
                try:
                    raw_json = call_gemini(quiz_prompt(text), json_mode=True)
                    st.session_state.quiz = parse_quiz_json(raw_json)
                    st.session_state.submitted = False
                except Exception as err:
                    st.error(f"Error generating quiz: {err}")

        quiz = st.session_state.get("quiz")
        if quiz:
            with st.form("quiz_form"):
                for idx, q in enumerate(quiz):
                    st.markdown(f"**Q{idx + 1}. {q['question']}**")
                    st.radio(
                        "Select Answer:", 
                        q["options"], 
                        index=None, 
                        key=f"ans_{idx}", 
                        label_visibility="collapsed"
                    )
                    st.write("")
                
                submitted = st.form_submit_button("Submit Answers", type="primary")
                if submitted:
                    st.session_state.submitted = True

            if st.session_state.get("submitted"):
                score = sum(
                    1 for idx, q in enumerate(quiz) 
                    if st.session_state.get(f"ans_{idx}") == q["options"][q["answer_index"]]
                )
                st.success(f"### Final Score: {score} / {len(quiz)}")
                
                for idx, q in enumerate(quiz):
                    user_ans = st.session_state.get(f"ans_{idx}")
                    correct_ans = q["options"][q["answer_index"]]
                    status = "✅" if user_ans == correct_ans else "❌"
                    
                    with st.expander(f"{status} Question {idx + 1}: {q['question']}"):
                        st.write(f"**Your Answer:** {user_ans if user_ans else 'Skipped'}")
                        st.write(f"**Correct Answer:** {correct_ans}")
                        st.write(f"**Explanation:** {q.get('explanation', 'N/A')}")

    # --- TAB 3: PRACTICE PAPER ---
    with tab_paper:
        if st.button("Generate Exam Paper", type="primary", key="btn_paper"):
            with st.spinner("Formulating examination paper..."):
                try:
                    st.session_state.paper = call_gemini(paper_prompt(text))
                except Exception as err:
                    st.error(f"API Error: {err}")

        if st.session_state.get("paper"):
            st.markdown(st.session_state.paper)
            st.download_button(
                "📥 Download Paper (.md)", 
                st.session_state.paper, 
                file_name="StudyX_Practice_Paper.md"
            )
