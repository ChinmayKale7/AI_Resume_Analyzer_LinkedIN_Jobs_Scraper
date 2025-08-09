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
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from shutil import which
import os
import warnings
warnings.filterwarnings('ignore')

# Configure Gemini Model
GEMINI_MODEL = "gemini-1.5-flash"

def streamlit_config():
    st.set_page_config(page_title='Resume Analyzer AI', layout="wide")
    st.markdown("""
    <style>
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f'<h1 style="text-align: center;">Resume Analyzer AI</h1>', unsafe_allow_html=True)

class resume_analyzer:
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

    def summary_prompt(text):
        return f"Need a detailed summarization of the following resume and conclude:\n\n{text}"

    def strength_prompt(text):
        return f"Need a detailed analysis explaining the strengths of the following resume and conclude:\n\n{text}"

    def weakness_prompt(text):
        return f"Need a detailed analysis explaining the weaknesses of the following resume and how to improve it:\n\n{text}"

    def job_title_prompt(text):
        return f"Suggest job roles I can apply to on LinkedIn based on the following resume:\n\n{text}"

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
            if pdf and api_key:
                try:
                    with st.spinner('Processing...'):
                        resume_text = resume_analyzer.pdf_to_text(pdf)
                        summary = resume_analyzer.gemini_response(api_key, resume_text,
                                                                  resume_analyzer.summary_prompt(resume_text))
                    st.markdown(f'<h4 style="color: orange;">Summary:</h4>', unsafe_allow_html=True)
                    st.write(summary)
                except Exception as e:
                    st.error(e)
            elif not pdf:
                st.warning("Please Upload Your Resume")
            else:
                st.warning("Please Enter Google API Key")

    def resume_strength():
        with st.form(key='Strength'):
            add_vertical_space(1)
            pdf = st.file_uploader(label='Upload Your Resume', type='pdf')
            add_vertical_space(1)
            col1, _ = st.columns([0.6, 0.4])
            with col1:
                api_key = st.text_input(label='Enter Google API Key', type='password')
            submit = st.form_submit_button(label='Submit')

        if submit:
            if pdf and api_key:
                try:
                    with st.spinner('Processing...'):
                        resume_text = resume_analyzer.pdf_to_text(pdf)
                        summary = resume_analyzer.gemini_response(api_key, resume_text,
                                                                  resume_analyzer.summary_prompt(resume_text))
                        strength = resume_analyzer.gemini_response(api_key, resume_text,
                                                                   resume_analyzer.strength_prompt(summary))
                    st.markdown(f'<h4 style="color: orange;">Strength:</h4>', unsafe_allow_html=True)
                    st.write(strength)
                except Exception as e:
                    st.error(e)
            elif not pdf:
                st.warning("Please Upload Your Resume")
            else:
                st.warning("Please Enter Google API Key")

    def resume_weakness():
        with st.form(key='Weakness'):
            add_vertical_space(1)
            pdf = st.file_uploader(label='Upload Your Resume', type='pdf')
            add_vertical_space(1)
            col1, _ = st.columns([0.6, 0.4])
            with col1:
                api_key = st.text_input(label='Enter Google API Key', type='password')
            submit = st.form_submit_button(label='Submit')

        if submit:
            if pdf and api_key:
                try:
                    with st.spinner('Processing...'):
                        resume_text = resume_analyzer.pdf_to_text(pdf)
                        summary = resume_analyzer.gemini_response(api_key, resume_text,
                                                                  resume_analyzer.summary_prompt(resume_text))
                        weakness = resume_analyzer.gemini_response(api_key, resume_text,
                                                                   resume_analyzer.weakness_prompt(summary))
                    st.markdown(f'<h4 style="color: orange;">Weakness and Suggestions:</h4>', unsafe_allow_html=True)
                    st.write(weakness)
                except Exception as e:
                    st.error(e)
            elif not pdf:
                st.warning("Please Upload Your Resume")
            else:
                st.warning("Please Enter Google API Key")

    def job_title_suggestion():
        with st.form(key='Job Titles'):
            add_vertical_space(1)
            pdf = st.file_uploader(label='Upload Your Resume', type='pdf')
            add_vertical_space(1)
            col1, _ = st.columns([0.6, 0.4])
            with col1:
                api_key = st.text_input(label='Enter Google API Key', type='password')
            submit = st.form_submit_button(label='Submit')

        if submit:
            if pdf and api_key:
                try:
                    with st.spinner('Processing...'):
                        resume_text = resume_analyzer.pdf_to_text(pdf)
                        summary = resume_analyzer.gemini_response(api_key, resume_text,
                                                                  resume_analyzer.summary_prompt(resume_text))
                        job_title = resume_analyzer.gemini_response(api_key, resume_text,
                                                                    resume_analyzer.job_title_prompt(summary))
                    st.markdown(f'<h4 style="color: orange;">Job Titles:</h4>', unsafe_allow_html=True)
                    st.write(job_title)
                except Exception as e:
                    st.error(e)
            elif not pdf:
                st.warning("Please Upload Your Resume")
            else:
                st.warning("Please Enter Google API Key")

class linkedin_scraper:
    def webdriver_setup():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        if os.path.exists("/usr/bin/chromium-browser"):
            chrome_options.binary_location = "/usr/bin/chromium-browser"
            chromedriver_path = "/usr/bin/chromedriver"
        else:
            chrome_options.binary_location = which("chrome") or which("chromium") or "/usr/bin/google-chrome"
            chromedriver_path = which("chromedriver")

        driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
        driver.maximize_window()
        return driver

    # keep all your scraper functions here exactly as before: get_userinput, build_url, open_link,
    # link_open_scrolldown, job_title_filter, scrap_company_data, scrap_job_description, display_data_userinterface

    def main():
        driver = None
        try:
            job_title_input, job_location, job_count, submit = linkedin_scraper.get_userinput()
            add_vertical_space(2)
            if submit:
                if job_title_input != [] and job_location != '':
                    with st.spinner('Chrome Webdriver Setup Initializing...'):
                        driver = linkedin_scraper.webdriver_setup()
                    with st.spinner('Loading More Job Listings...'):
                        link = linkedin_scraper.build_url(job_title_input, job_location)
                        linkedin_scraper.link_open_scrolldown(driver, link, job_count)
                    with st.spinner('Scraping Job Details...'):
                        df = linkedin_scraper.scrap_company_data(driver, job_title_input, job_location)
                        df_final = linkedin_scraper.scrap_job_description(driver, df, job_count)
                    linkedin_scraper.display_data_userinterface(df_final)
                elif job_title_input == []:
                    st.warning("Job Title is Empty")
                elif job_location == '':
                    st.warning("Job Location is Empty")
        except Exception as e:
            st.error(e)
        finally:
            if driver:
                driver.quit()

# ==== Streamlit UI ====
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
    resume_analyzer.resume_summary()
elif option == 'Strength':
    resume_analyzer.resume_strength()
elif option == 'Weakness':
    resume_analyzer.resume_weakness()
elif option == 'Job Titles':
    resume_analyzer.job_title_suggestion()
elif option == 'Linkedin Jobs':
    linkedin_scraper.main()
