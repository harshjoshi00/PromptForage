"""
Stage 1: Lexer — Intent Extraction
Parses raw natural language prompt into IntentIR.
Analogous to a compiler's lexer: raw text → tokens (structured intent).
"""

from __future__ import annotations
import json
import logging

from backend.llm.client import LLMClient
from backend.llm.prompts import STAGE_1_SYSTEM, STAGE_1_USER
from backend.schemas.intent_ir import IntentIR

logger = logging.getLogger(__name__)

STAGE_NAME = "stage_1_lexer"


def run(prompt: str, llm: LLMClient) -> IntentIR:
    """
    Extract structured intent from a raw user prompt.

    Args:
        prompt: Raw natural language application description.
        llm: LLM client instance.

    Returns:
        IntentIR — validated structured intent.

    Raises:
        ValidationError: If LLM output doesn't match IntentIR schema.
        LLMError: If LLM call fails after retries.
    """
    logger.info(f"[{STAGE_NAME}] Starting intent extraction...")
    logger.debug(f"[{STAGE_NAME}] Input prompt: {prompt[:200]}...")

    user_prompt = STAGE_1_USER.format(prompt=prompt)

    raw_output = llm.generate(
        system_prompt=STAGE_1_SYSTEM,
        user_prompt=user_prompt,
        stage=STAGE_NAME,
        max_tokens=4096,
    )

    # Inject original prompt for traceability
    raw_output["original_prompt"] = prompt

    # Validate against Pydantic schema
    intent = IntentIR.model_validate(raw_output)

    logger.info(
        f"[{STAGE_NAME}] Extracted: "
        f"{len(intent.features)} features, "
        f"{len(intent.entities)} entities, "
        f"{len(intent.roles)} roles, "
        f"{len(intent.assumptions)} assumptions"
    )

    return intent
