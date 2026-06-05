"""
Stage 2 Output: DesignIR
The "parser" output — intent converted into concrete system design.
Entities get fields, relationships get defined, roles get permissions.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from .common import FieldType, RelationType, BusinessRule


class FieldDesign(BaseModel):
    """A concrete field with type and constraints."""
    name: str
    type: FieldType = FieldType.STRING
    required: bool = True
    unique: bool = False
    default: str | None = None
    constraints: list[str] = Field(default_factory=list)
    description: str = ""


class RelationDesign(BaseModel):
    """A concrete relationship between two entities."""
    target_entity: str
    type: RelationType = RelationType.ONE_TO_MANY
    foreign_key_field: str = ""
    description: str = ""


class EntityDesign(BaseModel):
    """Full entity design with fields and relationships."""
    name: str
    description: str = ""
    fields: list[FieldDesign] = Field(min_length=1)
    relationships: list[RelationDesign] = Field(default_factory=list)


class PermissionDesign(BaseModel):
    """What a role can do on a specific entity."""
    entity: str
    actions: list[str] = Field(default_factory=lambda: ["read"])


class RoleDesign(BaseModel):
    """A role with its full permission set."""
    name: str
    description: str = ""
    permissions: list[PermissionDesign] = Field(default_factory=list)
    is_default: bool = False


class PageDesign(BaseModel):
    """A UI page derived from features."""
    name: str
    description: str = ""
    associated_entities: list[str] = Field(default_factory=list)
    access_roles: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)


class DesignIR(BaseModel):
    """
    Intermediate Representation from Stage 2 (Parser).
    Concrete system design: entities with fields, roles with permissions,
    pages derived from features, and business rules.
    """
    entities: list[EntityDesign] = Field(min_length=1)
    roles: list[RoleDesign] = Field(min_length=1)
    pages: list[PageDesign] = Field(min_length=1)
    business_rules: list[BusinessRule] = Field(default_factory=list)
