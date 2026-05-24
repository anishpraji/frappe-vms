frappe.ui.form.on("Visitor Entry", {

	setup(frm) {
		frm.set_query("employee_to_visit", () => ({ filters: { status: "Active" } }));
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

	employee_to_visit(frm) {
		if (frm.doc.employee_to_visit) {
			frappe.db.get_value("Employee", frm.doc.employee_to_visit, "department", r => {
				if (r) frm.set_value("department", r.department);
			});
		}
	},

	set_indicator(frm) {
		const map = {
			"Draft":            ["grey"],
			"Pending Approval": ["orange"],
			"Approved":         ["green"],
			"Rejected":         ["red"],
			"Checked In":       ["blue"],
			"Checked Out":      ["purple"],
			"Expired":          ["darkgrey"],
		};
		const color = (map[frm.doc.status] || ["grey"])[0];
		frm.page.set_indicator(__(frm.doc.status), color);
	},

	add_buttons(frm) {
		frm.clear_custom_buttons();
		const s = frm.doc.status;
		const roles = frappe.user_roles;
		const is_security = roles.some(r => ["Security Guard","Receptionist","System Manager","Administrator"].includes(r));
		const is_hr = roles.some(r => ["HR Manager","System Manager","Administrator"].includes(r));

		frappe.db.get_value("Employee", frm.doc.employee_to_visit, "user_id", r => {
			const is_host = r && r.user_id === frappe.session.user;
			const can_approve = is_host || is_hr;

			if (s === "Draft" && is_security && !frm.is_new()) {
				frm.add_custom_button(__("Request Approval"), () => {
					frappe.confirm(__("Send approval request to {0}?", [frm.doc.employee_to_visit]),
						() => frm.call("request_approval").then(() => frm.reload_doc()));
				}, __("Actions"));
				frm.page.set_primary_action(__("Request Approval"), () =>
					frappe.confirm(__("Send approval request to {0}?", [frm.doc.employee_to_visit]),
						() => frm.call("request_approval").then(() => frm.reload_doc())));
			}

			if (s === "Pending Approval" && can_approve) {
				frm.add_custom_button(__("Approve"), () => frm.trigger("dlg_approve"), __("Actions"));
				frm.add_custom_button(__("Reject"), () => frm.trigger("dlg_reject"), __("Actions"));
				frm.add_custom_button(__("Request Clarification"), () => frm.trigger("dlg_clarify"), __("Actions"));
				frm.page.set_primary_action(__("Approve"), () => frm.trigger("dlg_approve"));
			}

			if (s === "Approved" && is_security) {
				frm.add_custom_button(__("Check In"), () =>
					frappe.confirm(__("Confirm check-in for {0}?", [frm.doc.visitor_name]),
						() => frm.call("check_in").then(() => frm.reload_doc())), __("Actions"));
				frm.add_custom_button(__("Print Visitor Pass"), () =>
					frappe.utils.print("Visitor Entry", frm.docname, "Visitor Pass"), __("Actions"));
				frm.page.set_primary_action(__("Check In"), () =>
					frappe.confirm(__("Confirm check-in for {0}?", [frm.doc.visitor_name]),
						() => frm.call("check_in").then(() => frm.reload_doc())));
			}

			if (s === "Checked In" && is_security) {
				frm.add_custom_button(__("Check Out"), () =>
					frappe.confirm(__("Confirm check-out for {0}?", [frm.doc.visitor_name]),
						() => frm.call("check_out").then(() => frm.reload_doc())), __("Actions"));
				frm.page.set_primary_action(__("Check Out"), () =>
					frappe.confirm(__("Confirm check-out for {0}?", [frm.doc.visitor_name]),
						() => frm.call("check_out").then(() => frm.reload_doc())));
			}

			if (["Rejected","Checked Out"].includes(s) && is_hr) {
				frm.add_custom_button(__("Add to Blacklist"), () => frm.trigger("dlg_blacklist"), __("Actions"));
			}
		});
	},

	show_dashboard_info(frm) {
		if (["Approved","Checked In","Checked Out"].includes(frm.doc.status) && frm.doc.pass_number) {
			frm.dashboard.add_comment(
				__("Pass: <strong>{0}</strong>", [frm.doc.pass_number]), "green", true);
		}
		if (frm.doc.status === "Checked In" && frm.doc.check_in_time) {
			frm.dashboard.add_comment(
				__("Inside since {0}", [frappe.datetime.str_to_user(frm.doc.check_in_time)]), "blue", true);
		}
		if (frm.doc.status === "Checked Out" && frm.doc.total_duration) {
			frm.dashboard.add_comment(
				__("Total duration: <strong>{0}</strong>", [frm.doc.total_duration]), "purple", true);
		}
	},

	dlg_approve(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Approve Visitor"),
			fields: [{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks (optional)") }],
			primary_action_label: __("Approve"),
			primary_action(v) {
				frm.call("approve_visitor", { remarks: v.remarks }).then(() => { d.hide(); frm.reload_doc(); });
			}
		});
		d.show();
	},

	dlg_reject(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Reject Visitor"),
			fields: [{ fieldname: "remarks", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
			primary_action_label: __("Reject"),
			primary_action(v) {
				frm.call("reject_visitor", { remarks: v.remarks }).then(() => { d.hide(); frm.reload_doc(); });
			}
		});
		d.show();
	},

	dlg_clarify(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Request Clarification"),
			fields: [{ fieldname: "remarks", fieldtype: "Small Text", label: __("What clarification is needed?"), reqd: 1 }],
			primary_action_label: __("Send"),
			primary_action(v) {
				frm.call("request_clarification", { remarks: v.remarks }).then(() => { d.hide(); frm.reload_doc(); });
			}
		});
		d.show();
	},

	dlg_blacklist(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Add to Blacklist"),
			fields: [
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
				{ fieldname: "blacklist_duration", fieldtype: "Select", label: __("Duration"),
				  options: "Permanent\n3 Months\n6 Months\n1 Year", default: "Permanent" }
			],
			primary_action_label: __("Blacklist"),
			primary_action(v) {
				frappe.call({
					method: "visitor_management.visitor_management.doctype.visitor_blacklist.visitor_blacklist.add_to_blacklist",
					args: { visitor_name: frm.doc.visitor_name, mobile_number: frm.doc.mobile_number,
					        company_name: frm.doc.company_name, reason: v.reason,
					        duration: v.blacklist_duration, visitor_entry: frm.doc.name },
					callback(r) { if (!r.exc) { frappe.show_alert({ message: __("Blacklisted"), indicator: "red" }); d.hide(); } }
				});
			}
		});
		d.show();
	},
});
