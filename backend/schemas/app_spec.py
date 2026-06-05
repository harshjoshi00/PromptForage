"""
Stage 4 Output: AppSpec
The final, refined, production-ready application specification.
This is the "compiled" output — ready for runtime execution.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from .schema_ir import UISchema, APISchema, DBSchema, AuthSchema
from .common import BusinessRule


class AppMetadata(BaseModel):
    """Metadata about the generated application."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    generator_version: str = "1.0.0"
    original_prompt: str = ""
    assumptions: list[str] = Field(default_factory=list)


class AppSpec(BaseModel):
    """
    Final output from Stage 4 (Optimizer).
    The complete, validated, cross-referenced application specification.
    This is the compiler's final output — ready to be executed by a runtime.
    """
    metadata: AppMetadata
    ui: UISchema
    api: APISchema
    db: DBSchema
    auth: AuthSchema
    business_logic: list[BusinessRule] = Field(default_factory=list)
