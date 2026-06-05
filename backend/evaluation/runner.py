"""
Evaluation Runner — runs all test prompts through the pipeline and collects metrics.
Produces a detailed report with per-prompt breakdown and aggregated summary.
"""

from __future__ import annotations
import json
import logging
import time
from pathlib import Path

from backend.config import EVAL_RESULTS_DIR
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.evaluation.test_prompts import REAL_PROMPTS, EDGE_CASE_PROMPTS, ALL_PROMPTS
from backend.evaluation.metrics import PromptResult, EvaluationSummary

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """
    Runs all 20 test prompts through the full pipeline and collects metrics.
    Results are saved to disk for the metrics dashboard.
    """

    def __init__(self):
        self.results: list[PromptResult] = []

    def run_all(self, prompts: list[dict] | None = None) -> EvaluationSummary:
        """Run all prompts and return aggregated summary."""
        test_prompts = prompts or ALL_PROMPTS

        logger.info(f"[Eval] Starting evaluation with {len(test_prompts)} prompts...")
        self.results = []

        for i, prompt_data in enumerate(test_prompts):
            prompt_id = prompt_data.get("id", f"prompt_{i}")
            prompt_name = prompt_data.get("name", "Unknown")
            prompt_text = prompt_data.get("prompt", "")
            category = prompt_data.get("category", "real")

            logger.info(f"\n[Eval] {'=' * 40}")
            logger.info(f"[Eval] Running [{i + 1}/{len(test_prompts)}]: {prompt_name}")
            logger.info(f"[Eval] {'=' * 40}")

            result = self._run_single(prompt_id, prompt_name, prompt_text, category)
            self.results.append(result)

            logger.info(
                f"[Eval] Result: {'✅ PASS' if result.success else '❌ FAIL'} "
                f"| Latency: {result.total_latency_ms:.0f}ms "
                f"| Cost: ${result.total_cost_usd:.4f} "
                f"| Retries: {result.total_retries}"
            )

        # Compute summary
        summary = EvaluationSummary()
        summary.compute(self.results)

        # Save results
        self._save_results(summary)

        logger.info(f"\n[Eval] {'=' * 50}")
        logger.info(f"[Eval] EVALUATION COMPLETE")
        logger.info(f"[Eval] Success Rate: {summary.success_rate}%")
        logger.info(f"[Eval] Total Cost: ${summary.total_cost_usd:.4f}")
        logger.info(f"[Eval] Avg Latency: {summary.avg_latency_ms:.0f}ms")
        logger.info(f"[Eval] {'=' * 50}")

        return summary

    def _run_single(
        self, prompt_id: str, prompt_name: str, prompt_text: str, category: str
    ) -> PromptResult:
        """Run a single prompt through the pipeline."""
        start_time = time.time()

        try:
            orchestrator = PipelineOrchestrator()
            pipeline_result = orchestrator.run(prompt_text)

            latency = (time.time() - start_time) * 1000
            cost_data = pipeline_result.cost_summary

            stages_passed = sum(
                1 for s in pipeline_result.stages if s.success
            )
            total_retries = sum(
                s.repair_attempts for s in pipeline_result.stages
            )

            # Extract counts from app_spec if success
            entities = endpoints = tables = pages = 0
            if pipeline_result.success and pipeline_result.app_spec_dict:
                spec = pipeline_result.app_spec_dict
                pages = len(spec.get("ui", {}).get("pages", []))
                endpoints = len(spec.get("api", {}).get("endpoints", []))
                tables = len(spec.get("db", {}).get("tables", []))
                entities = tables  # approximate

            failure_stage = ""
            failure_type = ""
            if not pipeline_result.success:
                for s in pipeline_result.stages:
                    if not s.success:
                        failure_stage = s.stage
                        break
                failure_type = "pipeline_error"

            return PromptResult(
                prompt_id=prompt_id,
                prompt_name=prompt_name,
                prompt_text=prompt_text,
                category=category,
                success=pipeline_result.success,
                total_latency_ms=round(latency, 2),
                total_cost_usd=cost_data.get("total_cost_usd", 0),
                total_tokens=cost_data.get("total_tokens", 0),
                total_retries=total_retries,
                stages_passed=stages_passed,
                failure_stage=failure_stage,
                failure_type=failure_type,
                error_message=pipeline_result.error_message,
                entities_generated=entities,
                endpoints_generated=endpoints,
                tables_generated=tables,
                pages_generated=pages,
                runtime_executable=pipeline_result.success,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"[Eval] Prompt '{prompt_name}' crashed: {e}")
            return PromptResult(
                prompt_id=prompt_id,
                prompt_name=prompt_name,
                prompt_text=prompt_text,
                category=category,
                success=False,
                total_latency_ms=round(latency, 2),
                failure_type="crash",
                error_message=str(e),
            )

    def _save_results(self, summary: EvaluationSummary) -> None:
        """Save evaluation results to JSON file."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_path = Path(EVAL_RESULTS_DIR) / "latest_evaluation.json"
        output_path_timestamped = Path(EVAL_RESULTS_DIR) / f"evaluation_{timestamp}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = summary.model_dump()
        
        for path in [output_path, output_path_timestamped]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

        logger.info(f"[Eval] Results saved to: {output_path} and {output_path_timestamped}")


def run_evaluation():
    """Entry point for running evaluation from CLI."""
    runner = EvaluationRunner()
    summary = runner.run_all()
    return summary


if __name__ == "__main__":
    run_evaluation()
