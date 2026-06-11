"""
Baseline Evaluation Module — handles scoring stage outputs against baseline criteria and refining them.
"""

from __future__ import annotations
import json
import logging
from typing import Any

from backend.llm.client import LLMClient
from backend.validation.validator import validate
from backend.validation.validation_report import ErrorSeverity
from backend.schemas.intent_ir import IntentIR
from backend.schemas.design_ir import DesignIR
from backend.schemas.schema_ir import SchemaIR
from backend.schemas.app_spec import AppSpec

logger = logging.getLogger(__name__)

# Baseline Targets per Stage
BASELINE_TARGETS = {
    "stage_1_lexer": 80,
    "stage_2_parser": 80,
    "stage_3_ir_generator": 80,
    "stage_4_optimizer": 85,
}

# --- Prompt Constants ---

EVALUATION_SYSTEM_PROMPT = """You are a Baseline Evaluation Engine for a software compiler pipeline.
Your job is to critically evaluate the output of a specific compiler stage against the original user prompt and the stage inputs.

You must score the output on three dimensions (0-100):
1. Completeness: Does it capture all explicit and implicit requirements from the prompt?
2. Correctness: Are there missing fields, incorrect types, or design errors for this stage?
3. Logic: Is the output structured logically, coherent, and consistent?

Calculate the overall_score as a weighted average. You must also provide a detailed critique, list any missing elements, and give concrete suggestions for improvement.

You MUST output valid JSON matching this exact schema:
{
  "completeness_score": integer (0-100),
  "accuracy_score": integer (0-100),
  "logic_score": integer (0-100),
  "overall_score": integer (0-100),
  "critique": "string — constructive detailed critique of the output",
  "missing_elements": ["string — specific items missing or incorrect"],
  "suggestions": ["string — how to fix the errors or improve"]
}

ONLY output JSON. No explanation or markdown formatting."""

EVALUATION_USER_PROMPT = """Evaluate the output of stage "{stage_name}".

Original User Prompt:
---
{original_prompt}
---

Stage Inputs (Previous Stages context):
---
{stage_inputs}
---

Generated Stage Output:
---
{stage_output}
---

Provide a critical score and detailed feedback."""

# --- Stage Refiner System Prompts ---

STAGE_1_REFINER_SYSTEM = """You are an Intent Extraction Refinement Engine.
You have a previous IntentIR draft, the original prompt, and user feedback.
Your job is to update the IntentIR draft by incorporating the user feedback while preserving all other valid features, entities, roles, and constraints.

You MUST output valid JSON matching this exact schema:
{
  "app_name": "string — short name for the app (snake_case)",
  "app_description": "string — one-line description",
  "app_type": "string — one of: crm, ecommerce, saas, dashboard, social, marketplace, cms, project_management, booking, analytics, inventory, education, healthcare, finance, custom",
  "features": [
    {
      "name": "string — feature name (snake_case)",
      "description": "string — what this feature does",
      "priority": "high | medium | low",
      "requires_auth": true/false,
      "target_roles": ["role1", "role2"]
    }
  ],
  "entities": ["Entity1", "Entity2"],
  "roles": ["admin", "user"],
  "constraints": ["constraint1"],
  "assumptions": ["assumption"],
  "ambiguities_detected": ["ambiguity"]
}

ONLY output JSON. No markdown or explanation."""

STAGE_2_REFINER_SYSTEM = """You are a System Design Refinement Engine.
You have the final IntentIR, the previous DesignIR draft, and user feedback.
Your job is to update the DesignIR draft to incorporate the user feedback while keeping it consistent with the IntentIR.

You MUST output valid JSON matching this exact schema:
{
  "entities": [
    {
      "name": "string — PascalCase entity name",
      "description": "string",
      "fields": [
        {
          "name": "string — snake_case field name",
          "type": "string | integer | float | boolean | datetime | date | text | email | url | phone | password | json | uuid | enum",
          "required": true/false,
          "unique": true/false,
          "default": null,
          "constraints": [],
          "description": "string"
        }
      ],
      "relationships": [
        {
          "target_entity": "string — PascalCase entity name",
          "type": "one_to_one | one_to_many | many_to_many",
          "foreign_key_field": "string",
          "description": "string"
        }
      ]
    }
  ],
  "roles": [
    {
      "name": "string",
      "description": "string",
      "permissions": [
        {
          "entity": "string — entity name",
          "actions": ["create", "read", "update", "delete"]
        }
      ],
      "is_default": true/false
    }
  ],
  "pages": [
    {
      "name": "string — snake_case page name",
      "description": "string",
      "associated_entities": ["Entity1"],
      "access_roles": ["admin", "user"],
      "features": ["feature_name"]
    }
  ],
  "business_rules": [
    {
      "name": "string",
      "description": "string",
      "condition": "string",
      "action": "string",
      "entities_involved": ["Entity1"]
    }
  ]
}

ONLY output JSON. No markdown or explanation."""

STAGE_3_REFINER_SYSTEM = """You are a Schema Refinement Engine.
You have the DesignIR context, the previous SchemaIR draft, and user feedback.
Your job is to update the SchemaIR draft to incorporate the user feedback while maintaining perfect cross-layer consistency between UI, API, DB, and Auth schemas.

You MUST output valid JSON matching this exact schema:
{
  "ui_schema": {
    "pages": [
      {
        "name": "string",
        "route": "string",
        "title": "string",
        "layout": "grid | flex | sidebar | stack | tabs",
        "components": [
          {
            "id": "string",
            "type": "form | table | chart | card | list | detail | stats | navigation",
            "title": "string",
            "data_source": "string",
            "fields": [
              {"name": "string", "label": "string", "type": "text | number | email | select | checkbox | date | textarea | password | tel | url", "required": true/false, "options": []}
            ],
            "actions": ["create", "edit", "delete", "view"]
          }
        ],
        "access_roles": ["admin"],
        "is_public": false
      }
    ],
    "navigation": [{"name": "string", "route": "string", "icon": "string"}],
    "theme": "default"
  },
  "api_schema": {
    "base_path": "/api/v1",
    "endpoints": [
      {
        "path": "string",
        "method": "GET | POST | PUT | PATCH | DELETE",
        "summary": "string",
        "request_params": [{"name": "string", "type": "string", "required": true, "location": "body | path | query"}],
        "response_fields": [{"name": "string", "type": "string"}],
        "auth_required": true,
        "allowed_roles": ["admin"],
        "entity": "string"
      }
    ]
  },
  "db_schema": {
    "tables": [
      {
        "name": "string",
        "columns": [
          {"name": "string", "type": "string", "primary_key": false, "nullable": true, "unique": false, "default": null, "foreign_key": null}
        ],
        "indexes": [{"name": "string", "columns": ["col"], "unique": false}]
      }
    ]
  },
  "auth_schema": {
    "roles": [{"name": "string", "display_name": "string", "is_default": false, "inherits_from": null}],
    "rules": [{"role": "string", "resource": "string", "actions": ["read"], "conditions": []}],
    "session_type": "jwt",
    "password_hashing": "bcrypt"
  }
}

ONLY output JSON. No markdown or explanation."""

STAGE_4_REFINER_SYSTEM = """You are an AppSpec Refinement Engine.
You have the SchemaIR context, DesignIR context, original prompt, previous AppSpec draft, and user feedback.
Your job is to update the AppSpec draft to incorporate the user feedback, keeping everything consistent and production-ready.

You MUST output valid JSON matching this exact schema:
{
  "metadata": {
    "name": "string",
    "description": "string",
    "version": "1.0.0",
    "assumptions": ["string"]
  },
  "ui": { ... ui schema matching stage 3 format ... },
  "api": { ... api schema matching stage 3 format ... },
  "db": { ... db schema matching stage 3 format ... },
  "auth": { ... auth schema matching stage 3 format ... },
  "business_logic": [
    {
      "name": "string",
      "description": "string",
      "condition": "string",
      "action": "string",
      "entities_involved": ["string"]
    }
  ]
}

ONLY output JSON. No markdown or explanation."""

# In-memory attempts tracking for Mock LLM demo mode
MOCK_EVAL_ATTEMPTS = {}


def evaluate_stage_baseline(
    stage_name: str,
    stage_output: dict[str, Any],
    original_prompt: str,
    stage_inputs: dict[str, Any],
    llm: LLMClient,
) -> dict[str, Any]:
    """
    Evaluate stage output against baseline score.
    Factors in validation errors and asks LLM to critique and score completeness/accuracy/logic.
    """
    baseline_target = BASELINE_TARGETS.get(stage_name, 80)

    # 1. Run local validation engine checks
    report = validate(stage_output, stage_name)
    validation_errors_list = []
    
    critical_errors_count = 0
    warning_errors_count = 0
    
    for err in report.errors:
        if err.severity == ErrorSeverity.CRITICAL:
            critical_errors_count += 1
        else:
            warning_errors_count += 1
        validation_errors_list.append(f"CRITICAL: [{err.category.value}] {err.message} at {err.field_path}")
        
    for wrn in report.warnings:
        warning_errors_count += 1
        validation_errors_list.append(f"WARNING: [{wrn.category.value}] {wrn.message} at {wrn.field_path}")

    # 2. Check for MOCK_LLM
    from backend.config import MOCK_LLM
    if MOCK_LLM:
        key = f"{original_prompt[:50]}_{stage_name}"
        attempts = MOCK_EVAL_ATTEMPTS.get(key, 0)
        MOCK_EVAL_ATTEMPTS[key] = attempts + 1

        if attempts == 0:
            # First try: Below baseline
            mock_score = 72
            critique = f"The generated configuration for {stage_name} covers basics but lacks detailed schema fields and has some inconsistencies."
            missing_elements = ["Specific type definitions for complex fields", "Explicit role check rules"]
            suggestions = ["Add custom properties to entities", "Verify all CRUD actions are linked to authenticated roles"]
        else:
            # Second try: Above baseline
            mock_score = 92
            critique = f"Feedback incorporated. {stage_name} output now satisfies all completeness criteria and has 0 validation errors."
            missing_elements = []
            suggestions = []
            
        # Deduct validation penalty for realism if there are any real validation failures
        penalty = (critical_errors_count * 15) + (warning_errors_count * 5)
        overall_score = max(0, mock_score - penalty)
        passed = overall_score >= baseline_target
        
        # Merge validation logs into critique
        if validation_errors_list:
            critique += "\n\nValidation Engine Errors Found:\n" + "\n".join(validation_errors_list)
            
        return {
            "score": overall_score,
            "baseline": baseline_target,
            "passed": passed,
            "critique": critique,
            "missing_elements": missing_elements,
            "suggestions": suggestions,
            "completeness_score": mock_score,
            "accuracy_score": max(0, mock_score - penalty),
            "logic_score": mock_score
        }

    # 3. Call OpenAI for LLM Evaluation
    stage_inputs_str = json.dumps(stage_inputs, indent=2)
    stage_output_str = json.dumps(stage_output, indent=2)
    
    user_prompt = EVALUATION_USER_PROMPT.format(
        stage_name=stage_name,
        original_prompt=original_prompt,
        stage_inputs=stage_inputs_str,
        stage_output=stage_output_str
    )

    try:
        raw_eval = llm.generate(
            system_prompt=EVALUATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            stage="baseline_evaluate",
            max_tokens=2048
        )
        
        overall_score = raw_eval.get("overall_score", 75)
        critique = raw_eval.get("critique", "No critique provided.")
        missing_elements = raw_eval.get("missing_elements", [])
        suggestions = raw_eval.get("suggestions", [])
        
        # Factor in code validation penalties
        penalty = (critical_errors_count * 15) + (warning_errors_count * 5)
        final_score = max(0, min(100, overall_score - penalty))
        
        passed = final_score >= baseline_target
        
        # Append validation engine logs to the critique
        if validation_errors_list:
            critique += "\n\nValidation Engine Errors:\n" + "\n".join(validation_errors_list)
            missing_elements.extend([f"Validation Issue: {x}" for x in validation_errors_list[:3]])
            
        return {
            "score": final_score,
            "baseline": baseline_target,
            "passed": passed,
            "critique": critique,
            "missing_elements": missing_elements,
            "suggestions": suggestions,
            "completeness_score": raw_eval.get("completeness_score", 75),
            "accuracy_score": raw_eval.get("accuracy_score", 75),
            "logic_score": raw_eval.get("logic_score", 75)
        }
    except Exception as e:
        logger.error(f"Baseline evaluation failed: {e}", exc_info=True)
        # Graceful fallback: if eval fails, generate score based on validation report
        final_score = max(0, 100 - (critical_errors_count * 20) - (warning_errors_count * 5))
        return {
            "score": final_score,
            "baseline": baseline_target,
            "passed": final_score >= baseline_target,
            "critique": f"Evaluation engine fallback. Error evaluating with LLM: {str(e)}",
            "missing_elements": validation_errors_list[:3],
            "suggestions": ["Resolve structural and semantic validator errors to increase score."],
            "completeness_score": final_score,
            "accuracy_score": final_score,
            "logic_score": final_score
        }


def refine_stage_output(
    stage_name: str,
    prompt: str,
    previous_output: dict[str, Any],
    feedback: str,
    stage_inputs: dict[str, Any],
    llm: LLMClient,
) -> dict[str, Any]:
    """
    Runs the LLM refiner to incorporate user feedback into a stage's previous output.
    """
    logger.info(f"[Baseline Refiner] Refining stage {stage_name}...")
    
    # 1. Determine Refiner Prompts based on stage
    if stage_name == "stage_1_lexer":
        system_prompt = STAGE_1_REFINER_SYSTEM
        user_prompt = f"Original Prompt: {prompt}\n\nPrevious IntentIR:\n{json.dumps(previous_output, indent=2)}\n\nUser Feedback: {feedback}\n\nUpdate and output the corrected IntentIR JSON."
        model_class = IntentIR
    elif stage_name == "stage_2_parser":
        system_prompt = STAGE_2_REFINER_SYSTEM
        user_prompt = f"IntentIR Context:\n{json.dumps(stage_inputs.get('stage_1_lexer', {}), indent=2)}\n\nPrevious DesignIR:\n{json.dumps(previous_output, indent=2)}\n\nUser Feedback: {feedback}\n\nUpdate and output the corrected DesignIR JSON."
        model_class = DesignIR
    elif stage_name == "stage_3_ir_generator":
        system_prompt = STAGE_3_REFINER_SYSTEM
        user_prompt = f"DesignIR Context:\n{json.dumps(stage_inputs.get('stage_2_parser', {}), indent=2)}\n\nPrevious SchemaIR:\n{json.dumps(previous_output, indent=2)}\n\nUser Feedback: {feedback}\n\nUpdate and output the corrected SchemaIR JSON."
        model_class = SchemaIR
    elif stage_name == "stage_4_optimizer":
        system_prompt = STAGE_4_REFINER_SYSTEM
        design_ctx = json.dumps(stage_inputs.get("stage_2_parser", {}), indent=2)
        schema_ctx = json.dumps(stage_inputs.get("stage_3_ir_generator", {}), indent=2)
        user_prompt = f"Original Prompt: {prompt}\nDesignIR context:\n{design_ctx}\nSchemaIR context:\n{schema_ctx}\n\nPrevious AppSpec:\n{json.dumps(previous_output, indent=2)}\n\nUser Feedback: {feedback}\n\nUpdate and output the corrected AppSpec JSON."
        model_class = AppSpec
    else:
        raise ValueError(f"Unknown stage: {stage_name}")

    # 2. Call LLM to refine
    raw_output = llm.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        stage=f"{stage_name}_refine",
        max_tokens=8192 if stage_name in ("stage_1_lexer", "stage_2_parser") else 16384
    )

    # 3. Validate structure with Pydantic model validate
    validated_model = model_class.model_validate(raw_output)
    return validated_model.model_dump()
