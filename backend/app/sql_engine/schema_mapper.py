"""Schema Mapper and Catalog for QueryMind AI (Member 2 - SQL Engine).

Provides strict allowlists of database tables, columns, data types,
primary keys, foreign keys, and relational connectivity based on the
PostgreSQL academic schema.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


# Strict catalog of approved tables, columns, and data types
APPROVED_SCHEMA: Dict[str, Dict[str, Any]] = {
    "students": {
        "columns": {
            "student_id": "INTEGER",
            "name": "VARCHAR",
            "batch": "INTEGER",
            "cgpa": "FLOAT",
            "department": "VARCHAR",
        },
        "primary_key": "student_id",
        "foreign_keys": {},
    },
    "courses": {
        "columns": {
            "course_id": "INTEGER",
            "course_name": "VARCHAR",
            "credits": "INTEGER",
            "department": "VARCHAR",
        },
        "primary_key": "course_id",
        "foreign_keys": {},
    },
    "enrollments": {
        "columns": {
            "enrollment_id": "INTEGER",
            "student_id": "INTEGER",
            "course_id": "INTEGER",
            "semester": "VARCHAR",
            "grade": "VARCHAR",
        },
        "primary_key": "enrollment_id",
        "foreign_keys": {
            "student_id": ("students", "student_id"),
            "course_id": ("courses", "course_id"),
        },
    },
}

# Known bidirectional relationships for join validation
KNOWN_RELATIONSHIPS: List[Dict[str, str]] = [
    {
        "table_a": "students",
        "column_a": "student_id",
        "table_b": "enrollments",
        "column_b": "student_id",
    },
    {
        "table_a": "courses",
        "column_a": "course_id",
        "table_b": "enrollments",
        "column_b": "course_id",
    },
]


class SchemaMapper:
    """Manages schema validation and column/table resolution."""

    def __init__(self, schema: Optional[Dict[str, Dict[str, Any]]] = None):
        self.schema = schema or APPROVED_SCHEMA
        self.relationships = KNOWN_RELATIONSHIPS

    def is_valid_table(self, table_name: str) -> bool:
        """Check if a table name is in the approved schema."""
        if not isinstance(table_name, str):
            return False
        return table_name.lower() in self.schema

    def is_valid_column(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in the specified approved table."""
        if not self.is_valid_table(table_name) or not isinstance(column_name, str):
            return False
        return column_name.lower() in self.schema[table_name.lower()]["columns"]

    def get_table_columns(self, table_name: str) -> List[str]:
        """Return list of valid column names for an approved table."""
        if not self.is_valid_table(table_name):
            return []
        return list(self.schema[table_name.lower()]["columns"].keys())

    def split_qualified_identifier(self, identifier: str) -> Tuple[Optional[str], str]:
        """Split 'table.column' into (table, column) or return (None, column)."""
        if not isinstance(identifier, str):
            return None, ""
        parts = identifier.strip().split(".")
        if len(parts) == 2:
            return parts[0].strip().lower(), parts[1].strip().lower()
        return None, identifier.strip().lower()

    def resolve_column(
        self,
        column_identifier: str,
        available_tables: List[str],
        default_table: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Resolve a column identifier (qualified or unqualified) to (is_valid, table, column, error_msg).

        Returns:
            (is_valid, table_name, column_name, error_message)
        """
        table_prefix, col_name = self.split_qualified_identifier(column_identifier)

        if not col_name:
            return False, None, None, f"Empty or invalid column identifier: '{column_identifier}'"

        # Explicitly qualified: table.column
        if table_prefix:
            if not self.is_valid_table(table_prefix):
                return (
                    False,
                    None,
                    None,
                    f"Table '{table_prefix}' in '{column_identifier}' is not an approved schema entity.",
                )
            if table_prefix not in [t.lower() for t in available_tables]:
                return (
                    False,
                    None,
                    None,
                    f"Table '{table_prefix}' in '{column_identifier}' is not part of the active query tables.",
                )
            if not self.is_valid_column(table_prefix, col_name):
                return (
                    False,
                    None,
                    None,
                    f"Column '{col_name}' does not exist on table '{table_prefix}'.",
                )
            return True, table_prefix, col_name, None

        # Unqualified: col_name -> check against available tables
        matches = []
        for t in available_tables:
            t_lower = t.lower()
            if self.is_valid_column(t_lower, col_name):
                matches.append(t_lower)

        if len(matches) == 1:
            return True, matches[0], col_name, None

        if len(matches) > 1:
            # If default_table is one of the matches, disambiguate
            if default_table and default_table.lower() in matches:
                return True, default_table.lower(), col_name, None
            return (
                False,
                None,
                None,
                f"Column '{col_name}' is ambiguous across query tables: {matches}. Please qualify it.",
            )

        # No matches found
        target_t = default_table or (available_tables[0] if available_tables else "unknown")
        return (
            False,
            None,
            None,
            f"Column '{col_name}' does not exist in approved schema for active tables {available_tables}.",
        )

    def validate_join_connection(
        self,
        base_table: str,
        joined_tables: List[str],
        join_spec: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Validate that a join definition is syntactically and relationally valid.

        Verifies:
        - Join type is approved (INNER, LEFT, RIGHT).
        - Join table is approved and not already joined.
        - Left and right columns exist in the approved schema.
        - The join connects to an already-present table in the query.
        """
        join_type = str(join_spec.get("type", "INNER")).upper()
        if join_type not in {"INNER", "LEFT", "RIGHT"}:
            return False, f"Unsupported JOIN type '{join_type}'. Allowed types: INNER, LEFT, RIGHT."

        target_table = join_spec.get("table")
        if not target_table or not isinstance(target_table, str):
            return False, "Join target table must be a non-empty string."

        target_table_clean = target_table.strip().lower()
        if not self.is_valid_table(target_table_clean):
            return False, f"Joined table '{target_table}' is not in the approved schema."

        active_tables = [base_table.lower()] + [t.lower() for t in joined_tables]
        if target_table_clean in active_tables:
            return False, f"Table '{target_table_clean}' is already included in the query."

        left_col = join_spec.get("left_column")
        right_col = join_spec.get("right_column")

        if not left_col or not right_col:
            return False, "Join specification must include both 'left_column' and 'right_column'."

        left_tbl, left_name = self.split_qualified_identifier(left_col)
        right_tbl, right_name = self.split_qualified_identifier(right_col)

        if not left_tbl or not right_tbl:
            return False, "Join columns must be fully qualified (e.g. 'table.column')."

        if not self.is_valid_table(left_tbl):
            return False, f"Table '{left_tbl}' in left join column '{left_col}' is invalid."
        if not self.is_valid_column(left_tbl, left_name):
            return False, f"Column '{left_name}' does not exist on table '{left_tbl}'."

        if not self.is_valid_table(right_tbl):
            return False, f"Table '{right_tbl}' in right join column '{right_col}' is invalid."
        if not self.is_valid_column(right_tbl, right_name):
            return False, f"Column '{right_name}' does not exist on table '{right_tbl}'."

        # Verify that one side belongs to already active tables and the other side belongs to the new table
        all_tables_in_join = {left_tbl, right_tbl}
        if target_table_clean not in all_tables_in_join:
            return (
                False,
                f"Join condition does not reference joined table '{target_table_clean}' (references {all_tables_in_join}).",
            )

        connecting_tables = all_tables_in_join - {target_table_clean}
        if not connecting_tables.intersection(set(active_tables)):
            return (
                False,
                f"Disconnected join: table '{target_table_clean}' does not connect to any active query table {active_tables}.",
            )

        return True, None
