# Mate Academy Test Assignment
## Task 1: SQL queries
There are next tables: users, leads, domains, courses.

Prepare SQL queries to select the next data:

1.1. The number of created leads per week grouped by course type

1.2. The number of WON flex leads per country created from 01.01.2024

1.3. User email, lead id and lost reason for users who have lost flex leads from 01.07.2024

Table schemas:

__users__
| id  | email               | first_name | last_name | phone         | domain_id | language_id |
|-----|---------------------|------------|-----------|---------------|-----------|-------------|
| 35  | [jsmith@example.com](mailto:jsmith@example.com) | John       | Smith     | (123) 456-7890 | 1         | 1           |
| 47  | [ldoe@example.com](mailto:ldoe@example.com)    | Laura      | Doe       | (987) 654-3210 | 1         | 1           |
| 51  | [mbrown@example.com](mailto:mbrown@example.com)| Michael    | Brown     | (555) 123-4567 | 4         | 5           |


## Task 2: Web scraping 
Create a web scraper using Selenium to extract the list of courses from the landing page of the mate.academy website. The scraper should gather the following information for each course:
* Course name
* Short description
* Course type (full-time or flex)

Hints:
* Ensure your code adheres to the DRY (Don't Repeat Yourself) and KISS (Keep It Simple, Stupid) principles
* Follow the Single Responsibility Principle (SRP) to keep your code modular and maintainable
* Implement the simplest solution that fulfills the requirements

Optional Task:
Additionally, extract the following details for each course:
* Number of Modules
* Number of Topics
* Course Duration
