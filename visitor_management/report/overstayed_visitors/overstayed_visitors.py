# visitor_management/report/overstayed_visitors/overstayed_visitors.py

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    threshold = int(filters.get("threshold_hours") or 8)
    columns = get_columns()
    data = get_data(threshold)
    return columns, data


def get_columns():
    return [
        {"label": _("Entry"),        "fieldname": "name",             "fieldtype": "Link",     "options": "Visitor Entry", "width": 150},
        {"label": _("Visitor"),      "fieldname": "visitor_name",     "fieldtype": "Data",     "width": 160},
        {"label": _("Company"),      "fieldname": "company_name",     "fieldtype": "Data",     "width": 140},
        {"label": _("Mobile"),       "fieldname": "mobile_number",    "fieldtype": "Data",     "width": 120},
        {"label": _("Host"),         "fieldname": "employee_to_visit","fieldtype": "Link",     "options": "Employee", "width": 150},
        {"label": _("Department"),   "fieldname": "department",       "fieldtype": "Link",     "options": "Department", "width": 140},
        {"label": _("Check-In"),     "fieldname": "check_in_time",    "fieldtype": "Datetime", "width": 150},
        {"label": _("Hours Inside"), "fieldname": "hours_inside",     "fieldtype": "Float",    "width": 110},
        {"label": _("Gate"),         "fieldname": "gate_number",      "fieldtype": "Data",     "width": 130},
    ]


def get_data(threshold_hours):
    return frappe.db.sql(
        """
        SELECT
            name,
            visitor_name,
            company_name,
            mobile_number,
            employee_to_visit,
            department,
            check_in_time,
            gate_number,
            ROUND(TIMESTAMPDIFF(MINUTE, check_in_time, NOW()) / 60.0, 2) AS hours_inside
        FROM `tabVisitor Entry`
        WHERE status = 'Checked In'
          AND check_in_time IS NOT NULL
          AND TIMESTAMPDIFF(HOUR, check_in_time, NOW()) >= %(threshold)s
        ORDER BY check_in_time ASC
        """,
        {"threshold": threshold_hours},
        as_dict=True,
    )
