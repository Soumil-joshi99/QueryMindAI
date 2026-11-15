"""
Comprehensive Test Suite for Member 1 (NLP Module).
Includes:
- Mandatory contract queries (Section 9)
- Multi-hop JOIN queries (students <-> enrollments <-> courses)
- Compound multiple conditions (AND)
- Input validation (500-char limit, script injection, control characters)
- Lemmatization integration
- Ambiguous / out-of-domain query handling (ENTITY_NOT_FOUND)
"""

import unittest
from backend.app.nlp import process_natural_language


class TestMember1NLPModule(unittest.TestCase):
    """Verifies all mandatory test cases and edge cases."""

    # -------------------------------------------------------------------------
    # 1. Mandatory Contract Test Cases (Section 9)
    # -------------------------------------------------------------------------
    def test_01_show_all_students(self):
        """Query: 'Show all students' -> Expected: SELECT"""
        query = "Show all students"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "SELECT")
        self.assertEqual(ir["table"], "students")
        self.assertIn("name", ir["columns"])
        self.assertEqual(ir["conditions"], [])
        self.assertEqual(ir["joins"], [])
        self.assertEqual(ir["aggregations"], [])
        self.assertEqual(ir["group_by"], [])
        self.assertEqual(ir["order_by"], [])
        self.assertIsNone(ir["limit"])

    def test_02_show_students_cgpa_above_8_5(self):
        """Query: 'Show students with CGPA above 8.5' -> Expected: FILTER"""
        query = "Show students with CGPA above 8.5"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "FILTER")
        self.assertEqual(ir["table"], "students")
        self.assertIn("name", ir["columns"])
        self.assertIn("cgpa", ir["columns"])
        self.assertEqual(len(ir["conditions"]), 1)
        self.assertEqual(ir["conditions"][0]["column"], "cgpa")
        self.assertEqual(ir["conditions"][0]["operator"], ">")
        self.assertEqual(ir["conditions"][0]["value"], 8.5)

    def test_03_find_students_from_cse_department(self):
        """Query: 'Find students from CSE department' -> Expected: FILTER"""
        query = "Find students from CSE department"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "FILTER")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["conditions"]), 1)
        self.assertEqual(ir["conditions"][0]["column"], "department")
        self.assertEqual(ir["conditions"][0]["operator"], "=")
        self.assertEqual(ir["conditions"][0]["value"], "CSE")

    def test_04_show_students_descending_cgpa_order(self):
        """Query: 'Show students in descending CGPA order' -> Expected: ORDER BY"""
        query = "Show students in descending CGPA order"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "SELECT")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["order_by"]), 1)
        self.assertEqual(ir["order_by"][0]["column"], "cgpa")
        self.assertEqual(ir["order_by"][0]["direction"], "DESC")
        self.assertIsNone(ir["limit"])

    def test_05_show_top_5_students(self):
        """Query: 'Show the top 5 students' -> Expected: ORDER BY + LIMIT"""
        query = "Show the top 5 students"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "SELECT")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["order_by"]), 1)
        self.assertEqual(ir["order_by"][0]["column"], "cgpa")
        self.assertEqual(ir["order_by"][0]["direction"], "DESC")
        self.assertEqual(ir["limit"], 5)

    def test_06_count_all_students(self):
        """Query: 'Count all students' -> Expected: COUNT (AGGREGATE)"""
        query = "Count all students"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "AGGREGATE")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["aggregations"]), 1)
        self.assertEqual(ir["aggregations"][0]["function"], "COUNT")
        self.assertEqual(ir["aggregations"][0]["column"], "*")

    def test_07_find_average_cgpa(self):
        """Query: 'Find average CGPA' -> Expected: AVG (AGGREGATE)"""
        query = "Find average CGPA"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "AGGREGATE")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["aggregations"]), 1)
        self.assertEqual(ir["aggregations"][0]["function"], "AVG")
        self.assertEqual(ir["aggregations"][0]["column"], "cgpa")

    def test_08_show_students_enrolled_in_each_course_multihop_join(self):
        """
        Query: 'Show students enrolled in each course'
        Expected: Two-hop JOIN:
        1. students -> enrollments
        2. enrollments -> courses
        """
        query = "Show students enrolled in each course"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "SELECT")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["joins"]), 2)
        
        # Hop 1: enrollments
        self.assertEqual(ir["joins"][0]["table"], "enrollments")
        self.assertEqual(ir["joins"][0]["left_column"], "students.student_id")
        self.assertEqual(ir["joins"][0]["right_column"], "enrollments.student_id")

        # Hop 2: courses
        self.assertEqual(ir["joins"][1]["table"], "courses")
        self.assertEqual(ir["joins"][1]["left_column"], "enrollments.course_id")
        self.assertEqual(ir["joins"][1]["right_column"], "courses.course_id")

        # Projection includes student name and course name
        self.assertIn("name", ir["columns"])
        self.assertIn("course_name", ir["columns"])

    def test_09_find_average_cgpa_department_wise(self):
        """Query: 'Find average CGPA department-wise' -> Expected: GROUP BY + AVG"""
        query = "Find average CGPA department-wise"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "AGGREGATE")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["aggregations"]), 1)
        self.assertEqual(ir["aggregations"][0]["function"], "AVG")
        self.assertEqual(ir["group_by"], ["department"])

    # -------------------------------------------------------------------------
    # 2. Edge Cases: Multiple Conditions (Review Point 4)
    # -------------------------------------------------------------------------
    def test_10_multiple_conditions_compound_query(self):
        """Query with compound conditions: CGPA above 8.0 and department CSE"""
        query = "Find students with CGPA above 8.0 and department CSE"
        ir = process_natural_language(query)

        self.assertEqual(ir["intent"], "FILTER")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["conditions"]), 2)

        cols = {c["column"] for c in ir["conditions"]}
        self.assertIn("cgpa", cols)
        self.assertIn("department", cols)

        cgpa_cond = next(c for c in ir["conditions"] if c["column"] == "cgpa")
        self.assertEqual(cgpa_cond["operator"], ">")
        self.assertEqual(cgpa_cond["value"], 8.0)

        dept_cond = next(c for c in ir["conditions"] if c["column"] == "department")
        self.assertEqual(dept_cond["operator"], "=")
        self.assertEqual(dept_cond["value"], "CSE")

    # -------------------------------------------------------------------------
    # 3. Edge Cases: Input Validation (Review Point 2)
    # -------------------------------------------------------------------------
    def test_11_input_validation_empty_query(self):
        """Empty query should return structured UNSUPPORTED_QUERY error."""
        ir = process_natural_language("   ")
        self.assertFalse(ir.get("success", True))
        self.assertEqual(ir["error"]["code"], "UNSUPPORTED_QUERY")

    def test_12_input_validation_500_char_limit(self):
        """Query exceeding 500 characters must be rejected."""
        long_query = "Show students with " + ("high cgpa and " * 50)
        self.assertGreater(len(long_query), 500)
        ir = process_natural_language(long_query)

        self.assertFalse(ir.get("success", True))
        self.assertEqual(ir["error"]["code"], "UNSUPPORTED_QUERY")
        self.assertIn("500 characters", ir["error"]["message"])

    def test_13_input_validation_script_injection(self):
        """Queries containing script or HTML tags must be rejected."""
        malicious = "<script>alert('hack')</script> Show all students"
        ir = process_natural_language(malicious)

        self.assertFalse(ir.get("success", True))
        self.assertEqual(ir["error"]["code"], "UNSUPPORTED_QUERY")
        self.assertIn("disallowed markup", ir["error"]["message"])

    def test_14_input_validation_control_characters(self):
        """Queries containing non-printable control characters must be rejected."""
        control_query = "Show students \x00\x01 with cgpa > 8"
        ir = process_natural_language(control_query)

        self.assertFalse(ir.get("success", True))
        self.assertEqual(ir["error"]["code"], "UNSUPPORTED_QUERY")

    # -------------------------------------------------------------------------
    # 4. Edge Cases: Preprocessing & Lemmatization (Review Point 3)
    # -------------------------------------------------------------------------
    def test_15_lemmatized_entity_extraction(self):
        """Verifies inflected tokens are extracted via lemmatization ('pupils', 'classes')."""
        query = "List all pupils enrolling in classes"
        ir = process_natural_language(query)

        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["joins"]), 2)
        self.assertEqual(ir["joins"][0]["table"], "enrollments")
        self.assertEqual(ir["joins"][1]["table"], "courses")

    # -------------------------------------------------------------------------
    # 5. Edge Cases: Ambiguous & Out-of-Domain Queries (Review Point 4)
    # -------------------------------------------------------------------------
    def test_16_out_of_domain_ambiguous_query(self):
        """Queries not matching any academic domain entities should return ENTITY_NOT_FOUND."""
        query = "Show all airplanes at the international airport"
        ir = process_natural_language(query)

        self.assertFalse(ir.get("success", True))
        self.assertEqual(ir["error"]["code"], "ENTITY_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
