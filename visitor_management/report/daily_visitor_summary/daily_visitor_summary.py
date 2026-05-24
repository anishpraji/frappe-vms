import frappe
from frappe import _
from frappe.utils import today, add_days


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters), None, get_chart(get_data(filters)), get_summary(get_data(filters))


def get_columns():
    return [
        {"label": _("Date"),         "fieldname": "date",        "fieldtype": "Date", "width": 110},
        {"label": _("Total"),        "fieldname": "total",       "fieldtype": "Int",  "width": 80},
        {"label": _("Checked In"),   "fieldname": "checked_in",  "fieldtype": "Int",  "width": 110},
        {"label": _("Checked Out"),  "fieldname": "checked_out", "fieldtype": "Int",  "width": 115},
        {"label": _("Approved"),     "fieldname": "approved",    "fieldtype": "Int",  "width": 100},
        {"label": _("Pending"),      "fieldname": "pending",     "fieldtype": "Int",  "width": 90},
        {"label": _("Rejected"),     "fieldname": "rejected",    "fieldtype": "Int",  "width": 95},
    ]


def get_data(filters):
    return frappe.db.sql("""
        SELECT DATE(creation) AS `date`, COUNT(*) AS total,
               SUM(status='Checked In') AS checked_in,
               SUM(status='Checked Out') AS checked_out,
               SUM(status='Approved') AS approved,
               SUM(status='Pending Approval') AS pending,
               SUM(status='Rejected') AS rejected
        FROM `tabVisitor Entry`
        WHERE DATE(creation) BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY DATE(creation)
        ORDER BY DATE(creation) DESC
    """, {
        "from_date": filters.get("from_date") or add_days(today(), -30),
        "to_date":   filters.get("to_date")   or today(),
    }, as_dict=True)


def get_chart(data):
    if not data:
        return None
    rows = list(reversed(data))
    return {
        "data": {
            "labels": [str(r.date) for r in rows],
            "datasets": [
                {"name": _("Checked In"),  "values": [r.checked_in  or 0 for r in rows]},
                {"name": _("Checked Out"), "values": [r.checked_out or 0 for r in rows]},
                {"name": _("Rejected"),    "values": [r.rejected    or 0 for r in rows]},
            ],
        },
        "type": "bar",
        "colors": ["#2490EF", "#28A745", "#E74C3C"],
        "axisOptions": {"xIsSeries": True},
    }


def get_summary(data):
    total = sum(r.total or 0 for r in data)
    return [
        {"label": _("Total Visitors"), "value": total,                                     "indicator": "blue"},
        {"label": _("Checked In"),     "value": sum(r.checked_in  or 0 for r in data),     "indicator": "green"},
        {"label": _("Rejected"),       "value": sum(r.rejected    or 0 for r in data),     "indicator": "red"},
    ]
