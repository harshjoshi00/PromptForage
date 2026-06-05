"""
Validation Report — typed error models with categories.
Every validation error is categorized for targeted repair.
"""

from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    STRUCTURAL = "structural"    # Invalid JSON, missing required fields, wrong types
    SEMANTIC = "semantic"        # Logically invalid values (e.g., email field typed as int)
    CROSS_LAYER = "cross_layer"  # Inconsistency between UI/API/DB/Auth layers
    HALLUCINATION = "hallucination"  # Fields/entities not traceable to design input


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"  # Must fix — will break execution
    WARNING = "warning"    # Should fix — may cause issues
    INFO = "info"          # Minor — cosmetic or best-practice


class ValidationError(BaseModel):
    """A single validation error with full context for repair."""
    category: ErrorCategory
    severity: ErrorSeverity
    layer: str = ""           # Which layer: "ui", "api", "db", "auth", or "cross_layer"
    field_path: str = ""      # Dot-path to the problematic field: "ui.pages[0].components[1].data_source"
    message: str              # Human-readable error description
    expected: str = ""        # What was expected
    actual: str = ""          # What was found
    suggestion: str = ""      # How to fix it


class ValidationReport(BaseModel):
    """Complete validation report for a pipeline stage output."""
    stage: str
    is_valid: bool = True
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)

    @property
    def critical_errors(self) -> list[ValidationError]:
        return [e for e in self.errors if e.severity == ErrorSeverity.CRITICAL]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def add_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        layer: str = "",
        field_path: str = "",
        expected: str = "",
        actual: str = "",
        suggestion: str = "",
    ):
        """Add a validation error and update is_valid flag."""
        error = ValidationError(
            category=category,
            severity=severity,
            layer=layer,
            field_path=field_path,
            message=message,
            expected=expected,
            actual=actual,
            suggestion=suggestion,
        )
        if severity == ErrorSeverity.CRITICAL:
            self.errors.append(error)
            self.is_valid = False
        elif severity == ErrorSeverity.WARNING:
            self.warnings.append(error)
        else:
            self.warnings.append(error)

    def to_error_summary(self) -> str:
        """Compact error summary for LLM repair prompts."""
        lines = []
        for i, err in enumerate(self.errors, 1):
            lines.append(
                f"{i}. [{err.category.value}] {err.layer}.{err.field_path}: "
                f"{err.message} (expected: {err.expected}, got: {err.actual})"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Full report as dict for API response."""
        return {
            "stage": self.stage,
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [e.model_dump() for e in self.errors],
            "warnings": [e.model_dump() for e in self.warnings],
        }
