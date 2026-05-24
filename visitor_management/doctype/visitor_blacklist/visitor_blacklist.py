import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, add_to_date


class VisitorBlacklist(Document):
    def before_insert(self):
        self.blacklisted_by = frappe.session.user
        self.blacklist_date = today()
        duration_map = {"3 Months": {"months": 3}, "6 Months": {"months": 6}, "1 Year": {"years": 1}}
        if self.blacklist_duration and self.blacklist_duration != "Permanent":
            self.expiry_date = add_to_date(today(), **duration_map[self.blacklist_duration])


@frappe.whitelist()
def add_to_blacklist(visitor_name, mobile_number, company_name, reason, duration, visitor_entry):
    doc = frappe.get_doc({
        "doctype": "Visitor Blacklist",
        "visitor_name": visitor_name,
        "mobile_number": mobile_number,
        "company_name": company_name,
        "reason": reason,
        "blacklist_duration": duration or "Permanent",
        "visitor_entry_reference": visitor_entry,
        "is_active": 1
    })
    doc.insert(ignore_permissions=True)
    return doc.name
