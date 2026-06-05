"""Schema registry — typed Pydantic models for all pipeline intermediate representations."""

from .common import Entity, Field, Relation, Role, Permission, BusinessRule
from .intent_ir import IntentIR, Feature
from .design_ir import DesignIR, EntityDesign, FieldDesign, RelationDesign, RoleDesign
from .schema_ir import SchemaIR, UISchema, APISchema, DBSchema, AuthSchema
from .app_spec import AppSpec, AppMetadata
