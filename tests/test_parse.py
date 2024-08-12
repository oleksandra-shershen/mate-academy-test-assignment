import pytest
from app.parsing import get_all_courses, CourseLink, BASE_URL

EXPECTED_COURSES = [
    "UI/UX Designer",
    "QA Engineer",
    "Python developer",
    "Data analyst",
]


@pytest.fixture
def all_courses():
    return get_all_courses(BASE_URL)


def test_get_all_courses(all_courses):
    assert isinstance(all_courses, list), "Result should be a list"
    assert all_courses, "Course list should not be empty"

    course_names = [course_link.name for course_link in all_courses]
    print(f"Retrieved courses: {course_names}")

    for course in EXPECTED_COURSES:
        assert any(
            course.lower() in course_link.name.lower() for course_link in all_courses
        ), f"Course '{course}' was not found"

    for course_link in all_courses:
        assert isinstance(course_link, CourseLink), "Each item should be an instance of CourseLink"
        assert course_link.name, "Course name should not be empty"
        assert course_link.link.startswith(BASE_URL), "Link should start with BASE_URL"
        assert course_link.description, "Course description should not be empty"
