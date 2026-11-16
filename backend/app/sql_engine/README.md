# QueryMind AI — SQL Engine Module (Member 2)

The **SQL Engine** is responsible for converting the structured Intermediate Representation (IR) produced by Member 1's NLP module into parameterized, read-only SQL queries conforming to ANSI / PostgreSQL standards.

---

## 1. Architecture & Pipeline

```text
Natural Language Query
        │
        ▼
Member 1: NLP Module (process_natural_language)
        │
        ▼
Structured Intermediate Representation (IR)
        │
        ▼
Member 2: SQL Engine (process_ir)  <-- THIS MODULE
        │
        ▼
Generated SQL + Named Parameters (:p0, :p1, ...)
        │
        ▼
Member 3: Safe Execution Service (execute_read_query)
        │
        ▼
SQLGlot AST Validation & PostgreSQL Execution
```

The SQL Engine operates strictly as a query generator. It does **not** connect to the database, store credentials, or execute queries.

---

## 2. Package Structure

```text
backend/app/sql_engine/
├── __init__.py           # Public interface export (process_ir)
├── generator.py          # Core SQL synthesis and clause assembly
├── schema_mapper.py      # Schema catalog, column resolution, and join validation
├── validator.py          # IR structure, operator, and security validation
├── mock_sql_engine.py    # Day 2 prototype mock implementation (retained for fallback)
└── README.md             # Module documentation
```

---

## 3. Public Interface

```python
from app.sql_engine import process_ir

def process_ir(ir: dict) -> dict:
    """
    Translates a Canonical IR dictionary into parameterized SQL.
    
    Returns:
        On Success:
            {
                "success": True,
                "generated_sql": "SELECT students.name FROM students WHERE students.cgpa > :p0",
                "params": {"p0": 8.5}
            }
        On Error:
            {
                "success": False,
                "error": {
                    "code": "ENTITY_NOT_FOUND",
                    "message": "Column 'xyz' does not exist in table 'students'."
                }
            }
    """
```

### Error Codes
* `INVALID_IR`: Structural IR defect, missing required keys, or invalid types.
* `ENTITY_NOT_FOUND`: Table or column name not present in the approved schema catalog.
* `UNSUPPORTED_OPERATION`: Operator, aggregate function, or clause combination not supported.
* `SQL_GENERATION_FAILED`: Unrecoverable query synthesis error.

---

## 4. Supported Features

* **Basic SELECT:** Explicit column projections and all-column expansions (`*`).
* **Multi-Condition Filtering:** `>`, `>=`, `<`, `<=`, `=`, `!=`, `<>`, `LIKE`, `ILIKE`, `IN`, `NOT IN`, `IS NULL`, `IS NOT NULL`.
* **Parameter Binding:** User values bound as `:p0`, `:p1`, etc. (SQL injection immune).
* **JOINs:** `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN` with schema relationship checking.
* **Multi-Hop Traversal:** Chains queries across `students` $\leftrightarrow$ `enrollments` $\leftrightarrow$ `courses`.
* **Aggregations:** `COUNT(*)`, `COUNT(col)`, `AVG`, `SUM`, `MAX`, `MIN` with aliases (`AS alias`).
* **GROUP BY:** Department/course grouping aligned with PostgreSQL non-aggregated column rules.
* **ORDER BY:** Single and multi-column ordering with `ASC` and `DESC`.
* **LIMIT:** Validated positive integer row limits.

---

## 5. Testing

Run all unit, negative, security, and integration tests using Python's standard test runner:

```bash
python backend/tests/test_sql_engine.py
python backend/tests/test_sql_engine_invalid_ir.py
python backend/tests/test_sql_engine_security.py
python backend/tests/test_sql_engine_nlp_integration.py
```
