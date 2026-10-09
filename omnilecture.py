import streamlit as st
import os
import base64
import json
from io import BytesIO

try:
    from pypdf import PdfReader
    PDF_LIB = "pypdf"
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_LIB = "PyPDF2"
    except ImportError:
        PDF_LIB = None

# Gemini SDK Import
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Page Configuration
st.set_page_config(
    page_title="OmniLecture - AI Study Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Neon Blue & Charcoal Dark Theme */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px.solid #30363d;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #58a6ff !important;
        font-weight: 700;
    }
    
    /* Cards & Containers */
    .css-1r6slb0, .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
    }
    
    /* Custom Cards */
    .omni-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .bilingual-box {
        background-color: #21262d;
        border-left: 4px solid #58a6ff;
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 0 15px rgba(46, 160, 67, 0.4);
    }
    
    /* Secondary Action Buttons */
    .stDownloadButton>button {
        background-color: #30363d;
        color: #c9d1d9;
        border: 1px solid #484f58;
        border-radius: 8px;
    }
    .stDownloadButton>button:hover {
        background-color: #384048;
        color: white;
        border-color: #58a6ff;
    }
</style>
""", unsafe_allow_html=True)

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "file_name" not in st.session_state:
    st.session_state.file_name = ""
if "summary_data" not in st.session_state:
    st.session_state.summary_data = None
if "mcqs_data" not in st.session_state:
    st.session_state.mcqs_data = []
if "glossary_data" not in st.session_state:
    st.session_state.glossary_data = []
if "flashcards_data" not in st.session_state:
    st.session_state.flashcards_data = []
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

def extract_text_from_pdf(uploaded_file):
    """Extracts raw text from an uploaded PDF file."""
    if PDF_LIB is None:
        return "Error: pypdf or PyPDF2 is not installed."
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for i, page in enumerate(reader.pages):
            extracted = page.extract_text()
            if extracted:
                text += f"\n--- Page {i+1} ---\n" + extracted + "\n"
        return text
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"

def get_gemini_client(api_key):
    """Initializes and returns the Google GenAI client."""
    if not GEMINI_AVAILABLE:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def process_lecture_with_ai(client, pdf_text, subject_name):
    """Calls Gemini 2.5 Flash to generate structured summary, 30 MCQs, and glossary."""
    prompt = f"""
    You are an expert academic AI professor and study assistant.
    Analyze the following lecture/document text for the subject: "{subject_name}".
    
    Provide your output strictly in JSON format with the following keys:
    1. "summary_sections": A list of objects, each containing:
       - "topic": Main topic name (English)
       - "summary": Detailed summary of the topic (English)
       - "benefit": Practical/academic benefit or key takeaway (English)
       - "arabic_title": Arabic translation of the topic
       - "arabic_summary": Arabic translation of the summary
       - "arabic_benefit": Arabic translation of the benefit
    2. "mcqs": A list of 30 multiple-choice questions extracted deeply from the text. Exactly:
       - 10 Easy questions
       - 10 Medium questions
       - 10 Hard questions
       Each object must contain:
       - "level": "Easy", "Medium", or "Hard"
       - "question": Question text (English)
       - "options": List of 4 options (English)
       - "answer": Correct option string (matching one of the options)
       - "explanation": Scientific explanation for the correct answer (English)
    3. "glossary": A list of 10-15 key technical/engineering terms from the text, each containing:
       - "term": Technical term (English)
       - "definition": Definition (English)
       - "arabic_term": Arabic translation of the term
       - "arabic_definition": Arabic translation of the definition
    4. "flashcards": A list of 8 key concept flashcards, each containing:
       - "front": Question or concept prompt (English)
       - "back": Answer or core explanation (English)

    Document Text:
    {pdf_text[:12000]}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            ),
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        return {"error": str(e)}

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=70)
    st.title("OmniLecture")
    st.markdown("### 🚀 AI Study Assistant")
    st.markdown("---")
    
    api_key_input = st.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
    
    st.markdown("### 📂 Upload Study Material")
    subject_input = st.text_input("Subject / Course Name", value="Advanced Computer Science")
    uploaded_pdf = st.file_uploader("Upload Lecture PDF", type=["pdf"])
    
    if uploaded_pdf is not None:
        st.session_state.file_name = uploaded_pdf.name
        # Read bytes for viewer
        pdf_bytes_data = uploaded_pdf.read()
        st.session_state.pdf_bytes = pdf_bytes_data
        
        # Reset file pointer for reading text
        uploaded_pdf.seek(0)
        
        if st.button("⚡ Process Lecture with AI", type="primary"):
            if not api_key_input:
                st.error("Please enter a valid Gemini API Key.")
            else:
                client = get_gemini_client(api_key_input)
                if not client:
                    st.error("Failed to initialize Gemini client. Check your API key or SDK version.")
                else:
                    with st.spinner("Extracting text and running AI analysis (Summary, 30 MCQs, Glossary)..."):
                        raw_text = extract_text_from_pdf(uploaded_pdf)
                        st.session_state.pdf_text = raw_text
                        
                        ai_result = process_lecture_with_ai(client, raw_text, subject_input)
                        
                        if "error" in ai_result:
                            st.error(f"AI Processing Error: {ai_result['error']}")
                        else:
                            st.session_state.summary_data = ai_result.get("summary_sections", [])
                            st.session_state.mcqs_data = ai_result.get("mcqs", [])
                            st.session_state.glossary_data = ai_result.get("glossary", [])
                            st.session_state.flashcards_data = ai_result.get("flashcards", [])
                            st.session_state.quiz_submitted = False
                            st.session_state.user_answers = {}
                            st.session_state.chat_history = []
                            st.success("🎉 Lecture processed successfully!")

    if st.session_state.file_name:
        st.markdown("---")
        st.markdown("### 📊 File Metadata")
        st.markdown(f"**Filename:** `{st.session_state.file_name}`")
        st.markdown(f"**Extracted Length:** `{len(st.session_state.pdf_text)}` characters")

st.title("🎓 OmniLecture: Advanced AI Study Hub")
st.markdown("Transform your lecture PDFs into comprehensive bilingual summaries, adaptive 30-question exams, interactive flashcards, and an expert AI professor chat.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📖 Detailed Summary",
    "✍️ 30 MCQ Adaptive Exam",
    "📊 Performance Results",
    "🗂️ Flashcards & Glossary",
    "📄 Original PDF Viewer",
    "👨‍🏫 AI Professor Chat"
])

# --- Tab 1: Detailed Summary & Bilingual Guide ---
with tab1:
    st.header("📖 Detailed Summary & Bilingual Guide")
    st.markdown("Comprehensive breakdown of lecture topics, structured summaries, key benefits, and complete Arabic translations.")
    
    if st.session_state.summary_data:
        for idx, sec in enumerate(st.session_state.summary_data):
            with st.container():
                st.markdown(f"""
                <div class="omni-card">
                    <h3>Topic {idx+1}: {sec.get('topic', '')}</h3>
                    <p><b>Summary:</b> {sec.get('summary', '')}</p>
                    <p><b>Key Benefit / Takeaway:</b> {sec.get('benefit', '')}</p>
                    <div class="bilingual-box" dir="rtl">
                        <h4 style="color: #58a6ff; margin-bottom: 5px;">{sec.get('arabic_title', '')}</h4>
                        <p style="margin-bottom: 5px;"><b>الخلاصة:</b> {sec.get('arabic_summary', '')}</p>
                        <p style="margin-bottom: 0px;"><b>الفائدة الدراسية:</b> {sec.get('arabic_benefit', '')}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ Please upload a PDF and click 'Process Lecture with AI' in the sidebar to generate the summary.")

# --- Tab 2: 30 MCQ Adaptive Exam ---
with tab2:
    st.header("✍️ 30 MCQ Adaptive Exam")
    st.markdown("Test your deep comprehension with 30 rigorous questions across Easy, Medium, and Hard difficulty tiers.")
    
    if st.session_state.mcqs_data:
        with st.form("exam_form"):
            for idx, q in enumerate(st.session_state.mcqs_data):
                level = q.get("level", "Medium")
                badge_color = "#238636" if level == "Easy" else "#d29922" if level == "Medium" else "#da3633"
                
                st.markdown(f"### Q{idx+1}: {q.get('question')} <span style='background-color:{badge_color}; color:white; padding:2px 8px; border-radius:4px; font-size:12px;'>{level}</span>", unsafe_allow_html=True)
                
                options = q.get("options", [])
                user_choice = st.radio(
                    f"Select answer for question {idx+1}:",
                    options,
                    key=f"mcq_q_{idx}",
                    label_visibility="collapsed"
                )
                st.session_state.user_answers[idx] = user_choice
                st.markdown("---")
            
            submit_exam = st.form_submit_button("Submit Exam & View Performance", type="primary")
            if submit_exam:
                score = 0
                for idx, q in enumerate(st.session_state.mcqs_data):
                    if st.session_state.user_answers.get(idx) == q.get("answer"):
                        score += 1
                st.session_state.score = score
                st.session_state.quiz_submitted = True
                st.success("🎉 Exam submitted successfully! Check the 'Performance Results' tab for deep analytics and scientific explanations.")
    else:
        st.warning("⚠️ No MCQ questions generated yet. Please process your lecture PDF in the sidebar.")

# --- Tab 3: Performance & Detailed Results ---
with tab3:
    st.header("📊 Performance & Detailed Results")
    if st.session_state.quiz_submitted and st.session_state.mcqs_data:
        total_q = len(st.session_state.mcqs_data)
        score = st.session_state.score
        percentage = (score / total_q) * 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Final Score", f"{score} / {total_q}")
        with col2:
            st.metric("Percentage", f"{percentage:.1f}%")
        with col3:
            grade = "A+" if percentage >= 90 else "B" if percentage >= 75 else "C" if percentage >= 60 else "Needs Improvement"
            st.metric("Grade Rating", grade)
            
        if percentage >= 80:
            st.balloons()
            st.success("🌟 Outstanding performance! You have mastered this lecture content.")
        elif percentage >= 60:
            st.info("👍 Good job! Review the explanations below for questions you missed.")
        else:
            st.warning("📚 Consider reviewing the Detailed Summary and Flashcards to reinforce key concepts.")
            
        st.markdown("### Question Breakdown & Scientific Explanations")
        for idx, q in enumerate(st.session_state.mcqs_data):
            user_ans = st.session_state.user_answers.get(idx)
            correct_ans = q.get("answer")
            is_correct = user_ans == correct_ans
            
            with st.container():
                status_icon = "✅" if is_correct else "❌"
                st.markdown(f"""
                <div class="omni-card">
                    <h4>{status_icon} Q{idx+1}: {q.get('question')}</h4>
                    <p><b>Your Answer:</b> {user_ans}</p>
                    <p><b>Correct Answer:</b> {correct_ans}</p>
                    <p style="color: #8b949e;"><b>Scientific Explanation:</b> {q.get('explanation', 'No explanation provided.')}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ Complete and submit the 30 MCQ Exam in the previous tab to view your performance analytics.")

# --- Tab 4: Flashcards & Engineering Glossary ---
with tab4:
    st.header("🗂️ Flashcards & Engineering Glossary")
    
    sub_tab1, sub_tab2 = st.tabs(["⚡ Quick Study Flashcards", "📚 Technical Glossary"])
    
    with sub_tab1:
        st.markdown("Interactive flashcards for rapid memorization of core concepts.")
        if st.session_state.flashcards_data:
            fc_idx = st.slider("Select Flashcard", 0, len(st.session_state.flashcards_data)-1, 0)
            fc = st.session_state.flashcards_data[fc_idx]
            st.markdown(f"""
            <div class="omni-card" style="text-align: center; padding: 40px;">
                <h3 style="color: #58a6ff;">Concept / Question {fc_idx+1}</h3>
                <p style="font-size: 18px; margin: 20px 0;"><b>{fc.get('front')}</b></p>
                <hr style="border-color: #30363d;">
                <p style="font-size: 16px; color: #3fb950; margin-top: 20px;"><b>Answer / Core Explanation:</b> {fc.get('back')}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Process a lecture PDF to populate flashcards.")
            
    with sub_tab2:
        st.markdown("Searchable engineering and technical terminology with definitions and Arabic translations.")
        if st.session_state.glossary_data:
            search_term = st.text_input("🔍 Search technical terms...", "")
            for item in st.session_state.glossary_data:
                term = item.get("term", "")
                defn = item.get("definition", "")
                ar_term = item.get("arabic_term", "")
                ar_defn = item.get("arabic_definition", "")
                
                if search_term.lower() in term.lower() or search_term in ar_term:
                    st.markdown(f"""
                    <div class="omni-card">
                        <h4>{term} <span style="font-size:14px; color:#8b949e;">({ar_term})</span></h4>
                        <p><b>Definition:</b> {defn}</p>
                        <p style="color:#8b949e;" dir="rtl"><b>التعريف بالعربية:</b> {ar_defn}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Process a lecture PDF to populate the glossary.")

# --- Tab 5: Original PDF Document Viewer ---
with tab5:
    st.header("📄 Original PDF Document Viewer")
    st.markdown("View your original lecture PDF directly within the interface with full formatting preservation.")
    
    if st.session_state.pdf_bytes is not None:
        base64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("ℹ️ Please upload a PDF file in the sidebar to view it here.")

# --- Tab 6: AI Professor Chatbot ---
with tab6:
    st.header("👨‍🏫 AI Professor Chatbot")
    st.markdown("Chat with your virtual professor assistant who has fully analyzed your lecture document.")
    
    # Display Chat History
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # Chat Input
    if user_prompt := st.chat_input("Ask your professor assistant anything about this lecture..."):
        if not api_key_input:
            st.error("Please enter a valid Gemini API Key in the sidebar first.")
        elif not st.session_state.pdf_text:
            st.warning("Please upload and process a PDF lecture first so the professor has context.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)
                
            client = get_gemini_client(api_key_input)
            if client:
                with st.chat_message("assistant"):
                    with st.spinner("Professor is reviewing lecture notes..."):
                        context_prompt = f"""
                        You are an expert AI Professor Assistant. You have full context of the following lecture material.
                        Answer the student's question accurately, pedagogically, and clearly.
                        
                        Lecture Context:
                        {st.session_state.pdf_text[:10000]}
                        
                        Student Question:
                        {user_prompt}
                        """
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=context_prompt
                            )
                            answer_text = response.text
                            st.markdown(answer_text)

   st.sidebar.markdown("---")
st.sidebar.markdown("👨‍💻 Developed by 𝓌𝒶𝓁𝒶𝒶 𝓈𝒶𝓁𝒾𝓂 ༄")                         
                            st.session_state.chat_history.append({"role": "assistant", "content": answer_text})
                        except Exception as e:
                            err_msg = f"Error generating response: {str(e)}"
                            st.error(err_msg)
                            st.session_state.chat_history.append({"role": "assistant", "content": err_msg})
