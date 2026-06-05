"""
Stage 3 Output: SchemaIR
The "IR generator" output — full technical schemas for UI, API, DB, and Auth.
These are the actual configs that could drive a runtime.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from .common import HTTPMethod, ComponentType, LayoutType


# ==================== UI Schema ====================

class UIField(BaseModel):
    """A single field rendered in a UI component."""
    name: str
    label: str = ""
    type: str = "text"  # input type: text, number, email, select, checkbox, etc.
    required: bool = False
    options: list[str] = Field(default_factory=list)  # for select/radio


class UIComponent(BaseModel):
    """A UI component (form, table, chart, etc.) on a page."""
    id: str
    type: ComponentType
    title: str = ""
    data_source: str = ""  # API endpoint this component reads/writes
    fields: list[UIField] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)  # create, edit, delete, etc.


class PageConfig(BaseModel):
    """A full page configuration."""
    name: str
    route: str
    title: str = ""
    layout: LayoutType = LayoutType.STACK
    components: list[UIComponent] = Field(default_factory=list)
    access_roles: list[str] = Field(default_factory=list)
    is_public: bool = False


class UISchema(BaseModel):
    """Complete UI configuration for the application."""
    pages: list[PageConfig] = Field(min_length=1)
    navigation: list[dict] = Field(default_factory=list)  # [{name, route, icon}]
    theme: str = "default"


# ==================== API Schema ====================

class EndpointParam(BaseModel):
    """A parameter (path, query, or body field) for an API endpoint."""
    name: str
    type: str = "string"
    required: bool = True
    location: str = "body"  # body, path, query


class Endpoint(BaseModel):
    """A single API endpoint."""
    path: str
    method: HTTPMethod
    summary: str = ""
    request_params: list[EndpointParam] = Field(default_factory=list)
    response_fields: list[dict] = Field(default_factory=list)  # [{name, type}]
    auth_required: bool = True
    allowed_roles: list[str] = Field(default_factory=list)
    entity: str = ""  # which entity this endpoint operates on


class APISchema(BaseModel):
    """Complete API configuration for the application."""
    base_path: str = "/api/v1"
    endpoints: list[Endpoint] = Field(min_length=1)


# ==================== DB Schema ====================

class Column(BaseModel):
    """A single database column."""
    name: str
    type: str  # SQL-ish type: VARCHAR, INTEGER, BOOLEAN, TIMESTAMP, TEXT, etc.
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: str | None = None
    foreign_key: str | None = None  # "table_name.column_name"


class Index(BaseModel):
    """A database index."""
    name: str
    columns: list[str]
    unique: bool = False


class Table(BaseModel):
    """A single database table."""
    name: str
    columns: list[Column] = Field(min_length=1)
    indexes: list[Index] = Field(default_factory=list)


class DBSchema(BaseModel):
    """Complete database schema for the application."""
    tables: list[Table] = Field(min_length=1)


# ==================== Auth Schema ====================

class AuthRule(BaseModel):
    """An authorization rule: who can do what on which resource."""
    role: str
    resource: str  # entity or page name
    actions: list[str] = Field(default_factory=lambda: ["read"])
    conditions: list[str] = Field(default_factory=list)  # e.g., "own_records_only"


class RoleConfig(BaseModel):
    """A role definition in the auth system."""
    name: str
    display_name: str = ""
    is_default: bool = False
    inherits_from: str | None = None


class AuthSchema(BaseModel):
    """Complete auth configuration for the application."""
    roles: list[RoleConfig] = Field(min_length=1)
    rules: list[AuthRule] = Field(default_factory=list)
    session_type: str = "jwt"
    password_hashing: str = "bcrypt"


# ==================== Combined SchemaIR ====================

class SchemaIR(BaseModel):
    """
    Intermediate Representation from Stage 3 (IR Generator).
    The full technical specification: UI + API + DB + Auth schemas.
    """
    ui_schema: UISchema
    api_schema: APISchema
    db_schema: DBSchema
    auth_schema: AuthSchema
