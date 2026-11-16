"""Security and injection vulnerability tests for SQL Engine (Member 2)."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.sql_engine import process_ir


class TestSQLEngineSecurity(unittest.TestCase):
    """Verifies that SQL generation is impervious to SQL injection and enforces read-only semantics."""

    def test_01_sql_injection_in_condition_value(self):
        """Classic SQL injection payload in WHERE condition must be parameterized, not interpolated."""
        malicious_value = "' OR '1'='1"
        ir = {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name"],
            "conditions": [
                {"column": "department", "operator": "=", "value": malicious_value}
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        # Generated SQL must contain parameter placeholder, not the injected text
        self.assertNotIn("' OR '1'='1", res["generated_sql"])
        self.assertIn("students.department = :p0", res["generated_sql"])
        self.assertEqual(res["params"]["p0"], malicious_value)

    def test_02_drop_table_injection_in_condition_value(self):
        """Semicolon stacked statement injection in value must be parameterized safely."""
        malicious_value = "CSE'; DROP TABLE students; --"
        ir = {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name"],
            "conditions": [
                {"column": "department", "operator": "=", "value": malicious_value}
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        self.assertNotIn("DROP TABLE", res["generated_sql"])
        self.assertIn("students.department = :p0", res["generated_sql"])
        self.assertEqual(res["params"]["p0"], malicious_value)

    def test_03_malicious_table_name_rejected(self):
        """Malicious table name with stacked SQL statement must be rejected by schema mapper."""
        malicious_table = "students; DROP TABLE courses; --"
        ir = {
            "intent": "SELECT",
            "table": malicious_table,
            "columns": ["name"],
            "conditions": [],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "ENTITY_NOT_FOUND")

    def test_04_malicious_column_name_rejected(self):
        """Malicious column name with inline comment or UNION injection must be rejected."""
        malicious_column = "name FROM students UNION SELECT password FROM users --"
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": [malicious_column],
            "conditions": [],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "ENTITY_NOT_FOUND")

    def test_05_malicious_operator_rejected(self):
        """Malicious operator attempting injection must be rejected."""
        malicious_op = "= 1; DELETE FROM students WHERE 1=1 OR 1="
        ir = {
            "intent": "FILTER",
            "table": "students",
            "columns": ["name"],
            "conditions": [
                {"column": "cgpa", "operator": malicious_op, "value": 8.5}
            ],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "UNSUPPORTED_OPERATION")

    def test_06_malicious_join_identifier_rejected(self):
        """Malicious table or column in JOIN specification must be rejected."""
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": ["name"],
            "conditions": [],
            "joins": [
                {
                    "table": "courses",
                    "type": "INNER",
                    "left_column": "students.student_id; DROP TABLE students;",
                    "right_column": "courses.course_id",
                }
            ],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertFalse(res["success"])

    def test_07_malicious_alias_injection_rejected(self):
        """Malicious aggregation alias with SQL injection characters must be rejected."""
        malicious_alias = "val FROM students; UPDATE students SET cgpa = 10; --"
        ir = {
            "intent": "AGGREGATE",
            "table": "students",
            "columns": [],
            "conditions": [],
            "joins": [],
            "aggregations": [
                {"function": "AVG", "column": "cgpa", "alias": malicious_alias}
            ],
            "group_by": [],
            "order_by": [],
            "limit": None,
        }
        res = process_ir(ir)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "INVALID_IR")

    def test_08_strictly_read_only_select(self):
        """Generated SQL must strictly start with SELECT and never contain mutation keywords."""
        ir = {
            "intent": "SELECT",
            "table": "students",
            "columns": ["name", "cgpa"],
            "conditions": [{"column": "cgpa", "operator": ">", "value": 7.0}],
            "joins": [],
            "aggregations": [],
            "group_by": [],
            "order_by": [],
            "limit": 10,
        }
        res = process_ir(ir)
        self.assertTrue(res["success"])
        sql = res["generated_sql"].upper()
        self.assertTrue(sql.startswith("SELECT"))

        for forbidden in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]:
            self.assertNotRegex(sql, rf"\b{forbidden}\b")


if __name__ == "__main__":
    unittest.main()
