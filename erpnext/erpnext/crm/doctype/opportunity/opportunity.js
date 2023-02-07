// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}
frappe.provide("erpnext.crm");

cur_frm.email_field = "contact_email";
frappe.ui.form.on("Opportunity", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Quotation': 'Quotation',
			'Supplier Quotation': 'Supplier Quotation'
		};

		frm.set_query("opportunity_from", function() {
			return{
				"filters": {
					"name": ["in", ["Customer", "Lead", "Prospect"]],
				}
			}
		});

		if (frm.doc.opportunity_from && frm.doc.party_name){
			frm.trigger('set_contact_link');
		}
	},

	validate: function(frm) {
		if (frm.doc.status == "Lost" && !frm.doc.lost_reasons.length) {
			frm.trigger('set_as_lost_dialog');
			frappe.throw(__("Lost Reasons are required in case opportunity is Lost."));
		}
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	party_name: function(frm) {
		frm.trigger('set_contact_link');

		if (frm.doc.opportunity_from == "Customer") {
			erpnext.utils.get_party_details(frm);
		} else if (frm.doc.opportunity_from == "Lead") {
			erpnext.utils.map_current_doc({
				method: "erpnext.crm.doctype.lead.lead.make_opportunity",
				source_name: frm.doc.party_name,
				frm: frm
			});
		}
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	status:function(frm){
		if (frm.doc.status == "Lost"){
			frm.trigger('set_as_lost_dialog');
		}

	},

	customer_address: function(frm, cdt, cdn) {
		erpnext.utils.get_address_display(frm, 'customer_address', 'address_display', false);
	},

	contact_person: erpnext.utils.get_contact_details,

	opportunity_from: function(frm) {
		frm.trigger('setup_opportunity_from');

		frm.set_value("party_name", "");
	},

	setup_opportunity_from: function(frm) {
		frm.trigger('setup_queries');
		frm.trigger("set_dynamic_field_label");
	},

	refresh: function(frm) {
		var doc = frm.doc;
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol",
				callback: function(r){
					// console.log("aqui")
					// console.log(r.message)
					
					//frm.toggle_display("aprobado_por_ventas_corporativas", true);
					if(!(r.message.includes("Back Office"))){
						frm.remove_custom_button('Crear Contrato');
					}
					if(!(r.message.includes("Gerente de Ventas Corporativas"))){
						frm.set_df_property('aprobado_por_ventas_corporativas', 'read_only', frm.doc.__islocal ? 0 : 1);
					}
					if(!(r.message.includes("Gerencia General"))){
						frm.set_df_property('aprobado_por_gerencia_general', 'read_only', frm.doc.__islocal ? 0 : 1);
					}
			
			}
		});
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.obtener_planes_nuevos",
			"args": {
				"name": frm.doc.name,
				   },
				callback: function(r){
					console.log(r.message)
					const data = document.querySelector("#planes");
					var tmp_tt_table = `<table  style="font-size:12px">
					<thead>
					  <tr>
						<th scope="col">Planes</th>
					  </tr>
					</thead>
					<tbody>
					{% for(var i = 0; i < data.length; i++){ %}
					{%var row = data[i]%}
					  <tr>			
						<td><a style="text-decoration: underline;" href="http://54.210.180.175:8001/app/subscription-plan/{{row[0]}}"><b>{{row[0]}}</b></a></td>				
					  </tr>
					  {% } %}
					</tbody>
				  </table>`;
					data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
			   }
			});
		/******************************************************** */
		
		//if(frm.doc.__islocal){
			frm.set_value('flujo_neto',flt(frm.doc.total_de_ingresos)-flt(frm.doc.total_de_egresos))
			frm.set_value('flujo',(flt(frm.doc.flujo_neto)/flt(frm.doc.total_de_ingresos))*100)
			frm.trigger("calculate_total_egresos");
			frm.trigger("calculate_total_ingresos");
			frm.trigger("calculate_flujo_de_caja");
			frm.trigger("calculate_total_otc");
			frm.trigger("calculate_total");
	//   }

		
		/************************************************************************* */
		frm.trigger('setup_opportunity_from');
		erpnext.toggle_naming_series();
		if (!frm.is_new()) {
			//console.log("hola")
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		if(!frm.is_new() && doc.status!=="Lost") {
			// if(doc.items){
			// 	frm.add_custom_button(__('Supplier Quotation'),
			// 		function() {
			// 			frm.trigger("make_supplier_quotation")
			// 		}, __('Create'));

			// 	frm.add_custom_button(__('Request For Quotation'),
			// 		function() {
			// 			frm.trigger("make_request_for_quotation")
			// 		}, __('Create'));
			// }

			// if (frm.doc.opportunity_from != "Customer") {
			// 	frm.add_custom_button(__('Customer'),
			// 		function() {
			// 			frm.trigger("make_customer")
			// 		}, __('Create'));
			// }

			// frm.add_custom_button(__('Quotation'),
			// 	function() {
			// 		frm.trigger("create_quotation")
			// 	}, __('Create'));

		
		}

		if(!frm.doc.__islocal && frm.perm[0].write && frm.doc.docstatus==0) {
			if(frm.doc.status==="Open") {
				frm.add_custom_button(__("Close"), function() {
					frm.set_value("status", "Closed");
					frm.save();
				});
					if(frm.doc.opportunity_type === 'Nuevo Contrato'){
						frm.add_custom_button(__("Crear Contrato"), function() {
							// frm.set_value("status", "Closed");
							//frm.save();
							
							let total = 0;
							frm.doc.items.forEach(item => {
								total += item.precio_del_plan;						
							})
	
							if (frm.doc.ingresos_mrc!==total){
								frappe.msgprint(__("La suma de los precios asignados a los servicios, no es igual al MRC o mensualidad igresado en el flujo"));
							}
							if (frm.doc.customer === undefined || frm.doc.customer === ""){
								frappe.msgprint(__("Debe Seleccionar un cliente antes de intentar hacer un contrato"));
							}
							if(frm.doc.status==="Open" && frm.doc.customer !== undefined && frm.doc.customer !== "" && frm.doc.ingresos_mrc===total) {
								//console.log("crear contrato")
								frappe.call({
									"method": "erpnext.crm.doctype.opportunity.opportunity.crear_sus_por_items",
									"args": {
											"name": frm.doc.name,
										},
										callback: function(r){
											console.log(r.message)	
											if(r.message!=undefined){
												frappe.set_route(['Form', 'subscription',r.message]);	
											}
															
									}
								})
							}
						});
					}
					if(frm.doc.opportunity_type === 'Actualizacion de Contrato'){
						frm.add_custom_button(__("Crear Nuevo Plan"), function() {
							let total = 0;
							frm.doc.items.forEach(item => {
								total += item.precio_del_plan;						
							})
	
							if (frm.doc.ingresos_mrc!==total){
								frappe.msgprint(__("La suma de los precios asignados a los servicios, no es igual al MRC o mensualidad igresado en el flujo"));
							}
							if (frm.doc.customer === undefined || frm.doc.customer === ""){
								frappe.msgprint(__("Debe Seleccionar un cliente antes de intentar hacer un contrato"));
							}
							if(frm.doc.status==="Open" && frm.doc.customer !== undefined && frm.doc.customer !== "" && frm.doc.ingresos_mrc===total) {
								//console.log("crear contrato")
								frappe.call({
									"method": "erpnext.crm.doctype.opportunity.opportunity.crear_plan",
									"args": {
											"name": frm.doc.name,
										},
										callback: function(r){
											//console.log(r.message)	
											frm.reload_doc();				
									}
								})
							}

						});
					}
					
			} else {
				frm.add_custom_button(__("Reopen"), function() {
					frm.set_value("lost_reasons",[])
					frm.set_value("status", "Open");
					frm.save();
				});
			}

		}

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			//frm.trigger('render_contact_day_html');

		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
	},

	calculate_Precios_planes: function(frm) {
		let total = 0, base_total = 0;
		frm.doc.items.forEach(item => {
			total += item.amount;
			base_total += item.base_amount;
		})

		frm.set_value({
			'total': flt(total),
			'base_total': flt(base_total)
		});
	},
	set_contact_link: function(frm) {
		
		if(frm.doc.opportunity_from == "Customer" && frm.doc.party_name) {
			frappe.dynamic_link = {doc: frm.doc, fieldname: 'party_name', doctype: 'Customer'}
		} else if(frm.doc.opportunity_from == "Lead" && frm.doc.party_name) {
			frappe.dynamic_link = {doc: frm.doc, fieldname: 'party_name', doctype: 'Lead'}
		}
	},

	currency: function(frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		if (company_currency != frm.doc.company) {
			frappe.call({
				method: "erpnext.setup.utils.get_exchange_rate",
				args: {
					from_currency: frm.doc.currency,
					to_currency: company_currency
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('conversion_rate', flt(r.message));
						frm.set_df_property('conversion_rate', 'description', '1 ' + frm.doc.currency
						+ ' = [?] ' + company_currency);
					}
				}
			});
		} else {
			frm.set_value('conversion_rate', 1.0);
			frm.set_df_property('conversion_rate', 'hidden', 1);
			frm.set_df_property('conversion_rate', 'description', '');
		}

		frm.trigger('opportunity_amount');
		frm.trigger('set_dynamic_field_label');
	},

	opportunity_amount: function(frm) {
		frm.set_value('base_opportunity_amount', flt(frm.doc.opportunity_amount) * flt(frm.doc.conversion_rate));
	},

	set_dynamic_field_label: function(frm){
		if (frm.doc.opportunity_from) {
			frm.set_df_property("party_name", "label", frm.doc.opportunity_from);
		}
		frm.trigger('change_grid_labels');
		frm.trigger('change_form_labels');
	},

	make_supplier_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_supplier_quotation",
			frm: frm
		})
	},

	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_request_for_quotation",
			frm: frm
		})
	},

	change_form_labels: function(frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		frm.set_currency_labels(["base_opportunity_amount", "base_total"], company_currency);
		frm.set_currency_labels(["opportunity_amount", "total"], frm.doc.currency);

		// toggle fields
		frm.toggle_display(["conversion_rate", "base_opportunity_amount", "base_total"],
			frm.doc.currency != company_currency);
		frm.toggle_display(["base_total_otc", "total_de_egresos_nio"],
			frm.doc.currency != company_currency);
	},

	change_grid_labels: function(frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		frm.set_currency_labels(["base_rate", "base_amount"], company_currency, "items");
		frm.set_currency_labels(["rate", "amount"], frm.doc.currency, "items");

		let item_grid = frm.fields_dict.items.grid;
		$.each(["base_rate", "base_amount"], function(i, fname) {
			if(frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, frm.doc.currency != company_currency);
		});
		frm.refresh_fields();
	},

	calculate_total: function(frm) {
		let total = 0, base_total = 0;
		frm.doc.items.forEach(item => {
			total += item.amount;
			base_total += item.base_amount;
		})

		frm.set_value({
			'total': flt(total),
			'base_total': flt(base_total)
		});
	},
	/******************************************************************************************************* */
	calculate_total_otc: function(frm) {
		let total = 0, base_total = 0;
		frm.doc.productos_otc.forEach(item => {
			total += item.amount;
			base_total += item.base_amount;
		})

		frm.set_value({
			'total_otc': flt(total),
			'base_total_otc': flt(base_total)
		});
	},
	calculate_total_egresos: function(frm) {
		let total = (parseFloat(frm.doc.total)*Math.abs(frm.doc.plazo)) + parseFloat(frm.doc.total_otc) + parseFloat(frm.doc.com_vendedor) + parseFloat(frm.doc.comision_gerente);
		frm.set_value('total_de_egresos',total);
		frm.set_value('total_de_egresos_nio', flt(frm.doc.conversion_rate) * flt(frm.doc.total_de_egresos))
	},
	calculate_total_ingresos: function(frm) {
		let total = (Math.abs(frm.doc.plazo) * parseFloat(frm.doc.mrc)) + parseFloat(frm.doc.otc);
		frm.set_value('total_de_ingresos',total);
		frm.set_value('total_de_ingresos_nio', flt(frm.doc.conversion_rate) * flt(frm.doc.total_de_ingresos))
	},
	calculate_flujo_de_caja: function(frm){
		let flujo_arr = []
		let flujo_neto_arr = []
		let flujo_neto = 0
		let flujo_neto_descontado = 0
		let flujo_descontado_acumulado = 0
		let payback = 0
		let van = 0
		let payback_count = 0
		for(let i = 0; i < Math.abs(frm.doc.plazo) + 1; i++){
			if( i === 0)
			{
				flujo_neto =  flt(frm.doc.otc) - flt(frm.doc.total_otc) - flt(frm.doc.com_vendedor) - flt(frm.doc.comision_gerente)
				flujo_neto_descontado = flujo_neto / Math.pow((1 + (flt(frm.doc.tmar)/100)/12), i)
				flujo_descontado_acumulado = flujo_neto_descontado
				if(flujo_descontado_acumulado < 0){
					payback = 1
				}
				flujo_arr.push([flujo_neto,flujo_neto_descontado,flujo_descontado_acumulado, payback]);
			}
			else{
				flujo_neto =  flt(frm.doc.mrc) - flt(frm.doc.total)
				flujo_neto_descontado = flujo_neto / Math.pow((1 + (flt(frm.doc.tmar)/100)/12), i)
				if( flujo_neto_descontado != 0){
					flujo_descontado_acumulado = flujo_neto_descontado + flujo_arr[i-1][2]
				}
				else{
					flujo_descontado_acumulado = 0
				}	
				if(flujo_descontado_acumulado < 0){
					payback = 1
				}
				else{
					payback = 0
				}
				flujo_arr.push([flujo_neto,flujo_neto_descontado,flujo_descontado_acumulado, payback]);
			}
			van = van + flujo_neto_descontado
			payback_count = payback_count + payback
			flujo_neto_arr.push(flujo_neto);
		}
		
		console.log(flujo_arr);
		frm.set_value('van',flt(van,2))
		if(van > 0){
			frm.set_value('payback',payback_count+1)
		}
		else{
			frm.set_value('payback',0)
		}
		//console.log(flujo_neto_arr)
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.calculate_tir","args":{'arr':flujo_neto_arr}, callback: function(r) {
					//console.log(r.message)
					frm.set_value('tir',r.message)
			}})
		// console.log(frm.doc.tir)	
		frm.set_value('van_mrc',flt(flt(frm.doc.van)/flt(frm.doc.mrc),2))
	}
});

frappe.ui.form.on("Opportunity Item", {
	calculate: function(frm, cdt, cdn) {
		let uom = 0
		let compresion = 1
		let row = frappe.get_doc(cdt, cdn);
		uom = row.uom;
		uom = uom.replace(' Mbps', '');
		
		compresion = row.compresion;
		compresion = compresion.replace(':1','');	
		
		let proveedor = row.proveedor;
		let unidad = row.tasa;
		
		
		if(proveedor === "IBW"){
			frappe.model.set_value(cdt, cdn, "rate", (unidad*uom)/compresion);
			frappe.model.set_value(cdt, cdn, "precio_tercero", 0);
			frappe.model.set_value(cdt, cdn, "importe_ibw", 0);
		}
		else if(proveedor === "Tercero"){
			let rate = parseInt(row.precio_tercero) + parseInt(row.importe_ibw);
			frappe.model.set_value(cdt, cdn, "rate", rate);
		}
		let descuento = Math.abs(row.descuento_porcentaje)
		let amount = flt(row.qty) * flt(row.rate)
		frappe.model.set_value(cdt, cdn, "amount", amount-amount*(descuento/100));
		frappe.model.set_value(cdt, cdn, "base_rate", flt(frm.doc.conversion_rate) * flt(row.rate));
		frappe.model.set_value(cdt, cdn, "base_amount", flt(frm.doc.conversion_rate) * flt(row.amount));
		frm.trigger("calculate_total");
		frm.trigger("calculate_total_egresos");
	},
	qty: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	rate: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	compresion: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	departamento: function(frm, cdt, cdn) {
		let departamento = frappe.model.get_value(cdt, cdn, "departamento");
		if(departamento == "Managua"){
			frappe.model.set_value(cdt, cdn, "tasa", 1.8);
		}
		else if(departamento === "Departamentos")
		{
			frappe.model.set_value(cdt, cdn, "tasa", 2.8);
		}
	},
	proveedor: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	precio_tercero: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	importe_ibw: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	tasa: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	descuento_porcentaje: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	uom: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
})

frappe.ui.form.on("Opportunity Item OTC", {
	calculate: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "amount", row.rate * row.qty);
		frappe.model.set_value(cdt, cdn, "base_rate", flt(frm.doc.conversion_rate) * flt(row.rate));
		frappe.model.set_value(cdt, cdn, "base_amount", flt(frm.doc.conversion_rate) * flt(row.amount));
		frm.trigger("calculate_total_otc");
		frm.trigger("calculate_total_egresos");
	},
	rate: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	qty: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
})

frappe.ui.form.on("Opportunity", "porcentaje_comision_v", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.porcentaje_comision_v)
	total_mrc = total_mrc*(porcentaje/100)
	frm.set_value('com_vendedor',total_mrc)
	frm.trigger("calculate_total_egresos");
});
frappe.ui.form.on("Opportunity", "porcentaje_comision_g", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.porcentaje_comision_g)
	total_mrc = total_mrc*(porcentaje/100)
	frm.set_value('comision_gerente',total_mrc)
	frm.trigger("calculate_total_egresos");
});
frappe.ui.form.on("Opportunity", "descuento_ingreso_mrc", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.descuento_ingreso_mrc)
	total_mrc = total_mrc - total_mrc*(porcentaje/100)
	frm.set_value('mrc',total_mrc)

});
frappe.ui.form.on("Opportunity", "ingresos_mrc", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.descuento_ingreso_mrc)
	total_mrc = total_mrc - total_mrc*(porcentaje/100)
	frm.set_value('mrc',total_mrc)

	let total_mrc1 = frm.doc.ingresos_mrc
	let porcentaje1 = Math.abs(frm.doc.porcentaje_comision_v)
	total_mrc1 = total_mrc1*(porcentaje1/100)
	frm.set_value('com_vendedor',total_mrc1)

	let total_mrc2 = frm.doc.ingresos_mrc
	let porcentaje2 = Math.abs(frm.doc.porcentaje_comision_g)
	total_mrc2 = total_mrc2*(porcentaje2/100)
	frm.set_value('comision_gerente',total_mrc2)
	frm.trigger("calculate_total_egresos");

});
frappe.ui.form.on("Opportunity", "ingresos_otc", function(frm) {
	let total_otc = frm.doc.ingresos_otc
	let porcentaje = Math.abs(frm.doc.descuento_ingreso_otc)
	total_otc = total_otc - total_otc*(porcentaje/100)
	frm.set_value('otc',total_otc)
});
frappe.ui.form.on("Opportunity", "descuento_ingreso_otc", function(frm) {
	let total_otc = frm.doc.ingresos_otc
	let porcentaje = Math.abs(frm.doc.descuento_ingreso_otc)
	total_otc = total_otc - total_otc*(porcentaje/100)
	frm.set_value('otc',total_otc)
});
frappe.ui.form.on("Opportunity", "total_otc", function(frm) {
	frm.trigger("calculate_total_egresos");
});
frappe.ui.form.on("Opportunity", "total", function(frm) {
	frm.trigger("calculate_total_egresos");
});
frappe.ui.form.on("Opportunity", "plazo", function(frm) {
	frm.trigger("calculate_total_ingresos");
	frm.trigger("calculate_flujo_de_caja");
});
frappe.ui.form.on("Opportunity", "mrc", function(frm) {
	frm.trigger("calculate_total_ingresos");
	frm.trigger("calculate_flujo_de_caja");
});
frappe.ui.form.on("Opportunity", "otc", function(frm) {
	frm.trigger("calculate_total_ingresos");
	frm.trigger("calculate_flujo_de_caja");
});
frappe.ui.form.on("Opportunity", "total_de_ingresos", function(frm) {
	frm.set_value('flujo_neto',flt(frm.doc.total_de_ingresos)-flt(frm.doc.total_de_egresos))
	frm.set_value('flujo',(flt(frm.doc.flujo_neto)/flt(frm.doc.total_de_ingresos))*100)
});
frappe.ui.form.on("Opportunity", "total_de_egresos", function(frm) {
	frm.set_value('flujo_neto',flt(frm.doc.total_de_ingresos)-flt(frm.doc.total_de_egresos))
});
frappe.ui.form.on("Opportunity", "flujo_neto", function(frm) {
	frm.set_value('flujo',(flt(frm.doc.flujo_neto)/flt(frm.doc.total_de_ingresos))*100)
});
/************************************************************************************************************** */

// TODO commonify this code
erpnext.crm.Opportunity = class Opportunity extends frappe.ui.form.Controller {
	onload() {

		if(!this.frm.doc.status) {
			frm.set_value('status', 'Open');
		}
		if(!this.frm.doc.company && frappe.defaults.get_user_default("Company")) {
			frm.set_value('company', frappe.defaults.get_user_default("Company"));
		}
		// if(!this.frm.doc.currency) {
		// 	frm.set_value('currency', frappe.defaults.get_user_default("Currency"));
		// }

		this.setup_queries();
		this.frm.trigger('currency');
	}

	refresh() {
		this.show_notes();
		this.show_activities();
	}

	setup_queries() {
		var me = this;

		me.frm.set_query('customer_address', erpnext.queries.address_query);

		this.frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {'is_sales_item': 1}
			};
		});

		me.frm.set_query('contact_person', erpnext.queries['contact_query'])

		if (me.frm.doc.opportunity_from == "Lead") {
			me.frm.set_query('party_name', erpnext.queries['lead']);
		}
		else if (me.frm.doc.opportunity_from == "Customer") {
			me.frm.set_query('party_name', erpnext.queries['customer']);
		} else if (me.frm.doc.opportunity_from == "Prospect") {
			me.frm.set_query('party_name', function() {
				return {
					filters: {
						"company": me.frm.doc.company
					}
				};
			});
		}
	}

	create_quotation() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
			frm: cur_frm
		})
	}

	make_customer() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_customer",
			frm: cur_frm
		})
	}

	show_notes() {
		const crm_notes = new erpnext.utils.CRMNotes({
			frm: this.frm,
			notes_wrapper: $(this.frm.fields_dict.notes_html.wrapper),
		});
		crm_notes.refresh();
	}

	show_activities() {
		const crm_activities = new erpnext.utils.CRMActivities({
			frm: this.frm,
			open_activities_wrapper: $(this.frm.fields_dict.open_activities_html.wrapper),
			all_activities_wrapper: $(this.frm.fields_dict.all_activities_html.wrapper),
			form_wrapper: $(this.frm.wrapper),
		});
		crm_activities.refresh();
	}
};

extend_cscript(cur_frm.cscript, new erpnext.crm.Opportunity({frm: cur_frm}));

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return frappe.call({
			method: "erpnext.crm.doctype.opportunity.opportunity.get_item_details",
			args: {"item_code":d.item_code},
			callback: function(r, rt) {
				if(r.message) {
					$.each(r.message, function(k, v) {
						frappe.model.set_value(cdt, cdn, k, v);
					});
					refresh_field('image_view', d.name, 'items');
				}
			}
		})
	}
}
