"""Mock SQL Engine for QueryMind AI (Presentation & Offline Prototype).

DISCLAIMER:
-----------
This module is a deterministic MOCK implementation designed for offline
presentations, full-stack wiring, and contract verification. It does NOT connect
to PostgreSQL or run live SQL queries against a physical database.
"""

from typing import Any, Dict, List


# Rich deterministic mock datasets for offline presentations
MOCK_DATASETS: Dict[str, Dict[str, Any]] = {
    "students_cgpa_filter": {
        "columns": ["name", "cgpa"],
        "rows": [
            ["Aarav", 9.1],
            ["Diya", 8.8],
            ["Kabir", 8.7],
        ],
    },
    "students_sorted": {
        "columns": ["name", "cgpa", "graduation_year"],
        "rows": [
            ["Aarav Sharma", 9.1, 2025],
            ["Diya Patel", 8.8, 2024],
            ["Kabir Mehta", 8.7, 2025],
            ["Rohan Verma", 8.4, 2024],
            ["Ananya Gupta", 8.2, 2025],
        ],
    },
    "students_full": {
        "columns": ["student_id", "name", "department", "cgpa"],
        "rows": [
            [1, "Aarav Sharma", "CSE", 9.1],
            [2, "Diya Patel", "AI", 8.8],
            [3, "Kabir Mehta", "CSE", 8.7],
            [4, "Meera Nair", "AI", 8.5],
            [5, "Rohan Verma", "ECE", 8.4],
            [6, "Ananya Gupta", "CSE", 8.2],
            [7, "Vikram Singh", "ECE", 7.9],
            [8, "Ishita Rao", "AI", 9.3],
        ],
    },
    "courses_filter": {
        "columns": ["course_code", "course_name", "credits"],
        "rows": [
            ["CS101", "Introduction to Computer Science", 4],
            ["CS201", "Data Structures & Algorithms", 4],
            ["CS301", "Database Management Systems", 4],
            ["CS401", "Artificial Intelligence", 4],
        ],
    },
    "courses_three_credits": {
        "columns": ["course_code", "course_name", "credits"],
        "rows": [
            ["AI202", "Natural Language Processing", 3],
            ["EC205", "Digital Signal Processing", 3],
            ["AI304", "Machine Learning Foundations", 3],
        ],
    },
    "enrollments_joined": {
        "columns": ["student_name", "course_name", "semester", "grade"],
        "rows": [
            ["Aarav Sharma", "Database Management Systems", "Fall 2024", "A"],
            ["Aarav Sharma", "Natural Language Processing", "Spring 2025", "A+"],
            ["Diya Patel", "Artificial Intelligence", "Fall 2024", "A"],
            ["Diya Patel", "Data Structures & Algorithms", "Spring 2025", "A"],
            ["Kabir Mehta", "Database Management Systems", "Fall 2024", "B+"],
            ["Ishita Rao", "Machine Learning Foundations", "Fall 2024", "A+"],
            ["Rohan Verma", "Digital Signal Processing", "Fall 2024", "A-"],
        ],
    },
    "dept_avg_cgpa": {
        "columns": ["department", "avg_cgpa"],
        "rows": [
            ["AI", 8.87],
            ["CSE", 8.67],
            ["ECE", 8.15],
        ],
    },
    "default_students": {
        "columns": ["id", "name", "department", "cgpa"],
        "rows": [
            [1, "Aarav Sharma", "Computer Science", 9.1],
            [2, "Diya Patel", "Computer Science", 8.8],
            [3, "Kabir Mehta", "Electrical Engineering", 8.7],
            [4, "Rohan Verma", "Mechanical Engineering", 8.4],
            [5, "Ananya Gupta", "Information Technology", 8.2],
        ],
    },
}


def _build_mock_sql(ir: Dict[str, Any]) -> str:
    """Construct deterministic ANSI SQL from Intermediate Representation (IR)."""
    columns = ", ".join(ir.get("columns", ["*"]))
    table = ir.get("table", "students")
    sql = f"SELECT {columns} FROM {table}"

    joins = ir.get("joins", [])
    if joins:
        for j in joins:
            j_type = j.get("type", "INNER")
            j_tbl = j.get("table")
            left_col = j.get("left_column")
            right_col = j.get("right_column")
            sql += f" {j_type} JOIN {j_tbl} ON {left_col} = {right_col}"

    conditions = ir.get("conditions", [])
    if conditions:
        clause_parts: List[str] = []
        for cond in conditions:
            col = cond.get("column")
            op = cond.get("operator")
            val = cond.get("value")
            val_str = str(val) if isinstance(val, (int, float)) else f"'{val}'"
            clause_parts.append(f"{col} {op} {val_str}")
        sql += f" WHERE {' AND '.join(clause_parts)}"

    group_by = ir.get("group_by", [])
    if group_by:
        sql += f" GROUP BY {', '.join(group_by)}"

    if ir.get("order_by"):
        sql += f" ORDER BY {ir['order_by']}"

    if ir.get("limit"):
        sql += f" LIMIT {ir['limit']}"

    return f"{sql};"


def process_ir(ir: Dict[str, Any]) -> Dict[str, Any]:
    """Translate an Intermediate Representation (IR) into SQL and return mock execution results."""
    generated_sql = _build_mock_sql(ir)

    table = ir.get("table", "students")
    intent = ir.get("intent", "SELECT_ALL")
    conditions = ir.get("conditions", [])
    aggregations = ir.get("aggregations", [])
    group_by = ir.get("group_by", [])
    limit = ir.get("limit")

    # 1. Aggregations
    if intent == "AGGREGATE" and aggregations:
        if group_by and "department" in group_by:
            columns = MOCK_DATASETS["dept_avg_cgpa"]["columns"]
            rows = MOCK_DATASETS["dept_avg_cgpa"]["rows"]
        elif aggregations[0].get("function") == "COUNT":
            columns = ["total_students"]
            rows = [[8]]
        else:
            columns = ["average_cgpa"]
            rows = [[8.60]]

    # 2. Multi-table JOINs (enrollments)
    elif table == "enrollments" or intent == "JOIN":
        columns = MOCK_DATASETS["enrollments_joined"]["columns"]
        rows = MOCK_DATASETS["enrollments_joined"]["rows"]
        for cond in conditions:
            if cond.get("column") == "semester":
                rows = [r for r in rows if r[2] == cond.get("value")]

    # 3. Student CGPA filtering
    elif table == "students" and conditions and any(c.get("column") == "cgpa" for c in conditions):
        cond = next(c for c in conditions if c.get("column") == "cgpa")
        op = cond.get("operator")
        val = cond.get("value")
        # Preserve exact legacy Day 2 fixture for cgpa > 8.5
        if op == ">" and val == 8.5:
            columns = MOCK_DATASETS["students_cgpa_filter"]["columns"]
            rows = MOCK_DATASETS["students_cgpa_filter"]["rows"]
        else:
            columns = ["name", "cgpa"]
            all_students = [[r[1], r[3]] for r in MOCK_DATASETS["students_full"]["rows"]]
            if op == ">":
                rows = [r for r in all_students if r[1] > val]
            elif op == "<":
                rows = [r for r in all_students if r[1] < val]
            else:
                rows = all_students

    # 4. Student Department filtering
    elif table == "students" and conditions and any(c.get("column") == "department" for c in conditions):
        dept = next(c for c in conditions if c.get("column") == "department").get("value")
        columns = MOCK_DATASETS["students_full"]["columns"]
        rows = [r for r in MOCK_DATASETS["students_full"]["rows"] if r[2] == dept]

    # 5. Sorted students
    elif table == "students" and intent == "SORT":
        columns = MOCK_DATASETS["students_sorted"]["columns"]
        rows = MOCK_DATASETS["students_sorted"]["rows"]
        if isinstance(limit, int) and limit > 0:
            rows = rows[:limit]

    # 6. Courses
    elif table == "courses":
        if conditions and conditions[0].get("column") == "credits" and conditions[0].get("value") == 3:
            columns = MOCK_DATASETS["courses_three_credits"]["columns"]
            rows = MOCK_DATASETS["courses_three_credits"]["rows"]
        else:
            columns = MOCK_DATASETS["courses_filter"]["columns"]
            rows = MOCK_DATASETS["courses_filter"]["rows"]

    # 7. Default fallback
    else:
        columns = MOCK_DATASETS["default_students"]["columns"]
        rows = MOCK_DATASETS["default_students"]["rows"]

    execution_payload = {
        "status": "mock_success",
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "execution_time_ms": 12,
    }

    return {
        "generated_sql": generated_sql,
        "execution": execution_payload,
    }
