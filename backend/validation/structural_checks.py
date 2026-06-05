"""
Structural Checks — validates JSON structure, required fields, type correctness.
These are the first line of defense: if structure is wrong, nothing else matters.
"""

from __future__ import annotations
import logging

from backend.validation.validation_report import (
    ValidationReport,
    ErrorCategory,
    ErrorSeverity,
)
from backend.schemas.intent_ir import IntentIR
from backend.schemas.design_ir import DesignIR
from backend.schemas.schema_ir import SchemaIR
from backend.schemas.app_spec import AppSpec

logger = logging.getLogger(__name__)


def check_intent_ir(data: dict, report: ValidationReport) -> None:
    """Validate structural requirements for Stage 1 output."""

    # Must have features
    features = data.get("features", [])
    if not features:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "features array is empty — at least 1 feature required",
            layer="intent", field_path="features",
            expected="non-empty array", actual="[]",
        )

    # Must have entities
    entities = data.get("entities", [])
    if not entities:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "entities array is empty — at least 1 entity required",
            layer="intent", field_path="entities",
            expected="non-empty array", actual="[]",
        )

    # Must have app_name
    if not data.get("app_name"):
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "app_name is missing or empty",
            layer="intent", field_path="app_name",
            expected="non-empty string", actual=str(data.get("app_name", "")),
        )

    # Validate feature structure
    for i, feat in enumerate(features):
        if not isinstance(feat, dict):
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"features[{i}] is not a dict",
                layer="intent", field_path=f"features[{i}]",
                expected="dict", actual=str(type(feat)),
            )
            continue
        if not feat.get("name"):
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"features[{i}].name is missing",
                layer="intent", field_path=f"features[{i}].name",
                expected="non-empty string", actual="",
            )


def check_design_ir(data: dict, report: ValidationReport) -> None:
    """Validate structural requirements for Stage 2 output."""

    entities = data.get("entities", [])
    if not entities:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "entities array is empty",
            layer="design", field_path="entities",
            expected="non-empty array", actual="[]",
        )

    # Each entity must have fields
    for i, ent in enumerate(entities):
        if not isinstance(ent, dict):
            continue
        if not ent.get("fields"):
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"entities[{i}] ({ent.get('name', '?')}) has no fields",
                layer="design", field_path=f"entities[{i}].fields",
                expected="non-empty array", actual="[]",
            )

    roles = data.get("roles", [])
    if not roles:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "roles array is empty",
            layer="design", field_path="roles",
            expected="non-empty array", actual="[]",
        )

    pages = data.get("pages", [])
    if not pages:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "pages array is empty",
            layer="design", field_path="pages",
            expected="non-empty array", actual="[]",
        )


def check_schema_ir(data: dict, report: ValidationReport) -> None:
    """Validate structural requirements for Stage 3 output."""

    # Check all 4 top-level keys exist
    for key in ["ui_schema", "api_schema", "db_schema", "auth_schema"]:
        if key not in data or not data[key]:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"{key} is missing or empty",
                layer="schema", field_path=key,
                expected="non-empty object", actual=str(data.get(key, "missing")),
            )

    # UI pages
    ui = data.get("ui_schema", {})
    pages = ui.get("pages", [])
    if not pages:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "ui_schema.pages is empty",
            layer="ui", field_path="ui_schema.pages",
            expected="non-empty array", actual="[]",
        )

    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        if not page.get("route"):
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"page[{i}] ({page.get('name', '?')}) has no route",
                layer="ui", field_path=f"ui_schema.pages[{i}].route",
                expected="non-empty string", actual="",
            )

    # API endpoints
    api = data.get("api_schema", {})
    endpoints = api.get("endpoints", [])
    if not endpoints:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "api_schema.endpoints is empty",
            layer="api", field_path="api_schema.endpoints",
            expected="non-empty array", actual="[]",
        )

    for i, ep in enumerate(endpoints):
        if not isinstance(ep, dict):
            continue
        if not ep.get("path"):
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"endpoint[{i}] has no path",
                layer="api", field_path=f"api_schema.endpoints[{i}].path",
                expected="non-empty string", actual="",
            )
        if not ep.get("method"):
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"endpoint[{i}] has no method",
                layer="api", field_path=f"api_schema.endpoints[{i}].method",
                expected="GET|POST|PUT|DELETE", actual="",
            )

    # DB tables
    db = data.get("db_schema", {})
    tables = db.get("tables", [])
    if not tables:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "db_schema.tables is empty",
            layer="db", field_path="db_schema.tables",
            expected="non-empty array", actual="[]",
        )

    for i, tbl in enumerate(tables):
        if not isinstance(tbl, dict):
            continue
        cols = tbl.get("columns", [])
        if not cols:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"table[{i}] ({tbl.get('name', '?')}) has no columns",
                layer="db", field_path=f"db_schema.tables[{i}].columns",
                expected="non-empty array", actual="[]",
            )
        # Check for PK
        has_pk = any(
            c.get("primary_key", False) for c in cols if isinstance(c, dict)
        )
        if not has_pk and cols:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.WARNING,
                f"table[{i}] ({tbl.get('name', '?')}) has no primary key",
                layer="db", field_path=f"db_schema.tables[{i}]",
                expected="at least one column with primary_key=true",
                actual="none found",
                suggestion="Add an 'id' column with primary_key=true",
            )

        # Check for timestamps
        has_created_at = any(
            c.get("name", "").lower() == "created_at" for c in cols if isinstance(c, dict)
        )
        has_updated_at = any(
            c.get("name", "").lower() == "updated_at" for c in cols if isinstance(c, dict)
        )
        if not has_created_at:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.WARNING,
                f"table[{i}] ({tbl.get('name', '?')}) is missing 'created_at' timestamp column",
                layer="db", field_path=f"db_schema.tables[{i}]",
                expected="column named 'created_at'",
                actual="none found",
                suggestion="Add a 'created_at' column with type TIMESTAMP",
            )
        if not has_updated_at:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.WARNING,
                f"table[{i}] ({tbl.get('name', '?')}) is missing 'updated_at' timestamp column",
                layer="db", field_path=f"db_schema.tables[{i}]",
                expected="column named 'updated_at'",
                actual="none found",
                suggestion="Add an 'updated_at' column with type TIMESTAMP",
            )

    # Check that a users table exists
    users_tbl = next((t for t in tables if isinstance(t, dict) and t.get("name", "").lower() in ("users", "user")), None)
    if not users_tbl:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "db_schema is missing a 'users' table",
            layer="db", field_path="db_schema.tables",
            expected="a table named 'users'",
            actual="none found",
            suggestion="Add a 'users' table to DB schema for user management",
        )
    else:
        # Check for email and password/password_hash columns
        users_cols = [c.get("name", "").lower() for c in users_tbl.get("columns", []) if isinstance(c, dict)]
        if "email" not in users_cols:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                "'users' table is missing an 'email' column",
                layer="db", field_path="db_schema.tables",
                expected="'email' column",
                actual="none found",
                suggestion="Add an 'email' column to the 'users' table",
            )
        if not any(pwd in users_cols for pwd in ["password", "password_hash"]):
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                "'users' table is missing a password column",
                layer="db", field_path="db_schema.tables",
                expected="'password' or 'password_hash' column",
                actual="none found",
                suggestion="Add a 'password_hash' or 'password' column to the 'users' table",
            )

    # Auth roles
    auth = data.get("auth_schema", {})
    roles = auth.get("roles", [])
    if not roles:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "auth_schema.roles is empty",
            layer="auth", field_path="auth_schema.roles",
            expected="non-empty array", actual="[]",
        )


def check_app_spec(data: dict, report: ValidationReport) -> None:
    """Validate structural requirements for Stage 4 output."""

    if "metadata" not in data:
        report.add_error(
            ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
            "metadata is missing",
            layer="app_spec", field_path="metadata",
            expected="metadata object", actual="missing",
        )

    # Delegate to schema_ir checks for the nested schemas
    schema_data = {
        "ui_schema": data.get("ui", {}),
        "api_schema": data.get("api", {}),
        "db_schema": data.get("db", {}),
        "auth_schema": data.get("auth", {}),
    }
    check_schema_ir(schema_data, report)
