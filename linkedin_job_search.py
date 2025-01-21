""" Searches LinkedIn for jobs, copies job information to a csv file, and exposes relevant job details for ranking and organizing.

The purpose of this script is to aid in searching for and deciding what jobs are worth applying to and what are not. It does this using LinkedIn's job search tool and Selenium's webdriver. The user can feed the script some details of the job search criteria for LinkedIn and then step away from the task while the script completes it. Using keywords the script should help in narrowing down the initial amount of jobs that are worth looking at. The user is required to know how the LinkedIn job search tool functions (though not in great detail) and do a bit of research into what keywords are most effective for the jobs the user is looking for.

Returns:
    csv file: contains the job information scraped from LinkedIn using the given job search criteria
"""
# rainbow csv query: SELECT * ORDER BY a4 DESC (a4 is score)
import pytest
import time
import json
import csv
from enum import Enum
from quickApply import test_quickapply
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import WebDriverException
import quickApply.test_quickapply

URL_LINKEDIN = "https://www.linkedin.com/jobs/"
USERNAME = ""
PASSWORD = ""
# '"validation" OR "embedded" OR "python" OR "test" OR (("project manager" OR "field") AND "engineer") OR "Technical Writer"'
JOB_SEARCH_CRITERIA = '"validation" OR "Technical Writer"'
LOCATION_SEARCH_CRITERIA = "United States"
SEARCHBOX_XPATH = "//div[contains(@class, 'jobs-search-box__input')]"
JOBDESCRIPTION_SEARCHBOX_XPATH = SEARCHBOX_XPATH + "//input[contains(@aria-label, 'Search by title, skill, or company')]"
LOCATION_SEARCHBOX_XPATH = SEARCHBOX_XPATH + "//input[contains(@id, 'jobs-search-box-location-id') and contains(@aria-label, 'City, state, or zip code')]"
DATE_RANGES = {"any time": "Filter by Any time",
                     "month": "Filter by Past month",
                     "week": "Filter by Past week",
                     "24hr": "Filter by Past 24 hours"}
JOB_DICT_FORMAT = {"link": None, "title": None, "location": None, "score": 0, "company": None, "keywords": set([]), "description": None}
KEYWORDS_LVL5 = {"validation engineer": 5, "hardware validation": 5, "python": 5, "soc validation": 5, "silicon validation": 5, "post-si validation": 5, 
                 "post-silicon validation": 5, "IP validation": 5}
KEYWORDS_LVL4 = {"software validation": 4, "embedded": 4, "firmware": 4, "automation": 4, "C/C++": 4, " C ": 4, "system validation": 4, 
                 "hardware debug": 4, "firmware debug": 4, "system debug": 4, "system test": 4, "system-level debug": 4, "system-level test": 4, 
                 "system level debug": 4, "systems debug": 4, "systems test": 4, "platform debug": 4, "platform test": 4, "platform-level debug": 4,
                 "platform-level test": 4, "platform level debug": 4, "platform level test": 4, "asic debug": 4, "asic test": 4}
KEYWORDS_LVL3 = {"field engineer": 3, "project manager": 3, "computer architecture": 3, "soc architecture": 3}
KEYWORDS_LVL2 = {"design engineer": 2, "test plan": 2, "system under test": 2, "SUT": 2, "device under test": 2, "DUT": 2, "shift-left": 2, "shift left": 2}
KEYWORDS_LVL1 = {"technician": 1, "JTAG": 1, "T32": 1, "Trace32": 1}
KEYWORDS = [KEYWORDS_LVL5, KEYWORDS_LVL4, KEYWORDS_LVL3, KEYWORDS_LVL2, KEYWORDS_LVL1]

def sign_in(qa: test_quickapply.TestQuickApply):
  """ Checks if there are sign in inputs and fills them with the global variables USERNAME and PASSWORD.
  """
  #if self.element_exists("username"):
  #  qa.driver.find_element(By.ID, "username").send_keys(USERNAME)
  #if self.element_exists("password"):
  #  qa.driver.find_element(By.ID, "password").send_keys(PASSWORD)
  #qa.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Sign in')]").click()

  elements = qa.driver.find_elements(By.ID, "session_key")
  if len(elements) == 1:
    qa.driver.find_element(By.ID, "session_key").send_keys(USERNAME)
  else:
    test_quickapply.LOG.warning("Unable to find username input")
  elements = qa.driver.find_elements(By.ID, "session_password")
  if len(elements) == 1:
    qa.driver.find_element(By.ID, "session_password").send_keys(PASSWORD)
    qa.wait.until(lambda d: qa.driver.find_element(By.XPATH, "//button[contains(@class, 'sign-in-form__submit-btn')]").is_displayed())
    qa.driver.find_element(By.XPATH, "//button[contains(@class, 'sign-in-form__submit-btn')]").click()
  else:
    test_quickapply.LOG.warning("Unable to find password input")

def linkedin_job_search(qa: test_quickapply.TestQuickApply, criterias: list, locations: list, date: str):
  """Searches for jobs in LinkedIn and scrapes and processes the jobs and outputs the data in a csv file (utf-8 encoding).

  This script uses the quickApply framework to drive the LinkedIn web page. Below are the steps taken.
  1. Sets up and launches Selenium webdriverfor LinkedIn.com.
  2. Using the user provided job search criteria it enters the info into LinkedIn job search tool.
  3. It then parses each returned job and scrapes the relevant informaiton (company, job title, location, description, etc).
  4. Using the description, the script assigns scores to each job based on keywords found in the description.
  5. It then writes the job data to a csv file and exits.

  Args:
      qa (test_quickapply.TestQuickApply): test_quickapply.TestQuickApply object.
      criterias (list): list of strings for linkedin's job search job description box.
      locations (list): list of strings for linkedin's job search location box.
      date (str): "any time", "month", "week", or "24hr" for filtering based on jobs posted within the last amount of time selected.
  """

  #TODO: Check that the search criteria input into the linkedin search box is formatted for regex

  for place in locations:
    for idx, search in enumerate(criterias):

      qa.driver.get(URL_LINKEDIN)
      sign_in(qa) # check for login info
      # If LinkedIn suspects you are using a bot/automation tools (i.e. Selenium) it may ask for you to verify your actions. The qa.wait amount can also be changed and the script can wait on another element.
      time.sleep(12) # verify actions by user
      qa.driver.maximize_window()

      # search jobs
      qa.driver.find_element(By.XPATH, JOBDESCRIPTION_SEARCHBOX_XPATH).clear()

      qa.wait.until(lambda d: qa.driver.find_element(By.XPATH, JOBDESCRIPTION_SEARCHBOX_XPATH).is_displayed())
      qa.driver.find_element(By.XPATH, JOBDESCRIPTION_SEARCHBOX_XPATH).send_keys(search)
      
      qa.driver.find_element(By.XPATH, JOBDESCRIPTION_SEARCHBOX_XPATH).send_keys(Keys.ENTER)

      qa.wait.until(lambda d: qa.driver.find_element(By.XPATH, LOCATION_SEARCHBOX_XPATH).is_displayed())
      qa.driver.find_element(By.XPATH, LOCATION_SEARCHBOX_XPATH).clear()
      
      qa.wait.until(lambda d: qa.driver.find_element(By.XPATH, LOCATION_SEARCHBOX_XPATH).is_displayed())
      qa.driver.find_element(By.XPATH, LOCATION_SEARCHBOX_XPATH).send_keys(place)
      
      qa.driver.find_element(By.XPATH, LOCATION_SEARCHBOX_XPATH).send_keys(Keys.ENTER)

      time.sleep(3)
      # narrow number of hours for posted jobs
      qa.driver.find_element(By.ID, "searchFilter_timePostedRange").click()
      qa.wait.until(lambda d: qa.driver.find_element(By.XPATH, "//legend[text()='Filter results by: Date posted']").is_enabled())
      date_posted_menu = qa.driver.find_element(By.XPATH, "//legend[text()='Filter results by: Date posted']/..")
      menu_items = date_posted_menu.find_elements(By.XPATH, ".//li[contains(@class, 'search-reusables__collection-values-item')]")
      for element in menu_items:
        elements = qa.driver.find_elements(By.XPATH, f".//span[text()='{DATE_RANGES[date]}']")
        if len(elements) > 0:
          ActionChains(qa.driver).move_to_element(element.find_element(By.XPATH, "./input")).click().perform()

      time.sleep(1)
      qa.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Apply current filter to show')]").click()

      # start scraping information from the job descriptions
      time.sleep(2)
      page_links_elements = qa.driver.find_elements(By.XPATH, "//ul[contains(@class, 'pages--number')]")
      if len(page_links_elements) > 0:
        page_links_element = qa.driver.find_element(By.XPATH, "//ul[contains(@class, 'pages--number')]")
        page_links = page_links_element.find_elements(By.XPATH, ".//button[contains(@aria-label, 'Page')]")
        num_pages = len(page_links)
      else:
        num_pages = 1

      if num_pages > 15: # one search in the united states for previous 24hrs showed nearly 6,000 results
        num_pages = 15

      curr_page = 6
      #curr_page = len(page_links) #debug only
      jobs_data = []
      while curr_page <= num_pages:
        # check if the page should be updated to the next page
        if curr_page != 1:
          page_links_element = qa.driver.find_element(By.XPATH, "//ul[contains(@class, 'pages--number')]")
          next_page = page_links_element.find_element(By.XPATH, f".//button[contains(@aria-label, 'Page {curr_page}')]")
          qa.scroll_to_element(next_page)
          next_page.click()
        time.sleep(2)
        
        # sanity check that the page is not broken (linkedin has a problem)
        no_jobs_element = qa.driver.find_elements(By.XPATH, "//p[text()='No matching jobs found.']")

        if len(no_jobs_element) == 0:
          jobs_list_element = qa.driver.find_element(By.XPATH, "//header[contains(@class, 'jobs-search-results-list')]/..")
          jobs_list_ul_element = jobs_list_element.find_element(By.XPATH, ".//ul")
          jobs_list = jobs_list_ul_element.find_elements(By.XPATH, "./*")

          for job in jobs_list: # iterate through all jobs on page
            qa.scroll_to_element(job)
            job_dict = {"link": None, "title": None, "location": None, "score": 0, "company": None, "keywords": set([]), "description": None}
            time.sleep(.2)
            job.find_element(By.XPATH, ".//a").click()
            time.sleep(.5)

            # Any number of issues within linkedin can occur for a specific job card. It is easiest to have a generic
            # try catch block and attempt to continue executing to handle other job cards that do not have issues.
            try:
              job_element = qa.driver.find_element(By.CLASS_NAME, "jobs-search__job-details--container")
              
              job_dict["link"] = qa.driver.current_url

              job_dict["title"] = job_element.get_attribute("aria-label")

              location_element = job_element.find_element(By.XPATH, ".//div[contains(@class, 'primary-description-container')]//span") #first element should be location
              job_dict["location"] = location_element.text

              job_dict["company"] = job_element.find_element(By.XPATH, ".//div[contains(@class, 'top-card__company-name')]/a").text

              description_element = qa.driver.find_element(By.ID, "job-details")
              text_box = description_element.find_element(By.XPATH, ".//p[contains(@dir, 'ltr')]")
              raw_text = text_box.text
              text_no_newline = raw_text.replace("\n", " ")
              text_utf8_format = text_no_newline.encode("utf-8", errors="ignore").decode("utf-8")
              job_dict["description"] = text_utf8_format

              jobs_data.append(job_dict)

            except WebDriverException as e:
              test_quickapply.LOG.warning(f"Caught the following error on page {curr_page} with search criteria {search}, {place}.\nWill attempt to continue execution.\n{e}")

        curr_page += 1

      # search for keywords in the description and add to the score total
      for job in jobs_data:
        test_quickapply.LOG.debug(f"scoring job: {job["title"]}")
        for keyword_level in KEYWORDS:
          for keyword in keyword_level.keys():
            if keyword.lower() in job["description"].lower():
              job["score"] += keyword_level[keyword]
              job["keywords"].add(keyword)
              test_quickapply.LOG.debug(f"added {keyword_level[keyword]} to score and keyword {keyword} to keywords")

      csv_name = f"todays_jobs_{place.replace(" ", "")}_{idx}.csv"
      with open(csv_name, 'w', newline="", encoding="utf-8") as csvfile:
        fieldnames = ["link", "title", "location", "score", "company", "keywords", "description"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs_data)

  time.sleep(10) # for debug