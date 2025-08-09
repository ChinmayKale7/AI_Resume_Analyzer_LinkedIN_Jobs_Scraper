import time
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_extras.add_vertical_space import add_vertical_space
from PyPDF2 import PdfReader
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from shutil import which
import warnings
warnings.filterwarnings('ignore')

# ================= CONFIG =================
GEMINI_MODEL = "gemini-1.5-flash"
st.set_page_config(page_title='Resume Analyzer AI', layout="wide")

# Session state for storing resume & API key once
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "api_key" not in st.session_state:
    st.session_state.api_key = None


def pdf_to_text(pdf):
    pdf_reader = PdfReader(pdf)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def gemini_response(api_key, resume_text, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(f"{prompt}\n\n{resume_text}")
    return response.text if response and response.text else "No response generated."


# ================= PROMPTS =================
def summary_prompt(text):
    return f"Need a detailed summarization of the following resume and finally conclude:\n\n{text}"


def strength_prompt(text):
    return f"Need a detailed analysis explaining the strengths of the following resume and conclude:\n\n{text}"


def weakness_prompt(text):
    return f"Need a detailed analysis explaining the weaknesses of the following resume and how to improve it:\n\n{text}"


def job_title_prompt(text):
    return f"Suggest job roles I can apply to on LinkedIn based on the following resume:\n\n{text}"


# ================= UI FUNCTIONS =================
def resume_summary():
    with st.form(key='Summary'):
        add_vertical_space(1)
        pdf = st.file_uploader(label='Upload Your Resume', type='pdf')
        add_vertical_space(1)
        col1, _ = st.columns([0.6, 0.4])
        with col1:
            api_key = st.text_input(label='Enter Google API Key', type='password')
        add_vertical_space(2)
        submit = st.form_submit_button(label='Submit')

    if submit:
        if pdf is not None and api_key:
            with st.spinner('Processing...'):
                st.session_state.resume_text = pdf_to_text(pdf)
                st.session_state.api_key = api_key
                summary = gemini_response(api_key, st.session_state.resume_text, summary_prompt(st.session_state.resume_text))
            st.subheader("Summary")
            st.write(summary)
        elif not pdf:
            st.warning("Please upload your resume.")
        elif not api_key:
            st.warning("Please enter Google API Key.")


def resume_strength():
    if st.session_state.resume_text and st.session_state.api_key:
        with st.spinner("Analyzing strengths..."):
            summary = gemini_response(st.session_state.api_key, st.session_state.resume_text, summary_prompt(st.session_state.resume_text))
            strength = gemini_response(st.session_state.api_key, st.session_state.resume_text, strength_prompt(summary))
        st.subheader("Strength")
        st.write(strength)
    else:
        st.warning("Please upload resume & API key in Summary tab first.")


def resume_weakness():
    if st.session_state.resume_text and st.session_state.api_key:
        with st.spinner("Analyzing weaknesses..."):
            summary = gemini_response(st.session_state.api_key, st.session_state.resume_text, summary_prompt(st.session_state.resume_text))
            weakness = gemini_response(st.session_state.api_key, st.session_state.resume_text, weakness_prompt(summary))
        st.subheader("Weaknesses & Suggestions")
        st.write(weakness)
    else:
        st.warning("Please upload resume & API key in Summary tab first.")


def job_title_suggestion():
    if st.session_state.resume_text and st.session_state.api_key:
        with st.spinner("Suggesting job titles..."):
            summary = gemini_response(st.session_state.api_key, st.session_state.resume_text, summary_prompt(st.session_state.resume_text))
            jobs = gemini_response(st.session_state.api_key, st.session_state.resume_text, job_title_prompt(summary))
        st.subheader("Suggested Job Titles")
        st.write(jobs)
    else:
        st.warning("Please upload resume & API key in Summary tab first.")


# ================= LINKEDIN SCRAPER =================
class linkedin_scraper:
    @staticmethod
    def webdriver_setup():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.binary_location = "/usr/bin/chromium"
        return webdriver.Chrome(service=Service(which("chromedriver")), options=chrome_options)

    @staticmethod
    def get_userinput():
        with st.form(key='linkedin_form'):
            col1, col2, col3 = st.columns([0.5, 0.3, 0.2])
            with col1:
                job_title_input = st.text_input(label='Job Title').split(',')
            with col2:
                job_location = st.text_input(label='Job Location', value='India')
            with col3:
                job_count = st.number_input(label='Job Count', min_value=1, value=1, step=1)
            submit = st.form_submit_button(label='Submit')
        return job_title_input, job_location, job_count, submit

    @staticmethod
    def build_url(job_title, job_location):
        titles = ['%20'.join(i.split()) for i in job_title]
        job_title_str = '%2C%20'.join(titles)
        return f"https://in.linkedin.com/jobs/search?keywords={job_title_str}&location={job_location}&f_TPR=r604800"

    @staticmethod
    def open_link(driver, link):
        driver.get(link)
        driver.implicitly_wait(5)
        time.sleep(2)

    @staticmethod
    def link_open_scrolldown(driver, link, job_count):
        linkedin_scraper.open_link(driver, link)
        for _ in range(job_count * 3):  # scroll more to load enough jobs
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
            time.sleep(0.5)
            try:
                driver.find_element(By.CSS_SELECTOR, "button[aria-label='See more jobs']").click()
            except:
                pass

    @staticmethod
    def scrap_company_data(driver, job_title_input, job_location):
        companies = [i.text for i in driver.find_elements(By.CSS_SELECTOR, 'h4.base-search-card__subtitle')]
        titles = [i.text for i in driver.find_elements(By.CSS_SELECTOR, 'h3.base-search-card__title')]
        locations = [i.text for i in driver.find_elements(By.CSS_SELECTOR, 'span.job-search-card__location')]
        urls = [i.get_attribute('href') for i in driver.find_elements(By.XPATH, '//a[contains(@href, "/jobs/")]')]

        data = list(zip(companies, titles, locations, urls))
        df = pd.DataFrame(data, columns=['Company Name', 'Job Title', 'Location', 'Website URL'])
        df = df[df['Location'].str.contains(job_location, case=False, na=False)]
        return df.reset_index(drop=True)

    @staticmethod
    def scrap_job_description(driver, df, job_count):
        descriptions, valid_rows = [], []
        for _, row in df.iterrows():
            try:
                linkedin_scraper.open_link(driver, row['Website URL'])
                try:
                    driver.find_element(By.CSS_SELECTOR,
                        'button[data-tracking-control-name="public_jobs_show-more-html-btn"]').click()
                except:
                    pass
                desc_elem = driver.find_elements(By.CSS_SELECTOR, 'div.show-more-less-html__markup')
                desc = desc_elem[0].text.strip() if desc_elem else ""
                if desc:
                    valid_rows.append(row.to_dict())
                    descriptions.append(desc)
            except:
                continue
            if len(valid_rows) >= job_count:
                break
        if not valid_rows:
            return pd.DataFrame()
        df_valid = pd.DataFrame(valid_rows).reset_index(drop=True)
        df_valid['Job Description'] = descriptions
        return df_valid

    @staticmethod
    def display_data_userinterface(df_final):
        if len(df_final) > 0:
            for i in range(len(df_final)):
                st.subheader(f"Job Posting {i+1}")
                st.write(f"**Company Name:** {df_final.iloc[i, 0]}")
                st.write(f"**Job Title:** {df_final.iloc[i, 1]}")
                st.write(f"**Location:** {df_final.iloc[i, 2]}")
                st.write(f"**Website URL:** {df_final.iloc[i, 3]}")
                with st.expander('Job Description'):
                    st.write(df_final.iloc[i, 4])
        else:
            st.warning("No Matching Jobs Found")

    @staticmethod
    def main():
        driver = None
        try:
            job_title_input, job_location, job_count, submit = linkedin_scraper.get_userinput()
            if submit and job_title_input and job_location:
                driver = linkedin_scraper.webdriver_setup()
                link = linkedin_scraper.build_url(job_title_input, job_location)
                linkedin_scraper.link_open_scrolldown(driver, link, job_count)
                df = linkedin_scraper.scrap_company_data(driver, job_title_input, job_location)
                df_final = linkedin_scraper.scrap_job_description(driver, df, job_count)
                linkedin_scraper.display_data_userinterface(df_final)
        finally:
            if driver:
                driver.quit()


# ================= MAIN STREAMLIT UI =================
with st.sidebar:
    option = option_menu(
        menu_title='',
        options=['Summary', 'Strength', 'Weakness', 'Job Titles', 'Linkedin Jobs'],
        icons=['house-fill', 'star-fill', 'exclamation-triangle-fill', 'briefcase-fill', 'linkedin']
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
    linkedin_scraper.main()
