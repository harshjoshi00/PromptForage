"""
Stage 4: Optimizer — Refinement Layer
Refines SchemaIR into the final AppSpec with cross-layer consistency.
Analogous to a compiler's optimizer: IR → optimized IR.
"""

from __future__ import annotations
import json
import logging

from backend.llm.client import LLMClient
from backend.llm.prompts import STAGE_4_SYSTEM, STAGE_4_USER
from backend.schemas.schema_ir import SchemaIR
from backend.schemas.app_spec import AppSpec
from backend.schemas.design_ir import DesignIR

logger = logging.getLogger(__name__)

STAGE_NAME = "stage_4_optimizer"


def run(
    schema: SchemaIR,
    design: DesignIR,
    original_prompt: str,
    llm: LLMClient,
) -> AppSpec:
    """
    Refine schemas into the final production-ready AppSpec.

    Args:
        schema: SchemaIR from Stage 3.
        design: DesignIR from Stage 2 (for business rules).
        original_prompt: The user's original input prompt.
        llm: LLM client instance.

    Returns:
        AppSpec — final, validated, production-ready config.

    Raises:
        ValidationError: If LLM output doesn't match AppSpec schema.
        LLMError: If LLM call fails after retries.
    """
    logger.info(f"[{STAGE_NAME}] Starting refinement...")

    schema_json = schema.model_dump_json(indent=2)
    business_rules_json = json.dumps(
        [r.model_dump() for r in design.business_rules], indent=2
    )

    user_prompt = STAGE_4_USER.format(
        original_prompt=original_prompt,
        business_rules_json=business_rules_json,
        schema_json=schema_json,
    )

    raw_output = llm.generate(
        system_prompt=STAGE_4_SYSTEM,
        user_prompt=user_prompt,
        stage=STAGE_NAME,
        max_tokens=16384,
    )

    # Inject generated_at and original_prompt into metadata
    if "metadata" in raw_output:
        raw_output["metadata"]["original_prompt"] = original_prompt

    # Validate against Pydantic schema
    app_spec = AppSpec.model_validate(raw_output)

    logger.info(
        f"[{STAGE_NAME}] Refined: "
        f"{len(app_spec.ui.pages)} pages, "
        f"{len(app_spec.api.endpoints)} endpoints, "
        f"{len(app_spec.db.tables)} tables, "
        f"{len(app_spec.business_logic)} business rules"
    )

    return app_spec
