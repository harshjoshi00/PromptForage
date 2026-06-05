"""
Shared types used across all pipeline stages.
These are the atomic building blocks that every IR references.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field as PydanticField


# --- Enums ---

class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    TEXT = "text"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    PASSWORD = "password"
    JSON = "json"
    UUID = "uuid"
    ENUM = "enum"


class RelationType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ComponentType(str, Enum):
    FORM = "form"
    TABLE = "table"
    CHART = "chart"
    CARD = "card"
    LIST = "list"
    DETAIL = "detail"
    STATS = "stats"
    NAVIGATION = "navigation"


class LayoutType(str, Enum):
    GRID = "grid"
    FLEX = "flex"
    SIDEBAR = "sidebar"
    STACK = "stack"
    TABS = "tabs"


# --- Shared Models ---

class Entity(BaseModel):
    """A domain entity extracted from user intent."""
    name: str
    description: str = ""


class Field(BaseModel):
    """A single field on an entity."""
    name: str
    type: FieldType = FieldType.STRING
    required: bool = True
    description: str = ""


class Relation(BaseModel):
    """A relationship between two entities."""
    source: str
    target: str
    type: RelationType = RelationType.ONE_TO_MANY
    field: str = ""  # FK field name


class Role(BaseModel):
    """A user role in the system."""
    name: str
    description: str = ""


class Permission(BaseModel):
    """A permission rule binding role → entity → action."""
    role: str
    entity: str
    actions: list[str] = PydanticField(default_factory=lambda: ["read"])


class BusinessRule(BaseModel):
    """A business logic rule with condition and action."""
    name: str
    description: str = ""
    condition: str = ""
    action: str = ""
    entities_involved: list[str] = PydanticField(default_factory=list)
