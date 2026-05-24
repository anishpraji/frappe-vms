import frappe
from frappe.model.document import Document


class VisitorSettings(Document):
    pass


def get_settings():
    return frappe.get_single("Visitor Settings")
