"""Mock NLP Module for QueryMind AI (Presentation & Offline Prototype).

DISCLAIMER:
-----------
This module is a deterministic MOCK implementation created for offline
demonstration, architectural integration, and presentation purposes.
"""

import re
from typing import Any, Dict, List


def process_natural_language(query: str) -> Dict[str, Any]:
    """Parse natural language query into an Intermediate Representation (IR) for mock presentation."""
    normalized = query.strip().lower()

    # Pattern A: Average CGPA by department / department-wise
    if ("average" in normalized or "avg" in normalized) and "cgpa" in normalized and "department" in normalized:
        return {
            "intent": "AGGREGATE",
            "table": "students",
            "columns": ["department", "AVG(cgpa) AS avg_cgpa"],
            "conditions": [],
            "aggregations": [{"function": "AVG", "column": "cgpa", "alias": "avg_cgpa"}],
            "group_by": ["department"],
            "order_by": "avg_cgpa DESC",
            "limit": None,
        }

    # Pattern B: Overall average CGPA
    if ("average" in normalized or "avg" in normalized) and "cgpa" in normalized:
        return {
            "intent": "AGGREGATE",
            "table": "students",
            "columns": ["ROUND(AVG(cgpa), 2) AS average_cgpa"],
            "conditions": [],
            "aggregations": [{"function": "AVG", "column": "cgpa", "alias": "average_cgpa"}],
            "group_by": [],
            "order_by": None,
            "limit": None,
        }

    # Pattern C: Count students / courses / enrollments
    if ("count" in normalized or "how many" in normalized) and "student" in normalized:
        return {
            "intent": "AGGREGATE",
            "table": "students",
            "columns": ["COUNT(*) AS total_students"],
            "conditions": [],
            "aggregations": [{"function": "COUNT", "column": "*", "alias": "total_students"}],
            "group_by": [],
            "order_by": None,
            "limit": None,
        }

    # Pattern D: Enrollments / student-course JOIN queries
    if "enroll" in normalized or ("student" in normalized and "course" in normalized) or "grade" in normalized:
        conditions: List[Dict[str, Any]] = []
        if "fall 2024" in normalized:
            conditions.append({"column": "semester", "operator": "=", "value": "Fall 2024"})
        elif "spring 2025" in normalized:
            conditions.append({"column": "semester", "operator": "=", "value": "Spring 2025"})
        return {
            "intent": "JOIN",
            "table": "enrollments",
            "columns": ["students.name", "courses.course_name", "enrollments.semester", "enrollments.grade"],
            "conditions": conditions,
            "joins": [
                {"table": "students", "type": "INNER", "left_column": "enrollments.student_id", "right_column": "students.student_id"},
                {"table": "courses", "type": "INNER", "left_column": "enrollments.course_id", "right_column": "courses.course_id"},
            ],
            "order_by": None,
            "limit": 15,
        }

    # Pattern 1: Queries involving sorting / ranking students by CGPA
    if "student" in normalized and (
        "top" in normalized
        or "order" in normalized
        or "highest" in normalized
        or "rank" in normalized
    ):
        limit = 5
        limit_match = re.search(r"top\s+(\d+)", normalized)
        if limit_match:
            limit = max(1, min(int(limit_match.group(1)), 10))
        return {
            "intent": "SORT",
            "table": "students",
            "columns": ["name", "cgpa", "graduation_year"],
            "conditions": [],
            "order_by": "cgpa DESC",
            "limit": limit,
        }

    # Pattern 2: Queries involving students and CGPA / GPA filtering
    if "student" in normalized and ("cgpa" in normalized or "gpa" in normalized):
        threshold = 8.5
        operator = ">"
        below_match = re.search(r"(?:below|less than|<|under|lower than)\s*(\d+(?:\.\d+)?)", normalized)
        above_match = re.search(r"(?:above|greater than|>|higher than|more than)\s*(\d+(?:\.\d+)?)", normalized)
        if below_match:
            operator = "<"
            threshold = float(below_match.group(1))
        elif above_match:
            operator = ">"
            threshold = float(above_match.group(1))

        return {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name", "cgpa"],
            "conditions": [
                {
                    "column": "cgpa",
                    "operator": operator,
                    "value": threshold,
                }
            ],
            "order_by": None,
            "limit": None,
        }

    # Pattern E: Filter students by department (CSE, AI, ECE, IT, ME)
    if "student" in normalized:
        for dept_key, dept_val in [("cse", "CSE"), ("computer science", "CSE"), ("ai", "AI"), ("ece", "ECE"), ("it", "IT")]:
            if re.search(rf"\b{re.escape(dept_key)}\b", normalized):
                return {
                    "intent": "FILTER",
                    "table": "students",
                    "columns": ["student_id", "name", "department", "cgpa"],
                    "conditions": [{"column": "department", "operator": "=", "value": dept_val}],
                    "order_by": "cgpa DESC",
                    "limit": None,
                }

    # Pattern 3: Queries involving courses and credits
    if "course" in normalized:
        conditions = []
        if "credit" in normalized:
            credit_match = re.search(r"(\d+)\s*credit|credit[s]?\s*(?:equal to|=|of)?\s*(\d+)", normalized)
            credit_val = int(credit_match.group(1) or credit_match.group(2)) if credit_match else 4
            conditions.append({"column": "credits", "operator": "=", "value": credit_val})
        else:
            conditions.append({"column": "credits", "operator": "=", "value": 4})

        return {
            "intent": "FILTER",
            "table": "courses",
            "columns": ["course_code", "course_name", "credits"],
            "conditions": conditions,
            "order_by": None,
            "limit": None,
        }

    # Generic Fallback: Default deterministic IR for any other input query
    return {
        "intent": "SELECT_ALL",
        "table": "students",
        "columns": ["id", "name", "department", "cgpa"],
        "conditions": [],
        "order_by": None,
        "limit": 10,
    }
