"""
Semantic Checks — validates logical correctness within individual layers.
Catches things like: email field typed as integer, duplicate entity names, etc.
"""

from __future__ import annotations
import logging
import re

from backend.validation.validation_report import (
    ValidationReport,
    ErrorCategory,
    ErrorSeverity,
)

logger = logging.getLogger(__name__)

# Fields that should have specific types
FIELD_TYPE_HINTS = {
    "email": ["email", "string", "VARCHAR(255)"],
    "password": ["password", "string", "VARCHAR(255)"],
    "phone": ["phone", "string", "VARCHAR(50)"],
    "url": ["url", "string", "VARCHAR(500)", "TEXT"],
    "created_at": ["datetime", "TIMESTAMP"],
    "updated_at": ["datetime", "TIMESTAMP"],
    "is_active": ["boolean", "BOOLEAN"],
    "is_admin": ["boolean", "BOOLEAN"],
    "price": ["float", "DECIMAL", "DECIMAL(10,2)"],
    "amount": ["float", "DECIMAL", "DECIMAL(10,2)", "integer", "INTEGER"],
    "count": ["integer", "INTEGER"],
    "quantity": ["integer", "INTEGER"],
    "age": ["integer", "INTEGER"],
}


def check_design_semantics(data: dict, report: ValidationReport) -> None:
    """Check logical correctness of DesignIR."""

    entities = data.get("entities", [])

    # Build FULL entity name set FIRST — needed for relationship validation
    all_entity_names = {
        ent.get("name", "").lower()
        for ent in entities
        if isinstance(ent, dict)
    }
    seen_entity_names = set()

    for i, ent in enumerate(entities):
        if not isinstance(ent, dict):
            continue
        name = ent.get("name", "")

        # Duplicate entity names
        if name.lower() in seen_entity_names:
            report.add_error(
                ErrorCategory.SEMANTIC, ErrorSeverity.CRITICAL,
                f"Duplicate entity name: '{name}'",
                layer="design", field_path=f"entities[{i}].name",
                expected="unique entity name", actual=name,
            )
        seen_entity_names.add(name.lower())

        # Validate relationships reference existing entities
        for j, rel in enumerate(ent.get("relationships", [])):
            if not isinstance(rel, dict):
                continue
            target = rel.get("target_entity", "")
            if target.lower() not in all_entity_names:
                report.add_error(
                    ErrorCategory.SEMANTIC, ErrorSeverity.CRITICAL,
                    f"Relationship target '{target}' on entity '{name}' does not exist",
                    layer="design",
                    field_path=f"entities[{i}].relationships[{j}].target_entity",
                    expected="existing entity name", actual=target,
                    suggestion=f"Add entity '{target}' or fix the reference",
                )

        # Check field type sanity
        for j, field in enumerate(ent.get("fields", [])):
            if not isinstance(field, dict):
                continue
            fname = field.get("name", "").lower()
            ftype = field.get("type", "")
            for hint_name, valid_types in FIELD_TYPE_HINTS.items():
                if hint_name in fname and ftype not in valid_types:
                    report.add_error(
                        ErrorCategory.SEMANTIC, ErrorSeverity.WARNING,
                        f"Field '{fname}' on entity '{name}' has type '{ftype}' "
                        f"but expected one of {valid_types}",
                        layer="design",
                        field_path=f"entities[{i}].fields[{j}].type",
                        expected=str(valid_types), actual=ftype,
                        suggestion=f"Change type to one of {valid_types}",
                    )

    # Validate role permissions reference existing entities
    roles = data.get("roles", [])
    for i, role in enumerate(roles):
        if not isinstance(role, dict):
            continue
        for j, perm in enumerate(role.get("permissions", [])):
            if not isinstance(perm, dict):
                continue
            perm_entity = perm.get("entity", "")
            if perm_entity.lower() not in all_entity_names:
                report.add_error(
                    ErrorCategory.SEMANTIC, ErrorSeverity.CRITICAL,
                    f"Permission on role '{role.get('name', '?')}' references "
                    f"non-existent entity '{perm_entity}'",
                    layer="design",
                    field_path=f"roles[{i}].permissions[{j}].entity",
                    expected="existing entity name", actual=perm_entity,
                )


def check_schema_semantics(data: dict, report: ValidationReport) -> None:
    """Check logical correctness within SchemaIR layers."""

    # Check for duplicate routes
    ui = data.get("ui_schema", {})
    routes = set()
    for i, page in enumerate(ui.get("pages", [])):
        if not isinstance(page, dict):
            continue
        route = page.get("route", "")
        if route in routes:
            report.add_error(
                ErrorCategory.SEMANTIC, ErrorSeverity.CRITICAL,
                f"Duplicate route: '{route}'",
                layer="ui", field_path=f"ui_schema.pages[{i}].route",
                expected="unique route", actual=route,
            )
        routes.add(route)

    # Check for duplicate endpoint paths+methods
    api = data.get("api_schema", {})
    endpoint_keys = set()
    for i, ep in enumerate(api.get("endpoints", [])):
        if not isinstance(ep, dict):
            continue
        key = f"{ep.get('method', '')}:{ep.get('path', '')}"
        if key in endpoint_keys:
            report.add_error(
                ErrorCategory.SEMANTIC, ErrorSeverity.CRITICAL,
                f"Duplicate endpoint: {key}",
                layer="api", field_path=f"api_schema.endpoints[{i}]",
                expected="unique method+path", actual=key,
            )
        endpoint_keys.add(key)

    # Check for duplicate table names
    db = data.get("db_schema", {})
    table_names = set()
    for i, tbl in enumerate(db.get("tables", [])):
        if not isinstance(tbl, dict):
            continue
        tname = tbl.get("name", "").lower()
        if tname in table_names:
            report.add_error(
                ErrorCategory.SEMANTIC, ErrorSeverity.CRITICAL,
                f"Duplicate table name: '{tname}'",
                layer="db", field_path=f"db_schema.tables[{i}].name",
                expected="unique table name", actual=tname,
            )
        table_names.add(tname)

        # Check for duplicate column names within a table
        col_names = set()
        for j, col in enumerate(tbl.get("columns", [])):
            if not isinstance(col, dict):
                continue
            cname = col.get("name", "").lower()
            if cname in col_names:
                report.add_error(
                    ErrorCategory.SEMANTIC, ErrorSeverity.WARNING,
                    f"Duplicate column '{cname}' in table '{tname}'",
                    layer="db",
                    field_path=f"db_schema.tables[{i}].columns[{j}].name",
                    expected="unique column name", actual=cname,
                )
            col_names.add(cname)

    # Check FK references point to existing tables
    for i, tbl in enumerate(db.get("tables", [])):
        if not isinstance(tbl, dict):
            continue
        for j, col in enumerate(tbl.get("columns", [])):
            if not isinstance(col, dict):
                continue
            fk = col.get("foreign_key")
            if fk and "." in fk:
                ref_table = fk.split(".")[0].lower()
                if ref_table not in table_names:
                    report.add_error(
                        ErrorCategory.SEMANTIC, ErrorSeverity.CRITICAL,
                        f"FK '{fk}' in table '{tbl.get('name')}' references "
                        f"non-existent table '{ref_table}'",
                        layer="db",
                        field_path=f"db_schema.tables[{i}].columns[{j}].foreign_key",
                        expected="existing table name", actual=ref_table,
                    )


def check_intent_semantics(data: dict, report: ValidationReport) -> None:
    """Validate logical correctness and detect unresolved ambiguities/contradictions in IntentIR."""
    app_type = data.get("app_type", "").lower()
    app_name = data.get("app_name", "").lower()
    app_description = data.get("app_description", "").lower()
    features = data.get("features", [])
    original_prompt = data.get("original_prompt", "").lower()
    ambiguities = [a.lower() for a in data.get("ambiguities_detected", [])]
    constraints = [c.lower() for c in data.get("constraints", [])]
    assumptions = [asmp.lower() for asmp in data.get("assumptions", [])]

    # 1. Detect Extreme Vagueness (e.g. "Build a website" or "build me an app")
    is_very_vague = False
    vague_reasons = []
    
    # Prompt word length check and generic keywords
    words = original_prompt.split()
    if len(words) <= 4 and any(x in original_prompt for x in ["build", "make", "create", "need", "want"]) and any(x in original_prompt for x in ["app", "website", "site", "system", "portal", "dashboard"]):
        is_very_vague = True
        vague_reasons.append("Prompt is extremely brief and lacks functional details (e.g. 'Build a Website')")
        
    for amb in ambiguities:
        if "vague" in amb or "too general" in amb or "what is website" in amb or "lack of detail" in amb or "subject related" in amb or "which subject" in amb:
            is_very_vague = True
            vague_reasons.append(f"Ambiguity detected: {amb}")

    if is_very_vague:
        report.add_error(
            ErrorCategory.SEMANTIC, ErrorSeverity.WARNING,
            f"Vague Prompt Error: The compiler cannot determine what kind of application to build. "
            f"Found: {', '.join(vague_reasons)}.",
            layer="intent", field_path="original_prompt",
            expected="Specific application type (e.g. CRM, E-commerce, Blog, Task Management) with concrete feature details",
            actual=data.get("original_prompt", ""),
            suggestion="Please elaborate your prompt. For example: 'Build a blog website where users can view and write posts under categories...'"
        )

    # 2. Detect Contradictions / Conflicts (e.g., "without authentication but logged user accessed")
    is_conflicting = False
    conflict_reasons = []
    
    # Check for authentication contradictions in prompt text
    has_no_auth_claim = any(x in original_prompt for x in ["without login", "no login", "without authentication", "no authentication", "without auth", "no auth"])
    has_logged_user_claim = any(x in original_prompt for x in ["logged user", "logged-in", "authenticated user", "sign in", "sign-in", "user accessed", "role-based", "restrict to admin"])
    
    if has_no_auth_claim and has_logged_user_claim:
        is_conflicting = True
        conflict_reasons.append("Request specifies 'no authentication' but also implies 'logged-in/restricted user access'")

    # Check ambiguities array for contradiction keywords
    for amb in ambiguities:
        if "contradiction" in amb or "conflict" in amb or "mutually exclusive" in amb:
            is_conflicting = True
            conflict_reasons.append(f"Conflict detected: {amb}")

    if is_conflicting:
        report.add_error(
            ErrorCategory.SEMANTIC, ErrorSeverity.WARNING,
            f"Contradictory Requirements: The prompt contains logical contradictions. "
            f"Found: {', '.join(conflict_reasons)}.",
            layer="intent", field_path="original_prompt",
            expected="Logically consistent requirements (e.g., if logged-in user access is required, authentication features must be enabled)",
            actual=data.get("original_prompt", ""),
            suggestion="Resolve the contradictions. Example: 'Build a CRM with login and role-based access for admins and sales reps.'"
        )
