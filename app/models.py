from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class CourseLink:
    name: str
    link: str
    description: str


@dataclass(frozen=True)
class CourseModule:
    title: str
    description: str
    topics: List[str]


@dataclass(frozen=True)
class CourseDetail:
    modules: List[CourseModule]
