"""
Repair Strategies — defines how to fix different categories of validation errors.
Each strategy targets a specific error type with a targeted repair approach.
"""

from __future__ import annotations
import json
import logging
from typing import Any

from backend.llm.client import LLMClient
from backend.llm.prompts import REPAIR_SYSTEM, REPAIR_USER
from backend.validation.validation_report import ValidationReport, ErrorCategory

logger = logging.getLogger(__name__)


def repair_with_llm(
    stage: str,
    data: dict[str, Any],
    report: ValidationReport,
    llm: LLMClient,
) -> dict[str, Any]:
    """
    Targeted LLM-based repair: sends ONLY the errors and current schema
    to the LLM for surgical fixes.

    This is NOT a full retry. The LLM receives the specific errors and
    is instructed to fix only those while preserving valid data.
    """
    errors_json = json.dumps(
        [e.model_dump() for e in report.errors],
        indent=2,
    )
    schema_json = json.dumps(data, indent=2)

    user_prompt = REPAIR_USER.format(
        errors_json=errors_json,
        schema_json=schema_json,
    )

    logger.info(
        f"[Repair] Sending {len(report.errors)} errors to LLM for "
        f"targeted repair of {stage}"
    )

    repaired = llm.generate(
        system_prompt=REPAIR_SYSTEM,
        user_prompt=user_prompt,
        stage=f"{stage}_repair",
        is_repair=True,
        max_tokens=16384,
    )

    return repaired


def apply_structural_fixes(
    data: dict[str, Any],
    report: ValidationReport,
) -> dict[str, Any]:
    """
    Apply deterministic structural fixes that don't need LLM.
    For example: add missing timestamps, add missing PK, etc.
    """
    fixed = json.loads(json.dumps(data))  # deep copy

    for error in report.errors:
        if error.category != ErrorCategory.STRUCTURAL:
            continue

        # Fix: missing created_at/updated_at on DB tables
        if "created_at" in error.message or "updated_at" in error.message:
            _add_timestamp_columns(fixed)

        # Fix: missing primary key
        if "primary key" in error.message.lower():
            _add_primary_keys(fixed)

    return fixed


def _add_timestamp_columns(data: dict) -> None:
    """Add created_at and updated_at to all tables missing them."""
    db = data.get("db_schema", data.get("db", {}))
    for table in db.get("tables", []):
        col_names = {c.get("name", "").lower() for c in table.get("columns", [])}
        if "created_at" not in col_names:
            table["columns"].append({
                "name": "created_at",
                "type": "TIMESTAMP",
                "primary_key": False,
                "nullable": False,
                "unique": False,
                "default": "CURRENT_TIMESTAMP",
                "foreign_key": None,
            })
        if "updated_at" not in col_names:
            table["columns"].append({
                "name": "updated_at",
                "type": "TIMESTAMP",
                "primary_key": False,
                "nullable": False,
                "unique": False,
                "default": "CURRENT_TIMESTAMP",
                "foreign_key": None,
            })


def _add_primary_keys(data: dict) -> None:
    """Add 'id' PK column to tables missing a primary key."""
    db = data.get("db_schema", data.get("db", {}))
    for table in db.get("tables", []):
        has_pk = any(c.get("primary_key", False) for c in table.get("columns", []))
        if not has_pk:
            table["columns"].insert(0, {
                "name": "id",
                "type": "UUID",
                "primary_key": True,
                "nullable": False,
                "unique": True,
                "default": "gen_random_uuid()",
                "foreign_key": None,
            })
