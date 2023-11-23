// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Prospect', {
	refresh (frm) {
	
		frm.add_custom_button("Generar Lead", () => {
		
			frappe.db.get_value("Sales Person",{"usuario":frm.doc.prospect_owner},'name',function(d) {
			 d.name;
			  }).then(r =>{

				let d = frappe.model.get_new_name('lead');
				frappe.route_options = {
						'naming_series': 'LEAD-',
						'prospect': cur_frm.docname,
						'first_name':frm.doc.company_name,
						'lead_name':frm.doc.company_name,
						'type':'Client',
						'no_of_employees': frm.doc.no_of_employees,
						'sales_person': r.message.name
						
					};
					frappe.set_route(['Form', 'lead', d]);
			  })
            });

		// if(frm.doc.cliente_existente !== undefined){
		// 	frm.remove_custom_button('Generar Lead');
		// }
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: frm.doctype };

		// if (!frm.is_new() && frappe.boot.user.can_create.includes("Customer")) {
		// 	frm.add_custom_button(__("Customer"), function() {
		// 		frappe.model.open_mapped_doc({
		// 			method: "erpnext.crm.doctype.prospect.prospect.make_customer",
		// 			frm: frm
		// 		});
		// 	}, __("Create"));
		// }
		if (!frm.is_new() && frappe.boot.user.can_create.includes("Opportunity")) {
			frm.add_custom_button(__("Opportunity"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_opportunity",
					frm: frm
				});
			}, __("Create"));
		}
		// if (!frm.is_new() && frappe.boot.user.can_create.includes("Lead")) {
		// 	frm.add_custom_button(__("Opportunity"), function() {
		// 		frappe.model.open_mapped_doc({
		// 			method: "erpnext.crm.doctype.prospect.prospect.make_opportunity",
		// 			frm: frm
		// 		});
		// 	}, __("Create"));
		// }

		if (!frm.is_new()) {
			
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
		frm.trigger("show_notes");
		frm.trigger("show_activities");
	},

	show_notes (frm) {
		const crm_notes = new erpnext.utils.CRMNotes({
			frm: frm,
			notes_wrapper: $(frm.fields_dict.notes_html.wrapper),
		});
		crm_notes.refresh();
	},

	show_activities (frm) {
		const crm_activities = new erpnext.utils.CRMActivities({
			frm: frm,
			open_activities_wrapper: $(frm.fields_dict.open_activities_html.wrapper),
			all_activities_wrapper: $(frm.fields_dict.all_activities_html.wrapper),
			form_wrapper: $(frm.wrapper),
		});
		crm_activities.refresh();
	}

});
frappe.ui.form.on("Prospect", "cliente_existente", function(frm) {
	if(frm.doc.cliente_existente !== undefined){
		frm.remove_custom_button('Generar Lead');

		frappe.call({
			method: 'erpnext.crm.doctype.prospect.prospect.verificar_company_name',
			args: {
				"customer": frm.doc.cliente_existente
			},
			callback: function(r) {
				frm.set_value("company_name",r.message)
			}
		});

	}
	
});