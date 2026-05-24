import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today, time_diff_in_seconds, add_to_date, cstr
import json
from io import BytesIO


class VisitorEntry(Document):

    # ── Lifecycle ───────────────────────────────────────────

    def after_insert(self):
        """Use the ERPNext naming series (doc.name) as the pass number."""
        self.db_set("pass_number", self.name)

    def validate(self):
        self._check_blacklist()

    # ── Blacklist check ────────────────────────────────────

    def _check_blacklist(self):
        if not self.mobile_number:
            return
        bl = frappe.db.get_value(
            "Visitor Blacklist",
            {"mobile_number": self.mobile_number, "is_active": 1},
            ["name", "reason"],
            as_dict=True
        )
        if bl:
            frappe.throw(
                _("Visitor with mobile {0} is blacklisted. Reason: {1}").format(
                    self.mobile_number, bl.reason
                ),
                title=_("Blacklisted Visitor")
            )

    # ── Approval workflow ─────────────────────────────────

    @frappe.whitelist()
    def request_approval(self):
        if self.status != "Draft":
            frappe.throw(_("Only Draft entries can be submitted for approval."))
        self.status = "Pending Approval"
        self.approval_status = "Pending"
        self.save(ignore_permissions=True)
        self._notify_host_for_approval()
        frappe.msgprint(
            _("Approval request sent to {0}").format(self.employee_to_visit),
            indicator="blue", alert=True
        )

    @frappe.whitelist()
    def approve_visitor(self, remarks=None):
        """
        Only the selected host user (employee_to_visit) or
        an Administrator can approve.
        """
        if self.status != "Pending Approval":
            frappe.throw(_("Only Pending Approval entries can be approved."))
        self._assert_is_host_or_admin()

        self.status           = "Approved"
        self.approval_status  = "Approved"
        self.approved_by      = frappe.session.user
        self.approval_timestamp = now_datetime()
        if remarks:
            self.approver_remarks = remarks

        # Pass number = naming series (already set on insert)
        # Generate QR code
        self._generate_qr_code()
        self.save(ignore_permissions=True)
        self._notify_security("approved")
        frappe.msgprint(
            _("Visitor approved. Pass Number: {0}").format(self.pass_number),
            indicator="green", alert=True
        )

    @frappe.whitelist()
    def reject_visitor(self, remarks=None):
        """Only the host user or Administrator can reject."""
        if self.status != "Pending Approval":
            frappe.throw(_("Only Pending Approval entries can be rejected."))
        self._assert_is_host_or_admin()

        self.status           = "Rejected"
        self.approval_status  = "Rejected"
        self.approved_by      = frappe.session.user
        self.approval_timestamp = now_datetime()
        if remarks:
            self.approver_remarks = remarks
        self.save(ignore_permissions=True)
        self._notify_security("rejected")
        frappe.msgprint(_("Visitor rejected."), indicator="red", alert=True)

    @frappe.whitelist()
    def request_clarification(self, remarks=None):
        """Host user or Admin can request clarification."""
        if self.status != "Pending Approval":
            frappe.throw(_("Entry must be in Pending Approval state."))
        self._assert_is_host_or_admin()
        self.approval_status  = "Clarification Requested"
        self.approver_remarks = remarks or ""
        self.save(ignore_permissions=True)
        frappe.msgprint(
            _("Clarification requested. Security has been notified."),
            indicator="orange", alert=True
        )

    # ── Check-in / Check-out ───────────────────────────────

    @frappe.whitelist()
    def check_in(self):
        if self.status != "Approved":
            frappe.throw(_("Visitor must be Approved before check-in."))
        self.status        = "Checked In"
        self.check_in_time = now_datetime()
        self.save(ignore_permissions=True)
        self._create_gate_log("IN")
        frappe.msgprint(
            _("Visitor {0} checked in at {1}").format(
                self.visitor_name,
                frappe.utils.format_datetime(self.check_in_time)
            ),
            indicator="green", alert=True
        )

    @frappe.whitelist()
    def check_out(self):
        if self.status != "Checked In":
            frappe.throw(_("Visitor is not currently checked in."))
        self.status         = "Checked Out"
        self.check_out_time = now_datetime()
        self._calculate_duration()
        self.save(ignore_permissions=True)
        self._create_gate_log("OUT")
        frappe.msgprint(
            _("Visitor {0} checked out. Duration: {1}").format(
                self.visitor_name, self.total_duration
            ),
            indicator="blue", alert=True
        )

    # ── Permission assertion ───────────────────────────────

    def _assert_is_host_or_admin(self):
        """
        Approval is restricted to:
          1. The exact User selected in employee_to_visit
          2. Administrator / System Manager
        Everyone else gets a permission error.
        """
        user = frappe.session.user
        host = self.employee_to_visit          # direct User link

        if user == host:
            return                             # ✅ host approving their own visitor

        if user == "Administrator":
            return                             # ✅ site administrator

        user_roles = set(frappe.get_roles(user))
        if "System Manager" in user_roles:
            return                             # ✅ system manager

        frappe.throw(
            _("Only {0} or Administrator can approve / reject this visitor entry.").format(host),
            frappe.PermissionError
        )

    # ── Internal helpers ───────────────────────────────────

    def _generate_qr_code(self):
        try:
            import qrcode
            qr_data = json.dumps({
                "name":    self.name,
                "pass":    self.pass_number,
                "visitor": self.visitor_name,
                "mobile":  self.mobile_number,
                "host":    self.employee_to_visit,
                "date":    cstr(today())
            })
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            file_doc = frappe.get_doc({
                "doctype":               "File",
                "file_name":             "qr_{}.png".format(self.name),
                "attached_to_doctype":   "Visitor Entry",
                "attached_to_name":      self.name,
                "attached_to_field":     "qr_code",
                "content":               buf.read(),
                "is_private":            0
            })
            file_doc.save(ignore_permissions=True)
            self.qr_code = file_doc.file_url
        except Exception:
            pass   # QR is non-critical

    def _calculate_duration(self):
        if self.check_in_time and self.check_out_time:
            secs = time_diff_in_seconds(self.check_out_time, self.check_in_time)
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            self.total_duration = "{:02d}h {:02d}m".format(h, m)

    def _create_gate_log(self, direction):
        try:
            frappe.get_doc({
                "doctype":       "Gate Log",
                "visitor_entry": self.name,
                "visitor_name":  self.visitor_name,
                "mobile_number": self.mobile_number,
                "direction":     direction,
                "gate_number":   self.gate_number or "Gate 1 (Main)",
                "timestamp":     now_datetime(),
                "logged_by":     frappe.session.user
            }).insert(ignore_permissions=True)
        except Exception:
            pass

    # ── Notifications ──────────────────────────────────────

    def _notify_host_for_approval(self):
        try:
            host_user  = self.employee_to_visit
            user_email = frappe.db.get_value("User", host_user, "email")
            if not user_email:
                return
            url = frappe.utils.get_url_to_form("Visitor Entry", self.name)
            frappe.sendmail(
                recipients=[user_email],
                subject=_("Action Required: Visitor Approval – {0}").format(self.visitor_name),
                message="""
                <p>Dear {host},</p>
                <p>A visitor is waiting at the gate to meet you.
                   Please approve or reject their entry.</p>
                <table border="1" cellpadding="6" cellspacing="0"
                       style="border-collapse:collapse;margin:10px 0;">
                  <tr><td><b>Visitor</b></td><td>{name}</td></tr>
                  <tr><td><b>Company</b></td><td>{company}</td></tr>
                  <tr><td><b>Mobile</b></td><td>{mobile}</td></tr>
                  <tr><td><b>Purpose</b></td><td>{purpose}</td></tr>
                  <tr><td><b>Pass No.</b></td><td>{passno}</td></tr>
                </table>
                <a href="{url}"
                   style="background:#2490EF;color:#fff;padding:10px 24px;
                          text-decoration:none;border-radius:4px;font-weight:600;
                          display:inline-block;margin-top:8px;">
                  Open &amp; Approve / Reject
                </a>
                <p style="margin-top:14px;color:#888;font-size:12px;">
                  Only you ({host}) or the Administrator can approve this request.
                </p>
                """.format(
                    host    = host_user,
                    name    = self.visitor_name,
                    company = self.company_name or "—",
                    mobile  = self.mobile_number,
                    purpose = self.purpose_of_visit,
                    passno  = self.pass_number or self.name,
                    url     = url
                ),
                reference_doctype=self.doctype,
                reference_name=self.name
            )
            # Real-time bell notification in ERPNext
            frappe.publish_realtime(
                "msgprint",
                {
                    "message": _(
                        "Visitor waiting: {0} from {1} — please approve or reject."
                    ).format(self.visitor_name, self.company_name or "—")
                },
                user=host_user
            )
        except Exception:
            pass

    def _notify_security(self, action):
        try:
            msgs = {
                "approved": _(
                    "✅ Visitor {0} APPROVED by {1}. Issue gate pass {2}."
                ).format(self.visitor_name, self.approved_by, self.pass_number),
                "rejected": _(
                    "❌ Visitor {0} REJECTED by {1}. Reason: {2}"
                ).format(
                    self.visitor_name,
                    self.approved_by,
                    self.approver_remarks or "—"
                ),
            }
            msg = msgs.get(action, "")
            for user in frappe.db.sql(
                """SELECT DISTINCT u.name FROM `tabUser` u
                   JOIN `tabHas Role` hr ON hr.parent = u.name
                   WHERE hr.role IN ('Security Guard', 'Receptionist')
                   AND u.enabled = 1""",
                as_dict=True
            ):
                frappe.publish_realtime(
                    "msgprint", {"message": msg}, user=user.name
                )
        except Exception:
            pass


# ── Scheduled jobs ─────────────────────────────────────────

def expire_overdue_visitors():
    try:
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
    except Exception:
        pass


def send_daily_summary():
    try:
        counts = frappe.db.sql(
            "SELECT status, COUNT(*) cnt FROM `tabVisitor Entry` "
            "WHERE DATE(creation)=CURDATE() GROUP BY status",
            as_dict=True
        )
        rows = "".join(
            "<tr><td>{}</td><td>{}</td></tr>".format(r.status, r.cnt)
            for r in counts
        )
        summary = (
            "<h3>Daily Visitor Summary</h3>"
            "<table border='1' cellpadding='5'>"
            "<tr><th>Status</th><th>Count</th></tr>"
            "{}</table>"
        ).format(rows)
        emails = frappe.db.sql(
            """SELECT DISTINCT u.email FROM `tabUser` u
               JOIN `tabHas Role` hr ON hr.parent=u.name
               WHERE hr.role IN ('HR Manager','System Manager')
               AND u.enabled=1 AND u.email IS NOT NULL""",
            as_list=True
        )
        if emails:
            frappe.sendmail(
                recipients=[e[0] for e in emails],
                subject="Daily Visitor Summary",
                message=summary
            )
    except Exception:
        pass


# ── Whitelisted API ────────────────────────────────────────

@frappe.whitelist()
def check_in_by_pass(pass_number):
    name = frappe.db.get_value(
        "Visitor Entry",
        {"pass_number": pass_number, "status": "Approved"},
        "name"
    )
    if not name:
        frappe.throw(_("No approved visitor found with pass number {0}").format(pass_number))
    doc = frappe.get_doc("Visitor Entry", name)
    doc.check_in()
    return {"status": "ok", "visitor": doc.visitor_name}


@frappe.whitelist()
def check_out_by_qr(qr_data):
    data = json.loads(qr_data)
    doc  = frappe.get_doc("Visitor Entry", data.get("name"))
    doc.check_out()
    return {"status": "ok", "visitor": doc.visitor_name, "duration": doc.total_duration}


@frappe.whitelist()
def get_live_dashboard():
    return {
        "checked_in":       frappe.db.count("Visitor Entry", {"status": "Checked In"}),
        "pending_approval": frappe.db.count("Visitor Entry", {"status": "Pending Approval"}),
        "approved_today":   frappe.db.count("Visitor Entry", {"status": "Approved",     "approval_timestamp": [">=", today()]}),
        "checked_out_today":frappe.db.count("Visitor Entry", {"status": "Checked Out",  "check_out_time":     [">=", today()]}),
        "rejected_today":   frappe.db.count("Visitor Entry", {"status": "Rejected",     "creation":           [">=", today()]}),
    }
