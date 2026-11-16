"""SQL Engine Package for QueryMind AI (Member 2).

Exposes the primary contract interface: process_ir(ir: dict) -> dict
"""

from .generator import process_ir, SQLGenerator
from .schema_mapper import SchemaMapper, APPROVED_SCHEMA
from .validator import IRValidator

__all__ = [
    "process_ir",
    "SQLGenerator",
    "SchemaMapper",
    "IRValidator",
    "APPROVED_SCHEMA",
]
