import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import time
import base64
from webdriver_manager.chrome import ChromeDriverManager

# Set page configuration
st.set_page_config(
    page_title="LinkedIn Job Scraper",
    page_icon="💼",
    layout="wide"
)

# Title and description
st.title("LinkedIn Job Scraper")
st.markdown("This app scrapes LinkedIn job listings based on job titles and location.")

# Sidebar for inputs
with st.sidebar:
    st.header("Search Parameters")
    
    # Job titles input
    job_titles = st.text_input("Enter Job Titles (comma separated):", 
                              value="Data Scientist, Machine Learning Engineer")
    
    # Location input with India as default
    location = st.text_input("Location:", value="India")
    
    # Time range selection
    time_range = st.selectbox(
        "Time Range:",
        options=["Past 24 hours", "Past Week", "Past Month", "Any Time"],
        index=1
    )
    
    # Map time range to LinkedIn parameter
    time_range_param = {
        "Past 24 hours": "r86400",
        "Past Week": "r604800",
        "Past Month": "r2592000",
        "Any Time": ""
    }
    
    # Number of scrolls/pages to load
    num_scrolls = st.slider("Number of Pages to Load:", 
                           min_value=1, max_value=20, value=5)
    
    # Execute button
    search_button = st.button("Search Jobs", type="primary")
    
    # Display info about the app
    st.info("This app uses Selenium to scrape LinkedIn job listings. It may take some time to load all results.")

# Function to initialize the WebDriver
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return driver
    except Exception as e:
        st.error(f"Error initializing WebDriver: {e}")
        return None

# Function to scrape jobs
def scrape_linkedin_jobs(job_title, location, time_param, num_scrolls):
    driver = get_driver()
    if not driver:
        return []
    
    job_urls = []
    job_titles_list = []
    company_names = []
    locations_list = []
    
    # Construct URL
    location_param = location.replace(" ", "%20")
    job_param = job_title.replace(" ", "%20")
    base_url = "https://www.linkedin.com/jobs/search"
    
    if time_param:
        link = f"{base_url}?keywords={job_param}&location={location_param}&f_TPR={time_param}"
    else:
        link = f"{base_url}?keywords={job_param}&location={location_param}"
    
    try:
        with st.spinner(f"Searching for {job_title} jobs in {location}..."):
            driver.get(link)
            time.sleep(3)  # Allow page to load
            
            progress_bar = st.progress(0)
            
            for i in range(num_scrolls):
                try:
                    # Scroll to bottom
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    
                    # Wait for the "See more jobs" button and click it
                    try:
                        button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='See more jobs']"))
                        )
                        button.click()
                        time.sleep(2)  # Wait for new content
                    except Exception:
                        pass  # Button may not be available on all pages
                    
                    # Update progress
                    progress_bar.progress((i + 1) / num_scrolls)
                    
                except WebDriverException as e:
                    st.warning(f"WebDriver exception: {e}")
                    # Restart session
                    driver.quit()
                    driver = get_driver()
                    driver.get(link)
                    time.sleep(3)
            
            # Scrape job details
            job_cards = driver.find_elements(By.CLASS_NAME, "job-search-card")
            
            for card in job_cards:
                try:
                    # Get job URL
                    url_element = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title")
                    job_urls.append(url_element.get_attribute('href'))
                    
                    # Get job title
                    job_titles_list.append(url_element.text)
                    
                    # Get company name
                    try:
                        company = card.find_element(By.CSS_SELECTOR, ".job-card-container__company-name")
                        company_names.append(company.text)
                    except:
                        company_names.append("N/A")
                    
                    # Get location
                    try:
                        loc = card.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item")
                        locations_list.append(loc.text)
                    except:
                        locations_list.append("N/A")
                        
                except Exception as e:
                    continue  # Skip this card if there's an error
            
    except Exception as e:
        st.error(f"Error during scraping: {e}")
    finally:
        # No need to quit the driver as it's cached
        pass
    
    # Create a dictionary of results
    results = {
        "Job Title": job_titles_list,
        "Company": company_names,
        "Location": locations_list,
        "Job URL": job_urls
    }
    
    return results

# Function to create a download link for the DataFrame
def get_csv_download_link(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV File</a>'
    return href

# Main app logic
if search_button:
    job_titles_list = [title.strip() for title in job_titles.split(",")]
    
    # Container for results
    results_container = st.container()
    
    all_results = pd.DataFrame()
    
    for job_title in job_titles_list:
        # Show what we're currently scraping
        st.subheader(f"Scraping: {job_title}")
        
        # Get time parameter
        time_param = time_range_param[time_range]
        
        # Scrape jobs
        job_data = scrape_linkedin_jobs(job_title, location, time_param, num_scrolls)
        
        if job_data and len(job_data["Job URL"]) > 0:
            # Create DataFrame
            df = pd.DataFrame(job_data)
            
            # Add job search term
            df["Search Term"] = job_title
            
            # Append to all results
            all_results = pd.concat([all_results, df], ignore_index=True)
            
            # Show results for this job title
            st.write(f"Found {len(df)} jobs for '{job_title}'")
        else:
            st.warning(f"No jobs found for '{job_title}'")
    
    # Display all results if we have any
    if not all_results.empty:
        with results_container:
            st.header("Search Results")
            st.write(f"Total jobs found: {len(all_results)}")
            
            # Display the dataframe
            st.dataframe(all_results, use_container_width=True)
            
            # Create download link
            st.markdown(get_csv_download_link(all_results, "linkedin_jobs.csv"), unsafe_allow_html=True)
            
            # Create clickable URLs
            st.subheader("Job Links")
            for index, row in all_results.iterrows():
                st.markdown(f"[{row['Job Title']} at {row['Company']}]({row['Job URL']})")
    else:
        st.error("No jobs found. Try adjusting your search parameters.")

# Footer
st.markdown("---")
st.markdown("LinkedIn Job Scraper | Developed with Streamlit and Selenium")
