// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext");
cur_frm.email_field = "email_id";

erpnext.LeadController = class LeadController extends frappe.ui.form.Controller {
	setup () {
		this.frm.make_methods = {
			'Customer': this.make_customer,
			'Quotation': this.make_quotation,
			'Opportunity': this.make_opportunity
		};

		// For avoiding integration issues.
		this.frm.set_df_property('first_name', 'reqd', true);
	}

	onload () {
		this.frm.set_query("customer", function (doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.customer_query" }
		});

		this.frm.set_query("lead_owner", function (doc, cdt, cdn) {
			return { query: "frappe.core.doctype.user.user.user_query" }
		});
	}

	refresh () {


		var me = this;
		let doc = this.frm.doc;
		erpnext.toggle_naming_series();
		frappe.dynamic_link = {
			doc: doc,
			fieldname: 'name',
			doctype: 'Lead'
		};

		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol",
		}).then(r =>{
			if((r.message.includes("Back Office"))){
			if (doc.workflow_state==='Aprobado' || doc.workflow_state==='Aprobado con Deposito') {
				//if( frm.doc.cliente === undefined ){
				if (doc.cliente=== undefined) {
					this.frm.add_custom_button(__("Customer"), this.make_customer, __("Create"));
				}
				
				//}
				// this.frm.add_custom_button(__("Opportunity"), function() {
				// 	me.frm.trigger("make_opportunity");
				// }, __("Create"));
				this.frm.add_custom_button(__("Quotation"), this.make_quotation, __("Create"));
				if (!doc.__onload.linked_prospects.length) {
					this.frm.add_custom_button(__("Prospect"), this.make_prospect, __("Create"));
					this.frm.add_custom_button(__('Add to Prospect'), this.add_lead_to_prospect, __('Action'));
				}
			}
		}}
		);



		if (!this.frm.is_new()) {
			frappe.contacts.render_address_and_contact(this.frm);
		} else {
			frappe.contacts.clear_address_and_contact(this.frm);
		}

		this.show_notes();
		this.show_activities();

		if (this.frm.doc.cedula !== undefined) {
		frappe.call({
			"method": "erpnext.crm.doctype.lead.lead.verificar_cedula_html",
			"args": {
				"cedula": cur_frm.doc.cedula,
				   },
				callback: function(r){
					console.log(r.message)
					const data = document.querySelector("#bitacora_filtro");
					var tmp_tt_table = `<table class="table table-striped">
					<thead>
					  <tr>
						<th scope="col">ID</th>
						<th scope="col">Tipo Documento</th>
					  </tr>
					</thead>
					<tbody>
					{% for(var i = 0; i < data.length; i++){ %}
					{%var row = data[i]%}
				   <tr style="font-size:10px">		
						<td><a style="color:#4E8CF2; text-decoration: underline;" href="https://ibwni-crm.ibw.com/app/{{row[1]}}/{{row[0]}}"><b>{{row[0]}}</b></a></td>
						<td>{{row[1]}}</td>
					  </tr>
					  {% } %}
					</tbody>
				  </table>`;
					data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
			   }
			});}

			if (this.frm.doc.nis !== undefined) {
				frappe.call({
					"method": "erpnext.crm.doctype.lead.lead.verificar_nis_html",
					"args": {
						"nis": cur_frm.doc.nis,
						   },
						callback: function(r){
							console.log(r.message)
							const data = document.querySelector("#bitacora_filtro_nis");
							var tmp_tt_table = `<table class="table table-striped">
							<thead>
							  <tr>
								<th scope="col">ID</th>
								<th scope="col">Tipo Documento</th>
							  </tr>
							</thead>
							<tbody>
							{% for(var i = 0; i < data.length; i++){ %}
							{%var row = data[i]%}
						   <tr style="font-size:10px">		
								<td><a style="color:#4E8CF2; text-decoration: underline;" href="https://ibwni-crm.ibw.com/app/{{row[1]}}/{{row[0]}}"><b>{{row[0]}}</b></a></td>
								<td>{{row[1]}}</td>
							  </tr>
							  {% } %}
							</tbody>
						  </table>`;
							data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
					   }
					});}


	}

	add_lead_to_prospect () {
		frappe.prompt([
			{
				fieldname: 'prospect',
				label: __('Prospect'),
				fieldtype: 'Link',
				options: 'Prospect',
				reqd: 1
			}
		],
		function(data) {
			frappe.call({
				method: 'erpnext.crm.doctype.lead.lead.add_lead_to_prospect',
				args: {
					'lead': cur_frm.doc.name,
					'prospect': data.prospect
				},
				callback: function(r) {
					if (!r.exc) {
						frm.reload_doc();
					}
				},
				freeze: true,
				freeze_message: __('Adding Lead to Prospect...')
			});
		}, __('Add Lead to Prospect'), __('Add'));
	}

	make_customer () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_customer",
			frm: cur_frm
		})
	}

	make_quotation () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_quotation",
			frm: cur_frm
		})
	}

	make_prospect () {
		frappe.model.with_doctype("Prospect", function() {
			let prospect = frappe.model.get_new_doc("Prospect");
			prospect.company_name = cur_frm.doc.company_name;
			prospect.no_of_employees = cur_frm.doc.no_of_employees;
			prospect.industry = cur_frm.doc.industry;
			prospect.market_segment = cur_frm.doc.market_segment;
			prospect.territory = cur_frm.doc.territory;
			prospect.fax = cur_frm.doc.fax;
			prospect.website = cur_frm.doc.website;
			prospect.prospect_owner = cur_frm.doc.lead_owner;
			prospect.notes = cur_frm.doc.notes;

			let leads_row = frappe.model.add_child(prospect, 'leads');
			leads_row.lead = cur_frm.doc.name;

			frappe.set_route("Form", "Prospect", prospect.name);
		});
	}

	company_name () {
		if (!this.frm.doc.lead_name) {
			this.frm.set_value("lead_name", this.frm.doc.company_name);
		}
	}

	show_notes() {
		if (this.frm.doc.docstatus == 1) return;

		const crm_notes = new erpnext.utils.CRMNotes({
			frm: this.frm,
			notes_wrapper: $(this.frm.fields_dict.notes_html.wrapper),
		});
		crm_notes.refresh();
	}

	show_activities() {
		if (this.frm.doc.docstatus == 1) return;

		const crm_activities = new erpnext.utils.CRMActivities({
			frm: this.frm,
			open_activities_wrapper: $(this.frm.fields_dict.open_activities_html.wrapper),
			all_activities_wrapper: $(this.frm.fields_dict.all_activities_html.wrapper),
			form_wrapper: $(this.frm.wrapper),
		});
		crm_activities.refresh();
	}
};


extend_cscript(cur_frm.cscript, new erpnext.LeadController({ frm: cur_frm }));

frappe.ui.form.on("Lead", {
	make_opportunity: async function(frm) {
		let existing_prospect = (await frappe.db.get_value("Prospect Lead",
			{
				"lead": frm.doc.name
			},
			"name", null, "Prospect"
		)).message.name;

		if (!existing_prospect) {
			var fields = [
				{
					"label": "Create Prospect",
					"fieldname": "create_prospect",
					"fieldtype": "Check",
					"default": 1
				},
				{
					"label": "Prospect Name",
					"fieldname": "prospect_name",
					"fieldtype": "Data",
					"default": frm.doc.company_name,
					"depends_on": "create_prospect"
				}
			];
		}
		let existing_contact = (await frappe.db.get_value("Contact",
			{
				"first_name": frm.doc.first_name || frm.doc.lead_name,
				"last_name": frm.doc.last_name
			},
			"name"
		)).message.name;

		if (!existing_contact) {
			fields.push(
				{
					"label": "Create Contact",
					"fieldname": "create_contact",
					"fieldtype": "Check",
					"default": "1"
				}
			);
		}

		if (fields) {
			var d = new frappe.ui.Dialog({
				title: __('Create Opportunity'),
				fields: fields,
				primary_action: function() {
					var data = d.get_values();
					frappe.call({
						method: 'create_prospect_and_contact',
						doc: frm.doc,
						args: {
							data: data,
						},
						freeze: true,
						callback: function(r) {
							if (!r.exc) {
								frappe.model.open_mapped_doc({
									method: "erpnext.crm.doctype.lead.lead.make_opportunity",
									frm: frm
								});
							}
							d.hide();
						}
					});
				},
				primary_action_label: __('Create')
			});
			d.show();
		} else {
			frappe.model.open_mapped_doc({
				method: "erpnext.crm.doctype.lead.lead.make_opportunity",
				frm: frm
			});
		}
	}
});

frappe.ui.form.on("Lead", "cedula", function(frm){
	// var cedula = 
	// console.log(frm.doc.cedula.slice(4,11))
	// console.log(frm.doc.cedula.length)

	if(frm.doc.cedula){
		if (frm.doc.cedula.length === 10){
			if (isNaN(frm.doc.cedula.slice(4,10))){
				
				frappe.msgprint("Numero de Cédula invalida, ingrese un numero de cedula correcto");
			}else{
				var c2 = frm.doc.cedula + "-";
				cur_frm.set_value("cedula", c2);
			}
		
		}else if (frm.doc.cedula.length === 14) {	
			if (isNaN(frm.doc.cedula.slice(0,13)) === false && isNaN(frm.doc.cedula.charAt(13))){
				// frappe.throw(_(""))
				var c4 = frm.doc.cedula.slice(0,3) + "-" + frm.doc.cedula.slice(3,9) + "-" + frm.doc.cedula.slice(9,14);
				cur_frm.set_value("cedula", c4);
			}else{
				frappe.msgprint("Numero de Cédula invalida, ingrese un numero de cedula correcto");
			}
		}else if(frm.doc.cedula.length === 15){
			if (isNaN(frm.doc.cedula.slice(12,15))){
				// frappe.throw(_(""))
				frappe.msgprint("Numero de Cédula invalida, ingrese un numero de cedula correcto");
			}
	
		}else if(frm.doc.cedula.length === 16){
			console.log(frm.doc.cedula.charAt(15))
			if (isNaN(frm.doc.cedula.charAt(15)) == false){
				frappe.msgprint("Numero de Cédula invalida, ingrese un numero de cedula correcto");
			}
		}else if(frm.doc.cedula.length > 16){
			
			frappe.msgprint("Numero de Cédula invalida, no se permite menos o más de 16 caracteres");
			cur_frm.set_value("cedula",null);
			
		}else if (frm.doc.cedula.length === 3) {
			if (isNaN(frm.doc.cedula.slice(0,3))){
				// frappe.throw(_(""))
				frappe.msgprint("Numero de Cédula invalida, ingrese un numero de cedula correcto");
				// frappe.throw(_("Numero de Cédula invalida, ingrese un numero de cedula correcto"))
			}else{
				var c1 = frm.doc.cedula.slice(0,3) + "-";
				cur_frm.set_value("cedula", c1);
			}
		}else if (frm.doc.cedula.length < 14) {
			if (isNaN(frm.doc.cedula.slice(0,3))){
				// frappe.throw(_(""))
				frappe.msgprint("Numero de Cédula invalida, ingrese un numero de cedula correcto");
				cur_frm.set_value("cedula",null);
				// frappe.throw(_("Numero de Cédula invalida, ingrese un numero de cedula correcto"))
			}
		}
	}
});