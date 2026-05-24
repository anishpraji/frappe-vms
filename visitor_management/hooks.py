app_name        = "visitor_management"
app_title       = "Visitor Management"
app_publisher   = "Your Company"
app_description = "Complete Visitor Management System for Manufacturing Factories"
app_email       = "admin@yourcompany.com"
app_license     = "MIT"
app_version     = "1.0.0"

# ── Asset registration ─────────────────────────────────────
doctype_js = {
    "Visitor Entry": "public/js/visitor_entry.js",
}

doctype_list_js = {
    "Visitor Entry": "public/js/visitor_entry_list.js",
}

# ── Scheduled tasks ────────────────────────────────────────
scheduler_events = {
    "hourly": [
        "visitor_management.visitor_management.visitor_management.doctype.visitor_entry.visitor_entry.expire_overdue_visitors"
    ],
    "daily_long": [
        "visitor_management.visitor_management.visitor_management.doctype.visitor_entry.visitor_entry.send_daily_summary"
    ],
}
