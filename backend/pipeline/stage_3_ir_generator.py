"""
Stage 3: IR Generator — Schema Generation
Converts DesignIR into SchemaIR (UI + API + DB + Auth schemas).
Analogous to a compiler's IR generator: AST → intermediate representation.
"""

from __future__ import annotations
import json
import logging

from backend.llm.client import LLMClient
from backend.llm.prompts import STAGE_3_SYSTEM, STAGE_3_USER
from backend.schemas.design_ir import DesignIR
from backend.schemas.schema_ir import SchemaIR

logger = logging.getLogger(__name__)

STAGE_NAME = "stage_3_ir_generator"


def run(design: DesignIR, llm: LLMClient) -> SchemaIR:
    """
    Generate complete technical schemas from system design.

    Args:
        design: DesignIR from Stage 2.
        llm: LLM client instance.

    Returns:
        SchemaIR — validated UI + API + DB + Auth schemas.

    Raises:
        ValidationError: If LLM output doesn't match SchemaIR schema.
        LLMError: If LLM call fails after retries.
    """
    logger.info(f"[{STAGE_NAME}] Starting schema generation...")

    design_json = design.model_dump_json(indent=2)
    user_prompt = STAGE_3_USER.format(design_json=design_json)

    raw_output = llm.generate(
        system_prompt=STAGE_3_SYSTEM,
        user_prompt=user_prompt,
        stage=STAGE_NAME,
        max_tokens=16384,
    )

    # Validate against Pydantic schema
    schema = SchemaIR.model_validate(raw_output)

    logger.info(
        f"[{STAGE_NAME}] Generated: "
        f"{len(schema.ui_schema.pages)} pages, "
        f"{len(schema.api_schema.endpoints)} endpoints, "
        f"{len(schema.db_schema.tables)} tables, "
        f"{len(schema.auth_schema.roles)} roles"
    )

    return schema
