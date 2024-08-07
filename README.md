# Mate Academy Test Assignment
## Task 1: SQL queries
There are next tables: users, leads, domains, courses.

Prepare SQL queries to select the next data:

1.1. The number of created leads per week grouped by course type

1.2. The number of WON flex leads per country created from 01.01.2024

1.3. User email, lead id and lost reason for users who have lost flex leads from 01.07.2024

Table schemas:

_users_
| id  | email               | first_name | last_name | phone          | domain_id | language_id |
|-----|---------------------|------------|-----------|--------------- |-----------|-------------|
| 35  | jsmith@example.com  | John       | Smith     | (123) 456-7890 | 1         | 1           |
| 47  | ldoe@example.com    | Laura      | Doe       | (987) 654-3210 | 1         | 1           |
| 51  | mbrown@example.com  | Michael    | Brown     | (555) 123-4567 | 4         | 5           |

_leads_
| id  | user_id | course_id | created_at                 | updated_at                 | status | lost_reason |
|-----|---------|-----------|--------------------------  |--------------------------  |--------|-------------|
| 10  | 35      | 25        | 2024-01-14 11:17:29.664+00 | 2024-02-26 17:28:13.647+00 | LOST   | NO_CONTACT  |
| 16  | 35      | 38        | 2024-01-13 18:42:38.671+00 | 2024-01-30 12:01:44.473+00 | WON    | null        |
| 45  | 62      | 27        | 2024-01-12 16:49:15.082+00 | 2024-02-13 09:13:07.151+00 | NEW    | null        |

_domains_
| id  | slug | country_name | created_at                    | updated_at                 | active |
|-----|------|--------------|-------------------------------|----------------------------|--------|
| 1   | ua   | Ukraine      | 2023-07-27 09:31:22.147845+00 | 2024-02-26 10:21:53.046+00 | t      |
| 3   | pl   | Poland       | 2023-12-21 09:14:32.8806+00   | 2024-02-15 11:24:51.941+00 | f      |

_courses_
| id  | slug           | type      | language_id | sort |
|-----|----------------|-----------|-------------|------|
| 12  | python_basics  | MODULE    | 1           | 3    |
| 25  | frontend       | FULL_TIME | 1           | 5    |
| 27  | devops         | FLEX      | 1           | 1    |

## Solution for Task 1:
1.1:
```
SELECT 
    DATE_TRUNC('week', l.created_at) AS week,
    c.type AS course_type,
    COUNT(*) AS leads_count
FROM 
    leads l
JOIN 
    courses c ON l.course_id = c.id
GROUP BY 
    week, course_type
ORDER BY 
    week, course_type;
```

1.2:
```
SELECT 
    d.country_name,
    COUNT(*) AS won_flex_leads_count
FROM 
    leads l
JOIN 
    users u ON l.user_id = u.id
JOIN 
    domains d ON u.domain_id = d.id
JOIN 
    courses c ON l.course_id = c.id
WHERE 
    l.status = 'WON' 
    AND c.type = 'FLEX' 
    AND l.created_at >= '2024-01-01'
GROUP BY 
    d.country_name
ORDER BY 
    d.country_name;
```

1.3:
```
SELECT 
    u.email,
    l.id AS lead_id,
    l.lost_reason
FROM 
    leads l
JOIN 
    users u ON l.user_id = u.id
JOIN 
    courses c ON l.course_id = c.id
WHERE 
    l.status = 'LOST' 
    AND c.type = 'FLEX' 
    AND l.created_at >= '2024-07-01'
ORDER BY 
    u.email, l.id;
```

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
