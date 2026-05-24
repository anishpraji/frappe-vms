// visitor_management/public/js/visitor_entry_list.js
// Plugs into ERPNext's native List View via frappe.listview_settings

frappe.listview_settings["Visitor Entry"] = {

	add_fields: ["status", "visitor_photo", "employee_to_visit", "mobile_number", "check_in_time"],

	get_indicator: function (doc) {
		const map = {
			"Draft":           ["grey",   "status,=,Draft"],
			"Pending Approval":["orange", "status,=,Pending Approval"],
			"Approved":        ["green",  "status,=,Approved"],
			"Rejected":        ["red",    "status,=,Rejected"],
			"Checked In":      ["blue",   "status,=,Checked In"],
			"Checked Out":     ["purple", "status,=,Checked Out"],
			"Expired":         ["darkgrey","status,=,Expired"],
		};
		return map[doc.status] || ["grey", "status,=,Draft"];
	},

	onload: function (listview) {
		// Quick Check-In button in list toolbar
		listview.page.add_inner_button(__("Quick Check-In"), function () {
			frappe.prompt(
				[{ fieldname: "pass_number", fieldtype: "Data", label: __("Pass / Entry Number"), reqd: 1 }],
				function (values) {
					frappe.call({
						method: "visitor_management.visitor_management.doctype.visitor_entry.visitor_entry.check_in_by_pass",
						args: { pass_number: values.pass_number },
						callback: function (r) {
							if (r.message) {
								frappe.show_alert({ message: __("✅ {0} checked in", [r.message.visitor]), indicator: "green" });
								listview.refresh();
							}
						}
					});
				},
				__("Quick Check-In"),
				__("Check In")
			);
		}, __("Actions"));

		// Scan QR button
		listview.page.add_inner_button(__("Scan QR for Exit"), function () {
			frappe.msgprint(__("Open the visitor record and use the QR scan button from the form."));
		}, __("Actions"));
	},

	formatters: {
		visitor_name: function (value, df, doc) {
			const photo = doc.visitor_photo
				? `<img src="${doc.visitor_photo}" style="width:24px;height:24px;border-radius:50%;object-fit:cover;margin-right:6px;vertical-align:middle;">`
				: `<span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:var(--gray-200);text-align:center;line-height:24px;font-size:10px;margin-right:6px;vertical-align:middle;">${(value||"").charAt(0).toUpperCase()}</span>`;
			return photo + value;
		}
	},

	hide_name_column: false,
};
