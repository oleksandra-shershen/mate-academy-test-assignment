import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
from typing import Callable, Any

import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.hyperlink import Hyperlink

from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://mate.academy/"
JSON_RESULT_FILE = "courses_data.json"
EXCEL_RESULT_FILE = "courses_data.xlsx"


class HTTPResponseError(Exception):
    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(
            f"Error getting page: {url}, status code: {status_code}"
        )


@dataclass(frozen=True)
class CourseLinkDTO:
    name: str
    link: str
    description: str  # Added description field


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
        logging.info(
            f"Time taken by {func.__name__}: {elapsed_time:.2f} seconds"
        )
        return result

    return wrapper


@log_time
def get_page_content(url: str, timeout: int = 10) -> str:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as error:
        logging.error(f"Error fetching {url}: {error}")
        raise HTTPResponseError(url, response.status_code) from error


def get_course_detail(url: str) -> CourseDetailDTO:
    content = get_page_content(url)
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
        topics = [
            topic.text.strip()
            for topic in module.find(
                "div",
                class_=re.compile(r"CourseModuleItem_topicsListContainer.*")
            ).find_all("p", class_=re.compile(r"typography_landingTextMain.*"))
        ]
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
    content = get_page_content(url)
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
            "Description": course["description"]
        }
        for course in courses_data
    ]
    df_summary = pd.DataFrame(summary_data)

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)

        for course in courses_data:
            course_name = sanitize_sheet_name(course["name"])
            course_details = course.get("details", {})
            df_modules = pd.DataFrame(course_details.get("modules", []))

            for col in df_modules.columns:
                df_modules[col] = df_modules[col].apply(
                    lambda x: add_line_breaks(x, 10)
                    if isinstance(x, str) else x
                )

            df_modules.to_excel(writer, sheet_name=course_name, index=False)

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
