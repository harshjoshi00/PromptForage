"""
Pipeline Orchestrator — runs the full compiler pipeline with validation gates.

Flow: S1 → Gate → S2 → Gate → S3 → Gate → S4 → Gate → Runtime → Response

Each gate validates the stage output. On failure, the repair engine attempts
targeted fixes before the data moves to the next stage.
"""

from __future__ import annotations
import time
import logging
from typing import Any
from dataclasses import dataclass, field

from backend.llm.client import LLMClient, LLMError
from backend.llm.cost_tracker import CostTracker
from backend.validation.validator import validate
from backend.repair.repair_engine import RepairEngine
from backend.pipeline import stage_1_lexer, stage_2_parser, stage_3_ir_generator, stage_4_optimizer
from backend.schemas.intent_ir import IntentIR
from backend.schemas.design_ir import DesignIR
from backend.schemas.schema_ir import SchemaIR
from backend.schemas.app_spec import AppSpec

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    stage: str
    success: bool
    data: Any = None
    raw_data: dict = field(default_factory=dict)
    validation_errors: int = 0
    repair_attempts: int = 0
    latency_ms: float = 0.0
    errors: list[dict] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result of the full pipeline execution."""
    success: bool
    app_spec: AppSpec | None = None
    app_spec_dict: dict = field(default_factory=dict)
    stages: list[StageResult] = field(default_factory=list)
    cost_summary: dict = field(default_factory=dict)
    total_latency_ms: float = 0.0
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "app_spec": self.app_spec_dict if self.success else None,
            "pipeline": {
                "stages": [
                    {
                        "stage": s.stage,
                        "success": s.success,
                        "validation_errors": s.validation_errors,
                        "repair_attempts": s.repair_attempts,
                        "latency_ms": round(s.latency_ms, 2),
                        "errors": s.errors,
                    }
                    for s in self.stages
                ],
                "total_latency_ms": round(self.total_latency_ms, 2),
            },
            "cost": self.cost_summary,
            "error": self.error_message if not self.success else None,
        }


class PipelineOrchestrator:
    """
    Runs the 4-stage compiler pipeline with validation gates between each stage.

    Architecture:
        Prompt → [Stage 1: Lexer] → [Gate 1] → [Stage 2: Parser] → [Gate 2]
               → [Stage 3: IR Gen] → [Gate 3] → [Stage 4: Optimizer] → [Gate 4]
               → AppSpec

    Each gate:
        1. Validates stage output against its schema
        2. On failure: routes to RepairEngine for targeted fixes
        3. On repair failure: aborts pipeline with error report
    """

    def __init__(self):
        self.cost_tracker = CostTracker()
        self.llm = LLMClient(cost_tracker=self.cost_tracker)
        self.repair_engine = RepairEngine(llm=self.llm)

    def run(self, prompt: str) -> PipelineResult:
        """
        Execute the full pipeline for a given prompt.

        Args:
            prompt: Raw natural language application description.

        Returns:
            PipelineResult with AppSpec on success or error details on failure.
        """
        self.cost_tracker.reset()
        pipeline_start = time.time()
        stages: list[StageResult] = []

        logger.info("=" * 60)
        logger.info(f"[Pipeline] Starting compilation for: {prompt[:100]}...")
        logger.info("=" * 60)

        try:
            # ================================================================
            # STAGE 1: LEXER — Intent Extraction
            # ================================================================
            s1_result = self._run_stage(
                stage_name="stage_1_lexer",
                run_fn=lambda: stage_1_lexer.run(prompt, self.llm),
                model_class=IntentIR,
            )
            stages.append(s1_result)
            if not s1_result.success:
                err_msg = s1_result.errors[0].get("message", "Stage 1 (Lexer) failed") if s1_result.errors else "Stage 1 (Lexer) failed"
                return self._fail(stages, err_msg, pipeline_start)

            intent: IntentIR = s1_result.data

            # ================================================================
            # STAGE 2: PARSER — System Design
            # ================================================================
            s2_result = self._run_stage(
                stage_name="stage_2_parser",
                run_fn=lambda: stage_2_parser.run(intent, self.llm),
                model_class=DesignIR,
            )
            stages.append(s2_result)
            if not s2_result.success:
                err_msg = s2_result.errors[0].get("message", "Stage 2 (Parser) failed") if s2_result.errors else "Stage 2 (Parser) failed"
                return self._fail(stages, err_msg, pipeline_start)

            design: DesignIR = s2_result.data

            # ================================================================
            # STAGE 3: IR GENERATOR — Schema Generation
            # ================================================================
            s3_result = self._run_stage(
                stage_name="stage_3_ir_generator",
                run_fn=lambda: stage_3_ir_generator.run(design, self.llm),
                model_class=SchemaIR,
            )
            stages.append(s3_result)
            if not s3_result.success:
                err_msg = s3_result.errors[0].get("message", "Stage 3 (IR Generator) failed") if s3_result.errors else "Stage 3 (IR Generator) failed"
                return self._fail(stages, err_msg, pipeline_start)

            schema: SchemaIR = s3_result.data

            # ================================================================
            # STAGE 4: OPTIMIZER — Refinement
            # ================================================================
            s4_result = self._run_stage(
                stage_name="stage_4_optimizer",
                run_fn=lambda: stage_4_optimizer.run(schema, design, prompt, self.llm),
                model_class=AppSpec,
            )
            stages.append(s4_result)
            if not s4_result.success:
                err_msg = s4_result.errors[0].get("message", "Stage 4 (Optimizer) failed") if s4_result.errors else "Stage 4 (Optimizer) failed"
                return self._fail(stages, err_msg, pipeline_start)

            app_spec: AppSpec = s4_result.data

            # ================================================================
            # SUCCESS
            # ================================================================
            total_latency = (time.time() - pipeline_start) * 1000

            logger.info("=" * 60)
            logger.info(f"[Pipeline] Compilation SUCCEEDED in {total_latency:.0f}ms")
            logger.info("=" * 60)

            return PipelineResult(
                success=True,
                app_spec=app_spec,
                app_spec_dict=app_spec.model_dump(),
                stages=stages,
                cost_summary=self.cost_tracker.to_dict(),
                total_latency_ms=total_latency,
            )

        except LLMError as e:
            logger.error(f"[Pipeline] LLM Error: {e}")
            return self._fail(stages, f"LLM Error: {str(e)}", pipeline_start)
        except Exception as e:
            logger.error(f"[Pipeline] Unexpected error: {e}", exc_info=True)
            return self._fail(stages, f"Unexpected error: {str(e)}", pipeline_start)

    def _run_stage(
        self,
        stage_name: str,
        run_fn,
        model_class,
    ) -> StageResult:
        """
        Run a single pipeline stage with its validation gate.

        1. Execute the stage function
        2. Validate the raw output
        3. On validation failure → run repair engine
        4. Return StageResult
        """
        start = time.time()
        logger.info(f"\n[Pipeline] {'─' * 20} {stage_name} {'─' * 20}")

        try:
            # Run the stage
            result = run_fn()
            raw_data = result.model_dump()
            latency = (time.time() - start) * 1000

            # Validate through the gate
            report = validate(raw_data, stage_name)

            if report.is_valid:
                logger.info(f"[Pipeline] {stage_name} PASSED gate [OK]")
                return StageResult(
                    stage=stage_name,
                    success=True,
                    data=result,
                    raw_data=raw_data,
                    validation_errors=0,
                    repair_attempts=0,
                    latency_ms=latency,
                    errors=[],
                )

            # Gate FAILED — enter repair loop
            logger.warning(
                f"[Pipeline] {stage_name} FAILED gate [FAIL] — "
                f"{report.error_count} errors. Entering repair..."
            )

            repair_result = self.repair_engine.repair(
                stage=stage_name,
                data=raw_data,
                report=report,
                validate_fn=validate,
            )

            latency = (time.time() - start) * 1000

            if repair_result.success:
                # Re-parse the repaired data through the model
                repaired_model = model_class.model_validate(repair_result.data)
                logger.info(
                    f"[Pipeline] {stage_name} REPAIRED [OK] "
                    f"({repair_result.attempts} attempts)"
                )
                return StageResult(
                    stage=stage_name,
                    success=True,
                    data=repaired_model,
                    raw_data=repair_result.data,
                    validation_errors=report.error_count,
                    repair_attempts=repair_result.attempts,
                    latency_ms=latency,
                    errors=[],
                )
            else:
                logger.error(f"[Pipeline] {stage_name} REPAIR FAILED [FAIL]")
                final_errors = []
                if repair_result.final_report:
                    final_errors = [e.model_dump() for e in repair_result.final_report.errors]
                return StageResult(
                    stage=stage_name,
                    success=False,
                    raw_data=repair_result.data,
                    validation_errors=repair_result.final_report.error_count
                    if repair_result.final_report
                    else 0,
                    repair_attempts=repair_result.attempts,
                    latency_ms=latency,
                    errors=final_errors,
                )

        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.error(f"[Pipeline] {stage_name} CRASHED: {e}")
            return StageResult(
                stage=stage_name,
                success=False,
                latency_ms=latency,
                errors=[{"category": "structural", "severity": "critical", "message": str(e)}],
            )

    def _fail(
        self,
        stages: list[StageResult],
        message: str,
        start_time: float,
    ) -> PipelineResult:
        """Construct a failure result."""
        return PipelineResult(
            success=False,
            stages=stages,
            cost_summary=self.cost_tracker.to_dict(),
            total_latency_ms=(time.time() - start_time) * 1000,
            error_message=message,
        )
