"""
Retry Policy — defines budget, backoff, and convergence detection for repairs.
"""

from __future__ import annotations
import time
import logging
from dataclasses import dataclass, field

from backend.config import MAX_RETRIES_PER_STAGE, RETRY_BACKOFF_BASE

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """
    Controls how many times a stage can be repaired and how long to wait between attempts.
    Includes convergence detection: if errors don't change between attempts, abort early.
    """
    max_retries: int = MAX_RETRIES_PER_STAGE
    backoff_base: float = RETRY_BACKOFF_BASE
    current_attempt: int = 0
    previous_error_hashes: list[str] = field(default_factory=list)

    @property
    def retries_remaining(self) -> int:
        return max(0, self.max_retries - self.current_attempt)

    @property
    def is_exhausted(self) -> bool:
        return self.current_attempt >= self.max_retries

    def record_attempt(self, error_summary: str) -> None:
        """Record a repair attempt and check for convergence."""
        self.current_attempt += 1
        self.previous_error_hashes.append(hash(error_summary))

    def has_converged(self) -> bool:
        """
        Check if errors are not improving (same errors on last 2 attempts).
        If so, further retries are unlikely to help.
        """
        if len(self.previous_error_hashes) < 2:
            return False
        return self.previous_error_hashes[-1] == self.previous_error_hashes[-2]

    def wait_backoff(self) -> None:
        """Sleep for exponential backoff duration."""
        wait_time = self.backoff_base ** (self.current_attempt - 1)
        logger.info(f"[RetryPolicy] Waiting {wait_time:.1f}s before retry...")
        time.sleep(wait_time)

    def reset(self) -> None:
        """Reset for a new stage."""
        self.current_attempt = 0
        self.previous_error_hashes.clear()
