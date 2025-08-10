# 📄 Resume Analyzer AI + LinkedIn Job Scraper

**Author:** Chinmay Kale  
**Role:** Technical Head – Data Science Students Association  

## 👋 About Me
Hi! I'm **Chinmay Kale**, a passionate data science enthusiast and developer.  
I specialize in building intelligent applications that combine AI, automation, and data analytics to solve real-world problems.  
I believe in creating tools that are not just functional, but also intuitive and impactful.

---

## 🚀 Project Overview
This project is an **AI-powered Resume Analyzer** integrated with a **LinkedIn Job Scraper**.  
It allows users to:
- Upload their resume **once** and get a detailed **Summary**, **Strengths**, **Weaknesses**, and **Job Title Suggestions** instantly.
- Search **real-time job postings** on LinkedIn that match their profile.

---

## ✨ Key Functionalities

### 1️⃣ Resume Analyzer (Powered by Google Gemini AI)
- **Single Upload**: Upload your resume once in PDF format.
- **AI Summary**: Generates a detailed summary of your resume.
- **Strengths Analysis**: Identifies and explains your professional strengths.
- **Weaknesses & Suggestions**: Points out weaknesses and suggests improvements.
- **Job Title Recommendations**: Suggests job roles you are best suited for.

> All analyses are run **once** during the Summary tab and cached, so switching tabs is instant.

---

### 2️⃣ LinkedIn Job Scraper
- **Automated Job Search**: Search for relevant jobs on LinkedIn.
- **Custom Filters**:
  - Job title keywords
  - Location filter
  - Number of jobs to fetch
- **Data Extracted**:
  - Company Name
  - Job Title
  - Location
  - Job Description
  - Direct job posting URL

---

## 🛠️ Tech Stack

| Category            | Technology Used |
|---------------------|-----------------|
| **Frontend/UI**     | Streamlit, streamlit-option-menu, streamlit-extras |
| **AI/ML**           | Google Gemini API (`gemini-1.5-flash`) |
| **PDF Processing**  | PyPDF2 |
| **Web Scraping**    | Selenium, Chrome WebDriver |
| **Data Handling**   | Pandas, NumPy |
| **Language**        | Python 3 |

---

## 📂 Project Structure
resume-analyzer-ai/
│-- app.py # Main application
│-- requirements.txt # Dependencies
│-- README.md # Project documentation

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository
```bash
git clone https://github.com/ChinmayKale7/AI_Resume_Analyzer_LinkedIN_Jobs_Scraper.git

cd AI_Resume_Analyzer_LinkedIN_Jobs_Scraper


pip install -r requirements.txt


 3️⃣ Install ChromeDriver
Download from: https://chromedriver.chromium.org/downloads

Ensure the version matches your installed Chrome browser.

Add it to your system PATH.

▶️ Running the App
streamlit run app.py


📌 Usage Guide
Go to the "Summary" tab

Upload your resume (PDF)

Enter Google API key

Wait while AI generates all analyses

Navigate to other tabs:

Strengths

Weaknesses

Job Titles
(These load instantly from memory)

Search LinkedIn Jobs

Enter job title, location, and desired number of jobs

View results with descriptions and direct links



