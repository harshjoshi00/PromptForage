"""
Evaluation Metrics — models for tracking pipeline performance per prompt.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class PromptResult(BaseModel):
    """Result of running a single prompt through the pipeline."""
    prompt_id: str
    prompt_name: str
    prompt_text: str
    category: str = "real"  # real, vague, conflicting, etc.
    success: bool
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_retries: int = 0
    stages_passed: int = 0
    stages_total: int = 4
    failure_stage: str = ""
    failure_type: str = ""
    error_message: str = ""
    entities_generated: int = 0
    endpoints_generated: int = 0
    tables_generated: int = 0
    pages_generated: int = 0
    runtime_executable: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EvaluationSummary(BaseModel):
    """Aggregated metrics across all prompts."""
    total_prompts: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost_usd: float = 0.0
    avg_retries: float = 0.0
    total_cost_usd: float = 0.0
    failure_breakdown: dict[str, int] = Field(default_factory=dict)
    category_results: dict[str, dict] = Field(default_factory=dict)
    results: list[PromptResult] = Field(default_factory=list)

    def compute(self, results: list[PromptResult]) -> None:
        """Compute summary from individual results."""
        self.results = results
        self.total_prompts = len(results)
        self.successful = sum(1 for r in results if r.success)
        self.failed = self.total_prompts - self.successful
        self.success_rate = (
            round(self.successful / self.total_prompts * 100, 1)
            if self.total_prompts > 0
            else 0
        )

        latencies = [r.total_latency_ms for r in results if r.success]
        costs = [r.total_cost_usd for r in results]
        retries = [r.total_retries for r in results]

        self.avg_latency_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0
        self.avg_cost_usd = round(sum(costs) / len(costs), 6) if costs else 0
        self.avg_retries = round(sum(retries) / len(retries), 2) if retries else 0
        self.total_cost_usd = round(sum(costs), 4)

        # Failure breakdown
        self.failure_breakdown = {}
        for r in results:
            if not r.success:
                ft = r.failure_type or "unknown"
                self.failure_breakdown[ft] = self.failure_breakdown.get(ft, 0) + 1

        # Per-category results
        categories: dict[str, list[PromptResult]] = {}
        for r in results:
            cat = r.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        self.category_results = {}
        for cat, cat_results in categories.items():
            cat_success = sum(1 for r in cat_results if r.success)
            self.category_results[cat] = {
                "total": len(cat_results),
                "success": cat_success,
                "success_rate": round(cat_success / len(cat_results) * 100, 1),
            }
