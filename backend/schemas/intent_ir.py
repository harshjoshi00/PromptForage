"""
Stage 1 Output: IntentIR
The "lexer" output — raw user prompt parsed into structured intent.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from .common import Priority


class Feature(BaseModel):
    """A single feature extracted from the user prompt."""
    name: str
    description: str
    priority: Priority = Priority.MEDIUM
    requires_auth: bool = False
    target_roles: list[str] = Field(default_factory=list)


class IntentIR(BaseModel):
    """
    Intermediate Representation from Stage 1 (Lexer).
    Captures WHAT the user wants without deciding HOW to build it.
    """
    app_name: str
    app_description: str
    app_type: str  # crm, ecommerce, saas, dashboard, social, marketplace, etc.
    features: list[Feature] = Field(min_length=1)
    entities: list[str] = Field(min_length=1)  # raw entity names
    roles: list[str] = Field(default_factory=lambda: ["admin", "user"])
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ambiguities_detected: list[str] = Field(default_factory=list)
    original_prompt: str = ""
