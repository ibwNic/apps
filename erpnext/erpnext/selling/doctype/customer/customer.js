// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Customer", {
	setup: function(frm) {

		frm.make_methods = {
			'Quotation': () => frappe.model.open_mapped_doc({
				method: "erpnext.selling.doctype.customer.customer.make_quotation",
				frm: cur_frm
			}),
			'Opportunity': () => frappe.model.open_mapped_doc({
				method: "erpnext.selling.doctype.customer.customer.make_opportunity",
				frm: cur_frm
			})
		}

		frm.add_fetch('lead_name', 'company_name', 'customer_name');
		frm.add_fetch('default_sales_partner','commission_rate','default_commission_rate');
		frm.set_query('customer_group', {'is_group': 0});
		frm.set_query('default_price_list', { 'selling': 1});
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'account_type': 'Receivable',
				'company': d.company,
				"is_group": 0
			};

			if(doc.party_account_currency) {
				$.extend(filters, {"account_currency": doc.party_account_currency});
			}
			return {
				filters: filters
			}
		});

		if (frm.doc.__islocal == 1) {
			frm.set_value("represents_company", "");
		}

		frm.set_query('customer_primary_contact', function(doc) {
			return {
				query: "erpnext.selling.doctype.customer.customer.get_customer_primary_contact",
				filters: {
					'customer': doc.name
				}
			}
		})
		frm.set_query('customer_primary_address', function(doc) {
			return {
				filters: {
					'link_doctype': 'Customer',
					'link_name': doc.name
				}
			}
		})

		frm.set_query('default_bank_account', function() {
			return {
				filters: {
					'is_company_account': 1
				}
			}
		});
	},
	customer_primary_address: function(frm){
		if(frm.doc.customer_primary_address){
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: {
					"address_dict": frm.doc.customer_primary_address
				},
				callback: function(r) {
					frm.set_value("primary_address", r.message);
				}
			});
		}
		if(!frm.doc.customer_primary_address){
			frm.set_value("primary_address", "");
		}
	},

	is_internal_customer: function(frm) {
		if (frm.doc.is_internal_customer == 1) {
			frm.toggle_reqd("represents_company", true);
		}
		else {
			frm.toggle_reqd("represents_company", false);
		}
	},

	customer_primary_contact: function(frm){
		if(!frm.doc.customer_primary_contact){
			frm.set_value("mobile_no", "");
			frm.set_value("email_id", "");
		}
	},

	loyalty_program: function(frm) {
		if(frm.doc.loyalty_program) {
			frm.set_value('loyalty_program_tier', null);
		}
	},

	refresh: function(frm) {
		frappe.call({
			"method": "erpnext.selling.doctype.customer.customer.get_plans_customer",
			"args": {
				"name": frm.doc.name,
				   },
				callback: function(r){
					console.log(r.message)
					const data = document.querySelector("#lista");
					var tmp_tt_table = `<table class="table table-striped">
					<thead>
					  <tr>
						<th scope="col">Planes</th>
						<th scope="col">Estado</th>
						<th scope="col">Contrato</th>
						<th scope="col">Direccion</th>
						<th scope="col">Precio</th>
						<th scope="col">Service Start</th>
					  </tr>
					</thead>
					<tbody>
					{% for(var i = 0; i < data.length; i++){ %}
					{%var row = data[i]%}
					{% if row[1] == 'Activo'%} <tr class="bg-success">{%endif%}
					{% if row[1] == 'Inactivo'%}<tr class="bg-secondary">{%endif%}
					{% if row[1] == 'Plan Cerrado'%}<tr class="bg-danger">{%endif%}
					{% if row[1] == 'SUSPENDIDO: Manual'%}<tr class="bg-warning">{%endif%}
					{% if row[1] == 'SUSPENDIDO: Temporal'%}<tr class="bg-warning">{%endif%}			
						<th scope="row">{{row[0]}}</th>
						<td>{{row[1]}}</td>
						<td><a style="color:white; text-decoration: underline;" href="http://54.210.180.175:8001/app/subscription/{{row[2]}}"><b>{{row[2]}}</b></a></td>
						<td>{{row[3]}}</td>
						<td>{% if row[6] == 'USD'%}$ {%else%}C$ {%endif%} {{row[4]}}</td>		
						<td>{{row[5]}}</td>				
					  </tr>
					  {% } %}
					</tbody>
				  </table>`;
					data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
			   }
			});

			frappe.call({
				"method": "erpnext.selling.doctype.customer.customer.get_work_orders",
				"args": {
					"name": frm.doc.name,
					   },
					callback: function(r){
						//console.log(r.message)
						const data = document.querySelector("#ordenes");
						var tmp_tt_table = `
						<table class="table table-striped table-bordered">
						<thead style="font-size:12px">
						  <tr>
							<th scope="col">ID Orden</th>
							<th scope="col">Tipo Orden</th>
							<th scope="col">Estado</th>
							<th scope="col">Plan ID</th>
							<th scope="col">Vendedor</th>
							<th scope="col">Descripción</th>
							<th scope="col">Solución</th>
							<th scope="col">Fecha Solicitud</th>
							<th scope="col">Solicitado Por</th>
							<th scope="col">Fecha Finalizado</th>
							<th scope="col">Finalizado Por</th>
						  </tr>
						</thead>
						<tbody>
						{% for(var i = 0; i < data.length; i++){ %}
						{%var row = data[i]%}
					   <tr style="font-size:10px">		
							<td><a style="color:#4E8CF2; text-decoration: underline;" href="http://54.210.180.175:8001/app/service-order/{{row[0]}}"><b>{{row[0]}}</b></a></td>
							<td>{{row[1]}}</td>
							<td>{{row[5]}}</td>
							<td>{{row[8]}}</td>
							<td>{{row[4]}}</td>
							<td>{{row[12]}}</td>
							<td>{{row[15]}}</td>
							<td>{{row[22]}}</td>
							<td>{{row[2]}}</td>
							<td>{{row[26]}}</td>	
							<td>{{row[3]}}</td>				
						  </tr>
						  {% } %}
						</tbody>
					  </table>
					  {%if data.length == 0%}<p class="text-center">Este cliente no tiene ordenes de servicio.</p> {%endif%}

					  `;
					  
						data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
					}
			});

			frappe.call({
				"method": "erpnext.selling.doctype.customer.customer.get_issues",
				"args": {
					"name": frm.doc.name,
					   },
					callback: function(r){
						//console.log(r.message)
						const data = document.querySelector("#incidencias");
						var tmp_tt_table = `
						<table class="table table-striped table-bordered">
						<thead style="font-size:12px">
						  <tr>
							<th scope="col">ID Orden</th>
							<th scope="col">Estado</th>
							<th scope="col">Plan ID</th>
							<th scope="col">Servicio</th>
							<th scope="col">Averia</th>
							<th scope="col">Sub Averia</th>
							<th scope="col">Detalle Averia</th>
							<th scope="col">Solución</th>
							<th scope="col">Tipo de Orden</th>
							<th scope="col">Fecha Solicitud</th>
							<th scope="col">Solicitado Por</th>
							<th scope="col">Fecha Finalizado</th>
							<th scope="col">Finalizado Por</th>
							<th scope="col">Averia Masivo</th>
						  </tr>
						</thead>
						<tbody>
						{% for(var i = 0; i < data.length; i++){ %}
						{%var row = data[i]%}
					   <tr style="font-size:10px">		
							<td><a style="color:#FF4040; text-decoration: underline;" href="http://54.210.180.175:8001/app/issue/{{row[0]}}"><b>{{row[0]}}</b></a></td>
							<td>{{row[5]}}</td>
							<td>{{row[8]}}</td>
							<td>{{row[9]}}</td>
							<td>{{row[13]}}</td>
							<td>{{row[14]}}</td>
							<td>{{row[12]}}</td>
							<td>{{row[15]}}</td>
							<td>{{row[1]}}</td>
							<td>{{row[22]}}</td>
							<td>{{row[2]}}</td>
							<td>{{row[26]}}</td>	
							<td>{{row[3]}}</td>	
							<td>{{row[17]}}</td>			
						  </tr>
						  {% } %}
						</tbody>
					  </table>
					  {%if data.length == 0%}<p class="text-center">Este cliente no tiene incidencias.</p> {%endif%}					
						`;
						data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
					}
				});

				frappe.call({
					"method": "erpnext.selling.doctype.customer.customer.obtener_estado_de_cuenta",
					"args": {
						"name": frm.doc.name,
						   },
						callback: function(r){
							//console.log(r.message)
							const data = document.querySelector("#cuentas");
							var tmp_tt_table = `
							<table class="table table-bordered">
							<thead style="font-size:12px">
							  <tr>
								<th style="background-color:#FFE1D7; color:#000000;" scope="col">Fecha</th>
								<th style="background-color:#FFE1D7; color:#000000;" scope="col">Documento</th>
								<th style="background-color:#FFE1D7; color:#000000;" scope="col">Tipo</th>
								<th style="background-color:#FFE1D7; color:#000000;" scope="col">Comentario</th>
								<th style="background-color:#A6F8FF; color:#000000;" scope="col">Débito Córdobas</th>
								<th style="background-color:#A6F8FF; color:#000000;" scope="col">Crédito Córdobas</th>
								<th style="background-color:#FFF17B; color:#000000;" scope="col">Saldo Córdobas</th>
								<th style="background-color:#A6F8FF; color:#000000;" scope="col">Débito Dólares</th>
								<th style="background-color:#A6F8FF; color:#000000;" scope="col">Crédito Dolares</th>
								<th style="background-color:#FFF17B; color:#000000;" scope="col">Saldo Dólares</th>
							  </tr>
							</thead>
							<tbody>
							{% for(var i = 0; i < data.length; i++){ %}
							{%var row = data[i]%}
						   <tr style="font-size:10px">		
								<td style="background-color:#FFF7F2; color:#000000;">{{row[1]}}</td>
								<td style="background-color:#FFF7F2; color:#000000;"><a style="color:#24A860; text-decoration: underline;" {%if row[3] == 'Sales Invoice'%}href="http://54.210.180.175:8001/app/sales-invoice/{%else%}href="http://54.210.180.175:8001/app/journal-entry/{%endif%}{{row[4]}}"><b>{{row[4]}}</b></a></td>
								<td style="background-color:#FFF7F2; color:#000000;">{{row[3]}}</td>
								<td style="background-color:#FFF7F2; color:#000000;">{{row[5]}}</td>
								<td style="background-color:#C6F9FF; color:#000000;">C$ {{row[6]}}</td>
								<td style="background-color:#C6F9FF; color:#000000;">C$ {{row[7]}}</td>
								<td style="background-color:#FFE897; color:#000000;">C$ {{row[8]}}</td>
								<td style="background-color:#C6F9FF; color:#000000;">$ {{row[10]}}</td>
								<td style="background-color:#C6F9FF; color:#000000;">$ {{row[11]}}</td>	
								<td style="background-color:#FFE897; color:#000000;">$ {{row[12]}}</td>				
							  </tr>
							  {% } %}
							</tbody>
						  </table>
						  {%if data.length == 0%}<p class="text-center">No hay registros.</p> {%endif%}	
						  `;
						  
							data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
						}
				});

		if(frappe.defaults.get_default("cust_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Customer'}

		if(!frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(frm);

			// custom buttons

			frm.add_custom_button(__('Accounts Receivable'), function () {
				frappe.set_route('query-report', 'Accounts Receivable', {customer:frm.doc.name});
			}, __('View'));

			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.set_route('query-report', 'General Ledger',
					{party_type: 'Customer', party: frm.doc.name});
			}, __('View'));

			frm.add_custom_button(__('Pricing Rule'), function () {
				erpnext.utils.make_pricing_rule(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			frm.add_custom_button(__('Factura de debito'), function () {
				frm.trigger("get_customer_group_details");
			}, __('Actions'));

			// frm.add_custom_button(__('Get Customer Group Details'), function () {
			// 	frm.trigger("get_customer_group_details");
			// }, __('Actions'));

			// if (cint(frappe.defaults.get_default("enable_common_party_accounting"))) {
			// 	frm.add_custom_button(__('Link with Supplier'), function () {
			// 		frm.trigger('show_party_link_dialog');
			// 	}, __('Actions'));
			// }

			// indicator
			erpnext.utils.set_party_dashboard_indicators(frm);

		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		var grid = cur_frm.get_field("sales_team").grid;
		grid.set_column_disp("allocated_amount", false);
		grid.set_column_disp("incentives", false);
	},
	validate: function(frm) {
		if(frm.doc.lead_name) frappe.model.clear_doc("Lead", frm.doc.lead_name);

	},
	get_customer_group_details: function(frm) {
		frappe.call({
			method: "get_customer_group_details",
			doc: frm.doc,
			callback: function() {
				frm.refresh();
			}
		});

	},
	show_party_link_dialog: function(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __('Select a Supplier'),
			fields: [{
				fieldtype: 'Link', label: __('Supplier'),
				options: 'Supplier', fieldname: 'supplier', reqd: 1
			}],
			primary_action: function({ supplier }) {
				frappe.call({
					method: 'erpnext.accounts.doctype.party_link.party_link.create_party_link',
					args: {
						primary_role: 'Customer',
						primary_party: frm.doc.name,
						secondary_party: supplier
					},
					freeze: true,
					callback: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Successfully linked to Supplier'),
							alert: true
						});
					},
					error: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Linking to Supplier Failed. Please try again.'),
							title: __('Linking Failed'),
							indicator: 'red'
						});
					}
				});
			},
			primary_action_label: __('Create Link')
		});
		dialog.show();
	}
});


