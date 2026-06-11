"""
Mock responses for pipeline stages. Used when MOCK_LLM is enabled or API quota is exceeded.
Provides dynamic, schema-valid configurations for any user prompt.

IMPORTANT: Every mock response MUST match its corresponding Pydantic model exactly:
  - Stage 1: IntentIR (schemas/intent_ir.py)
  - Stage 2: DesignIR (schemas/design_ir.py)
  - Stage 3: SchemaIR (schemas/schema_ir.py)
  - Stage 4: AppSpec  (schemas/app_spec.py)
"""

import re
import json
from typing import Any


def extract_original_prompt(user_prompt: str) -> str:
    """Extracts the actual user prompt or intent description from pipeline wrapper prompts."""
    # 1. Stage 4 format: The original prompt was: "..."
    match_s4 = re.search(r'original prompt was:\s*"([^"]+)"', user_prompt, re.IGNORECASE)
    if match_s4:
        return match_s4.group(1)

    # 2. Triple dash block format
    parts = user_prompt.split("---")
    if len(parts) >= 3:
        inner = parts[1].strip()
        try:
            data = json.loads(inner)
            if isinstance(data, dict):
                if "original_prompt" in data and data["original_prompt"]:
                    return data["original_prompt"]
                if "app_description" in data and data["app_description"]:
                    return data["app_description"]
                if "app_name" in data and data["app_name"]:
                    return data["app_name"]
        except Exception:
            pass
        return inner

    # 3. Look for JSON block inside user_prompt (common in repair loops)
    json_matches = re.findall(r'(\{[\s\S]*?\})', user_prompt)
    for j_str in json_matches:
        try:
            data = json.loads(j_str)
            if isinstance(data, dict):
                if data.get("original_prompt"):
                    return data["original_prompt"]
                desc = data.get("app_description", "")
                if desc and "application:" in desc:
                    return desc.split("application:", 1)[1].strip()
        except Exception:
            pass

    # 4. Regex fallback for original_prompt field directly
    match_op = re.search(r'"original_prompt":\s*"([^"]+)"', user_prompt)
    if match_op:
        try:
            return json.loads(f'"{match_op.group(1)}"')
        except Exception:
            return match_op.group(1)

    return user_prompt



def parse_prompt_info(user_prompt: str) -> dict[str, Any]:
    """Parse user prompt to extract app type, entities, roles, features, and pages."""
    clean_prompt = extract_original_prompt(user_prompt)
    prompt_lower = clean_prompt.lower().replace("_", " ").replace("-", " ")

    def has_word(pattern: str) -> bool:
        return bool(re.search(r'\b(' + pattern + r')\b', prompt_lower))

    # Determine App Type, Entities, Roles, and Features based on keywords
    if has_word("task|tasks|todo|todos|project|projects|kanban|trello|boards|jira"):
        app_type = "project_management"
        default_name = "Task Management Board"
        entities = ["User", "Project", "Task", "Comment"]
        roles = ["admin", "manager", "member"]
        features = [
            ("authentication", "Secure logins and roles assignment", "high", True, ["admin", "manager", "member"]),
            ("projects_setup", "Group tasks under organized project folders", "high", True, ["admin", "manager"]),
            ("task_management", "Create tasks with priority levels, descriptions, and assignees", "high", True, ["admin", "manager", "member"]),
            ("kanban_board", "Drag tasks across Backlog, Active, and Done columns", "medium", True, ["admin", "manager", "member"]),
        ]
    elif has_word("hospital|clinic|doctor|doctors|patient|patients|medical|appointment|booking|health|healthcare"):
        app_type = "healthcare"
        default_name = "Healthcare Booking Portal"
        entities = ["User", "Patient", "Doctor", "Appointment"]
        roles = ["admin", "doctor", "patient"]
        features = [
            ("patient_auth_portal", "Secure login for doctors and patients", "high", True, ["admin", "doctor", "patient"]),
            ("doctor_schedules", "Manage availability windows for medical staff", "high", True, ["admin", "doctor"]),
            ("appointment_bookings", "Schedule consults and send confirmation codes", "high", True, ["admin", "patient"]),
            ("patient_records", "Access health summaries and visit histories", "medium", True, ["admin", "doctor"]),
        ]
    elif has_word("crm|sales|customer|contacts|pipeline|deals"):
        app_type = "crm"
        default_name = "Customer Relationship Manager"
        entities = ["User", "Contact", "Deal", "Interaction"]
        roles = ["admin", "sales_rep"]
        features = [
            ("user_authentication", "Secure sign-up, login, and authorization checks", "high", True, ["admin", "sales_rep"]),
            ("contacts_management", "Manage client contact details and history logs", "high", True, ["admin", "sales_rep"]),
            ("deals_tracking", "Monitor deal pipelines, value estimates, and closure stages", "high", True, ["admin", "sales_rep"]),
            ("analytics_dashboard", "Overview of pipeline health, wins, and losses", "medium", True, ["admin"]),
        ]
    elif has_word("e-commerce|ecommerce|e commerce|shop|store|product|products|cart|checkout"):
        app_type = "ecommerce"
        default_name = "E-Commerce Shopping Portal"
        entities = ["User", "Product", "Order", "OrderItem", "Review"]
        roles = ["admin", "customer"]
        features = [
            ("user_registration", "Authentication and profile settings", "high", True, ["admin", "customer"]),
            ("product_catalog", "Browse items categorized by collections", "high", False, ["admin", "customer"]),
            ("shopping_cart", "Manage items to purchase during a session", "high", True, ["customer"]),
            ("order_checkout", "Finalize billing details and generate order receipt", "high", True, ["customer"]),
            ("inventory_management", "Add, edit, or delete store products and quantities", "medium", True, ["admin"]),
        ]
    elif has_word("social|chat|forum|community|message|messages|channel|channels"):
        app_type = "social"
        default_name = "Community Forum App"
        entities = ["User", "Message", "Channel", "Reaction"]
        roles = ["admin", "moderator", "member"]
        features = [
            ("auth_registration", "Sign-in and user handles registration", "high", True, ["admin", "moderator", "member"]),
            ("channels_messaging", "Post messages in targeted chat channels", "high", True, ["admin", "moderator", "member"]),
            ("moderation_tools", "Delete inappropriate posts or ban members", "medium", True, ["admin", "moderator"]),
            ("user_profiles", "Customize profiles and add avatars", "medium", True, ["admin", "moderator", "member"]),
        ]
    elif has_word("school|student|students|course|courses|class|classes|teacher|teachers|education|portal"):
        app_type = "education"
        default_name = "Education Student Portal"
        entities = ["User", "Student", "Course", "Enrollment"]
        roles = ["admin", "teacher", "student"]
        features = [
            ("portal_logins", "Logins for students, teachers, and staff", "high", True, ["admin", "teacher", "student"]),
            ("course_registry", "View syllabus and enroll in classes", "high", True, ["admin", "teacher", "student"]),
            ("grade_tracker", "Assign grades to coursework", "medium", True, ["admin", "teacher"]),
            ("lesson_manager", "Upload assignments and slide decks", "medium", True, ["admin", "teacher"]),
        ]
    elif has_word("library|book|books|borrow|librarian|catalog"):
        app_type = "library"
        default_name = "Library Catalog System"
        entities = ["User", "Book", "Member", "BorrowRecord"]
        roles = ["admin", "librarian", "member"]
        features = [
            ("library_auth", "Authentication for members and librarians", "high", True, ["admin", "librarian", "member"]),
            ("catalog_browser", "Search books by title, author, or genre", "high", False, ["admin", "librarian", "member"]),
            ("borrow_transactions", "Check out books and calculate return due dates", "high", True, ["admin", "librarian"]),
            ("fines_tracker", "Register late returns and apply penalties", "medium", True, ["admin", "librarian"]),
        ]
    elif has_word("ticket|tickets|issue|issues|support|helpdesk|sla"):
        app_type = "helpdesk"
        default_name = "Support Helpdesk"
        entities = ["User", "Ticket", "TicketComment", "SlaRecord"]
        roles = ["admin", "agent", "customer"]
        features = [
            ("helpdesk_access", "Portal login for clients and support agents", "high", True, ["admin", "agent", "customer"]),
            ("ticket_creator", "Open requests with severity levels", "high", True, ["admin", "customer"]),
            ("agent_queue", "Assign tickets and update status to resolved", "high", True, ["admin", "agent"]),
            ("sla_tracker", "Alert agents when resolution deadline is near", "medium", True, ["admin", "agent"]),
        ]
    elif has_word("event|events|ticket|conference|attendee|organizer"):
        app_type = "event_management"
        default_name = "Event Management Platform"
        entities = ["User", "Event", "Ticket", "Attendance"]
        roles = ["admin", "organizer", "attendee"]
        features = [
            ("event_auth", "Login for organizers and attendees", "high", True, ["admin", "organizer", "attendee"]),
            ("event_creation", "Create events with dates, venues, and pricing", "high", True, ["admin", "organizer"]),
            ("ticket_purchase", "Browse events and purchase tickets", "high", True, ["attendee"]),
            ("attendance_tracking", "Check-in attendees and track attendance", "medium", True, ["admin", "organizer"]),
        ]
    elif has_word("inventory|warehouse|stock|sku|supplier"):
        app_type = "inventory"
        default_name = "Inventory Management System"
        entities = ["User", "Product", "PurchaseOrder", "Supplier"]
        roles = ["admin", "warehouse_manager", "viewer"]
        features = [
            ("inventory_auth", "Secure authentication for warehouse staff", "high", True, ["admin", "warehouse_manager", "viewer"]),
            ("product_tracking", "Track products with SKU, quantity, location", "high", True, ["admin", "warehouse_manager"]),
            ("purchase_orders", "Create and manage purchase orders from suppliers", "high", True, ["admin", "warehouse_manager"]),
            ("stock_alerts", "Low stock alerts and notifications", "medium", True, ["admin", "warehouse_manager"]),
        ]
    elif has_word("job|jobs|career|hiring|recruit|applicant|resume"):
        app_type = "job_board"
        default_name = "Job Board Platform"
        entities = ["User", "Company", "Job", "Application"]
        roles = ["admin", "employer", "candidate"]
        features = [
            ("job_auth", "Login for employers and candidates", "high", True, ["admin", "employer", "candidate"]),
            ("job_listings", "Post and manage job listings", "high", True, ["admin", "employer"]),
            ("job_search", "Search and filter job openings", "high", False, ["candidate"]),
            ("application_tracking", "Apply to jobs and track application status", "high", True, ["admin", "employer", "candidate"]),
        ]
    elif has_word("blog|blogging|article|articles|news|post|posts"):
        app_type = "blogging"
        default_name = "Publishing Blog Platform"
        entities = ["User", "Post", "Comment", "Category"]
        roles = ["admin", "author", "reader"]
        features = [
            ("membership_system", "Login, session checks, and author profiles", "high", True, ["admin", "author", "reader"]),
            ("article_publisher", "Draft, publish, edit, or delete articles and posts", "high", True, ["admin", "author"]),
            ("comments_feed", "Write and reply to article comment threads", "medium", True, ["admin", "author", "reader"]),
            ("categories_management", "Organize posts by subjects", "medium", True, ["admin", "author"]),
        ]
    else:
        # Generic fallback
        app_type = "custom"
        default_name = "Custom Application"
        entities = ["User", "Item", "Category", "Transaction"]
        roles = ["admin", "user"]
        features = [
            ("portal_access", "Secure authentication and authorization routing", "high", True, ["admin", "user"]),
            ("items_registry", "List, view, and organize primary business entities", "high", True, ["admin", "user"]),
            ("categories_management", "Classify entries under designated tags", "medium", True, ["admin"]),
            ("transactions_log", "Track actions, histories, or exchanges", "medium", True, ["admin", "user"]),
        ]

    # Try to refine App Name from prompt
    app_name = default_name
    match_build = re.search(r"(?:build|create|make|design)\s+(?:a|an|the)?\s*([^,.!?]+)", clean_prompt, re.IGNORECASE)
    if match_build:
        extracted = match_build.group(1).strip().title()
        if 5 < len(extracted) < 60:
            app_name = extracted

    # Generate pages from entities
    pages_list = ["Dashboard"]
    for ent in entities:
        if ent != "User":
            pages_list.append(f"{ent}s Management")
    pages_list.append("Settings")
    pages_list.append("Login")

    # Detect ambiguities and contradictions for failure cases
    ambiguities_detected = []
    
    # 1. Extreme Vagueness
    is_vague = False
    words = clean_prompt.strip().lower().split()
    if len(words) <= 4 and any(x in clean_prompt.lower() for x in ["build", "make", "create", "need", "want"]) and any(x in clean_prompt.lower() for x in ["app", "website", "site", "system", "portal", "dashboard"]):
        is_vague = True
        ambiguities_detected.append("What is website included? Which subject related it is: CRM, E-commerce, Blog, or anything?")
        
    for keyword in ["vague", "make an website", "build a website", "create website", "build website"]:
        if keyword in clean_prompt.lower():
            is_vague = True
            ambiguities_detected.append("What is website included? Which subject related it is: CRM, E-commerce, Blog, or anything?")
            break

    # 2. Authentication contradictions
    if "without authentication" in clean_prompt.lower() and ("logged user" in clean_prompt.lower() or "logged-in" in clean_prompt.lower() or "logged" in clean_prompt.lower() or "accesed" in clean_prompt.lower() or "access" in clean_prompt.lower()):
        ambiguities_detected.append("Contradiction: Request specifies 'without authentication' but also 'logged user accessed'. Authenticated routes require login.")

    # 3. Private vs Public contradiction
    if "all posts are private" in clean_prompt.lower() and "public feed" in clean_prompt.lower():
        ambiguities_detected.append("Conflict: Request specifies all posts must be private to author, but also a public feed of all posts.")

    # 4. Strict RBAC vs Admin Access contradiction
    if "full admin access to everything" in clean_prompt.lower() and "strict role-based access" in clean_prompt.lower():
        ambiguities_detected.append("Conflict: Request specifies full admin access to everyone, but also strict role-based access restricting actions.")

    return {
        "app_name": app_name,
        "app_type": app_type,
        "entities": entities,
        "roles": roles,
        "features": features,
        "pages": pages_list,
        "original_prompt": clean_prompt,
        "ambiguities_detected": ambiguities_detected,
    }


def _entity_to_table_name(entity: str) -> str:
    """Convert PascalCase entity name to snake_case plural table name."""
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', entity).lower()
    if s.endswith('s'):
        return s
    if s.endswith('y') and not s.endswith('ey'):
        return s[:-1] + 'ies'
    return s + 's'


def _get_entity_fields(entity: str, entities: list[str]) -> list[dict]:
    """Get appropriate fields for a given entity based on its name."""
    ent_lower = entity.lower()

    # Base fields every entity has
    base_fields = [
        {"name": "id", "type": "uuid", "required": True, "unique": True, "constraints": ["primaryKey"], "description": "Unique identifier"},
        {"name": "created_at", "type": "datetime", "required": True, "unique": False, "constraints": [], "description": "Record creation timestamp"},
        {"name": "updated_at", "type": "datetime", "required": True, "unique": False, "constraints": [], "description": "Last update timestamp"},
    ]

    if ent_lower == "user":
        return base_fields + [
            {"name": "email", "type": "email", "required": True, "unique": True, "constraints": ["format:email"], "description": "User email address"},
            {"name": "password_hash", "type": "password", "required": True, "unique": False, "constraints": [], "description": "Hashed password"},
            {"name": "full_name", "type": "string", "required": True, "unique": False, "constraints": [], "description": "User full name"},
            {"name": "role", "type": "string", "required": True, "unique": False, "default": "user", "constraints": [], "description": "User role"},
            {"name": "is_active", "type": "boolean", "required": True, "unique": False, "default": "true", "constraints": [], "description": "Account active status"},
        ]

    # Entity-specific fields
    specific = []
    if ent_lower in ("contact",):
        specific = [
            {"name": "first_name", "type": "string", "required": True, "description": "Contact first name"},
            {"name": "last_name", "type": "string", "required": True, "description": "Contact last name"},
            {"name": "email", "type": "email", "required": False, "unique": True, "description": "Contact email"},
            {"name": "phone", "type": "phone", "required": False, "description": "Contact phone number"},
            {"name": "company", "type": "string", "required": False, "description": "Associated company"},
            {"name": "status", "type": "string", "required": True, "default": "active", "description": "Contact status"},
        ]
    elif ent_lower in ("deal",):
        specific = [
            {"name": "title", "type": "string", "required": True, "description": "Deal title"},
            {"name": "value", "type": "float", "required": True, "description": "Deal monetary value"},
            {"name": "stage", "type": "string", "required": True, "default": "prospect", "description": "Pipeline stage"},
            {"name": "contact_id", "type": "uuid", "required": False, "description": "Associated contact"},
            {"name": "user_id", "type": "uuid", "required": True, "description": "Assigned sales rep"},
        ]
    elif ent_lower in ("product",):
        specific = [
            {"name": "name", "type": "string", "required": True, "description": "Product name"},
            {"name": "description", "type": "text", "required": False, "description": "Product description"},
            {"name": "price", "type": "float", "required": True, "description": "Product price"},
            {"name": "sku", "type": "string", "required": True, "unique": True, "description": "Stock keeping unit"},
            {"name": "quantity", "type": "integer", "required": True, "default": "0", "description": "Stock quantity"},
            {"name": "is_active", "type": "boolean", "required": True, "default": "true", "description": "Product availability"},
        ]
    elif ent_lower in ("order",):
        specific = [
            {"name": "user_id", "type": "uuid", "required": True, "description": "Customer who placed order"},
            {"name": "total_amount", "type": "float", "required": True, "description": "Order total"},
            {"name": "status", "type": "string", "required": True, "default": "pending", "description": "Order status"},
            {"name": "payment_status", "type": "string", "required": True, "default": "unpaid", "description": "Payment status"},
        ]
    elif ent_lower in ("post", "article"):
        specific = [
            {"name": "title", "type": "string", "required": True, "description": "Post title"},
            {"name": "content", "type": "text", "required": True, "description": "Post content body"},
            {"name": "author_id", "type": "uuid", "required": True, "description": "Post author"},
            {"name": "status", "type": "string", "required": True, "default": "draft", "description": "Publication status"},
            {"name": "category_id", "type": "uuid", "required": False, "description": "Post category"},
        ]
    elif ent_lower in ("comment", "ticketcomment"):
        specific = [
            {"name": "content", "type": "text", "required": True, "description": "Comment text"},
            {"name": "user_id", "type": "uuid", "required": True, "description": "Comment author"},
            {"name": "parent_id", "type": "uuid", "required": True, "description": "Parent entity ID"},
        ]
    elif ent_lower in ("task",):
        specific = [
            {"name": "title", "type": "string", "required": True, "description": "Task title"},
            {"name": "description", "type": "text", "required": False, "description": "Task description"},
            {"name": "status", "type": "string", "required": True, "default": "todo", "description": "Task status (todo/in_progress/done)"},
            {"name": "priority", "type": "string", "required": True, "default": "medium", "description": "Task priority"},
            {"name": "assignee_id", "type": "uuid", "required": False, "description": "Assigned user"},
            {"name": "project_id", "type": "uuid", "required": True, "description": "Parent project"},
        ]
    elif ent_lower in ("project",):
        specific = [
            {"name": "name", "type": "string", "required": True, "description": "Project name"},
            {"name": "description", "type": "text", "required": False, "description": "Project description"},
            {"name": "status", "type": "string", "required": True, "default": "active", "description": "Project status"},
            {"name": "owner_id", "type": "uuid", "required": True, "description": "Project owner"},
        ]
    elif ent_lower in ("ticket",):
        specific = [
            {"name": "title", "type": "string", "required": True, "description": "Ticket subject"},
            {"name": "description", "type": "text", "required": True, "description": "Ticket details"},
            {"name": "status", "type": "string", "required": True, "default": "open", "description": "Ticket status"},
            {"name": "priority", "type": "string", "required": True, "default": "medium", "description": "Ticket priority"},
            {"name": "user_id", "type": "uuid", "required": True, "description": "Reporter"},
            {"name": "assignee_id", "type": "uuid", "required": False, "description": "Assigned agent"},
        ]
    elif ent_lower in ("event",):
        specific = [
            {"name": "title", "type": "string", "required": True, "description": "Event title"},
            {"name": "description", "type": "text", "required": False, "description": "Event description"},
            {"name": "date", "type": "datetime", "required": True, "description": "Event date"},
            {"name": "location", "type": "string", "required": False, "description": "Event location"},
            {"name": "organizer_id", "type": "uuid", "required": True, "description": "Event organizer"},
            {"name": "capacity", "type": "integer", "required": False, "description": "Max attendees"},
        ]
    elif ent_lower in ("appointment",):
        specific = [
            {"name": "patient_id", "type": "uuid", "required": True, "description": "Patient"},
            {"name": "doctor_id", "type": "uuid", "required": True, "description": "Doctor"},
            {"name": "date_time", "type": "datetime", "required": True, "description": "Appointment date/time"},
            {"name": "status", "type": "string", "required": True, "default": "scheduled", "description": "Appointment status"},
            {"name": "notes", "type": "text", "required": False, "description": "Appointment notes"},
        ]
    elif ent_lower in ("course",):
        specific = [
            {"name": "title", "type": "string", "required": True, "description": "Course title"},
            {"name": "description", "type": "text", "required": False, "description": "Course description"},
            {"name": "instructor_id", "type": "uuid", "required": True, "description": "Course instructor"},
            {"name": "status", "type": "string", "required": True, "default": "active", "description": "Course status"},
        ]
    elif ent_lower in ("enrollment",):
        specific = [
            {"name": "student_id", "type": "uuid", "required": True, "description": "Enrolled student"},
            {"name": "course_id", "type": "uuid", "required": True, "description": "Enrolled course"},
            {"name": "grade", "type": "string", "required": False, "description": "Student grade"},
            {"name": "status", "type": "string", "required": True, "default": "active", "description": "Enrollment status"},
        ]
    else:
        # Generic entity fields
        specific = [
            {"name": "name", "type": "string", "required": True, "description": f"{entity} name"},
            {"name": "description", "type": "text", "required": False, "description": f"{entity} description"},
            {"name": "status", "type": "string", "required": True, "default": "active", "description": "Record status"},
            {"name": "user_id", "type": "uuid", "required": True, "description": "Owner user"},
        ]

    # Ensure all fields have defaults for optional Pydantic fields
    for f in specific:
        f.setdefault("unique", False)
        f.setdefault("constraints", [])
        f.setdefault("required", True)

    return base_fields + specific


def _get_entity_relationships(entity: str, entities: list[str]) -> list[dict]:
    """Get relationships for an entity based on common patterns."""
    ent_lower = entity.lower()
    rels = []

    # User is referenced by most entities
    if ent_lower != "user" and "User" in entities:
        rels.append({
            "target_entity": "User",
            "type": "one_to_many",
            "foreign_key_field": "user_id",
            "description": f"User who owns/created this {entity}",
        })

    # Entity-specific relationships
    if ent_lower == "deal" and "Contact" in entities:
        rels.append({
            "target_entity": "Contact",
            "type": "one_to_many",
            "foreign_key_field": "contact_id",
            "description": "Contact associated with deal",
        })
    elif ent_lower == "orderitem" and "Order" in entities:
        rels.append({
            "target_entity": "Order",
            "type": "one_to_many",
            "foreign_key_field": "order_id",
            "description": "Parent order",
        })
    elif ent_lower == "comment" and "Post" in entities:
        rels.append({
            "target_entity": "Post",
            "type": "one_to_many",
            "foreign_key_field": "parent_id",
            "description": "Post this comment belongs to",
        })
    elif ent_lower == "task" and "Project" in entities:
        rels.append({
            "target_entity": "Project",
            "type": "one_to_many",
            "foreign_key_field": "project_id",
            "description": "Project this task belongs to",
        })
    elif ent_lower == "enrollment" and "Course" in entities:
        rels.append({
            "target_entity": "Course",
            "type": "one_to_many",
            "foreign_key_field": "course_id",
            "description": "Enrolled course",
        })

    return rels


def _field_type_to_db_type(ftype: str) -> str:
    """Map Pydantic field type to SQL column type."""
    mapping = {
        "string": "VARCHAR(255)",
        "text": "TEXT",
        "integer": "INTEGER",
        "float": "DECIMAL(10,2)",
        "boolean": "BOOLEAN",
        "datetime": "TIMESTAMP",
        "date": "DATE",
        "email": "VARCHAR(255)",
        "url": "VARCHAR(500)",
        "phone": "VARCHAR(50)",
        "password": "VARCHAR(255)",
        "json": "JSON",
        "uuid": "UUID",
        "enum": "VARCHAR(50)",
    }
    return mapping.get(ftype, "VARCHAR(255)")


def _field_type_to_ui_type(ftype: str) -> str:
    """Map Pydantic field type to HTML input type."""
    mapping = {
        "string": "text",
        "text": "textarea",
        "integer": "number",
        "float": "number",
        "boolean": "checkbox",
        "datetime": "date",
        "date": "date",
        "email": "email",
        "url": "url",
        "phone": "tel",
        "password": "password",
        "uuid": "text",
    }
    return mapping.get(ftype, "text")


def get_mock_response(stage: str, user_prompt: str) -> dict[str, Any]:
    """Generate a schema-valid mock response for the given pipeline stage."""
    if stage.endswith("_repair"):
        base_stage = stage[:-7]
    elif stage.endswith("_refine"):
        base_stage = stage[:-7]
    else:
        base_stage = stage
    info = parse_prompt_info(user_prompt)
    app_name = info["app_name"]
    app_type = info["app_type"]
    entities = info["entities"]
    roles = info["roles"]
    features_list = info["features"]
    pages_list = info["pages"]
    original_prompt = info["original_prompt"]

    if base_stage == "stage_1_lexer":
        return _mock_stage_1(app_name, app_type, entities, roles, features_list, original_prompt, info.get("ambiguities_detected", []))
    elif base_stage == "stage_2_parser":
        return _mock_stage_2(entities, roles, features_list, pages_list)
    elif base_stage == "stage_3_ir_generator":
        return _mock_stage_3(entities, roles, pages_list)
    elif base_stage == "stage_4_optimizer":
        return _mock_stage_4(app_name, app_type, entities, roles, pages_list, user_prompt, original_prompt)
    return {}


def _mock_stage_1(app_name, app_type, entities, roles, features_list, original_prompt, ambiguities_detected=None) -> dict:
    """Stage 1: IntentIR — matches IntentIR Pydantic model."""
    features_json = []
    for name, desc, priority, requires_auth, target_roles in features_list:
        features_json.append({
            "name": name,
            "description": desc,
            "priority": priority,
            "requires_auth": requires_auth,
            "target_roles": target_roles,
        })

    return {
        "app_name": app_name.lower().replace(" ", "_"),
        "app_description": f"A {app_type} application: {original_prompt[:200]}",
        "app_type": app_type,
        "features": features_json,
        "entities": entities,
        "roles": roles,
        "constraints": [
            "All write operations require authentication",
            "Role-based access control on all endpoints",
        ],
        "assumptions": [
            "Default roles created on first run",
            "Email-based authentication assumed",
            "UTC timezone for all timestamps",
        ],
        "ambiguities_detected": ambiguities_detected or [],
        "original_prompt": original_prompt,
    }



def _mock_stage_2(entities, roles, features_list, pages_list) -> dict:
    """Stage 2: DesignIR — matches DesignIR Pydantic model."""
    # Entities with fields and relationships
    entities_json = []
    for ent in entities:
        fields = _get_entity_fields(ent, entities)
        relationships = _get_entity_relationships(ent, entities)
        entities_json.append({
            "name": ent,
            "description": f"Data model for {ent} records.",
            "fields": fields,
            "relationships": relationships,
        })

    # Roles with permissions
    roles_json = []
    for r in roles:
        permissions = []
        for ent in entities:
            if r == "admin" or r in ("manager", "warehouse_manager", "moderator"):
                actions = ["create", "read", "update", "delete"]
            elif r in ("viewer", "reader"):
                actions = ["read"]
            else:
                actions = ["read", "create", "update"]
            permissions.append({"entity": ent, "actions": actions})
        roles_json.append({
            "name": r,
            "description": f"Permissions for {r.replace('_', ' ').title()} role.",
            "permissions": permissions,
            "is_default": r != "admin",
        })

    # Pages
    pages_json = []
    for p in pages_list:
        assoc = []
        p_lower = p.lower()
        for ent in entities:
            if ent.lower() in p_lower:
                assoc.append(ent)
        if not assoc and "dashboard" in p_lower:
            assoc = entities[:3]
        elif not assoc and "settings" in p_lower:
            assoc = ["User"]
        elif not assoc and "login" in p_lower:
            assoc = ["User"]
        elif not assoc:
            assoc = [entities[1] if len(entities) > 1 else entities[0]]

        pages_json.append({
            "name": p.lower().replace(" ", "_"),
            "description": f"Page for {p}",
            "associated_entities": assoc,
            "access_roles": roles if "login" not in p_lower else [],
            "features": [features_list[0][0]] if features_list else [],
        })

    # Business rules — matches BusinessRule model: name, description, condition, action, entities_involved
    business_rules = [
        {
            "name": "ownership_enforcement",
            "description": "Non-admin users can only access their own records",
            "condition": "user.role != 'admin'",
            "action": "Filter records by user_id = current_user.id",
            "entities_involved": [e for e in entities if e != "User"],
        },
        {
            "name": "auto_timestamps",
            "description": "Automatically set created_at and updated_at timestamps",
            "condition": "on_create OR on_update",
            "action": "Set created_at/updated_at to current UTC time",
            "entities_involved": entities,
        },
    ]

    return {
        "entities": entities_json,
        "roles": roles_json,
        "pages": pages_json,
        "business_rules": business_rules,
    }


def _mock_stage_3(entities, roles, pages_list) -> dict:
    """Stage 3: SchemaIR — matches SchemaIR Pydantic model."""

    # =========== UI Schema ===========
    ui_pages = []
    navigation = []

    for idx, p in enumerate(pages_list):
        p_lower = p.lower()
        page_name = p_lower.replace(" ", "_")
        route = f"/{page_name}"
        if "dashboard" in p_lower:
            route = "/dashboard"
        elif "login" in p_lower:
            route = "/login"
        elif "settings" in p_lower:
            route = "/settings"

        # Find matching entity
        matched_ent = None
        for ent in entities:
            if ent.lower() in p_lower:
                matched_ent = ent
                break

        components = []

        if "dashboard" in p_lower:
            # Stats component
            stats_fields = []
            for ent in entities:
                if ent != "User":
                    stats_fields.append({
                        "name": f"total_{ent.lower()}s",
                        "label": f"Total {ent}s",
                        "type": "number",
                        "required": False,
                        "options": [],
                    })
            components.append({
                "id": "dashboard_stats",
                "type": "stats",
                "title": "Overview",
                "data_source": "",
                "fields": stats_fields,
                "actions": [],
            })
        elif "login" in p_lower:
            components.append({
                "id": "login_form",
                "type": "form",
                "title": "Sign In",
                "data_source": "/api/v1/auth/login",
                "fields": [
                    {"name": "email", "label": "Email", "type": "email", "required": True, "options": []},
                    {"name": "password", "label": "Password", "type": "password", "required": True, "options": []},
                ],
                "actions": ["create"],
            })
        elif "settings" in p_lower:
            components.append({
                "id": "settings_form",
                "type": "form",
                "title": "Account Settings",
                "data_source": "/api/v1/users",
                "fields": [
                    {"name": "full_name", "label": "Full Name", "type": "text", "required": True, "options": []},
                    {"name": "email", "label": "Email", "type": "email", "required": True, "options": []},
                ],
                "actions": ["edit"],
            })
        elif matched_ent:
            # Table component for entity listing
            ent_fields = _get_entity_fields(matched_ent, entities)
            table_fields = []
            form_fields = []
            for f in ent_fields:
                if f["name"] in ("id", "created_at", "updated_at", "password_hash"):
                    continue
                ui_type = _field_type_to_ui_type(f.get("type", "string"))
                table_fields.append({
                    "name": f["name"],
                    "label": f["name"].replace("_", " ").title(),
                    "type": ui_type,
                    "required": f.get("required", False),
                    "options": [],
                })
                if f["name"] not in ("user_id",):
                    form_fields.append({
                        "name": f["name"],
                        "label": f["name"].replace("_", " ").title(),
                        "type": ui_type,
                        "required": f.get("required", False),
                        "options": [],
                    })

            tbl_name = _entity_to_table_name(matched_ent)
            components.append({
                "id": f"{matched_ent.lower()}_table",
                "type": "table",
                "title": f"{matched_ent}s",
                "data_source": f"/api/v1/{tbl_name}",
                "fields": table_fields[:6],
                "actions": ["create", "view", "edit", "delete"],
            })
            components.append({
                "id": f"{matched_ent.lower()}_form",
                "type": "form",
                "title": f"Add {matched_ent}",
                "data_source": f"/api/v1/{tbl_name}",
                "fields": form_fields[:6],
                "actions": ["create"],
            })
        else:
            components.append({
                "id": f"card_{page_name}",
                "type": "card",
                "title": p,
                "data_source": "",
                "fields": [],
                "actions": [],
            })

        ui_pages.append({
            "name": page_name,
            "route": route,
            "title": p,
            "layout": "grid" if "dashboard" in p_lower else "stack",
            "components": components,
            "access_roles": [] if "login" in p_lower else roles,
            "is_public": "login" in p_lower,
        })

        if "login" not in p_lower:
            icon = "home" if "dashboard" in p_lower else "settings" if "settings" in p_lower else "list"
            navigation.append({"name": p, "route": route, "icon": icon})

    # =========== API Schema ===========
    endpoints = []

    # Auth endpoints
    endpoints.append({
        "path": "/api/v1/auth/login",
        "method": "POST",
        "summary": "Authenticate user and return JWT token",
        "request_params": [
            {"name": "email", "type": "string", "required": True, "location": "body"},
            {"name": "password", "type": "string", "required": True, "location": "body"},
        ],
        "response_fields": [{"name": "token", "type": "string"}, {"name": "user", "type": "object"}],
        "auth_required": False,
        "allowed_roles": roles,
        "entity": "User",
    })

    # CRUD endpoints for each entity
    for ent in entities:
        tbl_name = _entity_to_table_name(ent)
        ent_fields = _get_entity_fields(ent, entities)
        body_fields = [
            {"name": f["name"], "type": f.get("type", "string"), "required": f.get("required", True), "location": "body"}
            for f in ent_fields
            if f["name"] not in ("id", "created_at", "updated_at")
        ]
        response_fields = [{"name": f["name"], "type": f.get("type", "string")} for f in ent_fields]

        # GET list
        endpoints.append({
            "path": f"/api/v1/{tbl_name}",
            "method": "GET",
            "summary": f"List all {ent} records with pagination",
            "request_params": [
                {"name": "page", "type": "integer", "required": False, "location": "query"},
                {"name": "limit", "type": "integer", "required": False, "location": "query"},
            ],
            "response_fields": response_fields,
            "auth_required": True,
            "allowed_roles": roles,
            "entity": ent,
        })

        # GET by ID
        endpoints.append({
            "path": f"/api/v1/{tbl_name}/:id",
            "method": "GET",
            "summary": f"Get a single {ent} by ID",
            "request_params": [{"name": "id", "type": "string", "required": True, "location": "path"}],
            "response_fields": response_fields,
            "auth_required": True,
            "allowed_roles": roles,
            "entity": ent,
        })

        # POST create
        endpoints.append({
            "path": f"/api/v1/{tbl_name}",
            "method": "POST",
            "summary": f"Create a new {ent}",
            "request_params": body_fields[:6],
            "response_fields": response_fields,
            "auth_required": True,
            "allowed_roles": [r for r in roles if r != "viewer"],
            "entity": ent,
        })

        # PUT update
        endpoints.append({
            "path": f"/api/v1/{tbl_name}/:id",
            "method": "PUT",
            "summary": f"Update an existing {ent}",
            "request_params": [{"name": "id", "type": "string", "required": True, "location": "path"}] + body_fields[:6],
            "response_fields": response_fields,
            "auth_required": True,
            "allowed_roles": [r for r in roles if r not in ("viewer", "reader")],
            "entity": ent,
        })

        # DELETE
        endpoints.append({
            "path": f"/api/v1/{tbl_name}/:id",
            "method": "DELETE",
            "summary": f"Delete a {ent}",
            "request_params": [{"name": "id", "type": "string", "required": True, "location": "path"}],
            "response_fields": [{"name": "success", "type": "boolean"}],
            "auth_required": True,
            "allowed_roles": ["admin"],
            "entity": ent,
        })

    # =========== DB Schema ===========
    tables = []
    for ent in entities:
        tbl_name = _entity_to_table_name(ent)
        ent_fields = _get_entity_fields(ent, entities)

        columns = []
        indexes = []
        for f in ent_fields:
            col = {
                "name": f["name"],
                "type": _field_type_to_db_type(f.get("type", "string")),
                "primary_key": f["name"] == "id",
                "nullable": not f.get("required", True),
                "unique": f.get("unique", False),
                "default": f.get("default"),
                "foreign_key": None,
            }
            # Set FK references
            if f["name"].endswith("_id") and f["name"] != "id":
                ref_entity = f["name"].replace("_id", "")
                # Find the matching entity
                for e in entities:
                    if e.lower() == ref_entity:
                        ref_table = _entity_to_table_name(e)
                        col["foreign_key"] = f"{ref_table}.id"
                        break
                if not col["foreign_key"] and ref_entity == "user":
                    col["foreign_key"] = "users.id"
            columns.append(col)

            # Add indexes for FK and unique columns
            if f.get("unique") and f["name"] != "id":
                indexes.append({"name": f"idx_{tbl_name}_{f['name']}", "columns": [f["name"]], "unique": True})
            elif f["name"].endswith("_id") and f["name"] != "id":
                indexes.append({"name": f"idx_{tbl_name}_{f['name']}", "columns": [f["name"]], "unique": False})

        tables.append({"name": tbl_name, "columns": columns, "indexes": indexes})

    # =========== Auth Schema ===========
    roles_config = []
    rules = []
    for r in roles:
        roles_config.append({
            "name": r,
            "display_name": r.replace("_", " ").title(),
            "is_default": r != "admin",
            "inherits_from": None,
        })
        for ent in entities:
            if r == "admin":
                actions = ["create", "read", "update", "delete"]
            elif r in ("viewer", "reader"):
                actions = ["read"]
            else:
                actions = ["read", "create", "update"]
            rules.append({
                "role": r,
                "resource": ent,
                "actions": actions,
                "conditions": ["own_records_only"] if r != "admin" else [],
            })

    return {
        "ui_schema": {
            "pages": ui_pages,
            "navigation": navigation,
            "theme": "default",
        },
        "api_schema": {
            "base_path": "/api/v1",
            "endpoints": endpoints,
        },
        "db_schema": {
            "tables": tables,
        },
        "auth_schema": {
            "roles": roles_config,
            "rules": rules,
            "session_type": "jwt",
            "password_hashing": "bcrypt",
        },
    }


def _mock_stage_4(app_name, app_type, entities, roles, pages_list, user_prompt, original_prompt) -> dict:
    """Stage 4: AppSpec — matches AppSpec Pydantic model."""
    schema_data = _mock_stage_3(entities, roles, pages_list)

    return {
        "metadata": {
            "name": app_name.lower().replace(" ", "_"),
            "description": f"Production-ready {app_type} application compiled from: {original_prompt[:200]}",
            "version": "1.0.0",
            "original_prompt": original_prompt,
            "assumptions": [
                "Email-based authentication with JWT tokens",
                "Role-based access control enforced on all endpoints",
                "UTC timezone for all timestamps",
                "Simulated database using localStorage for demo",
            ],
        },
        "ui": schema_data["ui_schema"],
        "api": schema_data["api_schema"],
        "db": schema_data["db_schema"],
        "auth": schema_data["auth_schema"],
        "business_logic": [
            {
                "name": "ownership_enforcement",
                "description": "Non-admin users can only access their own records",
                "condition": "user.role != 'admin'",
                "action": "Filter records by user_id = current_user.id",
                "entities_involved": [e for e in entities if e != "User"],
            },
            {
                "name": "auto_timestamps",
                "description": "Automatically set created_at and updated_at on record changes",
                "condition": "on_create OR on_update",
                "action": "Set created_at/updated_at to current UTC time",
                "entities_involved": entities,
            },
            {
                "name": "cascade_delete",
                "description": "Deleting a parent record cascades to child records",
                "condition": "on_delete of parent entity",
                "action": "Delete all child records referencing the deleted parent",
                "entities_involved": entities,
            },
        ],
    }
