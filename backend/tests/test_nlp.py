"""
Backend Unit & Integration Test Suite for NLP Module (Member 1).
"""

import sys
import os
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.nlp import process_natural_language


class TestNLPIntegration(unittest.TestCase):
    def test_sample_query_filter(self):
        query = "Show students with CGPA above 8.5"
        ir = process_natural_language(query)
        self.assertEqual(ir["intent"], "FILTER")
        self.assertEqual(ir["table"], "students")
        self.assertEqual(ir["conditions"][0]["column"], "cgpa")
        self.assertEqual(ir["conditions"][0]["operator"], ">")
        self.assertEqual(ir["conditions"][0]["value"], 8.5)

    def test_multihop_join(self):
        query = "Show students enrolled in each course"
        ir = process_natural_language(query)
        self.assertEqual(ir["table"], "students")
        self.assertEqual(len(ir["joins"]), 2)
        self.assertEqual(ir["joins"][0]["table"], "enrollments")
        self.assertEqual(ir["joins"][1]["table"], "courses")

    def test_input_validation_limit_500(self):
        long_query = "Find students with " + ("marks > 8 and " * 50)
        ir = process_natural_language(long_query)
        self.assertFalse(ir.get("success", True))
        self.assertEqual(ir["error"]["code"], "UNSUPPORTED_QUERY")

    def test_out_of_domain_entity(self):
        query = "Show all rockets launched into orbit"
        ir = process_natural_language(query)
        self.assertFalse(ir.get("success", True))
        self.assertEqual(ir["error"]["code"], "ENTITY_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
