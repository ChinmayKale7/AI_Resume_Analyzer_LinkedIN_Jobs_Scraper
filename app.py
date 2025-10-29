import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_extras.add_vertical_space import add_vertical_space
from PyPDF2 import PdfReader
import google.generativeai as genai

# ====== CONFIG ======
GEMINI_MODEL = "gemini-2.5-flash"

# ====== STREAMLIT PAGE CONFIG ======
def streamlit_config():
    st.set_page_config(page_title='Resume Analyzer AI', layout="wide")
    st.markdown(
        """
        <style>
        [data-testid="stHeader"] {
            background: rgba(0,0,0,0);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<h1 style="text-align: center;">Resume Analyzer AI</h1>', unsafe_allow_html=True)

# ====== RESUME ANALYZER CLASS ======
class resume_analyzer:
    @staticmethod
    def pdf_to_text(pdf):
        pdf_reader = PdfReader(pdf)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text

    @staticmethod
    def gemini_response(api_key, resume_text, prompt):
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(f"{prompt}\n\n{resume_text}")
        return response.text if response and response.text else "No response generated."

    @staticmethod
    def summary_prompt(text):
        return f"Need a detailed summarization of the following resume and finally conclude:\n\n{text}"

    @staticmethod
    def strength_prompt(text):
        return f"Need a detailed analysis explaining the strengths of the following resume and conclude:\n\n{text}"

    @staticmethod
    def weakness_prompt(text):
        return f"Need a detailed analysis explaining the weaknesses of the following resume and how to improve it:\n\n{text}"

    @staticmethod
    def job_title_prompt(text):
        return f"Suggest job roles I can apply to on LinkedIn based on the following resume:\n\n{text}"

# ====== RESUME FUNCTIONS FOR EACH TAB ======
def resume_summary():
    add_vertical_space(1)
    st.session_state.pdf = st.file_uploader(label='Upload Your Resume', type='pdf')
    add_vertical_space(1)
    st.session_state.api_key = st.text_input(label='Enter Google API Key', type='password')
    add_vertical_space(1)
    if st.button("Analyze Summary"):
        if st.session_state.pdf and st.session_state.api_key:
            with st.spinner("Processing..."):
                resume_text = resume_analyzer.pdf_to_text(st.session_state.pdf)
                st.session_state.resume_text = resume_text
                summary = resume_analyzer.gemini_response(
                    st.session_state.api_key, resume_text,
                    resume_analyzer.summary_prompt(resume_text)
                )
                st.session_state.summary = summary
            st.markdown('<h4 style="color: orange;">Summary:</h4>', unsafe_allow_html=True)
            st.write(summary)
        else:
            st.warning("Please upload a resume and enter API key.")

def resume_strength():
    if 'resume_text' in st.session_state:
        if st.button("Analyze Strengths"):
            with st.spinner("Processing..."):
                strength = resume_analyzer.gemini_response(
                    st.session_state.api_key, st.session_state.resume_text,
                    resume_analyzer.strength_prompt(st.session_state.summary)
                )
                st.session_state.strength = strength
            st.markdown('<h4 style="color: orange;">Strengths:</h4>', unsafe_allow_html=True)
            st.write(strength)
    else:
        st.info("Please upload resume in the Summary tab first.")

def resume_weakness():
    if 'resume_text' in st.session_state:
        if st.button("Analyze Weaknesses"):
            with st.spinner("Processing..."):
                weakness = resume_analyzer.gemini_response(
                    st.session_state.api_key, st.session_state.resume_text,
                    resume_analyzer.weakness_prompt(st.session_state.summary)
                )
                st.session_state.weakness = weakness
            st.markdown('<h4 style="color: orange;">Weaknesses & Suggestions:</h4>', unsafe_allow_html=True)
            st.write(weakness)
    else:
        st.info("Please upload resume in the Summary tab first.")

def job_title_suggestion():
    if 'resume_text' in st.session_state:
        if st.button("Suggest Job Titles"):
            with st.spinner("Processing..."):
                job_titles = resume_analyzer.gemini_response(
                    st.session_state.api_key, st.session_state.resume_text,
                    resume_analyzer.job_title_prompt(st.session_state.summary)
                )
                st.session_state.job_titles = job_titles
            st.markdown('<h4 style="color: orange;">Suggested Job Titles:</h4>', unsafe_allow_html=True)
            st.write(job_titles)
    else:
        st.info("Please upload resume in the Summary tab first.")

# ====== NEW LINKEDIN JOBS GENERATOR ======
def linkedin_jobs():
    add_vertical_space(1)
    job_titles = st.text_input("Enter job titles (comma separated)", placeholder="Data Scientist, AI Engineer")
    location = st.text_input("Enter location", value="India")
    time_filter = st.selectbox(
        "Select time filter",
        options=["Any time", "Past 24 hours", "Past week", "Past month"],
        index=0
    )
    time_map = {
        "Any time": "",
        "Past 24 hours": "&f_TPR=r86400",
        "Past week": "&f_TPR=r604800",
        "Past month": "&f_TPR=r2592000"
    }
    if st.button("Generate Links"):
        if job_titles.strip():
            titles = [t.strip() for t in job_titles.split(",") if t.strip()]
            st.markdown("### 🔗 LinkedIn Job Search Links")
            for title in titles:
                query = "%20".join(title.split())
                url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={location}{time_map[time_filter]}"
                st.markdown(f"- [{title} jobs in {location} ({time_filter})]({url})")
        else:
            st.warning("Please enter at least one job title.")

# ====== MAIN APP ======
streamlit_config()
add_vertical_space(2)

with st.sidebar:
    add_vertical_space(4)
    option = option_menu(
        menu_title='',
        options=['Summary', 'Strength', 'Weakness', 'Job Titles', 'Linkedin Jobs'],
        icons=['house-fill', 'database-fill', 'pass-fill', 'list-ul', 'linkedin']
    )

if option == 'Summary':
    resume_summary()
elif option == 'Strength':
    resume_strength()
elif option == 'Weakness':
    resume_weakness()
elif option == 'Job Titles':
    job_title_suggestion()
elif option == 'Linkedin Jobs':
    linkedin_jobs()

