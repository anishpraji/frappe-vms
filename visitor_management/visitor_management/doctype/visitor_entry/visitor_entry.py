import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today, time_diff_in_seconds, add_to_date, cstr
import json
from io import BytesIO


class VisitorEntry(Document):

    def validate(self):
        self._check_blacklist()
        self._validate_id_number()

    def _check_blacklist(self):
        bl = frappe.db.get_value(
            "Visitor Blacklist",
            {"mobile_number": self.mobile_number, "is_active": 1},
            ["name", "reason"], as_dict=True
        )
        if bl:
            frappe.throw(
                _("Visitor with mobile {0} is blacklisted. Reason: {1}").format(
                    self.mobile_number, bl.reason),
                title=_("Blacklisted Visitor")
            )

    def _validate_id_number(self):
        if self.id_proof_type == "Aadhaar Card" and self.id_number:
            clean = self.id_number.replace(" ", "").replace("-", "")
            if len(clean) != 12:
                frappe.msgprint(_("Aadhaar number should be 12 digits."), alert=True, indicator="orange")

    @frappe.whitelist()
    def request_approval(self):
        self.status = "Pending Approval"
        self.approval_status = "Pending"
        self.save(ignore_permissions=True)
        self._notify_employee_for_approval()
        frappe.msgprint(_("Approval request sent to {0}").format(self.employee_to_visit), indicator="blue", alert=True)

    @frappe.whitelist()
    def approve_visitor(self, remarks=None):
        self._assert_approver()
        self.status = "Approved"
        self.approval_status = "Approved"
        self.approved_by = frappe.session.user
        self.approval_timestamp = now_datetime()
        if remarks:
            self.approver_remarks = remarks
        self._generate_pass_number()
        self._generate_qr_code()
        self.save(ignore_permissions=True)
        self._notify_security("approved")
        frappe.msgprint(_("Visitor approved. Pass {0} generated.").format(self.pass_number), indicator="green", alert=True)

    @frappe.whitelist()
    def reject_visitor(self, remarks=None):
        self._assert_approver()
        self.status = "Rejected"
        self.approval_status = "Rejected"
        self.approved_by = frappe.session.user
        self.approval_timestamp = now_datetime()
        if remarks:
            self.approver_remarks = remarks
        self.save(ignore_permissions=True)
        self._notify_security("rejected")
        frappe.msgprint(_("Visitor rejected."), indicator="red", alert=True)

    @frappe.whitelist()
    def request_clarification(self, remarks=None):
        self._assert_approver()
        self.approval_status = "Clarification Requested"
        self.approver_remarks = remarks or ""
        self.save(ignore_permissions=True)
        self._notify_security("clarification")

    @frappe.whitelist()
    def check_in(self):
        if self.status != "Approved":
            frappe.throw(_("Visitor must be Approved before check-in."))
        self.status = "Checked In"
        self.check_in_time = now_datetime()
        self.save(ignore_permissions=True)
        self._create_gate_log("IN")
        frappe.msgprint(
            _("✅ {0} checked in at {1}").format(
                self.visitor_name,
                frappe.utils.format_datetime(self.check_in_time)
            ),
            indicator="green", alert=True
        )

    @frappe.whitelist()
    def check_out(self):
        if self.status != "Checked In":
            frappe.throw(_("Visitor is not currently checked in."))
        self.status = "Checked Out"
        self.check_out_time = now_datetime()
        self._calculate_duration()
        self.save(ignore_permissions=True)
        self._create_gate_log("OUT")
        frappe.msgprint(
            _("👋 {0} checked out. Duration: {1}").format(self.visitor_name, self.total_duration),
            indicator="blue", alert=True
        )

    def _generate_pass_number(self):
        if not self.pass_number:
            last = frappe.db.sql(
                "SELECT MAX(CAST(SUBSTRING(pass_number,5) AS UNSIGNED)) FROM `tabVisitor Entry` WHERE pass_number IS NOT NULL"
            )
            seq = (last[0][0] or 0) + 1
            self.pass_number = "PASS{:06d}".format(seq)

    def _generate_qr_code(self):
        try:
            import qrcode
            qr_data = json.dumps({
                "name": self.name,
                "pass": self.pass_number,
                "visitor": self.visitor_name,
                "mobile": self.mobile_number,
                "host": self.employee_to_visit,
                "date": cstr(today())
            })
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": "qr_{}.png".format(self.name),
                "attached_to_doctype": "Visitor Entry",
                "attached_to_name": self.name,
                "attached_to_field": "qr_code",
                "content": buf.read(),
                "is_private": 0
            })
            file_doc.save(ignore_permissions=True)
            self.qr_code = file_doc.file_url
        except ImportError:
            frappe.msgprint(_("Install qrcode library: pip install qrcode[pil]"), indicator="orange", alert=True)

    def _calculate_duration(self):
        if self.check_in_time and self.check_out_time:
            secs = time_diff_in_seconds(self.check_out_time, self.check_in_time)
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            self.total_duration = "{:02d}h {:02d}m".format(h, m)

    def _create_gate_log(self, direction):
        frappe.get_doc({
            "doctype": "Gate Log",
            "visitor_entry": self.name,
            "visitor_name": self.visitor_name,
            "mobile_number": self.mobile_number,
            "direction": direction,
            "gate_number": self.gate_number or "Gate 1 (Main)",
            "timestamp": now_datetime(),
            "logged_by": frappe.session.user
        }).insert(ignore_permissions=True)

    def _assert_approver(self):
        user = frappe.session.user
        employee_user = frappe.db.get_value("Employee", self.employee_to_visit, "user_id")
        allowed_roles = {"HR Manager", "System Manager", "Administrator"}
        if user != employee_user and not (set(frappe.get_roles(user)) & allowed_roles):
            frappe.throw(_("Only the host employee or HR/Admin can approve this visitor."))

    def _notify_employee_for_approval(self):
        employee_user = frappe.db.get_value("Employee", self.employee_to_visit, "user_id")
        if not employee_user:
            return
        url = frappe.utils.get_url_to_form("Visitor Entry", self.name)
        frappe.sendmail(
            recipients=[employee_user],
            subject=_("Visitor Approval Request – {0}").format(self.visitor_name),
            message="""
            <p>A visitor is waiting at the gate to meet you.</p>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
                <tr><td><b>Visitor</b></td><td>{name}</td></tr>
                <tr><td><b>Company</b></td><td>{company}</td></tr>
                <tr><td><b>Mobile</b></td><td>{mobile}</td></tr>
                <tr><td><b>Purpose</b></td><td>{purpose}</td></tr>
                <tr><td><b>Gate</b></td><td>{gate}</td></tr>
            </table>
            <br>
            <a href="{url}" style="background:#2490EF;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px;">
                Open &amp; Respond
            </a>
            """.format(
                name=self.visitor_name, company=self.company_name or "—",
                mobile=self.mobile_number, purpose=self.purpose_of_visit,
                gate=self.gate_number or "Main Gate", url=url
            ),
            reference_doctype=self.doctype,
            reference_name=self.name
        )
        frappe.publish_realtime(
            "msgprint",
            {"message": _("Visitor waiting for your approval: {0}").format(self.visitor_name)},
            user=employee_user
        )

    def _notify_security(self, action):
        msgs = {
            "approved": _("✅ {0} APPROVED by {1}. Issue gate pass.").format(self.visitor_name, self.employee_to_visit),
            "rejected": _("❌ {0} REJECTED by {1}. Reason: {2}").format(self.visitor_name, self.employee_to_visit, self.approver_remarks or "—"),
            "clarification": _("⚠️ Clarification needed for {0}: {1}").format(self.visitor_name, self.approver_remarks),
        }
        msg = msgs.get(action, "")
        for user in frappe.db.sql(
            """SELECT DISTINCT u.name FROM `tabUser` u
               JOIN `tabHas Role` hr ON hr.parent=u.name
               WHERE hr.role IN ('Security Guard','Receptionist') AND u.enabled=1""",
            as_dict=True
        ):
            frappe.publish_realtime("msgprint", {"message": msg}, user=user.name)


# ── Scheduled jobs ─────────────────────────────────────────

def expire_overdue_visitors():
    two_hours_ago = add_to_date(now_datetime(), hours=-2)
    overdue = frappe.db.get_all(
        "Visitor Entry",
        filters={"status": "Approved", "approval_timestamp": ["<", two_hours_ago]},
        fields=["name"]
    )
    for e in overdue:
        frappe.db.set_value("Visitor Entry", e.name, "status", "Expired")
    if overdue:
        frappe.db.commit()


def send_daily_summary():
    counts = frappe.db.sql(
        "SELECT status, COUNT(*) cnt FROM `tabVisitor Entry` WHERE DATE(creation)=CURDATE() GROUP BY status",
        as_dict=True
    )
    summary = "<h3>Daily Visitor Summary</h3><table border='1' cellpadding='5'><tr><th>Status</th><th>Count</th></tr>"
    for r in counts:
        summary += "<tr><td>{}</td><td>{}</td></tr>".format(r.status, r.cnt)
    summary += "</table>"
    emails = frappe.db.sql(
        """SELECT DISTINCT u.email FROM `tabUser` u JOIN `tabHas Role` hr ON hr.parent=u.name
           WHERE hr.role IN ('HR Manager','System Manager') AND u.enabled=1 AND u.email IS NOT NULL""",
        as_list=True
    )
    if emails:
        frappe.sendmail(
            recipients=[e[0] for e in emails],
            subject="Daily Visitor Summary",
            message=summary
        )


# ── Whitelisted API ────────────────────────────────────────

@frappe.whitelist()
def check_in_by_pass(pass_number):
    name = frappe.db.get_value("Visitor Entry", {"pass_number": pass_number, "status": "Approved"}, "name")
    if not name:
        frappe.throw(_("No approved visitor found with pass number {0}").format(pass_number))
    doc = frappe.get_doc("Visitor Entry", name)
    doc.check_in()
    return {"status": "ok", "visitor": doc.visitor_name}


@frappe.whitelist()
def check_out_by_qr(qr_data):
    data = json.loads(qr_data)
    doc = frappe.get_doc("Visitor Entry", data.get("name"))
    doc.check_out()
    return {"status": "ok", "visitor": doc.visitor_name, "duration": doc.total_duration}


@frappe.whitelist()
def get_live_dashboard():
    return {
        "checked_in":      frappe.db.count("Visitor Entry", {"status": "Checked In"}),
        "pending_approval":frappe.db.count("Visitor Entry", {"status": "Pending Approval"}),
        "approved_today":  frappe.db.count("Visitor Entry", {"status": "Approved",      "approval_timestamp": [">=", today()]}),
        "checked_out_today":frappe.db.count("Visitor Entry", {"status": "Checked Out",  "check_out_time":     [">=", today()]}),
        "rejected_today":  frappe.db.count("Visitor Entry", {"status": "Rejected",      "creation":           [">=", today()]}),
    }
