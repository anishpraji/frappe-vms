// visitor_management/public/js/visitor_entry.js
// Uses only real Frappe/ERPNext APIs - no custom CSS, no custom HTML shells.
// ERPNext renders all UI automatically from DocType JSON + this controller.

frappe.ui.form.on("Visitor Entry", {

	// ── Setup ──────────────────────────────────────────────
	setup: function (frm) {
		frm.set_query("employee_to_visit", function () {
			return { filters: { status: "Active" } };
		});
		frm.set_query("department", function () {
			return {};
		});
	},

	// ── On Load ────────────────────────────────────────────
	onload: function (frm) {
		if (frm.is_new()) {
			frm.set_value("status", "Draft");
			frm.set_value("number_of_visitors", 1);
			frm.set_value("gate_number", "Gate 1 (Main)");
		}
	},

	// ── Refresh (runs on every render) ─────────────────────
	refresh: function (frm) {
		frm.trigger("set_status_color");
		frm.trigger("add_action_buttons");
		frm.trigger("setup_camera_button");
		frm.trigger("show_pass_section");
	},

	// ── Field events ───────────────────────────────────────
	employee_to_visit: function (frm) {
		if (frm.doc.employee_to_visit) {
			frappe.db.get_value(
				"Employee",
				frm.doc.employee_to_visit,
				["department", "cell_number", "user_id"],
				function (r) {
					if (r) {
						frm.set_value("department", r.department);
					}
				}
			);
		}
	},

	check_in_time: function (frm) {
		frm.trigger("calculate_duration");
	},

	check_out_time: function (frm) {
		frm.trigger("calculate_duration");
	},

	// ── Custom triggers ────────────────────────────────────

	set_status_color: function (frm) {
		const color_map = {
			"Draft":            "grey",
			"Pending Approval": "orange",
			"Approved":         "green",
			"Rejected":         "red",
			"Checked In":       "blue",
			"Checked Out":      "purple",
			"Expired":          "darkgrey",
		};
		const color = color_map[frm.doc.status] || "grey";
		frm.page.set_indicator(__(frm.doc.status), color);
	},

	add_action_buttons: function (frm) {
		// Clear previous custom buttons first
		frm.clear_custom_buttons();

		const status  = frm.doc.status;
		const roles   = frappe.user_roles || [];
		const is_sec  = roles.some(r => ["Security Guard", "Receptionist", "System Manager", "Administrator"].includes(r));
		const is_hr   = roles.some(r => ["HR Manager", "System Manager", "Administrator"].includes(r));

		// Determine if current user is the host employee
		frappe.db.get_value("Employee", frm.doc.employee_to_visit, "user_id", function (r) {
			const is_host = r && r.user_id === frappe.session.user;
			const can_approve = is_host || is_hr;

			// 1. Request Approval — Security, Draft state, saved doc
			if (status === "Draft" && is_sec && !frm.is_new()) {
				frm.add_custom_button(__("Request Approval"), function () {
					frappe.confirm(
						__("Send approval request to {0}?", [frm.doc.employee_to_visit]),
						function () {
							frm.call("request_approval").then(() => frm.reload_doc());
						}
					);
				}, __("Actions"));
				frm.page.set_primary_action(__("Request Approval"), () => {
					frappe.confirm(
						__("Send approval request to {0}?", [frm.doc.employee_to_visit]),
						() => frm.call("request_approval").then(() => frm.reload_doc())
					);
				});
			}

			// 2. Approve / Reject / Clarify — host employee or HR
			if (status === "Pending Approval" && can_approve) {
				frm.add_custom_button(__("Approve"), function () {
					frm.trigger("approval_dialog");
				}, __("Actions"));

				frm.add_custom_button(__("Reject"), function () {
					frm.trigger("reject_dialog");
				}, __("Actions"));

				frm.add_custom_button(__("Request Clarification"), function () {
					frm.trigger("clarify_dialog");
				}, __("Actions"));

				frm.page.set_primary_action(__("Approve"), () => frm.trigger("approval_dialog"));
			}

			// 3. Check In — Security, Approved
			if (status === "Approved" && is_sec) {
				frm.add_custom_button(__("Check In"), function () {
					frappe.confirm(
						__("Confirm check-in for {0}?", [frm.doc.visitor_name]),
						function () {
							frm.call("check_in").then(() => frm.reload_doc());
						}
					);
				}, __("Actions"));

				frm.add_custom_button(__("Print Visitor Pass"), function () {
					frappe.utils.print(frm.doctype, frm.docname, "Visitor Pass", null, frm.doc.language);
				}, __("Actions"));

				frm.page.set_primary_action(__("Check In"), () => {
					frappe.confirm(
						__("Confirm check-in for {0}?", [frm.doc.visitor_name]),
						() => frm.call("check_in").then(() => frm.reload_doc())
					);
				});
			}

			// 4. Check Out — Security, Checked In
			if (status === "Checked In" && is_sec) {
				frm.add_custom_button(__("Check Out"), function () {
					frappe.confirm(
						__("Confirm check-out for {0}?", [frm.doc.visitor_name]),
						function () {
							frm.call("check_out").then(() => frm.reload_doc());
						}
					);
				}, __("Actions"));

				frm.page.set_primary_action(__("Check Out"), () => {
					frappe.confirm(
						__("Confirm check-out for {0}?", [frm.doc.visitor_name]),
						() => frm.call("check_out").then(() => frm.reload_doc())
					);
				});
			}

			// 5. Add to Blacklist — HR/Admin on Rejected or Checked Out
			if (["Rejected", "Checked Out"].includes(status) && is_hr) {
				frm.add_custom_button(__("Add to Blacklist"), function () {
					frm.trigger("blacklist_dialog");
				}, __("Actions"));
			}
		});
	},

	// ── Dialogs using frappe.ui.Dialog (native ERPNext) ───

	approval_dialog: function (frm) {
		const d = new frappe.ui.Dialog({
			title: __("Approve Visitor"),
			fields: [
				{
					fieldname: "remarks",
					fieldtype: "Small Text",
					label: __("Remarks (optional)"),
					description: __("Any special instructions for security staff"),
				},
			],
			primary_action_label: __("Approve"),
			primary_action: function (values) {
				frm.call("approve_visitor", { remarks: values.remarks }).then(() => {
					d.hide();
					frm.reload_doc();
				});
			},
		});
		d.show();
	},

	reject_dialog: function (frm) {
		const d = new frappe.ui.Dialog({
			title: __("Reject Visitor"),
			fields: [
				{
					fieldname: "remarks",
					fieldtype: "Small Text",
					label: __("Reason for Rejection"),
					reqd: 1,
				},
			],
			primary_action_label: __("Reject"),
			primary_action: function (values) {
				frm.call("reject_visitor", { remarks: values.remarks }).then(() => {
					d.hide();
					frm.reload_doc();
				});
			},
		});
		d.show();
	},

	clarify_dialog: function (frm) {
		const d = new frappe.ui.Dialog({
			title: __("Request Clarification"),
			fields: [
				{
					fieldname: "remarks",
					fieldtype: "Small Text",
					label: __("What clarification is needed?"),
					reqd: 1,
				},
			],
			primary_action_label: __("Send"),
			primary_action: function (values) {
				frm.call("request_clarification", { remarks: values.remarks }).then(() => {
					d.hide();
					frm.reload_doc();
				});
			},
		});
		d.show();
	},

	blacklist_dialog: function (frm) {
		const d = new frappe.ui.Dialog({
			title: __("Add Visitor to Blacklist"),
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Reason for Blacklisting"),
					reqd: 1,
				},
				{
					fieldname: "blacklist_duration",
					fieldtype: "Select",
					label: __("Duration"),
					options: "Permanent\n3 Months\n6 Months\n1 Year",
					default: "Permanent",
				},
			],
			primary_action_label: __("Blacklist Visitor"),
			primary_action: function (values) {
				frappe.call({
					method: "visitor_management.visitor_management.doctype.visitor_blacklist.visitor_blacklist.add_to_blacklist",
					args: {
						visitor_name: frm.doc.visitor_name,
						mobile_number: frm.doc.mobile_number,
						company_name: frm.doc.company_name,
						reason: values.reason,
						duration: values.blacklist_duration,
						visitor_entry: frm.doc.name,
					},
					callback: function (r) {
						if (!r.exc) {
							frappe.show_alert({ message: __("Visitor added to blacklist"), indicator: "red" });
							d.hide();
						}
					},
				});
			},
		});
		d.show();
	},

	// ── Webcam capture using frappe.ui.Dialog ─────────────
	setup_camera_button: function (frm) {
		if (frm.doc.docstatus === 1) return;

		// Use frappe's built-in attach mechanism + add a camera button via field
		// This hooks into the visitor_photo Attach Image field's area
		setTimeout(function () {
			const $field = frm.get_field("visitor_photo").$wrapper;
			if ($field.find(".vms-cam-btn").length) return;
			$field.find(".attached-file, .btn-attach").after(
				$(`<button class="btn btn-xs btn-default vms-cam-btn" style="margin:4px 0 0;">
					<i class="fa fa-camera"></i> ${__("Use Webcam")}
				</button>`).on("click", function () {
					frm.trigger("open_webcam_capture");
				})
			);
		}, 600);
	},

	open_webcam_capture: function (frm) {
		const dialog_html = `
			<div style="text-align:center">
				<video id="vms-video" autoplay playsinline
					style="width:100%;max-height:280px;border-radius:var(--border-radius-md);background:#000;">
				</video>
				<canvas id="vms-canvas" style="display:none;"></canvas>
				<img id="vms-preview" style="display:none;width:100%;max-height:280px;border-radius:var(--border-radius-md);">
			</div>`;

		const d = new frappe.ui.Dialog({
			title: __("Capture Visitor Photo"),
			fields: [{ fieldtype: "HTML", options: dialog_html }],
			primary_action_label: __("Capture"),
			primary_action: function () {
				const video   = document.getElementById("vms-video");
				const canvas  = document.getElementById("vms-canvas");
				const preview = document.getElementById("vms-preview");

				if (preview.style.display !== "none") {
					// Save the captured image
					canvas.toBlob(function (blob) {
						const file = new File([blob], `visitor_${frm.doc.name || "new"}.jpg`, { type: "image/jpeg" });
						frappe.ui.upload.handle_uploaded_file(file, frm, "visitor_photo");
						frappe.show_alert({ message: __("Photo captured successfully"), indicator: "green" });
					}, "image/jpeg", 0.88);
					if (stream) stream.getTracks().forEach(t => t.stop());
					d.hide();
				} else {
					// First click = capture frame
					const video = document.getElementById("vms-video");
					const canvas = document.getElementById("vms-canvas");
					canvas.width  = video.videoWidth;
					canvas.height = video.videoHeight;
					canvas.getContext("2d").drawImage(video, 0, 0);
					preview.src = canvas.toDataURL("image/jpeg");
					preview.style.display = "block";
					video.style.display   = "none";
					d.set_primary_action_label(__("Use This Photo"));
				}
			},
		});

		let stream = null;
		d.show();

		navigator.mediaDevices.getUserMedia({ video: true })
			.then(function (s) {
				stream = s;
				document.getElementById("vms-video").srcObject = s;
			})
			.catch(function () {
				frappe.msgprint(__("Camera not available. Please upload a photo instead."));
				d.hide();
			});

		d.$wrapper.on("hidden.bs.modal", function () {
			if (stream) stream.getTracks().forEach(t => t.stop());
		});
	},

	// ── Show pass & QR on approved docs ───────────────────
	show_pass_section: function (frm) {
		if (["Approved", "Checked In", "Checked Out"].includes(frm.doc.status) && frm.doc.pass_number) {
			frm.dashboard.add_comment(
				__("Pass Number: <strong>{0}</strong>  |  Issued: {1}",
					[frm.doc.pass_number, frappe.datetime.str_to_user(frm.doc.approval_timestamp)]
				),
				"green",
				true
			);
		}
		if (frm.doc.status === "Checked In" && frm.doc.check_in_time) {
			const since = frappe.datetime.prettyDate(frm.doc.check_in_time);
			frm.dashboard.add_comment(
				__("Visitor has been inside the premises since {0}", [since]),
				"blue",
				true
			);
		}
		if (frm.doc.status === "Checked Out" && frm.doc.total_duration) {
			frm.dashboard.add_comment(
				__("Total time on premises: <strong>{0}</strong>", [frm.doc.total_duration]),
				"purple",
				true
			);
		}
	},

	// ── Duration calculation ───────────────────────────────
	calculate_duration: function (frm) {
		if (frm.doc.check_in_time && frm.doc.check_out_time) {
			const diff = moment(frm.doc.check_out_time).diff(moment(frm.doc.check_in_time), "seconds");
			const h = Math.floor(diff / 3600);
			const m = Math.floor((diff % 3600) / 60);
			frm.set_value("total_duration", `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:00`);
		}
	},
});
