"""
LLM Client — OpenAI wrapper with JSON mode, retry logic, deterministic settings,
and integrated cost tracking. All pipeline stages call LLMs through this client.
"""

from __future__ import annotations
import json
import time
import logging
from typing import Any

from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError

from backend.config import (
    OPENAI_API_KEY,
    PRIMARY_MODEL,
    FAST_MODEL,
    TEMPERATURE,
    SEED,
    MAX_RETRIES_PER_STAGE,
    RETRY_BACKOFF_BASE,
    MOCK_LLM,
)
from backend.llm.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Centralized LLM client. Every pipeline stage and repair call goes through here.
    Features:
      - JSON mode for structured output
      - Temperature=0 + seed for determinism
      - Automatic retry on transient API errors
      - Token/cost tracking per call
    """

    def __init__(self, cost_tracker: CostTracker | None = None):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.cost_tracker = cost_tracker or CostTracker()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        stage: str = "unknown",
        model: str | None = None,
        use_fast_model: bool = False,
        is_repair: bool = False,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        Call the LLM and return parsed JSON output.

        Args:
            system_prompt: System message defining the stage's role and output format.
            user_prompt: User message with the actual input data.
            stage: Pipeline stage name (for cost tracking).
            model: Override model name. If None, uses PRIMARY or FAST based on flag.
            use_fast_model: If True and no model override, use FAST_MODEL.
            is_repair: Whether this is a repair call (tracked separately).
            max_tokens: Maximum completion tokens.

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            LLMError: If all retries are exhausted or JSON parsing fails.
        """
        if MOCK_LLM:
            logger.info(f"[{stage}] MOCK_LLM is enabled. Returning mock response.")
            from backend.llm.mock_data import get_mock_response
            return get_mock_response(stage, user_prompt)

        selected_model = model or (FAST_MODEL if use_fast_model else PRIMARY_MODEL)
        last_error = None

        for attempt in range(MAX_RETRIES_PER_STAGE):
            raw_content = ""  # Initialize before try block for error handler scope
            try:
                start_time = time.time()

                response = self.client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=TEMPERATURE,
                    seed=SEED,
                    max_tokens=max_tokens,
                )

                latency_ms = (time.time() - start_time) * 1000

                # Track cost
                usage = response.usage
                if usage:
                    self.cost_tracker.record_call(
                        stage=stage,
                        model=selected_model,
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        latency_ms=latency_ms,
                        is_repair=is_repair,
                    )

                # Parse JSON
                raw_content = response.choices[0].message.content or "{}"
                parsed = json.loads(raw_content)

                logger.info(
                    f"[{stage}] LLM call succeeded | model={selected_model} "
                    f"| tokens={usage.total_tokens if usage else '?'} "
                    f"| latency={latency_ms:.0f}ms"
                    f"{'| REPAIR' if is_repair else ''}"
                )

                return parsed

            except json.JSONDecodeError as e:
                last_error = LLMError(
                    f"JSON parse failed on attempt {attempt + 1}: {e}",
                    stage=stage,
                    raw_output=raw_content,
                )
                logger.warning(f"[{stage}] JSON parse error (attempt {attempt + 1}): {e}")

            except (APIError, RateLimitError, APIConnectionError) as e:
                # If it's a quota/billing limit error, automatically fall back to mock data
                # so the local demo application works even without credits.
                if "insufficient_quota" in str(e).lower() or "quota" in str(e).lower():
                    logger.warning(
                        f"[{stage}] OpenAI API Quota Exceeded (429). "
                        "Automatically falling back to mock response for local demo."
                    )
                    from backend.llm.mock_data import get_mock_response
                    return get_mock_response(stage, user_prompt)

                last_error = LLMError(
                    f"API error on attempt {attempt + 1}: {e}",
                    stage=stage,
                )
                logger.warning(f"[{stage}] API error (attempt {attempt + 1}): {e}")

            # Exponential backoff
            if attempt < MAX_RETRIES_PER_STAGE - 1:
                backoff = RETRY_BACKOFF_BASE ** attempt
                logger.info(f"[{stage}] Retrying in {backoff:.1f}s...")
                time.sleep(backoff)

        raise last_error or LLMError("All retries exhausted", stage=stage)


class LLMError(Exception):
    """Raised when the LLM client fails after all retries."""

    def __init__(self, message: str, stage: str = "", raw_output: str = ""):
        super().__init__(message)
        self.stage = stage
        self.raw_output = raw_output
