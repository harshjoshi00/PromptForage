"""
Repair Engine — orchestrates targeted repairs when validation fails.
Routes errors to appropriate repair strategies based on error category.
NOT a brute retry — it fixes specific failures while preserving valid data.
"""

from __future__ import annotations
import json
import logging
from typing import Any

from backend.llm.client import LLMClient
from backend.validation.validation_report import ValidationReport, ErrorCategory
from backend.repair.retry_policy import RetryPolicy
from backend.repair.strategies import repair_with_llm, apply_structural_fixes

logger = logging.getLogger(__name__)


class RepairResult:
    """Result of a repair attempt."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any],
        attempts: int,
        final_report: ValidationReport | None = None,
    ):
        self.success = success
        self.data = data
        self.attempts = attempts
        self.final_report = final_report

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "attempts": self.attempts,
            "final_errors": self.final_report.error_count if self.final_report else 0,
        }


class RepairEngine:
    """
    Orchestrates the repair loop for a failed pipeline stage.

    Flow:
    1. Receive validation errors + raw data
    2. Classify errors (structural vs semantic vs cross-layer)
    3. Try deterministic fixes first (no LLM cost)
    4. If still failing, send targeted errors to LLM for repair
    5. Re-validate after each attempt
    6. Stop on: success, convergence (same errors), or budget exhaustion
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def repair(
        self,
        stage: str,
        data: dict[str, Any],
        report: ValidationReport,
        validate_fn,
    ) -> RepairResult:
        """
        Attempt to repair failed validation output.

        Args:
            stage: Pipeline stage name.
            data: Raw dict that failed validation.
            report: ValidationReport with errors to fix.
            validate_fn: Function(data, stage) -> ValidationReport to re-validate.

        Returns:
            RepairResult with repaired data (or original if repair failed).
        """
        policy = RetryPolicy()
        current_data = data
        current_report = report

        logger.info(
            f"[RepairEngine] Starting repair for {stage} — "
            f"{current_report.error_count} errors to fix"
        )

        while not policy.is_exhausted:
            # Record this attempt
            error_summary = current_report.to_error_summary()
            policy.record_attempt(error_summary)

            # Check convergence — same errors means repair isn't helping
            if policy.has_converged():
                logger.warning(
                    f"[RepairEngine] Repair converged (same errors) after "
                    f"{policy.current_attempt} attempts — aborting"
                )
                break

            logger.info(
                f"[RepairEngine] Attempt {policy.current_attempt}/{policy.max_retries} "
                f"for {stage}"
            )

            # --- Step 1: Try deterministic fixes (free, no LLM call) ---
            has_structural = any(
                e.category == ErrorCategory.STRUCTURAL
                for e in current_report.errors
            )
            if has_structural:
                current_data = apply_structural_fixes(current_data, current_report)
                # Re-validate after deterministic fix
                current_report = validate_fn(current_data, stage)
                if current_report.is_valid:
                    logger.info(
                        f"[RepairEngine] Fixed by deterministic repair "
                        f"on attempt {policy.current_attempt}"
                    )
                    return RepairResult(
                        success=True,
                        data=current_data,
                        attempts=policy.current_attempt,
                        final_report=current_report,
                    )

            # --- Step 2: LLM-based targeted repair ---
            try:
                current_data = repair_with_llm(
                    stage=stage,
                    data=current_data,
                    report=current_report,
                    llm=self.llm,
                )
            except Exception as e:
                logger.error(f"[RepairEngine] LLM repair call failed: {e}")
                policy.wait_backoff()
                continue

            # --- Step 3: Re-validate ---
            current_report = validate_fn(current_data, stage)

            if current_report.is_valid:
                logger.info(
                    f"[RepairEngine] Successfully repaired {stage} "
                    f"on attempt {policy.current_attempt}"
                )
                return RepairResult(
                    success=True,
                    data=current_data,
                    attempts=policy.current_attempt,
                    final_report=current_report,
                )

            logger.warning(
                f"[RepairEngine] Still {current_report.error_count} errors "
                f"after attempt {policy.current_attempt}"
            )

            # Backoff before next attempt
            if not policy.is_exhausted:
                policy.wait_backoff()

        # All retries exhausted
        logger.error(
            f"[RepairEngine] Failed to repair {stage} after "
            f"{policy.current_attempt} attempts — "
            f"{current_report.error_count} errors remain"
        )

        return RepairResult(
            success=False,
            data=current_data,
            attempts=policy.current_attempt,
            final_report=current_report,
        )
