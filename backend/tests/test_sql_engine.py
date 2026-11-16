"""Unit tests for QueryMind AI SQL Engine (Member 2).

Tests basic functionality across:
- Basic SELECT
- Single and multiple WHERE conditions
- Parameter binding
- INNER, LEFT, RIGHT JOINs
- Single-hop and multi-hop relationships
- Aggregations (COUNT, AVG, SUM, MAX, MIN)
- GROUP BY
- Single and multi-column ORDER BY
- LIMIT
- Combined query operations
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.sql_engine import process_ir


class TestSQLEngineCoreFunctionality(unittest.TestCase):
    """Test suite covering all functional query generation capabilities."""

    def test_01_basic_select_explicit_columns(self):
        """SELECT approved columns from approved base table."""
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": ["name", "cgpa"],
            "conditions": [],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(res["generated_sql"], "SELECT students.name, students.cgpa FROM students")
        self.assertEqual(res["params"], {})

    def test_02_basic_select_all_columns(self):
        """SELECT * or empty columns expands to approved table columns."""
        ir = {
            "intent": "SELECT",
            "table": "courses",
            "columns": ["*"],
            "conditions": [],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertIn("SELECT courses.course_id, courses.course_name, courses.credits, courses.department FROM courses", res["generated_sql"])
        self.assertEqual(res["params"], {})

    def test_03_single_where_condition(self):
        """SELECT with single WHERE comparison condition and parameterized value."""
        ir = {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name", "cgpa"],
            "conditions": [
                {"column": "cgpa", "operator": ">", "value": 8.5}
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT students.name, students.cgpa FROM students WHERE students.cgpa > :p0",
        )
        self.assertEqual(res["params"], {"p0": 8.5})

    def test_04_multiple_where_conditions(self):
        """SELECT with multiple WHERE conditions combined via AND with distinct parameters."""
        ir = {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name", "cgpa", "department"],
            "conditions": [
                {"column": "cgpa", "operator": ">=", "value": 8.0},
                {"column": "department", "operator": "=", "value": "CSE"},
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT students.name, students.cgpa, students.department FROM students WHERE students.cgpa >= :p0 AND students.department = :p1",
        )
        self.assertEqual(res["params"], {"p0": 8.0, "p1": "CSE"})

    def test_05_where_null_operators(self):
        """SELECT with IS NULL and IS NOT NULL conditions."""
        ir = {
            "intent": "FILTER",
            "table": "enrollments",
            "columns": ["enrollment_id", "grade"],
            "conditions": [
                {"column": "grade", "operator": "IS NULL", "value": None},
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT enrollments.enrollment_id, enrollments.grade FROM enrollments WHERE enrollments.grade IS NULL",
        )
        self.assertEqual(res["params"], {})

    def test_06_where_in_operator(self):
        """SELECT with IN operator expanding into multiple bound parameters."""
        ir = {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name", "department"],
            "conditions": [
                {"column": "department", "operator": "IN", "value": ["CSE", "AI"]},
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT students.name, students.department FROM students WHERE students.department IN (:p0, :p1)",
        )
        self.assertEqual(res["params"], {"p0": "CSE", "p1": "AI"})

    def test_07_where_like_operators(self):
        """SELECT with LIKE, LIKE_PREFIX, and LIKE_SUFFIX operators."""
        ir = {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name"],
            "conditions": [
                {"column": "name", "operator": "LIKE_PREFIX", "value": "Aa"},
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT students.name FROM students WHERE students.name LIKE :p0",
        )
        self.assertEqual(res["params"], {"p0": "Aa%"})

    def test_08_inner_join_single_hop(self):
        """Single-hop INNER JOIN between students and enrollments."""
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": ["name", "grade"],
            "conditions": [],
            "joins": [
                {
                    "table": "enrollments",
                    "type": "INNER",
                    "left_column": "students.student_id",
                    "right_column": "enrollments.student_id",
                }
            ],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT students.name, enrollments.grade FROM students INNER JOIN enrollments ON students.student_id = enrollments.student_id",
        )

    def test_09_left_and_right_joins(self):
        """LEFT JOIN and RIGHT JOIN support."""
        ir_left = {
            "intent": "SELECT",
            "table": "courses",
            "columns": ["course_name", "grade"],
            "conditions": [],
            "joins": [
                {
                    "table": "enrollments",
                    "type": "LEFT",
                    "left_column": "courses.course_id",
                    "right_column": "enrollments.course_id",
                }
            ],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir_left)
        self.assertTrue(res["success"])
        self.assertIn("LEFT JOIN enrollments ON courses.course_id = enrollments.course_id", res["generated_sql"])

    def test_10_multi_hop_join(self):
        """Two-hop JOIN connecting students -> enrollments -> courses."""
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": ["name", "course_name"],
            "conditions": [],
            "joins": [
                {
                    "table": "enrollments",
                    "type": "INNER",
                    "left_column": "students.student_id",
                    "right_column": "enrollments.student_id",
                },
                {
                    "table": "courses",
                    "type": "INNER",
                    "left_column": "enrollments.course_id",
                    "right_column": "courses.course_id",
                },
            ],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        expected_sql = (
            "SELECT students.name, courses.course_name "
            "FROM students "
            "INNER JOIN enrollments ON students.student_id = enrollments.student_id "
            "INNER JOIN courses ON enrollments.course_id = courses.course_id"
        )
        self.assertEqual(res["generated_sql"], expected_sql)

    def test_11_aggregation_count_all(self):
        """COUNT(*) aggregation query."""
        ir = {
            "intent": "AGGREGATE",
            "table": "students",
            "columns": [],
            "conditions": [],
            "joins": [],
            "aggregations": [
                {"function": "COUNT", "column": "*", "alias": "total_count"}
            ],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(res["generated_sql"], "SELECT COUNT(*) AS total_count FROM students")

    def test_12_aggregations_avg_sum_max_min(self):
        """AVG, SUM, MAX, MIN aggregations with aliases."""
        for func, expected_alias in [
            ("AVG", "avg_cgpa"),
            ("SUM", "sum_cgpa"),
            ("MAX", "max_cgpa"),
            ("MIN", "min_cgpa"),
        ]:
            ir = {
                "intent": "AGGREGATE",
                "table": "students",
                "columns": [],
                "conditions": [],
                "joins": [],
                "aggregations": [
                    {"function": func, "column": "cgpa", "alias": expected_alias}
                ],
                "group_by": [],
                "order_by": [],
                "limit": None,
            }
            res = process_ir(ir)
            self.assertTrue(res["success"], f"Failed for aggregate {func}")
            self.assertEqual(
                res["generated_sql"],
                f"SELECT {func}(students.cgpa) AS {expected_alias} FROM students",
            )

    def test_13_group_by_with_aggregation(self):
        """GROUP BY department with AVG(cgpa)."""
        ir = {
            "intent": "AGGREGATE",
            "table": "students",
            "columns": ["department"],
            "conditions": [],
            "joins": [],
            "aggregations": [
                {"function": "AVG", "column": "cgpa", "alias": "average_cgpa"}
            ],
            "group_by": ["department"],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT students.department, AVG(students.cgpa) AS average_cgpa FROM students GROUP BY students.department",
        )

    def test_14_single_and_multi_column_order_by(self):
        """Single and multiple column ORDER BY with ASC/DESC directions."""
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": ["name", "cgpa"],
            "conditions": [],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [
                {"column": "cgpa", "direction": "DESC"},
                {"column": "name", "direction": "ASC"},
            ],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(
            res["generated_sql"],
            "SELECT students.name, students.cgpa FROM students ORDER BY students.cgpa DESC, students.name ASC",
        )

    def test_15_limit_clause(self):
        """LIMIT clause with strictly validated integer."""
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": ["name"],
            "conditions": [],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": 5,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertEqual(res["generated_sql"], "SELECT students.name FROM students LIMIT 5")

    def test_16_combined_all_operations(self):
        """Combined: WHERE + JOIN + GROUP BY + Aggregation + ORDER BY + LIMIT."""
        ir = {
            "intent": "AGGREGATE",
            "table": "students",
            "columns": ["department"],
            "conditions": [
                {"column": "batch", "operator": ">=", "value": 2024}
            ],
            "joins": [
                {
                    "table": "enrollments",
                    "type": "INNER",
                    "left_column": "students.student_id",
                    "right_column": "enrollments.student_id",
                }
            ],
            "aggregations": [
                {"function": "AVG", "column": "cgpa", "alias": "dept_avg_cgpa"}
            ],
            "group_by": ["department"],
            "order_by": [
                {"column": "department", "direction": "ASC"}
            ],
            "limit": 10,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        expected_sql = (
            "SELECT students.department, AVG(students.cgpa) AS dept_avg_cgpa "
            "FROM students "
            "INNER JOIN enrollments ON students.student_id = enrollments.student_id "
            "WHERE students.batch >= :p0 "
            "GROUP BY students.department "
            "ORDER BY students.department ASC "
            "LIMIT 10"
        )
        self.assertEqual(res["generated_sql"], expected_sql)
        self.assertEqual(res["params"], {"p0": 2024})


if __name__ == "__main__":
    unittest.main()
