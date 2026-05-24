# visitor_management/report/daily_visitor_summary/daily_visitor_summary.py
# Registered as a Script Report in ERPNext — shows in Report Builder natively

import frappe
from frappe import _
from frappe.utils import getdate, today, add_days


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": _("Checked In"),
            "fieldname": "checked_in",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "label": _("Checked Out"),
            "fieldname": "checked_out",
            "fieldtype": "Int",
            "width": 115,
        },
        {
            "label": _("Approved"),
            "fieldname": "approved",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Pending"),
            "fieldname": "pending",
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "label": _("Rejected"),
            "fieldname": "rejected",
            "fieldtype": "Int",
            "width": 95,
        },
    ]


def get_data(filters):
    from_date = filters.get("from_date") or add_days(today(), -30)
    to_date   = filters.get("to_date") or today()

    return frappe.db.sql(
        """
        SELECT
            DATE(creation)                                           AS `date`,
            COUNT(*)                                                 AS total,
            SUM(status = 'Checked In')                               AS checked_in,
            SUM(status = 'Checked Out')                              AS checked_out,
            SUM(status = 'Approved')                                 AS approved,
            SUM(status = 'Pending Approval')                         AS pending,
            SUM(status = 'Rejected')                                 AS rejected
        FROM `tabVisitor Entry`
        WHERE DATE(creation) BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY DATE(creation)
        ORDER BY DATE(creation) DESC
        """,
        {"from_date": from_date, "to_date": to_date},
        as_dict=True,
    )


def get_chart(data):
    if not data:
        return None
    labels     = [str(row.date) for row in reversed(data)]
    checked_in = [row.checked_in or 0 for row in reversed(data)]
    checked_out= [row.checked_out or 0 for row in reversed(data)]
    rejected   = [row.rejected or 0 for row in reversed(data)]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Checked In"),  "values": checked_in,  "chartType": "bar"},
                {"name": _("Checked Out"), "values": checked_out, "chartType": "bar"},
                {"name": _("Rejected"),    "values": rejected,    "chartType": "line"},
            ],
        },
        "type": "axis-mixed",
        "barOptions": {"stacked": 0},
        "colors": ["#2490EF", "#28A745", "#E74C3C"],
        "axisOptions": {"xIsSeries": True},
    }


def get_summary(data):
    if not data:
        return []
    total      = sum(r.total or 0 for r in data)
    checked_in = sum(r.checked_in or 0 for r in data)
    rejected   = sum(r.rejected or 0 for r in data)
    return [
        {"label": _("Total Visitors"),   "value": total,      "indicator": "blue"},
        {"label": _("Checked In"),        "value": checked_in, "indicator": "green"},
        {"label": _("Rejected"),          "value": rejected,   "indicator": "red"},
    ]
