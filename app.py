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
import warnings
warnings.filterwarnings('ignore')

# Gemini model
GEMINI_MODEL = "gemini-1.5-flash"

# ===== Streamlit Config =====
def streamlit_config():
    st.set_page_config(page_title='Resume Analyzer AI', layout="wide")
    st.markdown("<style>[data-testid='stHeader']{background:rgba(0,0,0,0);}</style>", unsafe_allow_html=True)
    st.markdown('<h1 style="text-align:center;">Resume Analyzer AI</h1>', unsafe_allow_html=True)

# ===== Resume Analyzer =====
class resume_analyzer:
    @staticmethod
    def pdf_to_text(pdf):
        reader = PdfReader(pdf)
        return "\n".join([page.extract_text() or "" for page in reader.pages])

    @staticmethod
    def gemini_response(api_key, resume_text, prompt):
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(f"{prompt}\n\n{resume_text}")
        return resp.text if resp and resp.text else "No response generated."

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

# ===== LinkedIn Scraper =====
class linkedin_scraper:
    @staticmethod
    def webdriver_setup():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.binary_location = "/usr/bin/chromium"
        driver_path = "/usr/bin/chromedriver"
        driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        driver.maximize_window()
        return driver

    @staticmethod
    def get_userinput():
        with st.form(key='linkedin_scarp'):
            col1, col2, col3 = st.columns([0.5, 0.3, 0.2])
            with col1:
                job_title_input = st.text_input('Job Title').split(',')
            with col2:
                job_location = st.text_input('Job Location', value='India')
            with col3:
                job_count = st.number_input('Job Count', min_value=1, value=1, step=1)
            submit = st.form_submit_button('Submit')
        return job_title_input, job_location, job_count, submit

    @staticmethod
    def build_url(job_title, job_location):
        encoded = '%2C%20'.join(['%20'.join(i.split()) for i in job_title])
        return f"https://in.linkedin.com/jobs/search?keywords={encoded}&location={job_location}&f_TPR=r604800"

    @staticmethod
    def open_link(driver, link):
        while True:
            try:
                driver.get(link)
                time.sleep(3)
                driver.find_element(By.CSS_SELECTOR, 'span.switcher-tabs__placeholder-text.m-auto')
                return
            except NoSuchElementException:
                continue

    @staticmethod
    def link_open_scrolldown(driver, link, job_count):
        linkedin_scraper.open_link(driver, link)
        for _ in range(job_count):
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_UP)
            try:
                driver.find_element(By.CSS_SELECTOR,
                    "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']").click()
            except:
                pass
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            try:
                driver.find_element(By.CSS_SELECTOR, "button[aria-label='See more jobs']").click()
            except:
                pass

    @staticmethod
    def job_title_filter(scrap_job_title, user_job_title_input):
        user_input = [i.lower().strip() for i in user_job_title_input]
        scrap_title = scrap_job_title.lower().strip()
        for i in user_input:
            if all(word in scrap_title for word in i.split()):
                return scrap_job_title
        return np.nan

    @staticmethod
    def scrap_company_data(driver, job_title_input, job_location):
        companies = driver.find_elements(By.CSS_SELECTOR, 'h4.base-search-card__subtitle')
        locations = driver.find_elements(By.CSS_SELECTOR, 'span.job-search-card__location')
        titles = driver.find_elements(By.CSS_SELECTOR, 'h3.base-search-card__title')
        urls = driver.find_elements(By.XPATH, '//a[contains(@href, "/jobs/")]')

        rows = []
        for comp, loc, title, url in zip(companies, locations, titles, urls):
            jt_filtered = linkedin_scraper.job_title_filter(title.text, job_title_input)
            loc_filtered = loc.text if job_location.lower() in loc.text.lower() else np.nan
            if pd.notna(jt_filtered) and pd.notna(loc_filtered):
                rows.append({
                    'Company Name': comp.text,
                    'Job Title': jt_filtered,
                    'Location': loc_filtered,
                    'Website URL': url.get_attribute('href')
                })

        return pd.DataFrame(rows)

    @staticmethod
    def scrap_job_description(driver, df, job_count):
        descriptions = []
        for url in df['Website URL'][:job_count]:
            try:
                linkedin_scraper.open_link(driver, url)
                driver.find_element(By.CSS_SELECTOR,
                    'button[data-tracking-control-name="public_jobs_show-more-html-btn"]').click()
                time.sleep(1)
                desc = driver.find_element(By.CSS_SELECTOR,
                    'div.show-more-less-html__markup').text
                descriptions.append(desc if desc.strip() else np.nan)
            except:
                descriptions.append(np.nan)
        df['Job Description'] = descriptions
        return df.dropna().reset_index(drop=True)

    @staticmethod
    def display_data_userinterface(df_final):
        if not df_final.empty:
            for i, row in df_final.iterrows():
                st.markdown(f'<h3 style="color: orange;">Job Posting Details : {i + 1}</h3>', unsafe_allow_html=True)
                st.write(f"Company Name : {row['Company Name']}")
                st.write(f"Job Title    : {row['Job Title']}")
                st.write(f"Location     : {row['Location']}")
                st.write(f"Website URL  : {row['Website URL']}")
                with st.expander('Job Description'):
                    st.write(row['Job Description'])
        else:
            st.markdown('<h5 style="text-align:center;color:orange;">No Matching Jobs Found</h5>', unsafe_allow_html=True)

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

# ===== Streamlit UI =====
streamlit_config()
add_vertical_space(2)

with st.sidebar:
    option = option_menu(
        menu_title='',
        options=['Summary', 'Strength', 'Weakness', 'Job Titles', 'Linkedin Jobs'],
        icons=['house-fill', 'database-fill', 'pass-fill', 'list-ul', 'linkedin']
    )

# Shared state for resume + API key
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = None

if option == 'Summary':
    with st.form(key='Summary'):
        pdf = st.file_uploader('Upload Your Resume', type='pdf')
        api_key = st.text_input('Enter Google API Key', type='password')
        submit = st.form_submit_button('Submit')
    if submit and pdf and api_key:
        st.session_state.resume_text = resume_analyzer.pdf_to_text(pdf)
        st.session_state.api_key = api_key
        summary = resume_analyzer.gemini_response(api_key, st.session_state.resume_text,
                                                  resume_analyzer.summary_prompt(st.session_state.resume_text))
        st.write(summary)

elif option == 'Strength' and st.session_state.resume_text:
    strength = resume_analyzer.gemini_response(st.session_state.api_key, st.session_state.resume_text,
                                               resume_analyzer.strength_prompt(st.session_state.resume_text))
    st.write(strength)

elif option == 'Weakness' and st.session_state.resume_text:
    weakness = resume_analyzer.gemini_response(st.session_state.api_key, st.session_state.resume_text,
                                               resume_analyzer.weakness_prompt(st.session_state.resume_text))
    st.write(weakness)

elif option == 'Job Titles' and st.session_state.resume_text:
    jobs = resume_analyzer.gemini_response(st.session_state.api_key, st.session_state.resume_text,
                                           resume_analyzer.job_title_prompt(st.session_state.resume_text))
    st.write(jobs)

elif option == 'Linkedin Jobs':
    linkedin_scraper.main()
