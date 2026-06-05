"""
Cost & token tracker — records every LLM call's token usage and estimated cost.
Provides per-stage and per-pipeline aggregation.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from backend.config import MODEL_COSTS


@dataclass
class CallRecord:
    """A single LLM API call record."""
    stage: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
    is_repair: bool = False


class CostTracker:
    """
    Tracks token usage and cost across the entire pipeline run.
    Thread-safe for single pipeline execution (not concurrent).
    """

    def __init__(self):
        self.records: list[CallRecord] = []

    def record_call(
        self,
        stage: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        is_repair: bool = False,
    ) -> CallRecord:
        """Record a single LLM call and compute its cost."""
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        cost_usd = (
            (prompt_tokens / 1_000_000) * costs["input"]
            + (completion_tokens / 1_000_000) * costs["output"]
        )

        record = CallRecord(
            stage=stage,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=round(cost_usd, 6),
            latency_ms=round(latency_ms, 2),
            is_repair=is_repair,
        )
        self.records.append(record)
        return record

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.records)

    @property
    def total_cost(self) -> float:
        return round(sum(r.cost_usd for r in self.records), 6)

    @property
    def total_latency_ms(self) -> float:
        return round(sum(r.latency_ms for r in self.records), 2)

    @property
    def total_calls(self) -> int:
        return len(self.records)

    @property
    def repair_calls(self) -> int:
        return sum(1 for r in self.records if r.is_repair)

    def get_stage_summary(self) -> dict[str, dict]:
        """Get per-stage aggregated metrics."""
        stages: dict[str, dict] = {}
        for r in self.records:
            if r.stage not in stages:
                stages[r.stage] = {
                    "calls": 0,
                    "repair_calls": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "latency_ms": 0.0,
                }
            s = stages[r.stage]
            s["calls"] += 1
            s["repair_calls"] += int(r.is_repair)
            s["total_tokens"] += r.total_tokens
            s["cost_usd"] = round(s["cost_usd"] + r.cost_usd, 6)
            s["latency_ms"] = round(s["latency_ms"] + r.latency_ms, 2)
        return stages

    def to_dict(self) -> dict:
        """Full summary for API response / metrics dashboard."""
        return {
            "total_calls": self.total_calls,
            "repair_calls": self.repair_calls,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
            "total_latency_ms": self.total_latency_ms,
            "per_stage": self.get_stage_summary(),
        }

    def reset(self):
        """Clear all records for a new pipeline run."""
        self.records.clear()
