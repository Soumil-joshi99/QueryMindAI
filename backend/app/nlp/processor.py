"""
NLP Processor for QueryMind AI (Member 1 - NLP Module).
Implements the core public interface required by Team Integration Contract Version 1.0:
    process_natural_language(query: str) -> dict
"""

import re
from typing import Dict, Any
from .preprocessing import TextPreprocessor
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor


class NLPProcessor:
    """Orchestrates natural language processing pipeline to construct Canonical IR."""

    MAX_QUERY_LENGTH = 500
    MIN_QUERY_LENGTH = 3

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()

    def validate_input(self, query: str) -> Dict[str, Any]:
        """
        Validates raw input query against contract constraints.
        Returns a dict with 'is_valid': bool and 'error': Optional[dict].
        """
        # 1. Check for empty or whitespace-only query
        if not query or not query.strip():
            return {
                "is_valid": False,
                "error": {
                    "code": "UNSUPPORTED_QUERY",
                    "message": "Input query cannot be empty or whitespace."
                }
            }

        # 2. Check maximum length (500 characters)
        if len(query) > self.MAX_QUERY_LENGTH:
            return {
                "is_valid": False,
                "error": {
                    "code": "UNSUPPORTED_QUERY",
                    "message": f"Query exceeds maximum allowed limit of {self.MAX_QUERY_LENGTH} characters."
                }
            }

        # 3. Check for disallowed script or HTML markup injection
        if re.search(r"<\s*script[^>]*>|<\s*/\s*script\s*>|<[^>]+>", query, re.IGNORECASE):
            return {
                "is_valid": False,
                "error": {
                    "code": "UNSUPPORTED_QUERY",
                    "message": "Query contains disallowed markup or script injection patterns."
                }
            }

        # 4. Check for non-printable control characters
        if any((ord(c) < 32 and c not in "\t\n\r") or ord(c) == 127 for c in query):
            return {
                "is_valid": False,
                "error": {
                    "code": "UNSUPPORTED_QUERY",
                    "message": "Query contains non-printable control characters."
                }
            }

        # 5. Check minimum length
        cleaned = self.preprocessor.clean_text(query)
        if len(cleaned) < self.MIN_QUERY_LENGTH:
            return {
                "is_valid": False,
                "error": {
                    "code": "UNSUPPORTED_QUERY",
                    "message": f"Query is too short (minimum {self.MIN_QUERY_LENGTH} characters required)."
                }
            }

        return {"is_valid": True, "error": None}

    def process(self, query: str) -> Dict[str, Any]:
        """Processes query string and outputs Canonical IR or structured error."""
        # Step 1: Input validation
        validation = self.validate_input(query)
        if not validation["is_valid"]:
            return {
                "success": False,
                "error": validation["error"]
            }

        cleaned = self.preprocessor.clean_text(query)

        try:
            # Step 2: Full Preprocessing (Tokenization, Lemmatization, POS tagging)
            prep = self.preprocessor.process(cleaned)

            # Step 3: Entity & Slot Extraction leveraging lemmatized output
            table = self.entity_extractor.extract_table(cleaned, prep=prep)
            if not table:
                return {
                    "success": False,
                    "error": {
                        "code": "ENTITY_NOT_FOUND",
                        "message": "No recognized database entities or attributes found in query."
                    }
                }

            columns = self.entity_extractor.extract_columns(cleaned, table, prep=prep)
            conditions = self.entity_extractor.extract_conditions(cleaned, table, prep=prep)
            joins = self.entity_extractor.extract_joins(cleaned, table, prep=prep)
            aggregations = self.entity_extractor.extract_aggregations(cleaned, table, prep=prep)
            group_by = self.entity_extractor.extract_group_by(cleaned, table, prep=prep)
            order_by = self.entity_extractor.extract_order_by(cleaned, table, prep=prep)
            limit = self.entity_extractor.extract_limit(cleaned, prep=prep)

            # Step 4: Intent classification
            intent = self.intent_classifier.classify(
                query=cleaned,
                has_conditions=bool(conditions),
                has_aggregations=bool(aggregations)
            )

            # Step 5: Assemble Canonical Intermediate Representation (Contract Version 1.0)
            ir = {
                "intent": intent,
                "table": table,
                "columns": columns,
                "conditions": conditions,
                "joins": joins,
                "aggregations": aggregations,
                "group_by": group_by,
                "order_by": order_by,
                "limit": limit
            }

            return ir

        except Exception as exc:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_IR",
                    "message": f"Failed to generate IR: {str(exc)}"
                }
            }


# Singleton instance for public function access
_processor_instance = NLPProcessor()


def process_natural_language(query: str) -> dict:
    """
    Public entrypoint function required by Member 1 contract:
    Converts a natural language query into the Canonical Intermediate Representation (IR).

    Args:
        query (str): The plain English input query from user.

    Returns:
        dict: The Canonical IR dictionary matching Version 1.0 of the contract,
              or a structured error dictionary on failure.
    """
    return _processor_instance.process(query)
