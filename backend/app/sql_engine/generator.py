"""SQL Generator for QueryMind AI (Member 2 - SQL Engine).

Converts Canonical Intermediate Representation (IR) into secure, parameterized,
read-only ANSI / PostgreSQL SQL statements.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from .schema_mapper import SchemaMapper
from .validator import (
    IRValidator,
    make_error,
    ERROR_INVALID_IR,
    ERROR_ENTITY_NOT_FOUND,
    ERROR_UNSUPPORTED_OPERATION,
    ERROR_SQL_GENERATION_FAILED,
)


class SQLGenerator:
    """Synthesizes secure, parameterized SQL from validated IR."""

    KNOWN_IR_FIELDS = {
        "intent",
        "table",
        "columns",
        "conditions",
        "joins",
        "aggregations",
        "group_by",
        "order_by",
        "limit",
        # Metadata fields that may be passed by frameworks
        "success",
        "error",
        "original_query",
    }

    def __init__(self, mapper: Optional[SchemaMapper] = None):
        self.mapper = mapper or SchemaMapper()
        self.validator = IRValidator()

    def generate(self, ir: Dict[str, Any]) -> Dict[str, Any]:
        """Core generation method: validates IR and generates parameterized SQL."""
        # 1. Top-level IR structure validation
        is_valid, struct_err = self.validator.validate_structure(ir)
        if not is_valid:
            return struct_err or make_error(ERROR_INVALID_IR, "Invalid IR structure.")

        # 2. Check for unknown non-empty fields to prevent silently ignoring requested clauses
        unknown_fields = set(ir.keys()) - self.KNOWN_IR_FIELDS
        for u_field in unknown_fields:
            val = ir.get(u_field)
            if val is not None and val != [] and val != {}:
                return make_error(
                    ERROR_UNSUPPORTED_OPERATION,
                    f"Unsupported IR field '{u_field}' with active operations is not supported.",
                )

        # 3. Base table validation
        base_table = ir["table"].strip().lower()
        if not self.mapper.is_valid_table(base_table):
            return make_error(
                ERROR_ENTITY_NOT_FOUND,
                f"Table '{base_table}' does not exist in the approved database schema.",
            )

        # 4. Joins validation and resolution
        joins_input = ir.get("joins", [])
        active_tables = [base_table]
        join_clauses = []

        for idx, j_spec in enumerate(joins_input):
            if not isinstance(j_spec, dict):
                return make_error(ERROR_INVALID_IR, f"Join specification at index {idx} must be a dictionary.")

            is_join_valid, join_err = self.mapper.validate_join_connection(
                base_table=base_table,
                joined_tables=active_tables[1:],
                join_spec=j_spec,
            )
            if not is_join_valid:
                err_msg = join_err or "Invalid join specification."
                # Check if it's an unknown/unapproved entity error
                if any(k in err_msg.lower() for k in ["not exist", "not in the approved schema", "not an approved schema entity", "does not exist"]):
                    code = ERROR_ENTITY_NOT_FOUND
                else:
                    code = ERROR_INVALID_IR
                return make_error(code, err_msg)

            target_tbl = j_spec["table"].strip().lower()
            join_type = j_spec.get("type", "INNER").strip().upper()
            left_col = j_spec["left_column"].strip()
            right_col = j_spec["right_column"].strip()

            active_tables.append(target_tbl)
            join_clauses.append(f"{join_type} JOIN {target_tbl} ON {left_col} = {right_col}")

        # 5. Conditions validation
        conditions_input = ir.get("conditions", [])
        is_cond_valid, cond_err = self.validator.validate_conditions(conditions_input)
        if not is_cond_valid:
            return cond_err or make_error(ERROR_INVALID_IR, "Invalid conditions.")

        # 6. Aggregations validation
        aggregations_input = ir.get("aggregations", [])
        is_agg_valid, agg_err = self.validator.validate_aggregations(aggregations_input)
        if not is_agg_valid:
            return agg_err or make_error(ERROR_INVALID_IR, "Invalid aggregations.")

        # 7. ORDER BY validation
        order_by_input = ir.get("order_by", [])
        is_order_valid, order_err = self.validator.validate_order_by(order_by_input)
        if not is_order_valid:
            return order_err or make_error(ERROR_INVALID_IR, "Invalid order_by.")

        # 8. GROUP BY validation
        group_by_input = ir.get("group_by", [])
        group_by_clauses = []
        for g_col in group_by_input:
            if not isinstance(g_col, str) or not g_col.strip():
                return make_error(ERROR_INVALID_IR, "GROUP BY columns must be non-empty strings.")
            res_valid, res_tbl, res_col, res_err = self.mapper.resolve_column(
                column_identifier=g_col,
                available_tables=active_tables,
                default_table=base_table,
            )
            if not res_valid:
                return make_error(ERROR_ENTITY_NOT_FOUND, res_err or f"Invalid GROUP BY column '{g_col}'.")
            group_by_clauses.append(f"{res_tbl}.{res_col}")

        # 9. Build SELECT expressions
        select_parts = []
        has_aggregations = len(aggregations_input) > 0
        has_group_by = len(group_by_clauses) > 0

        if has_aggregations:
            # PostgreSQL rule: if aggregations are used, non-aggregated columns must be in GROUP BY
            if has_group_by:
                # Include grouped columns first
                for g_clause in group_by_clauses:
                    if g_clause not in select_parts:
                        select_parts.append(g_clause)
            # Add aggregated expressions
            for agg in aggregations_input:
                func = agg["function"].strip().upper()
                col_name = agg["column"].strip()
                alias = agg.get("alias")

                if col_name == "*":
                    if func != "COUNT":
                        return make_error(
                            ERROR_UNSUPPORTED_OPERATION,
                            f"Aggregate function '{func}' cannot be applied to '*'.",
                        )
                    target_expr = "*"
                else:
                    res_valid, res_tbl, res_col, res_err = self.mapper.resolve_column(
                        column_identifier=col_name,
                        available_tables=active_tables,
                        default_table=base_table,
                    )
                    if not res_valid:
                        return make_error(ERROR_ENTITY_NOT_FOUND, res_err or f"Invalid column '{col_name}' in aggregate.")
                    target_expr = f"{res_tbl}.{res_col}"

                agg_expr = f"{func}({target_expr})"
                if alias:
                    agg_expr += f" AS {alias}"
                select_parts.append(agg_expr)

        else:
            # Standard column selection without aggregations
            columns_input = ir.get("columns", [])
            if not columns_input or columns_input == ["*"]:
                # Select all approved columns from base table (and joined tables if single base table)
                for col in self.mapper.get_table_columns(base_table):
                    select_parts.append(f"{base_table}.{col}")
            else:
                for col in columns_input:
                    if not isinstance(col, str) or not col.strip():
                        return make_error(ERROR_INVALID_IR, "Projected column must be a non-empty string.")
                    res_valid, res_tbl, res_col, res_err = self.mapper.resolve_column(
                        column_identifier=col,
                        available_tables=active_tables,
                        default_table=base_table,
                    )
                    if not res_valid:
                        return make_error(ERROR_ENTITY_NOT_FOUND, res_err or f"Invalid column '{col}'.")
                    qualified = f"{res_tbl}.{res_col}"
                    if qualified not in select_parts:
                        select_parts.append(qualified)

            # If GROUP BY exists without aggregations, verify all projected columns appear in GROUP BY
            if has_group_by:
                for s_part in select_parts:
                    if s_part not in group_by_clauses:
                        return make_error(
                            ERROR_UNSUPPORTED_OPERATION,
                            f"Column '{s_part}' must appear in the GROUP BY clause or be used in an aggregate function.",
                        )

        if not select_parts:
            return make_error(ERROR_SQL_GENERATION_FAILED, "No valid columns or aggregations to select.")

        # 10. Build WHERE clause with parameterization
        params: Dict[str, Any] = {}
        where_clauses = []
        param_counter = 0

        for cond in conditions_input:
            c_col = cond["column"].strip()
            res_valid, res_tbl, res_col, res_err = self.mapper.resolve_column(
                column_identifier=c_col,
                available_tables=active_tables,
                default_table=base_table,
            )
            if not res_valid:
                return make_error(ERROR_ENTITY_NOT_FOUND, res_err or f"Invalid condition column '{c_col}'.")

            qualified_col = f"{res_tbl}.{res_col}"
            op = cond["operator"].strip().upper()
            val = cond.get("value")

            # Handle NULL predicates
            if val is None or op in {"IS NULL", "IS NOT NULL"}:
                if op in {"!=", "<>", "IS NOT NULL"}:
                    where_clauses.append(f"{qualified_col} IS NOT NULL")
                else:
                    where_clauses.append(f"{qualified_col} IS NULL")
                continue

            # Handle IN / NOT IN lists
            if op in {"IN", "NOT IN"}:
                param_placeholders = []
                for item in val:
                    p_name = f"p{param_counter}"
                    param_counter += 1
                    params[p_name] = item
                    param_placeholders.append(f":{p_name}")
                where_clauses.append(f"{qualified_col} {op} ({', '.join(param_placeholders)})")
                continue

            # Handle LIKE_PREFIX ('starts with')
            if op == "LIKE_PREFIX":
                p_name = f"p{param_counter}"
                param_counter += 1
                params[p_name] = f"{val}%"
                where_clauses.append(f"{qualified_col} LIKE :{p_name}")
                continue

            # Handle LIKE_SUFFIX ('ends with')
            if op == "LIKE_SUFFIX":
                p_name = f"p{param_counter}"
                param_counter += 1
                params[p_name] = f"%{val}"
                where_clauses.append(f"{qualified_col} LIKE :{p_name}")
                continue

            # Standard comparison or pattern match
            p_name = f"p{param_counter}"
            param_counter += 1
            params[p_name] = val
            where_clauses.append(f"{qualified_col} {op} :{p_name}")

        # 11. Build ORDER BY clause
        order_clauses = []
        for o_item in order_by_input:
            o_col = o_item["column"].strip()
            res_valid, res_tbl, res_col, res_err = self.mapper.resolve_column(
                column_identifier=o_col,
                available_tables=active_tables,
                default_table=base_table,
            )
            if not res_valid:
                return make_error(ERROR_ENTITY_NOT_FOUND, res_err or f"Invalid ORDER BY column '{o_col}'.")
            direction = o_item.get("direction", "ASC").strip().upper()
            order_clauses.append(f"{res_tbl}.{res_col} {direction}")

        # 12. Assemble complete SQL query
        sql_parts = [
            f"SELECT {', '.join(select_parts)}",
            f"FROM {base_table}",
        ]

        if join_clauses:
            sql_parts.extend(join_clauses)

        if where_clauses:
            sql_parts.append(f"WHERE {' AND '.join(where_clauses)}")

        if group_by_clauses:
            sql_parts.append(f"GROUP BY {', '.join(group_by_clauses)}")

        if order_clauses:
            sql_parts.append(f"ORDER BY {', '.join(order_clauses)}")

        limit_val = ir.get("limit")
        if limit_val is not None:
            sql_parts.append(f"LIMIT {limit_val}")

        generated_sql = " ".join(sql_parts)

        return {
            "success": True,
            "generated_sql": generated_sql,
            "params": params,
        }


# Global generator singleton instance
_generator_instance = SQLGenerator()


def process_ir(ir: dict) -> dict:
    """Public contract entrypoint for QueryMind AI (Member 2 - SQL Engine).

    Converts a structured NLP Intermediate Representation (IR) into
    parameterized, read-only SQL adhering to ANSI / PostgreSQL dialect.

    This function does NOT connect to the database or execute the SQL.

    Args:
        ir (dict): The Canonical IR dictionary produced by Member 1.

    Returns:
        dict: A dictionary containing:
            - On success: {"success": True, "generated_sql": str, "params": dict}
            - On failure: {"success": False, "error": {"code": str, "message": str}}
    """
    return _generator_instance.generate(ir)
