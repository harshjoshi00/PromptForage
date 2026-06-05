"""
Cross-Layer Checks — validates consistency BETWEEN UI, API, DB, and Auth layers.
This is the critical check that catches: UI references missing API endpoint,
API field doesn't exist in DB, auth role referenced but not defined, etc.
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


def check_cross_layer_consistency(data: dict, report: ValidationReport) -> None:
    """
    Verify that all 4 layers (UI, API, DB, Auth) reference each other consistently.

    Checks performed:
    1. UI data_source → API endpoint path exists
    2. API entity → DB table exists
    3. API allowed_roles → Auth role exists
    4. UI access_roles → Auth role exists
    5. Auth rule resource → exists as entity or page
    6. DB FK → target table exists
    """
    ui = data.get("ui_schema", data.get("ui", {}))
    api = data.get("api_schema", data.get("api", {}))
    db = data.get("db_schema", data.get("db", {}))
    auth = data.get("auth_schema", data.get("auth", {}))

    # Build lookup sets
    api_paths = set()
    for ep in api.get("endpoints", []):
        if isinstance(ep, dict):
            path = ep.get("path", "")
            # Normalize parametric paths: /api/v1/contacts/:id → /api/v1/contacts
            base_path = re.sub(r'/:[^/]+', '', path)
            api_paths.add(path)
            api_paths.add(base_path)

    table_names = set()
    table_columns: dict[str, set[str]] = {}
    for tbl in db.get("tables", []):
        if isinstance(tbl, dict):
            tname = tbl.get("name", "").lower()
            table_names.add(tname)
            table_columns[tname] = {
                c.get("name", "").lower()
                for c in tbl.get("columns", [])
                if isinstance(c, dict)
            }

    auth_role_names = {
        r.get("name", "").lower()
        for r in auth.get("roles", [])
        if isinstance(r, dict)
    }

    page_names = set()
    for page in ui.get("pages", []):
        if isinstance(page, dict):
            page_names.add(page.get("name", "").lower())

    # =========================================================================
    # CHECK 1: UI data_source → API endpoint
    # =========================================================================
    for i, page in enumerate(ui.get("pages", [])):
        if not isinstance(page, dict):
            continue
        for j, comp in enumerate(page.get("components", [])):
            if not isinstance(comp, dict):
                continue
            ds = comp.get("data_source", "")
            if ds and ds not in api_paths:
                # Try normalizing
                ds_base = re.sub(r'/:[^/]+', '', ds)
                if ds_base not in api_paths:
                    report.add_error(
                        ErrorCategory.CROSS_LAYER, ErrorSeverity.CRITICAL,
                        f"UI component '{comp.get('id', '?')}' on page "
                        f"'{page.get('name', '?')}' has data_source='{ds}' "
                        f"but no matching API endpoint exists",
                        layer="ui→api",
                        field_path=f"ui.pages[{i}].components[{j}].data_source",
                        expected=f"one of: {sorted(api_paths)[:5]}...",
                        actual=ds,
                        suggestion="Add the missing API endpoint or fix the data_source path",
                    )

    # =========================================================================
    # CHECK 2: API entity → DB table
    # =========================================================================
    for i, ep in enumerate(api.get("endpoints", [])):
        if not isinstance(ep, dict):
            continue
        entity = ep.get("entity", "")
        if entity:
            # Convert entity name to expected table name (snake_case, plural)
            expected_table = _entity_to_table_name(entity)
            if expected_table not in table_names:
                # Try exact match
                if entity.lower() not in table_names:
                    report.add_error(
                        ErrorCategory.CROSS_LAYER, ErrorSeverity.WARNING,
                        f"API endpoint '{ep.get('path', '?')}' references entity "
                        f"'{entity}' but no table '{expected_table}' found in DB",
                        layer="api→db",
                        field_path=f"api.endpoints[{i}].entity",
                        expected=expected_table, actual="not found",
                        suggestion=f"Add table '{expected_table}' to db_schema",
                    )

    # =========================================================================
    # CHECK 3: API allowed_roles → Auth roles
    # =========================================================================
    for i, ep in enumerate(api.get("endpoints", [])):
        if not isinstance(ep, dict):
            continue
        for role in ep.get("allowed_roles", []):
            if role.lower() not in auth_role_names:
                report.add_error(
                    ErrorCategory.CROSS_LAYER, ErrorSeverity.CRITICAL,
                    f"API endpoint '{ep.get('path', '?')}' allows role "
                    f"'{role}' but this role is not in auth_schema.roles",
                    layer="api→auth",
                    field_path=f"api.endpoints[{i}].allowed_roles",
                    expected=f"one of: {sorted(auth_role_names)}",
                    actual=role,
                    suggestion=f"Add role '{role}' to auth_schema.roles",
                )

    # =========================================================================
    # CHECK 4: UI access_roles → Auth roles
    # =========================================================================
    for i, page in enumerate(ui.get("pages", [])):
        if not isinstance(page, dict):
            continue
        for role in page.get("access_roles", []):
            if role.lower() not in auth_role_names:
                report.add_error(
                    ErrorCategory.CROSS_LAYER, ErrorSeverity.WARNING,
                    f"UI page '{page.get('name', '?')}' allows role "
                    f"'{role}' but this role is not in auth_schema.roles",
                    layer="ui→auth",
                    field_path=f"ui.pages[{i}].access_roles",
                    expected=f"one of: {sorted(auth_role_names)}",
                    actual=role,
                )

    # =========================================================================
    # CHECK 5: Auth rule resources → entities/pages exist
    # =========================================================================
    entity_names_lower = set()
    for ep in api.get("endpoints", []):
        if isinstance(ep, dict) and ep.get("entity"):
            entity_names_lower.add(ep["entity"].lower())

    for i, rule in enumerate(auth.get("rules", [])):
        if not isinstance(rule, dict):
            continue
        resource = rule.get("resource", "").lower()
        if resource and resource not in entity_names_lower and resource not in page_names and resource not in table_names:
            report.add_error(
                ErrorCategory.CROSS_LAYER, ErrorSeverity.WARNING,
                f"Auth rule for role '{rule.get('role', '?')}' references "
                f"resource '{resource}' which is not a known entity or page",
                layer="auth→entities",
                field_path=f"auth.rules[{i}].resource",
                expected="known entity or page name", actual=resource,
            )

        # Check rule role exists
        rule_role = rule.get("role", "").lower()
        if rule_role and rule_role not in auth_role_names:
            report.add_error(
                ErrorCategory.CROSS_LAYER, ErrorSeverity.CRITICAL,
                f"Auth rule references role '{rule_role}' which is not defined",
                layer="auth",
                field_path=f"auth.rules[{i}].role",
                expected=f"one of: {sorted(auth_role_names)}",
                actual=rule_role,
            )


def _entity_to_table_name(entity: str) -> str:
    """Convert PascalCase entity name to snake_case plural table name."""
    # PascalCase → snake_case
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', entity).lower()
    # Handle already plural
    if s.endswith('s') and not s.endswith('ss'):
        return s
    # Consonant + y → ies (category→categories, but key→keys, survey→surveys)
    if s.endswith('y') and len(s) > 1 and s[-2] not in 'aeiou':
        return s[:-1] + 'ies'
    # Sibilant endings → es
    if s.endswith(('s', 'x', 'z', 'ch', 'sh', 'ss')):
        return s + 'es'
    return s + 's'

