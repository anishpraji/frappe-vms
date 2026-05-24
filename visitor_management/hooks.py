app_name        = "visitor_management"
app_title       = "Visitor Management"
app_publisher   = "Your Company"
app_description = "Complete Visitor Management System for Manufacturing Factories"
app_icon        = "octicon octicon-person"
app_color       = "#2490EF"
app_email       = "admin@yourcompany.com"
app_license     = "MIT"
app_version     = "1.0.0"

# ── Asset bundles ──────────────────────────────────────────
# These are loaded by ERPNext's own asset pipeline.
# ERPNext applies its own CSS; we only ship behavioural JS.

app_include_js = [
    "visitor_management/public/js/visitor_entry.js",
    "visitor_management/public/js/visitor_entry_list.js",
]

# No custom CSS — we rely entirely on ERPNext's design system
app_include_css = []

# ── DocType JS overrides ───────────────────────────────────
# Maps each DocType to its client controller (alternative to app_include_js)
doctype_js = {
    "Visitor Entry": "visitor_management/public/js/visitor_entry.js",
}

doctype_list_js = {
    "Visitor Entry": "visitor_management/public/js/visitor_entry_list.js",
}

# ── Fixtures ───────────────────────────────────────────────
fixtures = [
    {
        "doctype": "Role",
        "filters": [["name", "in", ["Security Guard", "Receptionist", "Visitor Approver"]]]
    },
    {
        "doctype": "Workflow",
        "filters": [["document_type", "=", "Visitor Entry"]]
    },
    {
        "doctype": "Notification",
        "filters": [["document_type", "=", "Visitor Entry"]]
    },
    {
        "doctype": "Print Format",
        "filters": [["doc_type", "=", "Visitor Entry"]]
    },
    {
        "doctype": "Number Card",
        "filters": [["name", "in", [
            "Visitors Inside Now", "Pending Approvals",
            "Approved Today", "Checked Out Today"
        ]]]
    },
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "Visitor Management"]]
    },
    {
        "doctype": "Report",
        "filters": [["module", "=", "Visitor Management"]]
    },
]

# ── Scheduled tasks ────────────────────────────────────────
scheduler_events = {
    "hourly": [
        "visitor_management.visitor_management.doctype.visitor_entry.visitor_entry.expire_overdue_visitors"
    ],
    "daily_long": [
        "visitor_management.visitor_management.doctype.visitor_entry.visitor_entry.send_daily_summary"
    ],
}

# ── Jinja helpers ──────────────────────────────────────────
jinja = {
    "methods": [
        "visitor_management.visitor_management.utils.get_qr_code_base64"
    ]
}

# ── Override Employee dashboard ────────────────────────────
override_doctype_dashboards = {
    "Employee": "visitor_management.visitor_management.utils.get_employee_dashboard_data"
}
