import os
import base
import base64
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# PAGE CONFIGURATION & HIGH-CONTRAST DARK THEME STYLING
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OmniLecture - AI Study Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Dark Theme Background & Neon Accent Styling */
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    /* Headers & Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #60a5fa !important;
        font-weight: 700;
    }
    
    /* Cards / Containers */
    .css-1r7sldb, .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    /* Custom Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
    }
    
    /* Radio options styling */
    .stRadio label {
        color: #e2e8f0 !important;
        font-size: 1rem !important;
    }
    
    /* Signature styling */
    .sidebar-signature {
        position: fixed;
        bottom: 15px;
        left: 15px;
        width: 260px;
        font-size: 0.85rem;
        color: #94a3b8;
        background: #1e293b;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #334155;
        text-align: center;
        z-index: 999;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------------------------
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "file_name" not in st.session_state:
    st.session_state.file_name = ""
if "summary_data" not in st.session_state:
    st.session_state.summary_data = None
if "exam_data" not in st.session_state:
    st.session_state.exam_data = None
if "flashcards_data" not in st.session_state:
    st.session_state.flashcards_data = None
if "glossary_data" not in st.session_state:
    st.session_state.glossary_data = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False

# ---------------------------------------------------------------------------
# SIDEBAR - NAVIGATION & PDF UPLOAD
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎓 OmniLecture")
    st.markdown("### AI Study Assistant")
    st.markdown("---")
    
    # API Key Input
    api_key_input = st.text_input("Gemini API Key", type="password", placeholder="Enter your Gemini API key...")
    
    st.markdown("---")
    st.markdown("### 📂 Document Upload")
    uploaded_file = st.file_uploader("Upload Lecture PDF", type=["pdf"])
    
    if uploaded_file is not None:
        if st.session_state.file_name != uploaded_file.name:
            st.session_state.file_name = uploaded_file.name
            # Extract text using pypdf
            try:
                reader = PdfReader(uploaded_file)
                extracted_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
                st.session_state.pdf_text = extracted_text
                uploaded_file.seek(0) # Reset pointer for viewer
                st.session_state.pdf_bytes = uploaded_file.read()
                
                # Reset previous caches on new file upload
                st.session_state.summary_data = None
                st.session_state.exam_data = None
                st.session_state.flashcards_data = None
                st.session_state.glossary_data = None
                st.session_state.chat_history = []
                st.session_state.exam_submitted = False
                st.success("PDF processed successfully!")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
        
        st.info(f"**File:** {st.session_state.file_name}\n\n**Length:** {len(st.session_state.pdf_text)} characters")
    
    # Permanent Signature requested precisely at the bottom-left of sidebar
    st.markdown("""
        <div class="sidebar-signature">
            👨‍💻 𝒟ℯ𝓋ℯ𝓁ℴ𝓅ℯ𝒹 𝒷𝓎 𝓌𝒶𝓁𝒶𝒶 𝓈𝒶𝓁𝒾𝓂 ༄
        </div>
    """, unsafe_allow_html=True)

# Helper function to get Gemini Client
def get_gemini_client():
    if api_key_input:
        return genai.Client(api_key=api_key_input)
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return genai.Client(api_key=env_key)
    return None

# ---------------------------------------------------------------------------
# MAIN APP HEADER
# ---------------------------------------------------------------------------
st.title("🚀 OmniLecture AI Study Assistant")
st.markdown("Transform your academic materials into structured summaries, interactive adaptive exams, intelligent flashcards, and access your AI Professor instantly.")

if not st.session_state.pdf_text:
    st.warning("⚠️ Please upload a PDF lecture file from the left sidebar to begin processing your study materials.")
    st.stop()

# ---------------------------------------------------------------------------
# TABS INTERFACE STRUCTURE
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "📖 Detailed Summary",
    "✍️ 30 MCQ Exam",
    "📊 Results & Review",
    "🗂️ Flashcards & Glossary",
    "📄 PDF Document Viewer",
    "👨‍🏫 AI Professor Chat"
])

client = get_gemini_client()

# ===========================================================================
# TAB 1: DETAILED SUMMARY & BILINGUAL GUIDE
# ===========================================================================
with tabs[0]:
    st.header("📖 Detailed Summary & Bilingual Guide")
    st.markdown("Thorough breakdown of all main topics, key sections, practical benefits, paired with comprehensive Arabic translations.")
    
    if st.button("Generate Detailed Bilingual Summary", key="gen_summary_btn"):
        if not client:
            st.error("Please provide a valid Gemini API Key in the sidebar.")
        else:
            with st.spinner("Analyzing document structure and translating key insights..."):
                prompt = f"""
                Analyze the following academic text extracted from a PDF lecture. 
                Extract all major topics and sections. For each topic, provide:
                1. Topic Title (English)
                2. Detailed Summary (English)
                3. Practical Benefit / Learning Outcome (English)
                4. Full Professional Arabic Translation / Equivalent for the section & summary.

                Format your response clearly using Markdown sections, bullet points, and headers.
                
                Document Text:
                {st.session_state.pdf_text[:12000]}
                """
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    st.session_state.summary_data = response.text
                except Exception as e:
                    st.error(f"Error generating summary: {e}")
                    
    if st.session_state.summary_data:
        st.markdown(st.session_state.summary_data)

# ===========================================================================
# TAB 2: 30 MCQ ADAPTIVE EXAM
# ===========================================================================
with tabs[1]:
    st.header("✍️ 30 MCQ Adaptive Exam")
    st.markdown("Test your deep comprehension with 30 rigorous multiple-choice questions extracted directly from the lecture material, categorized into Easy, Medium, and Hard levels.")
    
    if not st.session_state.exam_data:
        if st.button("Generate 30-Question Adaptive Exam", key="gen_exam_btn"):
            if not client:
                st.error("Please provide a valid Gemini API Key in the sidebar.")
            else:
                with st.spinner("Extracting concepts and generating 30 high-level adaptive questions..."):
                    prompt = f"""
                    Based strictly on the following PDF document content, generate exactly 30 multiple-choice questions (MCQs).
                    Divide the questions into 3 distinct difficulty tiers:
                    - 10 Easy Questions (Level 1)
                    - 10 Medium Questions (Level 2)
                    - 10 Hard Questions (Level 3)

                    You MUST output the result strictly in valid JSON format without markdown code blocks, structured as a list of objects, where each object has:
                    - "id": integer (1 to 30)
                    - "level": string ("Easy", "Medium", or "Hard")
                    - "question": string
                    - "options": list of 4 strings
                    - "answer": string (exact match of the correct option)
                    - "explanation": string (scientific explanation of why the answer is correct)

                    Document Text:
                    {st.session_state.pdf_text[:14000]}
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        import json
                        st.session_state.exam_data = json.loads(response.text)
                        st.session_state.exam_submitted = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating exam data: {e}")
    
    if st.session_state.exam_data:
        exam_questions = st.session_state.exam_data
        
        with st.form("exam_form"):
            user_answers = {}
            
            for q in exam_questions:
                q_id = q["id"]
                level_badge = "🟢 Easy" if q["level"]=="Easy" else ("🟡 Medium" if q["level"]=="Medium" else "🔴 Hard")
                st.markdown(f"**Q{q_id} ({level_badge}):** {q['question']}")
                
                # index=None makes sure all options are unselected by default
                ans = st.radio(
                    f"Select answer for Q{q_id}",
                    options=q["options"],
                    index=None,
                    key=f"q_{q_id}",
                    label_visibility="collapsed"
                )
                user_answers[q_id] = ans
                st.markdown("---")
                
            submitted = st.form_submit_button("Submit Exam & View Results")
            if submitted:
                st.session_state.user_answers = user_answers
                st.session_state.exam_submitted = True
                st.success("Exam submitted successfully! Check the Results & Review tab.")

# ===========================================================================
# TAB 3: PERFORMANCE & DETAILED RESULTS
# ===========================================================================
with tabs[2]:
    st.header("📊 Performance & Detailed Results")
    
    if not st.session_state.get("exam_submitted", False):
        st.info("⚠️ Please complete and submit the 30 MCQ Exam in the previous tab to view your performance evaluation.")
    else:
        exam_data = st.session_state.exam_data
        user_answers = st.session_state.user_answers
        
        score = 0
        total = len(exam_data)
        
        for q in exam_data:
            if user_answers.get(q["id"]) == q["answer"]:
                score += 1
                
        percentage = (score / total) * 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Final Score", value=f"{score} / {total}")
        with col2:
            st.metric(label="Percentage", value=f"{percentage:.1f}%")
        with col3:
            perf_grade = "Outstanding 🏆" if percentage >= 85 else ("Good Progress 👍" if percentage >= 60 else "Needs Review 📚")
            st.metric(label="Evaluation", value=perf_grade)
            
        st.markdown("---")
        st.subheader("Detailed Question Review & Scientific Explanations")
        
        for q in exam_data:
            q_id = q["id"]
            u_ans = user_answers.get(q_id)
            c_ans = q["answer"]
            is_correct = (u_ans == c_ans)
            
            status_icon = "✅" if is_correct else "❌"
            st.markdown(f"### Q{q_id}: {q['question']} {status_icon}")
            st.markdown(f"- **Your Answer:** `{u_ans if u_ans else 'No Answer Provided'}`")
            st.markdown(f"- **Correct Answer:** `{c_ans}`")
            st.markdown(f"- **Scientific Explanation:** {q['explanation']}")
            st.markdown("---")

# ===========================================================================
# TAB 4: FLASHCARDS & ENGINEERING GLOSSARY
# ===========================================================================
with tabs[3]:
    st.header("🗂️ Flashcards & Engineering Glossary")
    st.markdown("Quick revision flashcards and a comprehensive technical glossary extracted from your document.")
    
    if st.button("Generate Flashcards & Glossary", key="gen_flash_btn"):
        if not client:
            st.error("Please provide a valid Gemini API Key in the sidebar.")
        else:
            with st.spinner("Extracting glossary terms and flashcard pairs..."):
                prompt = f"""
                Extract key academic/technical terms and definitions from the text, and create key flashcard questions.
                Output strictly in valid JSON format without markdown code blocks with two keys:
                1. "glossary": list of objects with keys "term", "definition", "arabic_translation"
                2. "flashcards": list of objects with keys "front", "back"

                Document Text:
                {st.session_state.pdf_text[:10000]}
                """
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    import json
                    st.session_state.flash_glossary = json.loads(response.text)
                except Exception as e:
                    st.error(f"Error generating flashcards: {e}")
                    
    if "flash_glossary" in st.session_state:
        fg = st.session_state.flash_glossary
        
        st.subheader("📚 Technical Glossary & Definitions")
        glossary_items = fg.get("glossary", [])
        for item in glossary_items:
            with st.expander(f"📌 {item.get('term', '')}"):
                st.markdown(f"**Definition:** {item.get('definition', '')}")
                st.markdown(f"**Arabic Translation:** {item.get('arabic_translation', '')}")
                
        st.markdown("---")
        st.subheader("⚡ Quick Study Flashcards")
        flashcards = fg.get("flashcards", [])
        for i, fc in enumerate(flashcards):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.info(f"**Card {i+1} (Front):**\n\n{fc.get('front', '')}")
            with col_f2:
                st.success(f"**Card {i+1} (Back):**\n\n{fc.get('back', '')}")

# ===========================================================================
# TAB 5: ORIGINAL PDF DOCUMENT VIEWER
# ===========================================================================
with tabs[4]:
    st.header("📄 Original PDF Document Viewer")
    st.markdown("View your original lecture document with full formatting preserved.")
    
    if "pdf_bytes" in st.session_state:
        base64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("No PDF document currently loaded.")

# ===========================================================================
# TAB 6: AI PROFESSOR CHATBOT
# ===========================================================================
with tabs[5]:
    st.header("👨‍🏫 AI Professor Chatbot")
    st.markdown("Interact directly with your virtual professor assistant who has total context of your uploaded lecture file.")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    user_query = st.chat_input("Ask your professor anything about the lecture...")
    if user_query:
        if not client:
            st.error("Please provide a valid Gemini API Key in the sidebar.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
                
            with st.chat_message("assistant"):
                with st.spinner("Professor is thinking..."):
                    system_instruction = f"""
                    You are an expert AI Professor Assistant for the subject/lecture titled '{st.session_state.file_name}'.
                    Your task is to answer student questions accurately, professionally, and pedagogically based strictly on the provided lecture document text.
                    
                    Document Context:
                    {st.session_state.pdf_text}
                    """
                    try:
                        chat = client.chats.create(
                            model="gemini-2.5-flash",
                            config=types.GenerateContentConfig(system_instruction=system_instruction)
                        )
                        # Rebuild previous turns in chat session if needed, or send message with context
                        response = chat.send_message(user_query)
                        answer = response.text
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        err_msg = f"Error communicating with AI Professor: {e}"
                        st.error(err_msg)
                        st.session_state.chat_history.append({"role": "assistant", "content": err_msg})
