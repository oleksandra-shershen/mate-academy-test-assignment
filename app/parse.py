import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
from typing import Callable, Any
import os

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://mate.academy/"
script_dir = os.path.dirname(os.path.abspath(__file__))
JSON_RESULT_FILE = os.path.join(script_dir, "courses_data.json")
EXCEL_RESULT_FILE = os.path.join(script_dir, "courses_data.xlsx")


class HTTPResponseError(Exception):
    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(f"Error getting page: {url}, status code: {status_code}")


class CourseType(Enum):
    FULL_TIME = "full-time"
    PART_TIME = "part-time"


@dataclass(frozen=True)
class CourseLinkDTO:
    name: str
    link: str
    course_type: CourseType


@dataclass(frozen=True)
class CourseModuleDTO:
    title: str
    description: str
    topics: list[str]


@dataclass(frozen=True)
class CourseDetailDTO:
    duration: str
    num_modules: int
    num_topics: int
    modules: list[CourseModuleDTO]


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
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logging.info(f"Time taken by {func.__name__}: {elapsed_time:.2f} seconds")
        return result

    return wrapper


@log_time
def get_page_content_with_selenium(url: str, timeout: int = 10) -> str:
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
    content = get_page_content_with_selenium(url)
    soup = BeautifulSoup(content, "html.parser")

    heading = soup.find(
        "div",
        class_=re.compile(r"CourseModulesHeading_headingGrid.*")
    )
    duration = heading.find(
        "div", class_=re.compile(r"CourseModulesHeading_courseDuration.*")
    ).text.strip()
    num_modules = int(
        heading.find(
            "div",
            class_=re.compile(r"CourseModulesHeading_modulesNumber.*")
        )
        .text.strip()
        .split()[0]
    )
    num_topics = int(
        heading.find(
            "div",
            class_=re.compile(r"CourseModulesHeading_topicsNumber.*")
        )
        .text.strip()
        .split()[0]
    )

    modules = []
    module_elements = soup.find_all(
        "div", class_=re.compile(r"CourseModuleItem_grid.*")
    )

    for module in module_elements:
        title = module.find("h4").text.strip()
        description = module.find(
            "p", class_=re.compile(r"CourseModuleItem_description.*")
        ).text.strip()

        topics_container = module.find(
            "div",
            class_=re.compile(r"CourseModuleItem_topicsListContainer.*")
        )

        if topics_container:
            topics = [
                topic.text.strip()
                for topic in topics_container.find_all(
                    "p",
                    class_=re.compile(r"typography_landingTextMain.*")
                )
            ]
        else:
            topics = []

        modules.append(
            CourseModuleDTO(
                title=title,
                description=description,
                topics=topics
            )
        )

    return CourseDetailDTO(
        duration=duration,
        num_modules=num_modules,
        num_topics=num_topics,
        modules=modules,
    )


def get_all_courses(url: str) -> list[CourseLinkDTO]:
    content = get_page_content_with_selenium(url)
    soup = BeautifulSoup(content, "html.parser")
    courses = []

    ul_elements = soup.find_all(
        "ul", class_=re.compile(r"DropdownCoursesList_coursesList.*")
    )

    for ul in ul_elements:
        course_list_items = ul.find_all(
            "li", class_=re.compile(r"DropdownCoursesList_coursesListItem.*")
        )
        for item in course_list_items:
            course_name_tag = item.select_one(
                "span.ButtonBody_buttonText__FMZEg"
            )
            course_link_tag = item.select_one("a")
            if course_name_tag and course_link_tag:
                course_name = course_name_tag.text
                course_link = urljoin(BASE_URL, course_link_tag.get("href"))
                course_type = (
                    CourseType.PART_TIME
                    if "parttime" in course_link
                    else CourseType.FULL_TIME
                )
                courses.append(
                    CourseLinkDTO(course_name, course_link, course_type)
                )
            else:
                logging.warning(f"Missing course name or link in item: {item}")
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
            "Type": course["type"]
        }
        for course in courses_data
    ]
    df_summary = pd.DataFrame(summary_data)

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)

        for course in courses_data:
            course_name = sanitize_sheet_name(course["name"])
            course_details = course["details"]
            df_modules = pd.DataFrame(course_details["modules"])

            for col in df_modules.columns:
                df_modules[col] = df_modules[col].apply(
                    lambda x: add_line_breaks(x, 10)
                    if isinstance(x, str) else x
                )

            df_modules.to_excel(writer, sheet_name=course_name, index=False)

    workbook = load_workbook(file_name)

    summary_sheet = workbook["Summary"]
    for row in summary_sheet.iter_rows(
            min_row=2, max_row=len(courses_data) + 1, min_col=1, max_col=1
    ):
        for cell in row:
            course_name = cell.value
            sanitized_name = sanitize_sheet_name(course_name)
            cell.hyperlink = f"#'{sanitized_name}'!A1"
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
            course_details = get_course_detail(course.link)
            course_dict = {
                "name": course.name,
                "link": course.link,
                "type": course.course_type.value,
                "details": asdict(course_details),
            }
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
