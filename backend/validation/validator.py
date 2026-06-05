"""
Main Validator — orchestrates all validation checks for each pipeline stage.
Runs structural → semantic → cross-layer checks in order, building a full report.
"""

from __future__ import annotations
import logging
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from backend.validation.validation_report import (
    ValidationReport,
    ErrorCategory,
    ErrorSeverity,
)
from backend.validation import structural_checks, semantic_checks, cross_layer_checks
from backend.schemas.intent_ir import IntentIR
from backend.schemas.design_ir import DesignIR
from backend.schemas.schema_ir import SchemaIR
from backend.schemas.app_spec import AppSpec

logger = logging.getLogger(__name__)

# Maps stage name → (Pydantic model, structural check fn, semantic check fn)
STAGE_VALIDATORS = {
    "stage_1_lexer": {
        "model": IntentIR,
        "structural": structural_checks.check_intent_ir,
        "semantic": semantic_checks.check_intent_semantics,
    },
    "stage_2_parser": {
        "model": DesignIR,
        "structural": structural_checks.check_design_ir,
        "semantic": semantic_checks.check_design_semantics,
    },
    "stage_3_ir_generator": {
        "model": SchemaIR,
        "structural": structural_checks.check_schema_ir,
        "semantic": semantic_checks.check_schema_semantics,
        "cross_layer": cross_layer_checks.check_cross_layer_consistency,
    },
    "stage_4_optimizer": {
        "model": AppSpec,
        "structural": structural_checks.check_app_spec,
        "semantic": semantic_checks.check_schema_semantics,
        "cross_layer": cross_layer_checks.check_cross_layer_consistency,
    },
}


def validate(data: dict[str, Any], stage: str) -> ValidationReport:
    """
    Run all applicable validation checks for a given pipeline stage.

    Args:
        data: Raw dict output from the LLM (before Pydantic parsing).
        stage: Pipeline stage name (e.g., "stage_1_lexer").

    Returns:
        ValidationReport with all errors and warnings.
    """
    report = ValidationReport(stage=stage)
    config = STAGE_VALIDATORS.get(stage, {})

    if not config:
        logger.warning(f"No validators configured for stage '{stage}'")
        return report

    logger.info(f"[Validator] Running checks for {stage}...")

    # --- Layer 1: Structural checks ---
    structural_fn = config.get("structural")
    if structural_fn:
        try:
            structural_fn(data, report)
            logger.info(
                f"[Validator] Structural: {report.error_count} errors, "
                f"{report.warning_count} warnings"
            )
        except Exception as e:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"Structural check crashed: {str(e)}",
                layer="validator",
            )

    # If structural checks found critical errors, skip deeper checks
    if report.critical_errors:
        logger.warning(
            f"[Validator] {len(report.critical_errors)} critical structural errors — "
            f"skipping semantic/cross-layer checks"
        )
        return report

    # --- Layer 2: Pydantic model validation ---
    pydantic_model = config.get("model")
    if pydantic_model:
        try:
            # For Stage 4, the schema structure is different
            if stage == "stage_4_optimizer":
                _validate_app_spec_structure(data, report)
            else:
                pydantic_model.model_validate(data)
        except PydanticValidationError as e:
            for err in e.errors():
                report.add_error(
                    ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                    f"Schema validation: {err['msg']}",
                    layer="pydantic",
                    field_path=".".join(str(x) for x in err.get("loc", [])),
                    expected="valid schema", actual=str(err.get("input", ""))[:100],
                )

    # --- Layer 3: Semantic checks ---
    semantic_fn = config.get("semantic")
    if semantic_fn and not report.critical_errors:
        try:
            # For schema stages, pass the right data shape
            if stage in ("stage_3_ir_generator",):
                semantic_fn(data, report)
            elif stage == "stage_4_optimizer":
                # Reshape AppSpec data to look like SchemaIR for semantic checks
                schema_data = {
                    "ui_schema": data.get("ui", {}),
                    "api_schema": data.get("api", {}),
                    "db_schema": data.get("db", {}),
                    "auth_schema": data.get("auth", {}),
                }
                semantic_fn(schema_data, report)
            else:
                semantic_fn(data, report)

            logger.info(
                f"[Validator] After semantic: {report.error_count} errors, "
                f"{report.warning_count} warnings"
            )
        except Exception as e:
            logger.warning(f"[Validator] Semantic check error: {e}")

    # --- Layer 4: Cross-layer checks ---
    cross_layer_fn = config.get("cross_layer")
    if cross_layer_fn and not report.critical_errors:
        try:
            if stage == "stage_4_optimizer":
                reshaped = {
                    "ui_schema": data.get("ui", {}),
                    "api_schema": data.get("api", {}),
                    "db_schema": data.get("db", {}),
                    "auth_schema": data.get("auth", {}),
                }
                cross_layer_fn(reshaped, report)
            else:
                cross_layer_fn(data, report)

            logger.info(
                f"[Validator] After cross-layer: {report.error_count} errors, "
                f"{report.warning_count} warnings"
            )
        except Exception as e:
            logger.warning(f"[Validator] Cross-layer check error: {e}")

    logger.info(
        f"[Validator] Final result for {stage}: "
        f"{'PASS' if report.is_valid else 'FAIL'} "
        f"({report.error_count} errors, {report.warning_count} warnings)"
    )

    return report


def _validate_app_spec_structure(data: dict, report: ValidationReport) -> None:
    """Validate AppSpec has the right top-level keys."""
    required_keys = ["metadata", "ui", "api", "db", "auth"]
    for key in required_keys:
        if key not in data:
            report.add_error(
                ErrorCategory.STRUCTURAL, ErrorSeverity.CRITICAL,
                f"AppSpec missing required key: '{key}'",
                layer="app_spec", field_path=key,
                expected="present", actual="missing",
            )
