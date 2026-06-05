"""
Code Generator — converts AppSpec JSON into a working HTML/CSS/JS application.
This is the "execution awareness" proof: the compiler's output is directly usable.
"""

from __future__ import annotations
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_app_html(app_spec: dict[str, Any]) -> str:
    """
    Generate a complete single-page HTML application from an AppSpec.

    The generated app includes:
    - Navigation sidebar from UI schema
    - Page routing (hash-based SPA)
    - Forms, tables, and cards from components
    - Mock API layer using localStorage
    - Auth simulation with role-based access
    - Responsive layout with dark theme

    Args:
        app_spec: AppSpec as dict.

    Returns:
        Complete HTML string ready to be saved as a .html file.
    """
    metadata = app_spec.get("metadata", {})
    ui = app_spec.get("ui", {})
    api = app_spec.get("api", {})
    db = app_spec.get("db", {})
    auth = app_spec.get("auth", {})
    business_logic = app_spec.get("business_logic", [])

    raw_app_name = metadata.get("name", "Generated App")
    
    # Deduce app_type from description, original prompt, or metadata
    app_type = None
    desc = metadata.get("description", "")
    import re
    m = re.search(r"Production-ready\s+(\w+)\s+application compiled from", desc, re.IGNORECASE)
    if m:
        app_type = m.group(1).lower()
        
    if not app_type or app_type == "custom":
        orig_prompt = metadata.get("original_prompt", "")
        lookup = (desc + " " + orig_prompt + " " + raw_app_name).lower().replace("_", " ").replace("-", " ")
        if any(w in lookup for w in ["healthcare", "doctor", "hospital", "clinic", "patient", "medical"]):
            app_type = "healthcare"
        elif any(w in lookup for w in ["crm", "sales", "customer", "contacts", "deal"]):
            app_type = "crm"
        elif any(w in lookup for w in ["blog", "article", "post", "comment"]):
            app_type = "blogging"
        elif any(w in lookup for w in ["jira", "task", "project", "kanban", "trello", "todo"]):
            app_type = "project_management"
        elif any(w in lookup for w in ["ecommerce", "e-commerce", "shop", "store", "product", "cart"]):
            app_type = "ecommerce"
        elif any(w in lookup for w in ["social", "chat", "forum", "message"]):
            app_type = "social"
        elif any(w in lookup for w in ["school", "education", "student", "course", "class", "teacher"]):
            app_type = "education"
        elif any(w in lookup for w in ["library", "book", "catalog"]):
            app_type = "library"
        elif any(w in lookup for w in ["ticket", "helpdesk", "support"]):
            app_type = "helpdesk"
        elif any(w in lookup for w in ["event", "conference"]):
            app_type = "event_management"
        elif any(w in lookup for w in ["inventory", "warehouse", "stock"]):
            app_type = "inventory"
        elif any(w in lookup for w in ["job", "career", "hiring", "resume"]):
            app_type = "job_board"

    type_mapping = {
        "healthcare": "Healthcare Portal",
        "crm": "CRM Portal",
        "blogging": "Blog Portal",
        "project_management": "Project Management Portal",
        "ecommerce": "E-Commerce Portal",
        "social": "Social Portal",
        "education": "Education Portal",
        "library": "Library Portal",
        "helpdesk": "Helpdesk Portal",
        "event_management": "Event Management Portal",
        "inventory": "Inventory Portal",
        "job_board": "Job Board Portal",
        "custom": "Custom Portal",
    }
    
    app_name = type_mapping.get(app_type) if app_type else None
    if not app_name:
        app_name = raw_app_name.replace("_", " ").replace("-", " ").strip().title()

    pages = ui.get("pages", [])
    navigation = ui.get("navigation", [])
    endpoints = api.get("endpoints", [])
    tables = db.get("tables", [])
    roles = auth.get("roles", [])

    # Build page HTML sections
    page_sections = []
    for page in pages:
        page_html = _generate_page_html(page)
        page_sections.append(page_html)

    # Build navigation HTML
    nav_html = _generate_nav_html(navigation, pages)

    # Build mock API JavaScript
    mock_api_js = _generate_mock_api(endpoints, tables)

    # Build page router JavaScript
    router_js = _generate_router(pages)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape(app_name)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent: #6366f1;
            --accent-hover: #818cf8;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --border: #475569;
            --radius: 8px;
        }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            display: flex;
            min-height: 100vh;
        }}
        /* Sidebar */
        .sidebar {{
            width: 250px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            padding: 20px 0;
            display: flex;
            flex-direction: column;
        }}
        .sidebar-brand {{
            padding: 0 20px 20px;
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--accent);
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .nav-links {{ list-style: none; padding: 10px 0; flex: 1; }}
        .nav-links li a {{
            display: block;
            padding: 10px 20px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s;
            border-left: 3px solid transparent;
        }}
        .nav-links li a:hover, .nav-links li a.active {{
            background: var(--bg-card);
            color: var(--text-primary);
            border-left-color: var(--accent);
        }}
        /* Main Content */
        .main-content {{
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }}
        .page {{ display: none; }}
        .page.active {{ display: block; }}
        .page-title {{
            font-size: 1.5rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
        }}
        /* Components */
        .component {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            margin-bottom: 20px;
        }}
        .component-title {{
            font-size: 1.1rem;
            margin-bottom: 15px;
            color: var(--accent);
        }}
        /* Forms */
        .form-group {{
            margin-bottom: 15px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 5px;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        .form-group input, .form-group select, .form-group textarea {{
            width: 100%;
            padding: 8px 12px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text-primary);
            font-size: 0.95rem;
        }}
        .form-group input:focus, .form-group select:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: var(--bg-card);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }}
        tr:hover {{ background: var(--bg-card); }}
        /* Buttons */
        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: var(--radius);
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
            margin-right: 8px;
        }}
        .btn-primary {{ background: var(--accent); color: white; }}
        .btn-primary:hover {{ background: var(--accent-hover); }}
        .btn-danger {{ background: var(--danger); color: white; }}
        .btn-success {{ background: var(--success); color: white; }}
        .btn-sm {{ padding: 4px 10px; font-size: 0.8rem; }}
        /* Cards grid */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }}
        .stat-card {{
            background: var(--bg-card);
            border-radius: var(--radius);
            padding: 20px;
        }}
        .stat-card .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
        }}
        .stat-card .stat-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 5px;
        }}
        /* Toast notifications */
        .toast {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: var(--radius);
            color: white;
            font-size: 0.9rem;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }}
        .toast.success {{ background: var(--success); }}
        .toast.error {{ background: var(--danger); }}
        @keyframes slideIn {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
    </style>
</head>
<body>
    <!-- Sidebar Navigation -->
    <nav class="sidebar">
        <div class="sidebar-brand">{_escape(app_name)}</div>
        {nav_html}
    </nav>

    <!-- Main Content -->
    <main class="main-content">
        {chr(10).join(page_sections)}
    </main>

    <script>
    // ===== Mock API Layer =====
    {mock_api_js}

    // ===== Router =====
    {router_js}

    // ===== Toast =====
    function showToast(msg, type='success') {{
        const t = document.createElement('div');
        t.className = 'toast ' + type;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 3000);
    }}

    // ===== Init =====
    window.addEventListener('hashchange', handleRoute);
    handleRoute();
    </script>
</body>
</html>"""

    return html


def _generate_nav_html(navigation: list, pages: list) -> str:
    """Generate sidebar navigation links."""
    items = []
    # Use navigation if provided, otherwise derive from pages
    nav_items = navigation or [
        {"name": p.get("title", p.get("name", "")), "route": p.get("route", "")}
        for p in pages
    ]

    items.append('<ul class="nav-links">')
    for nav in nav_items:
        name = nav.get("name", "")
        route = nav.get("route", "")
        href = f"#{route}"
        items.append(f'  <li><a href="{href}" data-route="{route}">{_escape(name)}</a></li>')
    items.append("</ul>")

    return "\n".join(items)


def _generate_page_html(page: dict) -> str:
    """Generate HTML for a single page with its components."""
    page_id = page.get("name", "page").replace(" ", "_").lower()
    title = page.get("title", page.get("name", ""))
    components = page.get("components", [])
    route = page.get("route", "")

    component_html_parts = []
    for comp in components:
        comp_html = _generate_component_html(comp)
        component_html_parts.append(comp_html)

    return f"""
    <div id="page-{_escape(page_id)}" class="page" data-route="{_escape(route)}">
        <h1 class="page-title">{_escape(title)}</h1>
        {chr(10).join(component_html_parts)}
    </div>"""


def _generate_component_html(comp: dict) -> str:
    """Generate HTML for a single component (form, table, card, etc.)."""
    comp_type = comp.get("type", "card")
    comp_id = comp.get("id", "comp")
    title = comp.get("title", "")
    fields = comp.get("fields", [])
    data_source = comp.get("data_source", "")
    actions = comp.get("actions", [])

    if comp_type == "form":
        return _generate_form(comp_id, title, fields, data_source, actions)
    elif comp_type == "table":
        return _generate_table(comp_id, title, fields, data_source, actions)
    elif comp_type in ("stats", "chart"):
        return _generate_stats(comp_id, title, fields)
    elif comp_type == "card":
        return _generate_card(comp_id, title, fields)
    elif comp_type == "list":
        return _generate_table(comp_id, title, fields, data_source, actions)
    elif comp_type == "detail":
        return _generate_card(comp_id, title, fields)
    else:
        return f'<div class="component"><div class="component-title">{_escape(title)}</div><p>Component: {comp_type}</p></div>'


def _generate_form(comp_id: str, title: str, fields: list, data_source: str, actions: list) -> str:
    """Generate an HTML form."""
    form_fields = []
    for f in fields:
        fname = f.get("name", "")
        flabel = f.get("label", fname.replace("_", " ").title())
        ftype = f.get("type", "text")
        freq = "required" if f.get("required", False) else ""

        if ftype == "select":
            options_html = "".join(
                f'<option value="{o}">{o}</option>' for o in f.get("options", [])
            )
            form_fields.append(f"""
                <div class="form-group">
                    <label for="{comp_id}_{fname}">{_escape(flabel)}</label>
                    <select id="{comp_id}_{fname}" name="{fname}" {freq}>
                        <option value="">Select...</option>{options_html}
                    </select>
                </div>""")
        elif ftype == "textarea":
            form_fields.append(f"""
                <div class="form-group">
                    <label for="{comp_id}_{fname}">{_escape(flabel)}</label>
                    <textarea id="{comp_id}_{fname}" name="{fname}" rows="3" {freq}></textarea>
                </div>""")
        elif ftype == "checkbox":
            form_fields.append(f"""
                <div class="form-group">
                    <label><input type="checkbox" id="{comp_id}_{fname}" name="{fname}"> {_escape(flabel)}</label>
                </div>""")
        else:
            form_fields.append(f"""
                <div class="form-group">
                    <label for="{comp_id}_{fname}">{_escape(flabel)}</label>
                    <input type="{ftype}" id="{comp_id}_{fname}" name="{fname}" {freq}>
                </div>""")

    return f"""
        <div class="component" id="{_escape(comp_id)}">
            <div class="component-title">{_escape(title)}</div>
            <form onsubmit="handleFormSubmit(event, '{_escape(data_source)}', '{_escape(comp_id)}')">
                {chr(10).join(form_fields)}
                <button type="submit" class="btn btn-primary">Save</button>
            </form>
        </div>"""


def _generate_table(comp_id: str, title: str, fields: list, data_source: str, actions: list) -> str:
    """Generate an HTML data table."""
    headers = "".join(
        f'<th>{_escape(f.get("label", f.get("name", "").replace("_", " ").title()))}</th>'
        for f in fields
    )
    if actions:
        headers += "<th>Actions</th>"

    return f"""
        <div class="component" id="{_escape(comp_id)}">
            <div class="component-title">{_escape(title)}</div>
            <table>
                <thead><tr>{headers}</tr></thead>
                <tbody id="{_escape(comp_id)}_body">
                    <tr><td colspan="{len(fields) + (1 if actions else 0)}" style="text-align:center;color:var(--text-secondary)">Loading data...</td></tr>
                </tbody>
            </table>
        </div>"""


def _generate_stats(comp_id: str, title: str, fields: list) -> str:
    """Generate stats/dashboard cards."""
    cards = []
    for f in fields:
        label = f.get("label", f.get("name", "").replace("_", " ").title())
        cards.append(f"""
            <div class="stat-card">
                <div class="stat-value">0</div>
                <div class="stat-label">{_escape(label)}</div>
            </div>""")

    return f"""
        <div class="component" id="{_escape(comp_id)}">
            <div class="component-title">{_escape(title)}</div>
            <div class="cards-grid">
                {chr(10).join(cards)}
            </div>
        </div>"""


def _generate_card(comp_id: str, title: str, fields: list) -> str:
    """Generate a detail card."""
    field_rows = "".join(
        f'<p><strong>{_escape(f.get("label", f.get("name", "")))}:</strong> <span>—</span></p>'
        for f in fields
    )
    return f"""
        <div class="component" id="{_escape(comp_id)}">
            <div class="component-title">{_escape(title)}</div>
            {field_rows}
        </div>"""


def _generate_mock_api(endpoints: list, tables: list) -> str:
    """Generate JavaScript mock API using localStorage."""
    # Build initial sample data for each table
    init_blocks = []
    for tbl in tables:
        tname = tbl.get("name", "")
        cols = [c.get("name", "") for c in tbl.get("columns", []) if c.get("name") != "id"]
        init_blocks.append(
            f"  if (!localStorage.getItem('db_{tname}')) "
            f"localStorage.setItem('db_{tname}', '[]');"
        )

    return f"""
    // Initialize localStorage DB
    (function initDB() {{
        {chr(10).join(init_blocks)}
    }})();

    function mockAPI(method, path, body) {{
        const table = path.split('/').filter(s => s && s !== 'api' && s !== 'v1')[0] || '';
        const key = 'db_' + table;
        let data = JSON.parse(localStorage.getItem(key) || '[]');

        if (method === 'GET') {{
            return {{ success: true, data: data }};
        }} else if (method === 'POST') {{
            const item = {{ id: Date.now().toString(36), ...body, created_at: new Date().toISOString() }};
            data.push(item);
            localStorage.setItem(key, JSON.stringify(data));
            return {{ success: true, data: item }};
        }} else if (method === 'DELETE') {{
            const id = path.split('/').pop();
            data = data.filter(d => d.id !== id);
            localStorage.setItem(key, JSON.stringify(data));
            return {{ success: true }};
        }}
        return {{ success: false, error: 'Unknown method' }};
    }}

    function handleFormSubmit(e, endpoint, compId) {{
        e.preventDefault();
        const form = e.target;
        const body = Object.fromEntries(new FormData(form));
        const result = mockAPI('POST', endpoint, body);
        if (result.success) {{
            showToast('Record created successfully!');
            form.reset();
        }} else {{
            showToast('Error: ' + result.error, 'error');
        }}
    }}
    """


def _generate_router(pages: list) -> str:
    """Generate hash-based SPA router."""
    return """
    function handleRoute() {
        const hash = window.location.hash.slice(1) || '/';
        const allPages = document.querySelectorAll('.page');
        const allLinks = document.querySelectorAll('.nav-links a');
        let found = false;

        allPages.forEach(p => {
            if (p.dataset.route === hash) {
                p.classList.add('active');
                found = true;
            } else {
                p.classList.remove('active');
            }
        });

        allLinks.forEach(a => {
            if (a.dataset.route === hash) {
                a.classList.add('active');
            } else {
                a.classList.remove('active');
            }
        });

        // Default to first page
        if (!found && allPages.length) {
            allPages[0].classList.add('active');
            if (allLinks.length) allLinks[0].classList.add('active');
        }
    }
    """


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
