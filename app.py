import time
import os
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
import warnings
warnings.filterwarnings('ignore')

# -----------------------
# CONFIG
# -----------------------
GEMINI_MODEL = "gemini-1.5-flash"

def streamlit_config():
    st.set_page_config(page_title='Resume Analyzer AI', layout="wide")
    st.markdown("""
    <style>
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f'<h1 style="text-align: center;">Resume Analyzer AI</h1>', unsafe_allow_html=True)


# -----------------------
# RESUME ANALYZER (with single upload + caching)
# -----------------------
class resume_analyzer:

    @staticmethod
    def pdf_to_text(pdf_file):
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()

    @staticmethod
    def gemini_response(api_key, resume_text, prompt):
        # configure API key and call Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(f"{prompt}\n\n{resume_text}")
        # model.generate_content may return object with .text
        return getattr(response, "text", str(response)) or "No response generated."

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

    # Summary tab: upload once, store results & api key in st.session_state and precompute all outputs
    @staticmethod
    def resume_summary():
        with st.form(key='Summary'):
            add_vertical_space(1)
            uploaded_pdf = st.file_uploader(label='Upload Your Resume (PDF)', type='pdf')
            add_vertical_space(1)
            col1, col2 = st.columns([0.6, 0.4])
            with col1:
                api_key = st.text_input(label='Enter Google API Key', type='password')
            add_vertical_space(1)
            submit = st.form_submit_button(label='Submit')

        if submit:
            if not uploaded_pdf:
                st.warning("Please upload your resume (PDF) before submitting.")
                return
            if not api_key:
                st.warning("Please enter your Google API Key.")
                return

            # Save API key & resume text in session state
            try:
                with st.spinner("Reading resume and running analyses..."):
                    resume_text = resume_analyzer.pdf_to_text(uploaded_pdf)
                    st.session_state['api_key'] = api_key
                    st.session_state['resume_text'] = resume_text

                    # Run all analyses once and cache them
                    summary = resume_analyzer.gemini_response(api_key, resume_text, resume_analyzer.summary_prompt(resume_text))
                    strength = resume_analyzer.gemini_response(api_key, resume_text, resume_analyzer.strength_prompt(summary))
                    weakness = resume_analyzer.gemini_response(api_key, resume_text, resume_analyzer.weakness_prompt(summary))
                    job_titles = resume_analyzer.gemini_response(api_key, resume_text, resume_analyzer.job_title_prompt(summary))

                    st.session_state['summary_result'] = summary
                    st.session_state['strength_result'] = strength
                    st.session_state['weakness_result'] = weakness
                    st.session_state['job_titles_result'] = job_titles

                st.success("Analysis complete — results cached. Switch tabs to view them.")
                st.markdown(f'<h4 style="color: orange;">Summary:</h4>', unsafe_allow_html=True)
                st.write(st.session_state['summary_result'])

                # small controls: re-run or clear cache
                colA, colB = st.columns([0.5,0.5])
                with colA:
                    if st.button("Re-run analyses"):
                        # remove cached results and re-trigger by rerunning the same function via st.experimental_rerun
                        for k in ['summary_result','strength_result','weakness_result','job_titles_result']:
                            st.session_state.pop(k, None)
                        st.experimental_rerun()
                with colB:
                    if st.button("Clear stored resume & API key"):
                        for k in ['api_key','resume_text','summary_result','strength_result','weakness_result','job_titles_result']:
                            st.session_state.pop(k, None)
                        st.success("Cleared cached resume and API key. You can upload again in Summary tab.")
            except Exception as e:
                st.error(f"Error during analysis: {e}")

    # Other tabs read from session_state and display instantly
    @staticmethod
    def resume_strength():
        if 'strength_result' in st.session_state:
            st.markdown(f'<h4 style="color: orange;">Strength:</h4>', unsafe_allow_html=True)
            st.write(st.session_state['strength_result'])
        else:
            st.info("No cached analysis found. Go to the **Summary** tab, upload resume and run the analysis once.")

    @staticmethod
    def resume_weakness():
        if 'weakness_result' in st.session_state:
            st.markdown(f'<h4 style="color: orange;">Weakness and Suggestions:</h4>', unsafe_allow_html=True)
            st.write(st.session_state['weakness_result'])
        else:
            st.info("No cached analysis found. Go to the **Summary** tab, upload resume and run the analysis once.")

    @staticmethod
    def job_title_suggestion():
        if 'job_titles_result' in st.session_state:
            st.markdown(f'<h4 style="color: orange;">Job Titles:</h4>', unsafe_allow_html=True)
            st.write(st.session_state['job_titles_result'])
        else:
            st.info("No cached analysis found. Go to the **Summary** tab, upload resume and run the analysis once.")


# -----------------------
# LINKEDIN SCRAPER (Selenium) — robust webdriver_setup
# -----------------------
class linkedin_scraper:

    @staticmethod
    def webdriver_setup():
        """
        Attempt to find and use a Chrome/Chromium binary and chromedriver.
        On Streamlit Cloud you must include packages.txt in repo root with:
            chromium-browser
            chromedriver

        If chromedriver cannot be found this method raises RuntimeError with guidance.
        """
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        # optional: reduce detection
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--ignore-certificate-errors')

        # Candidate Chrome/Chromium binary paths (cloud/local)
        binary_candidates = [
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            "/opt/google/chrome/chrome",
            which("chrome"),
            which("chromium"),
            which("google-chrome"),
        ]
        chrome_binary = next((p for p in binary_candidates if p and os.path.exists(p)), None)
        if chrome_binary:
            chrome_options.binary_location = chrome_binary

        # Candidate chromedriver paths
        driver_candidates = [
            which("chromedriver"),
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            "/snap/bin/chromium/chromedriver",
            "/opt/chromedriver/chromedriver"
        ]
        chromedriver_path = next((p for p in driver_candidates if p and os.path.exists(p)), None)

        # final guard: if path is None -> give clear actionable error
        if not chromedriver_path:
            help_msg = (
                "chromedriver executable not found on the system.\n\n"
                "If you are deploying on Streamlit Cloud, add a file named `packages.txt` in the ROOT of your repository\n"
                "with the apt packages to install. For example:\n\n"
                "    chromium-browser\n"
                "    chromedriver\n\n"
                "Then commit & push, and redeploy the app. After deployment, check the app logs (Manage app → Logs) to confirm the packages were installed.\n\n"
                "If you're running locally, install Chrome/Chromium and chromedriver and ensure `chromedriver` is on your PATH.\n"
                "Examples (Ubuntu):\n"
                "    sudo apt update && sudo apt install -y chromium-browser chromedriver\n\n"
                "Detected binary candidates (checked):\n"
                f"  {binary_candidates}\n\n"
                "Detected driver candidates (checked):\n"
                f"  {driver_candidates}\n\n"
                "If you still see issues, open the Streamlit Cloud logs and paste the relevant 'chromedriver' lines here and I will help."
            )
            # raise so Streamlit shows clear message
            raise RuntimeError(help_msg)

        # create driver using found chromedriver path
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.maximize_window()
        return driver

    # Below functions are identical to your original logic (unchanged)
    @staticmethod
    def get_userinput():
        add_vertical_space(2)
        with st.form(key='linkedin_scarp'):
            col1, col2, col3 = st.columns([0.5, 0.3, 0.2], gap='medium')
            with col1:
                job_title_input = st.text_input(label='Job Title')
                job_title_input = job_title_input.split(',') if job_title_input else []
            with col2:
                job_location = st.text_input(label='Job Location', value='India')
            with col3:
                job_count = st.number_input(label='Job Count', min_value=1, value=1, step=1)
            submit = st.form_submit_button(label='Submit')
        return job_title_input, job_location, job_count, submit

    @staticmethod
    def build_url(job_title, job_location):
        b = []
        for i in job_title:
            x = i.split()
            y = '%20'.join(x)
            b.append(y)
        job_title = '%2C%20'.join(b)
        return f"https://in.linkedin.com/jobs/search?keywords={job_title}&location={job_location}&locationId=&geoId=102713980&f_TPR=r604800&position=1&pageNum=0"

    @staticmethod
    def open_link(driver, link):
        while True:
            try:
                driver.get(link)
                driver.implicitly_wait(5)
                time.sleep(3)
                driver.find_element(By.CSS_SELECTOR, 'span.switcher-tabs__placeholder-text.m-auto')
                return
            except NoSuchElementException:
                continue

    @staticmethod
    def link_open_scrolldown(driver, link, job_count):
        linkedin_scraper.open_link(driver, link)
        for _ in range(job_count):
            body = driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.PAGE_UP)
            try:
                driver.find_element(By.CSS_SELECTOR,
                    "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']").click()
            except:
                pass
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            driver.implicitly_wait(2)
            try:
                driver.find_element(By.CSS_SELECTOR, "button[aria-label='See more jobs']").click()
                driver.implicitly_wait(5)
            except:
                pass

    @staticmethod
    def job_title_filter(scrap_job_title, user_job_title_input):
        user_input = [i.lower().strip() for i in user_job_title_input]
        scrap_title = scrap_job_title.lower().strip()
        return scrap_job_title if any(all(word in scrap_title for word in i.split()) for i in user_input) else np.nan

    @staticmethod
    def scrap_company_data(driver, job_title_input, job_location):
        company = [i.text for i in driver.find_elements(By.CSS_SELECTOR, 'h4.base-search-card__subtitle')]
        location = [i.text for i in driver.find_elements(By.CSS_SELECTOR, 'span.job-search-card__location')]
        title = [i.text for i in driver.find_elements(By.CSS_SELECTOR, 'h3.base-search-card__title')]
        url = [i.get_attribute('href') for i in driver.find_elements(By.XPATH, '//a[contains(@href, "/jobs/")]')]
        df = pd.DataFrame({'Company Name': company, 'Job Title': title, 'Location': location, 'Website URL': url})
        df['Job Title'] = df['Job Title'].apply(lambda x: linkedin_scraper.job_title_filter(x, job_title_input))
        df['Location'] = df['Location'].apply(lambda x: x if job_location.lower() in x.lower() else np.nan)
        return df.dropna().reset_index(drop=True)

    @staticmethod
    def scrap_job_description(driver, df, job_count):
        job_description = []
        description_count = 0
        for url in df['Website URL'].tolist():
            try:
                linkedin_scraper.open_link(driver, url)
                driver.find_element(By.CSS_SELECTOR,
                    'button[data-tracking-control-name="public_jobs_show-more-html-btn"]').click()
                driver.implicitly_wait(5)
                time.sleep(1)
                data = driver.find_elements(By.CSS_SELECTOR, 'div.show-more-less-html__markup')
                text = data[0].text if data else ""
                if len(text.strip()) > 0 and text not in job_description:
                    job_description.append(text)
                    description_count += 1
                else:
                    job_description.append('Description Not Available')
            except:
                job_description.append('Description Not Available')

            if description_count == job_count:
                break

        df = df.iloc[:len(job_description), :].copy()
        df['Job Description'] = job_description
        df['Job Description'] = df['Job Description'].apply(lambda x: np.nan if x == 'Description Not Available' else x)
        df = df.dropna().reset_index(drop=True)
        return df

    @staticmethod
    def display_data_userinterface(df_final):
        add_vertical_space(1)
        if len(df_final) > 0:
            for i in range(len(df_final)):
                st.markdown(f'<h3 style="color: orange;">Job Posting Details : {i + 1}</h3>', unsafe_allow_html=True)
                st.write(f"Company Name : {df_final.iloc[i, 0]}")
                st.write(f"Job Title    : {df_final.iloc[i, 1]}")
                st.write(f"Location     : {df_final.iloc[i, 2]}")
                st.write(f"Website URL  : {df_final.iloc[i, 3]}")
                with st.expander(label='Job Description'):
                    st.write(df_final.iloc[i, 4])
                add_vertical_space(3)
        else:
            st.warning("No Matching Jobs Found")

    @staticmethod
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


# -----------------------
# STREAMLIT UI
# -----------------------
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
