import json
import logging
import os
import re
import time
from dataclasses import dataclass, asdict
from functools import wraps
from typing import Callable, Any, List
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.hyperlink import Hyperlink

BASE_URL = "https://mate.academy/"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_RESULT_FILE = os.path.join(APP_DIR, "courses_data.json")
EXCEL_RESULT_FILE = os.path.join(APP_DIR, "courses_data.xlsx")


class HTTPResponseError(Exception):
    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(
            f"Error getting page: {url}, status code: {status_code}"
        )


@dataclass(frozen=True)
class CourseLinkDTO:
    name: str
    link: str
    description: str


@dataclass(frozen=True)
class CourseModuleDTO:
    title: str
    description: str
    topics: List[str]


@dataclass(frozen=True)
class CourseDetailDTO:
    modules: List[CourseModuleDTO]


def configure_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("app.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)


def log_time(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(url: str, *args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(url, *args, **kwargs)
        elapsed_time = time.time() - start_time
        logging.info(f"Time taken by {func.__name__} for {url}: {elapsed_time:.2f} seconds")
        return result

    return wrapper


@log_time
def fetch_full_page(url: str, timeout: int = 10) -> str:
    driver = webdriver.Chrome()
    driver.get(url)

    try:
        while True:
            show_more_button = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    ".CourseModulesBlock_showMoreButton__N0f0_"
                ))
            )
            driver.execute_script("arguments[0].click();", show_more_button)
            time.sleep(2)
    except:
        pass

    page_content = driver.page_source
    driver.quit()
    return page_content


def get_course_detail(url: str) -> CourseDetailDTO:
    content = fetch_full_page(url)
    soup = BeautifulSoup(content, "html.parser")

    modules = []
    module_items = soup.find_all("div", class_=re.compile(r"CourseModuleItem_grid__.*"))

    for item in module_items:
        title = item.find("h4").text.strip()
        description = item.find("p", class_=re.compile(r"CourseModuleItem_description__.*")).text.strip()
        topics_section = item.find("div", class_="CourseModuleItem_topicsList__Dmm8g")
        if topics_section:
            topics = [topic.text.strip() for topic in
                      topics_section.find_all("p", class_="typography_landingTextMain__Rc8BD")]
        else:
            topics = []

        modules.append(CourseModuleDTO(title=title, description=description, topics=topics))

    return CourseDetailDTO(modules=modules)


def get_all_courses(url: str) -> list[CourseLinkDTO]:
    content = fetch_full_page(url)
    soup = BeautifulSoup(content, "html.parser")
    courses = []

    profession_cards = soup.find_all(
        "div", class_=re.compile(r"ProfessionCard_cardWrapper__JQBNJ")
    )

    for card in profession_cards:
        name_tag = card.find(
            "a", class_="typography_landingH3__vTjok ProfessionCard_title__Zq5ZY mb-12"
        )
        description_tag = card.find(
            "p", class_="typography_landingTextMain__Rc8BD mb-32"
        )
        if name_tag and description_tag:
            name = name_tag.find("h3").text.strip()
            link = urljoin(BASE_URL, name_tag.get("href"))
            description = description_tag.text.strip()
            courses.append(
                CourseLinkDTO(name=name, link=link, description=description)
            )
        else:
            logging.warning(f"Missing course name or description in card: {card}")

    return courses


def write_to_json(courses_details: list[dict], file_name: str) -> None:
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(courses_details, f, ensure_ascii=False, indent=4)
    logging.info(f"Write to file: {file_name}")


def sanitize_sheet_name(sheet_name: str) -> str:
    return re.sub(r'[\/:*?"<>|]', "_", sheet_name)[:31]


def add_line_breaks(text: str, max_words: int) -> str:
    words = text.split()
    lines = [
        " ".join(words[i: i + max_words])
        for i in range(0, len(words), max_words)
    ]
    return "\n".join(lines)


def write_to_excel(courses_data: list[dict], file_name: str) -> None:
    summary_data = [
        {
            "Name": course["name"],
            "Link": course["link"],
            "Description": course["description"],
        }
        for course in courses_data
    ]
    df_summary = pd.DataFrame(summary_data)

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)

        for course in courses_data:
            sheet_name = sanitize_sheet_name(course["name"])
            module_data = [
                {
                    "Title": module["title"],
                    "Description": module["description"],
                    "Topics": ", ".join(module["topics"]),
                }
                for module in course["details"]["modules"]
            ]
            df_modules = pd.DataFrame(module_data)
            df_modules.to_excel(writer, sheet_name=sheet_name, index=False)

    workbook = load_workbook(file_name)

    summary_sheet = workbook["Summary"]
    for row in summary_sheet.iter_rows(
            min_row=2, max_row=len(courses_data) + 1, min_col=2, max_col=2
    ):
        for cell in row:
            link = cell.value
            cell.hyperlink = Hyperlink(ref=cell.coordinate, target=link)
            cell.style = "Hyperlink"
            cell.alignment = Alignment(
                wrap_text=True, horizontal="center", vertical="center"
            )

    for sheet_name in workbook.sheetnames:
        worksheet = workbook[sheet_name]

        for row in worksheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(
                    wrap_text=True, horizontal="center", vertical="center"
                )

        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = min((max_length + 2), 50)
            worksheet.column_dimensions[column].width = adjusted_width

    workbook.save(file_name)
    logging.info(f"Write to Excel file: {file_name}")


@log_time
def main(base_url: str) -> None:
    configure_logging()
    try:
        courses = get_all_courses(base_url)
        courses_data = []
        for course in courses:
            course_dict = {
                "name": course.name,
                "link": course.link,
                "description": course.description,
            }
            details = get_course_detail(course.link)
            course_dict["details"] = asdict(details)
            courses_data.append(course_dict)
    except HTTPResponseError as e:
        logging.error(f"Failed to fetch courses: {e}")
    else:
        write_to_json(courses_data, JSON_RESULT_FILE)
        write_to_excel(courses_data, EXCEL_RESULT_FILE)
        logging.info(
            f"Courses data saved to {JSON_RESULT_FILE} and {EXCEL_RESULT_FILE}"
        )


if __name__ == "__main__":
    main(BASE_URL)
