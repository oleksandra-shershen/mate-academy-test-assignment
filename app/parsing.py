import logging
import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from models import CourseDetail, CourseModule, CourseLink
from config import BASE_URL
from logger import log_time


@log_time
def fetch_full_page(url: str, timeout: int = 10) -> str:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    while click_show_more_button(driver, timeout):
        WebDriverWait(driver, timeout).until_not(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".CourseModulesBlock_showMoreButton__N0f0_")
            )
        )

    page_content = driver.page_source
    driver.quit()
    return page_content


def click_show_more_button(driver: webdriver.Chrome, timeout: int) -> bool:
    try:
        show_more_button = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".CourseModulesBlock_showMoreButton__N0f0_")
            )
        )
        driver.execute_script("arguments[0].click();", show_more_button)
        return True
    except Exception as e:
        logging.debug(f"No more 'Show more' button found: {e}")
        return False


def get_course_detail(url: str) -> (CourseDetail, int, int, str, str):
    content = fetch_full_page(url)
    soup = BeautifulSoup(content, "html.parser")

    num_modules, num_topics = extract_modules_and_topics(soup)
    full_time_duration, flex_time_duration = extract_durations(soup)
    modules = extract_modules(soup)

    return (
        CourseDetail(modules=modules),
        num_modules,
        num_topics,
        full_time_duration,
        flex_time_duration,
    )


def extract_modules_and_topics(soup: BeautifulSoup) -> (int, int):
    modules_heading = soup.find(
        "div",
        class_="CourseModulesHeading_headingGrid__ynoxV"
    )

    if modules_heading is None:
        logging.error("Modules heading not found.")
        raise ValueError("Modules heading not found.")

    num_modules = int(
        modules_heading.find(
            "div",
            class_="CourseModulesHeading_modulesNumber__UrnUh"
        )
        .text.strip()
        .split()[0]
    )
    num_topics = int(
        modules_heading.find(
            "div",
            class_="CourseModulesHeading_topicsNumber__5IA8Z"
        )
        .text.strip()
        .split()[0]
    )

    return num_modules, num_topics


def extract_durations(soup: BeautifulSoup) -> (str, str):
    full_time_duration = ""
    flex_time_duration = ""

    comparison_tables = soup.find_all(
        "div",
        class_=re.compile(r"ComparisonTable_wrapper__.*")
    )

    if not comparison_tables:
        logging.error("No comparison tables found.")
        raise ValueError("No comparison tables found.")

    for table in comparison_tables:
        cells = table.find_all("div", class_=re.compile(r"ComparisonTable_cell__.*"))

        for cell in cells:
            if cell.find("img", alt="Calendar"):
                full_time_duration = extract_duration_from_table(table)
            elif cell.find("img", alt="One o'clock"):
                flex_time_duration = extract_duration_from_table(table)

    return full_time_duration, flex_time_duration


def extract_table_header(table: BeautifulSoup) -> str:
    header = table.find("div", class_="ComparisonTable_row__P2dAA")

    if header:
        return header.text.strip()

    return ""


def extract_duration_from_table(table: BeautifulSoup) -> str:
    rows = table.find_all("div", class_="ComparisonTable_row__P2dAA")
    for row in rows:
        title = row.find(
            "div",
            class_="ComparisonTable_cell__8DNfm ComparisonTable_rowTitle__hwc7p"
        )
        if title and title.text.strip() == "Тривалість":
            value = row.find_all("div", class_="ComparisonTable_cell__8DNfm")[1]
            if value:
                return value.text.strip()
    return ""


def extract_modules(soup: BeautifulSoup) -> List[CourseModule]:
    modules = []
    module_items = soup.find_all(
        "div",
        class_=re.compile(r"CourseModuleItem_grid__.*")
    )

    for item in module_items:
        title, description = extract_module_title_and_description(item)
        topics = extract_module_topics(item)

        if title and description:
            modules.append(
                CourseModule(
                    title=title,
                    description=description,
                    topics=topics
                )
            )

    return modules


def extract_module_title_and_description(item: BeautifulSoup) -> (str, str):
    title_container = item.find(
        "div",
        class_=re.compile(r"CourseModuleItem_titleContainer__.*")
    )
    title = title_container.find(
        "h4",
        class_=re.compile(r"typography_landingH5__.*")
    ) if title_container else None
    description = item.find(
        "p",
        class_=re.compile(r"CourseModuleItem_description__.*")
    )

    if title and description:
        return title.text.strip(), description.text.strip()

    return "", ""


def extract_module_topics(item: BeautifulSoup) -> List[str]:
    topics_section = item.find(
        "div",
        class_="CourseModuleItem_topicsList__Dmm8g"
    )
    topics = []
    if topics_section:
        topics = [
            topic.text.strip()
            for topic in topics_section.find_all(
                "p", class_="typography_landingTextMain__Rc8BD"
            )
        ]

    return topics


def get_all_courses(url: str) -> list[CourseLink]:
    content = fetch_full_page(url)
    soup = BeautifulSoup(content, "html.parser")
    courses = []

    profession_cards = soup.find_all(
        "div", class_=re.compile(r"ProfessionCard_cardWrapper__JQBNJ")
    )

    for card in profession_cards:
        course = extract_course_from_card(card)
        if course:
            courses.append(course)

    return courses


def extract_course_from_card(card: BeautifulSoup) -> CourseLink | None:
    name_tag = card.find("a", class_=re.compile(r"ProfessionCard_title__.*"))
    description_tag = card.find(
        "p",
        class_=re.compile(r"ProfessionCard_subtitle__.*")
    )

    if name_tag and description_tag:
        name = name_tag.find("h3").text.strip()
        link = urljoin(BASE_URL, name_tag.get("href"))
        description = card.find(
            "p",
            class_=re.compile(r"typography_landingTextMain__.* mb-32")
        ).text.strip()
        return CourseLink(name=name, link=link, description=description)

    logging.warning(f"Missing course name or description in card: {card}")
    return None
