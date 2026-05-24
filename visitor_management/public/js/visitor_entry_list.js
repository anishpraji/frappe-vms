frappe.listview_settings["Visitor Entry"] = {
	add_fields: ["status", "visitor_photo", "employee_to_visit", "mobile_number"],

	get_indicator(doc) {
		return {
			"Draft":            ["grey",     "status,=,Draft"],
			"Pending Approval": ["orange",   "status,=,Pending Approval"],
			"Approved":         ["green",    "status,=,Approved"],
			"Rejected":         ["red",      "status,=,Rejected"],
			"Checked In":       ["blue",     "status,=,Checked In"],
			"Checked Out":      ["purple",   "status,=,Checked Out"],
			"Expired":          ["darkgrey", "status,=,Expired"],
		}[doc.status] || ["grey", "status,=,Draft"];
	},

	onload(listview) {
		listview.page.add_inner_button(__("Quick Check-In"), () => {
			frappe.prompt(
				[{ fieldname: "pass_number", fieldtype: "Data", label: __("Pass Number"), reqd: 1 }],
				values => {
					frappe.call({
						method: "visitor_management.visitor_management.doctype.visitor_entry.visitor_entry.check_in_by_pass",
						args: { pass_number: values.pass_number },
						callback(r) {
							if (r.message) {
								frappe.show_alert({ message: __("{0} checked in", [r.message.visitor]), indicator: "green" });
								listview.refresh();
							}
						}
					});
				},
				__("Quick Check-In"), __("Check In")
			);
		}, __("Actions"));
	},
};
