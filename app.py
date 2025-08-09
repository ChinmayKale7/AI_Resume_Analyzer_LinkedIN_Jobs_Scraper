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

# ==== Config ====
GEMINI_MODEL = "gemini-1.5-flash"

# ==== Streamlit page config ====
def streamlit_config():
    st.set_page_config(page_title='Resume Analyzer AI', layout="wide")
    st.markdown("""
        <style>
        [data-testid="stHeader"] { background: rgba(0,0,0,0); }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<h1 style="text-align: center;">Resume Analyzer AI</h1>', unsafe_allow_html=True)


# ==== Resume Analyzer (single upload + cached results) ====
class resume_analyzer:

    @staticmethod
    def pdf_to_text(pdf):
        pdf_reader = PdfReader(pdf)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()

    @staticmethod
    def gemini_response(api_key, resume_text, prompt):
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(f"{prompt}\n\n{resume_text}")
        # response may be object with .text
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


# ==== LinkedIn Scraper (robust) ====
class linkedin_scraper:

    @staticmethod
    def webdriver_setup():
        """
        Uses system chromium & chromedriver provided by packages.txt on Streamlit Cloud (Debian Bullseye).
        Expects /usr/bin/chromium and /usr/bin/chromedriver to exist after apt install.
        """
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--ignore-certificate-errors')

        # Paths expected on Streamlit Cloud after installing packages 'chromium' and 'chromium-driver'
        chrome_options.binary_location = "/usr/bin/chromium"
        driver_path = "/usr/bin/chromedriver"

        # create driver
        driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        driver.maximize_window()
        return driver

    @staticmethod
    def get_userinput():
        add_vertical_space(2)
        with st.form(key='linkedin_scrap'):
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
        # try until page loads (original behavior)
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
                    "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']>icon>svg").click()
            except:
                pass
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            try:
                driver.find_element(By.CSS_SELECTOR, value="button[aria-label='See more jobs']").click()
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
        """
        Safe scraping: iterate using zip() over elements to avoid mismatched lists.
        Returns DataFrame with only rows that pass job title & location filters.
        """
        companies = driver.find_elements(By.CSS_SELECTOR, 'h4.base-search-card__subtitle')
        locations = driver.find_elements(By.CSS_SELECTOR, 'span.job-search-card__location')
        titles = driver.find_elements(By.CSS_SELECTOR, 'h3.base-search-card__title')
        urls = driver.find_elements(By.XPATH, '//a[contains(@href, "/jobs/")]')

        rows = []
        for comp_el, loc_el, title_el, url_el in zip(companies, locations, titles, urls):
            comp_text = comp_el.text.strip()
            loc_text = loc_el.text.strip()
            title_text = title_el.text.strip()
            url = url_el.get_attribute('href')

            # filter job title and location inline
            jt_filtered = linkedin_scraper.job_title_filter(title_text, job_title_input)
            loc_filtered = loc_text if job_location.lower() in loc_text.lower() else np.nan

            if pd.notna(jt_filtered) and pd.notna(loc_filtered):
                rows.append({
                    'Company Name': comp_text,
                    'Job Title': jt_filtered,
                    'Location': loc_filtered,
                    'Website URL': url
                })

        return pd.DataFrame(rows)

    @staticmethod
    def scrap_job_description(driver, df, job_count):
        """
        Build descriptions and rows together to ensure lengths match.
        Only keep rows that successfully yield a description.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        descriptions = []
        valid_rows = []

        # iterate over the rows up to requested job_count
        for idx, row in df.head(job_count).iterrows():
            url = row['Website URL']
            try:
                linkedin_scraper.open_link(driver, url)
                # click show more if present
                try:
                    driver.find_element(By.CSS_SELECTOR,
                        'button[data-tracking-control-name="public_jobs_show-more-html-btn"]').click()
                    time.sleep(0.5)
                except:
                    pass

                elems = driver.find_elements(By.CSS_SELECTOR, 'div.show-more-less-html__markup')
                text = elems[0].text.strip() if elems else ""
                if text:
                    valid_rows.append(row.to_dict())
                    descriptions.append(text)
                else:
                    # skip if empty description found
                    continue
            except Exception:
                # skip this job if any error occurs while opening or reading
                continue

        if not valid_rows:
            return pd.DataFrame()

        df_valid = pd.DataFrame(valid_rows).reset_index(drop=True)
        df_valid['Job Description'] = descriptions
        return df_valid

    @staticmethod
    def display_data_userinterface(df_final):
        add_vertical_space(1)
        if df_final is not None and not df_final.empty:
            for i in range(len(df_final)):
                st.markdown(f'<h3 style="color: orange;">Job Posting Details : {i+1}</h3>', unsafe_allow_html=True)
                st.write(f"Company Name : {df_final.iloc[i,0]}")
                st.write(f"Job Title    : {df_final.iloc[i,1]}")
                st.write(f"Location     : {df_final.iloc[i,2]}")
                st.write(f"Website URL  : {df_final.iloc[i,3]}")
                with st.expander(label='Job Description'):
                    st.write(df_final.iloc[i,4])
                add_vertical_space(2)
        else:
            st.markdown('<h5 style="text-align: center;color: orange;">No Matching Jobs Found</h5>', unsafe_allow_html=True)

    @staticmethod
    def main():
        driver = None
        try:
            job_title_input, job_location, job_count, submit = linkedin_scraper.get_userinput()
            add_vertical_space(2)
            if submit:
                if job_title_input != [] and job_location != '':
                    with st.spinner('Initializing Chrome WebDriver...'):
                        driver = linkedin_scraper.webdriver_setup()
                    with st.spinner('Loading job listings & scrolling...'):
                        link = linkedin_scraper.build_url(job_title_input, job_location)
                        linkedin_scraper.link_open_scrolldown(driver, link, job_count)
                    with st.spinner('Scraping job details...'):
                        df = linkedin_scraper.scrap_company_data(driver, job_title_input, job_location)
                        df_final = linkedin_scraper.scrap_job_description(driver, df, job_count)
                    linkedin_scraper.display_data_userinterface(df_final)
                else:
                    st.warning("Please provide Job Title and Job Location")
        except Exception as e:
            st.error(f"Scraper error: {e}")
        finally:
            if driver:
                driver.quit()


# ==== Streamlit UI ====
streamlit_config()
add_vertical_space(2)

with st.sidebar:
    option = option_menu(
        menu_title='',
        options=['Summary', 'Strength', 'Weakness', 'Job Titles', 'Linkedin Jobs'],
        icons=['house-fill', 'database-fill', 'pass-fill', 'list-ul', 'linkedin']
    )

# keep resume + api in session_state
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = None

if option == 'Summary':
    with st.form(key='Summary'):
        pdf = st.file_uploader('Upload Your Resume', type='pdf')
        api_key = st.text_input('Enter Google API Key', type='password')
        submit = st.form_submit_button('Submit')
    if submit:
        if pdf and api_key:
            st.session_state.resume_text = resume_analyzer.pdf_to_text(pdf)
            st.session_state.api_key = api_key
            with st.spinner("Running analyses..."):
                summary = resume_analyzer.gemini_response(api_key, st.session_state.resume_text, resume_analyzer.summary_prompt(st.session_state.resume_text))
            st.markdown(f'<h4 style="color: orange;">Summary:</h4>', unsafe_allow_html=True)
            st.write(summary)
        else:
            st.warning("Please upload resume and enter API key")

elif option == 'Strength':
    if st.session_state.resume_text and st.session_state.api_key:
        with st.spinner("Analyzing strengths..."):
            strength = resume_analyzer.gemini_response(st.session_state.api_key, st.session_state.resume_text, resume_analyzer.strength_prompt(st.session_state.resume_text))
        st.markdown(f'<h4 style="color: orange;">Strength:</h4>', unsafe_allow_html=True)
        st.write(strength)
    else:
        st.info("Go to Summary tab, upload resume & enter API key first.")

elif option == 'Weakness':
    if st.session_state.resume_text and st.session_state.api_key:
        with st.spinner("Analyzing weaknesses..."):
            weakness = resume_analyzer.gemini_response(st.session_state.api_key, st.session_state.resume_text, resume_analyzer.weakness_prompt(st.session_state.resume_text))
        st.markdown(f'<h4 style="color: orange;">Weakness and Suggestions:</h4>', unsafe_allow_html=True)
        st.write(weakness)
    else:
        st.info("Go to Summary tab, upload resume & enter API key first.")

elif option == 'Job Titles':
    if st.session_state.resume_text and st.session_state.api_key:
        with st.spinner("Suggesting job titles..."):
            jobs = resume_analyzer.gemini_response(st.session_state.api_key, st.session_state.resume_text, resume_analyzer.job_title_prompt(st.session_state.resume_text))
        st.markdown(f'<h4 style="color: orange;">Job Titles:</h4>', unsafe_allow_html=True)
        st.write(jobs)
    else:
        st.info("Go to Summary tab, upload resume & enter API key first.")

elif option == 'Linkedin Jobs':
    linkedin_scraper.main()
