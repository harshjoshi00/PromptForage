"""
Stage 2: Parser — System Design
Converts IntentIR into DesignIR with concrete entities, fields, relationships.
Analogous to a compiler's parser: tokens → AST (system design).
"""

from __future__ import annotations
import json
import logging

from backend.llm.client import LLMClient
from backend.llm.prompts import STAGE_2_SYSTEM, STAGE_2_USER
from backend.schemas.intent_ir import IntentIR
from backend.schemas.design_ir import DesignIR

logger = logging.getLogger(__name__)

STAGE_NAME = "stage_2_parser"


def run(intent: IntentIR, llm: LLMClient) -> DesignIR:
    """
    Convert structured intent into a concrete system design.

    Args:
        intent: IntentIR from Stage 1.
        llm: LLM client instance.

    Returns:
        DesignIR — validated system design with entities, roles, pages.

    Raises:
        ValidationError: If LLM output doesn't match DesignIR schema.
        LLMError: If LLM call fails after retries.
    """
    logger.info(f"[{STAGE_NAME}] Starting system design...")

    intent_json = intent.model_dump_json(indent=2)
    user_prompt = STAGE_2_USER.format(intent_json=intent_json)

    raw_output = llm.generate(
        system_prompt=STAGE_2_SYSTEM,
        user_prompt=user_prompt,
        stage=STAGE_NAME,
        max_tokens=8192,
    )

    # Validate against Pydantic schema
    design = DesignIR.model_validate(raw_output)

    logger.info(
        f"[{STAGE_NAME}] Designed: "
        f"{len(design.entities)} entities, "
        f"{len(design.roles)} roles, "
        f"{len(design.pages)} pages, "
        f"{len(design.business_rules)} business rules"
    )

    return design
