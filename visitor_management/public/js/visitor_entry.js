frappe.ui.form.on("Visitor Entry", {

	setup(frm) {
		frm.set_query("employee_to_visit", () => ({
			filters: { enabled: 1, user_type: "System User" }
		}));
	},

	onload(frm) {
		if (frm.is_new()) {
			frm.set_value("status", "Draft");
			frm.set_value("number_of_visitors", 1);
			frm.set_value("gate_number", "Gate 1 (Main)");
		}
	},

	refresh(frm) {
		frm.trigger("set_indicator");
		frm.trigger("add_buttons");
		frm.trigger("show_dashboard_info");
	},

	// ── Status indicator dot ──────────────────────────────
	set_indicator(frm) {
		const colors = {
			"Draft":            "grey",
			"Pending Approval": "orange",
			"Approved":         "green",
			"Rejected":         "red",
			"Checked In":       "blue",
			"Checked Out":      "purple",
			"Expired":          "darkgrey",
		};
		frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "grey");
	},

	// ── Action buttons ────────────────────────────────────
	add_buttons(frm) {
		frm.clear_custom_buttons();

		const s         = frm.doc.status;
		const me        = frappe.session.user;
		const host      = frm.doc.employee_to_visit;  // direct User link
		const roles     = frappe.user_roles;

		const is_security = roles.some(r =>
			["Security Guard", "Receptionist", "System Manager", "Administrator"].includes(r)
		);
		// Approval only allowed for the exact host user or Administrator/System Manager
		const is_host_or_admin = (me === host)
			|| me === "Administrator"
			|| roles.includes("System Manager");

		// 1. Draft → request approval (security creates the entry)
		if (s === "Draft" && is_security && !frm.is_new()) {
			frm.page.set_primary_action(__("Submit for Approval"), () => {
				if (!frm.doc.employee_to_visit) {
					frappe.msgprint(__("Please select the Person to Visit before submitting."));
					return;
				}
				frappe.confirm(
					__("Send approval request to {0}?", [host]),
					() => frm.call("request_approval").then(() => frm.reload_doc())
				);
			});
		}

		// 2. Pending Approval → only host user or admin sees these buttons
		if (s === "Pending Approval") {
			if (is_host_or_admin) {
				frm.page.set_primary_action(__("Approve"), () => frm.trigger("dlg_approve"));

				frm.add_custom_button(__("Reject"), () =>
					frm.trigger("dlg_reject"), __("Actions")
				);
				frm.add_custom_button(__("Request Clarification"), () =>
					frm.trigger("dlg_clarify"), __("Actions")
				);
			} else {
				// Other users see a notice only
				frm.dashboard.add_comment(
					__("Waiting for approval from <strong>{0}</strong>.", [host]),
					"orange", true
				);
			}
		}

		// 3. Approved → security checks in
		if (s === "Approved" && is_security) {
			frm.page.set_primary_action(__("Check In"), () =>
				frappe.confirm(
					__("Confirm check-in for {0}?", [frm.doc.visitor_name]),
					() => frm.call("check_in").then(() => frm.reload_doc())
				)
			);
			frm.add_custom_button(__("Print Visitor Pass"), () =>
				frappe.utils.print("Visitor Entry", frm.docname, "Visitor Pass"),
				__("Actions")
			);
		}

		// 4. Checked In → security checks out
		if (s === "Checked In" && is_security) {
			frm.page.set_primary_action(__("Check Out"), () =>
				frappe.confirm(
					__("Confirm check-out for {0}?", [frm.doc.visitor_name]),
					() => frm.call("check_out").then(() => frm.reload_doc())
				)
			);
		}

		// 5. Blacklist option for HR/Admin on completed or rejected entries
		if (["Rejected", "Checked Out"].includes(s) && is_host_or_admin) {
			frm.add_custom_button(__("Add to Blacklist"), () =>
				frm.trigger("dlg_blacklist"), __("Actions")
			);
		}
	},

	// ── Dashboard info strips ─────────────────────────────
	show_dashboard_info(frm) {
		// Pass number = naming series name
		if (frm.doc.name && !frm.is_new()) {
			frm.dashboard.add_comment(
				__("Pass / Entry No: <strong>{0}</strong>", [frm.doc.name]),
				"blue", true
			);
		}
		if (["Approved","Checked In","Checked Out"].includes(frm.doc.status) && frm.doc.approved_by) {
			frm.dashboard.add_comment(
				__("Approved by <strong>{0}</strong> on {1}", [
					frm.doc.approved_by,
					frappe.datetime.str_to_user(frm.doc.approval_timestamp)
				]),
				"green", true
			);
		}
		if (frm.doc.status === "Checked In" && frm.doc.check_in_time) {
			frm.dashboard.add_comment(
				__("Inside since {0}", [frappe.datetime.str_to_user(frm.doc.check_in_time)]),
				"blue", true
			);
		}
		if (frm.doc.status === "Checked Out" && frm.doc.total_duration) {
			frm.dashboard.add_comment(
				__("Total duration: <strong>{0}</strong>", [frm.doc.total_duration]),
				"purple", true
			);
		}
		if (frm.doc.status === "Rejected" && frm.doc.approver_remarks) {
			frm.dashboard.add_comment(
				__("Rejection reason: {0}", [frm.doc.approver_remarks]),
				"red", true
			);
		}
	},

	// ── Dialogs ───────────────────────────────────────────
	dlg_approve(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Approve Visitor"),
			fields: [{
				fieldname: "remarks",
				fieldtype: "Small Text",
				label: __("Remarks (optional)")
			}],
			primary_action_label: __("Approve"),
			primary_action(v) {
				frm.call("approve_visitor", { remarks: v.remarks })
					.then(() => { d.hide(); frm.reload_doc(); });
			}
		});
		d.show();
	},

	dlg_reject(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Reject Visitor"),
			fields: [{
				fieldname: "remarks",
				fieldtype: "Small Text",
				label: __("Reason for Rejection"),
				reqd: 1
			}],
			primary_action_label: __("Reject"),
			primary_action(v) {
				frm.call("reject_visitor", { remarks: v.remarks })
					.then(() => { d.hide(); frm.reload_doc(); });
			}
		});
		d.show();
	},

	dlg_clarify(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Request Clarification"),
			fields: [{
				fieldname: "remarks",
				fieldtype: "Small Text",
				label: __("What clarification is needed?"),
				reqd: 1
			}],
			primary_action_label: __("Send"),
			primary_action(v) {
				frm.call("request_clarification", { remarks: v.remarks })
					.then(() => { d.hide(); frm.reload_doc(); });
			}
		});
		d.show();
	},

	dlg_blacklist(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Add to Blacklist"),
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Reason for Blacklisting"),
					reqd: 1
				},
				{
					fieldname: "blacklist_duration",
					fieldtype: "Select",
					label: __("Duration"),
					options: "Permanent\n3 Months\n6 Months\n1 Year",
					default: "Permanent"
				}
			],
			primary_action_label: __("Blacklist"),
			primary_action(v) {
				frappe.call({
					method: "visitor_management.visitor_management.visitor_management"
					        + ".doctype.visitor_blacklist.visitor_blacklist.add_to_blacklist",
					args: {
						visitor_name:  frm.doc.visitor_name,
						mobile_number: frm.doc.mobile_number,
						company_name:  frm.doc.company_name,
						reason:        v.reason,
						duration:      v.blacklist_duration,
						visitor_entry: frm.doc.name
					},
					callback(r) {
						if (!r.exc) {
							frappe.show_alert({
								message: __("Visitor added to blacklist"),
								indicator: "red"
							});
							d.hide();
						}
					}
				});
			}
		});
		d.show();
	}
});
