import logging
from dataclasses import asdict

from exceptions import HTTPResponseError
from processing import write_to_json, write_to_excel
from config import JSON_RESULT_FILE, EXCEL_RESULT_FILE, BASE_URL
from logger import log_time, configure_logging
from parsing import get_all_courses, get_course_detail


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
            (
                details,
                num_modules,
                num_topics,
                full_time_duration,
                flex_time_duration
            ) = get_course_detail(course.link)
            course_dict["details"] = asdict(details)
            course_dict["num_modules"] = num_modules
            course_dict["num_topics"] = num_topics
            course_dict["full_time_duration"] = full_time_duration
            course_dict["flex_time_duration"] = flex_time_duration
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
