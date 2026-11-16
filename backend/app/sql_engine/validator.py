"""IR Validator and Structured Error Handler for QueryMind AI (Member 2 - SQL Engine).

Enforces structural, syntactic, and security validation on Intermediate Representation (IR)
dictionaries before SQL generation.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# Allowed relational and pattern operators
ALLOWED_OPERATORS = {
    "=",
    "!=",
    "<>",
    ">",
    ">=",
    "<",
    "<=",
    "LIKE",
    "ILIKE",
    "IN",
    "NOT IN",
    "IS NULL",
    "IS NOT NULL",
    "LIKE_PREFIX",
    "LIKE_SUFFIX",
}

# Allowed SQL aggregate functions
ALLOWED_AGGREGATES = {
    "COUNT",
    "AVG",
    "SUM",
    "MAX",
    "MIN",
}

# Allowed sort directions
ALLOWED_SORT_DIRECTIONS = {
    "ASC",
    "DESC",
}

# Allowed intents
ALLOWED_INTENTS = {
    "SELECT",
    "FILTER",
    "AGGREGATE",
    # Legacy / prototype synonyms normalized to canonical
    "SELECT_ALL",
    "SORT",
}

# Standard error code definitions
ERROR_INVALID_IR = "INVALID_IR"
ERROR_ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
ERROR_UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
ERROR_SQL_GENERATION_FAILED = "SQL_GENERATION_FAILED"


def make_error(code: str, message: str) -> Dict[str, Any]:
    """Construct a standardized structured error response."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


def is_valid_identifier(identifier: str) -> bool:
    """Validate that an alias or identifier string contains only safe alphanumeric/underscore characters."""
    if not isinstance(identifier, str) or not identifier.strip():
        return False
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", identifier.strip()))


class IRValidator:
    """Validates Intermediate Representation (IR) contracts and constraints."""

    REQUIRED_FIELDS = {
        "intent",
        "table",
        "columns",
        "conditions",
        "joins",
        "aggregations",
        "group_by",
        "order_by",
        "limit",
    }

    def validate_structure(self, ir: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate top-level IR types, required fields, and structural integrity."""
        if not isinstance(ir, dict):
            return False, make_error(ERROR_INVALID_IR, "The provided IR must be a dictionary.")

        # If incoming IR is already marked as a failed NLP response, forward its error
        if ir.get("success") is False and "error" in ir:
            err = ir["error"]
            code = err.get("code", ERROR_INVALID_IR) if isinstance(err, dict) else ERROR_INVALID_IR
            msg = err.get("message", "Upstream NLP processing failed.") if isinstance(err, dict) else str(err)
            return False, make_error(code, msg)

        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(ir.keys())
        if missing_fields:
            return False, make_error(
                ERROR_INVALID_IR,
                f"Missing required IR field(s): {sorted(list(missing_fields))}.",
            )

        # Validate 'table' field
        table = ir.get("table")
        if not isinstance(table, str) or not table.strip():
            return False, make_error(ERROR_INVALID_IR, "IR field 'table' must be a non-empty string.")

        # Validate 'intent' field
        intent = ir.get("intent")
        if not isinstance(intent, str) or intent.strip().upper() not in ALLOWED_INTENTS:
            return False, make_error(
                ERROR_UNSUPPORTED_OPERATION,
                f"Unsupported or invalid intent '{intent}'. Expected one of {sorted(list(ALLOWED_INTENTS))}.",
            )

        # Validate collection types
        if not isinstance(ir.get("columns"), list):
            return False, make_error(ERROR_INVALID_IR, "IR field 'columns' must be a list.")
        if not isinstance(ir.get("conditions"), list):
            return False, make_error(ERROR_INVALID_IR, "IR field 'conditions' must be a list.")
        if not isinstance(ir.get("joins"), list):
            return False, make_error(ERROR_INVALID_IR, "IR field 'joins' must be a list.")
        if not isinstance(ir.get("aggregations"), list):
            return False, make_error(ERROR_INVALID_IR, "IR field 'aggregations' must be a list.")
        if not isinstance(ir.get("group_by"), list):
            return False, make_error(ERROR_INVALID_IR, "IR field 'group_by' must be a list.")
        if not isinstance(ir.get("order_by"), list):
            return False, make_error(ERROR_INVALID_IR, "IR field 'order_by' must be a list.")

        # Validate 'limit' field
        limit = ir.get("limit")
        if limit is not None:
            # Prevent booleans (bool is a subclass of int in Python)
            if isinstance(limit, bool) or not isinstance(limit, int):
                return False, make_error(ERROR_INVALID_IR, f"LIMIT must be an integer, received {type(limit).__name__}.")
            if limit < 1:
                return False, make_error(ERROR_INVALID_IR, f"LIMIT must be a positive integer, received {limit}.")

        return True, None

    def validate_conditions(self, conditions: List[Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate condition clause structures, operators, and parameters."""
        for idx, cond in enumerate(conditions):
            if not isinstance(cond, dict):
                return False, make_error(ERROR_INVALID_IR, f"Condition at index {idx} must be a dictionary.")

            col = cond.get("column")
            if not isinstance(col, str) or not col.strip():
                return False, make_error(ERROR_INVALID_IR, f"Condition at index {idx} has invalid or missing 'column'.")

            op = cond.get("operator")
            if not isinstance(op, str) or not op.strip():
                return False, make_error(ERROR_INVALID_IR, f"Condition at index {idx} has invalid or missing 'operator'.")

            op_normalized = op.strip().upper()
            if op_normalized not in ALLOWED_OPERATORS:
                return False, make_error(
                    ERROR_UNSUPPORTED_OPERATION,
                    f"Unsupported operator '{op}' in condition for column '{col}'.",
                )

            val = cond.get("value")
            # Special check for IN / NOT IN
            if op_normalized in {"IN", "NOT IN"}:
                if not isinstance(val, (list, tuple)) or len(val) == 0:
                    return False, make_error(
                        ERROR_INVALID_IR,
                        f"Operator '{op_normalized}' requires a non-empty list of values for column '{col}'.",
                    )

            # Prohibit raw nested dictionary injections in values
            if isinstance(val, dict):
                return False, make_error(
                    ERROR_INVALID_IR,
                    f"Condition value for column '{col}' cannot be a complex object.",
                )

        return True, None

    def validate_aggregations(self, aggregations: List[Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate aggregate functions, column targets, and aliases."""
        for idx, agg in enumerate(aggregations):
            if not isinstance(agg, dict):
                return False, make_error(ERROR_INVALID_IR, f"Aggregation at index {idx} must be a dictionary.")

            func = agg.get("function")
            if not isinstance(func, str) or func.strip().upper() not in ALLOWED_AGGREGATES:
                return False, make_error(
                    ERROR_UNSUPPORTED_OPERATION,
                    f"Unsupported aggregate function '{func}'. Allowed functions: {sorted(list(ALLOWED_AGGREGATES))}.",
                )

            col = agg.get("column")
            if not isinstance(col, str) or not col.strip():
                return False, make_error(ERROR_INVALID_IR, f"Aggregation at index {idx} has invalid 'column'.")

            # Check alias
            alias = agg.get("alias")
            if alias is not None:
                if not is_valid_identifier(alias):
                    return False, make_error(
                        ERROR_INVALID_IR,
                        f"Invalid aggregation alias '{alias}'. Must be a safe SQL identifier.",
                    )

        return True, None

    def validate_order_by(self, order_by: List[Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate ORDER BY elements and sort directions."""
        for idx, item in enumerate(order_by):
            if not isinstance(item, dict):
                return False, make_error(ERROR_INVALID_IR, f"ORDER BY entry at index {idx} must be an object.")

            col = item.get("column")
            if not isinstance(col, str) or not col.strip():
                return False, make_error(ERROR_INVALID_IR, f"ORDER BY entry at index {idx} has invalid 'column'.")

            direction = item.get("direction", "ASC")
            if not isinstance(direction, str) or direction.strip().upper() not in ALLOWED_SORT_DIRECTIONS:
                return False, make_error(
                    ERROR_INVALID_IR,
                    f"Invalid ORDER BY direction '{direction}'. Allowed: ASC, DESC.",
                )

        return True, None
