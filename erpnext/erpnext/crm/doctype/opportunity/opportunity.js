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
					// "name": ["in", ["Customer", "Lead", "Prospect"]],
					"name": ["in", [ "Prospect"]],
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

	// onload_post_render: function(frm) {
	// 	frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	// },

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

	// onload_post_render: function(frm) {
	// 	frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	// },

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
		console.log(frm.doc.suma_precio_de_planes)
		var doc = frm.doc;
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol",
				callback: function(r){
					
					if(!(r.message.includes("Back Office"))){
						frm.remove_custom_button('Crear Contrato');
						frm.remove_custom_button('Crear Nuevo Plan');
						frm.remove_custom_button('Factura de Venta');
					}
					if(!(r.message.includes("Gerente de Ventas Corporativas"))){
						frm.set_df_property('aprobado_por_ventas_corporativas', 'read_only', frm.doc.__islocal ? 0 : 1);
						frm.set_df_property('aprobado_por_gerencia_ve', 'read_only', frm.doc.__islocal ? 0 : 1);
					}
					if(!(r.message.includes("Gerencia General"))){
						frm.set_df_property('aprobado_por_gerencia_general', 'read_only', frm.doc.__islocal ? 0 : 1);
						frm.set_df_property('aprobado_por_gerencia_general_equipo', 'read_only', frm.doc.__islocal ? 0 : 1);
					}
			
			}
		});
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.obtener_planes_nuevos",
			"args": {
				"name": frm.doc.name,
				   },
				callback: function(r){
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
						<td><a style="text-decoration: underline;" href="https://ibwni-crm.ibw.com/app/subscription-plan/{{row[0]}}"><b>{{row[0]}}</b></a></td>				
					  </tr>
					  {% } %}
					</tbody>
				  </table>`;
					data.innerHTML = frappe.render(tmp_tt_table, {"data": r.message});
			   }
			});
		frm.trigger('setup_opportunity_from');
		erpnext.toggle_naming_series();
		if (!frm.is_new()) {
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

		// 	// if (frm.doc.opportunity_from != "Customer") {
		// 	// 	frm.add_custom_button(__('Customer'),
		// 	// 		function() {
		// 	// 			frm.trigger("make_customer")
		// 	// 		}, __('Create'));
		// 	// }

		// 	// frm.add_custom_button(__('Quotation'),
		// 	// 	function() {
		// 	// 		frm.trigger("create_quotation")
		// 	// 	}, __('Create'));
		
		}

		if(frm.doc.opportunity_type === 'Nuevo Contrato'){
			frm.add_custom_button(__("Crear Contrato"), function() {						
				let total = 0;
				frm.doc.items.forEach(item => {
					total += item.precio_del_plan;						
				})
				console.log("crear..")
				if (parseFloat(frm.doc.ingresos_mrc.toFixed(2))!=parseFloat(total.toFixed(2))){
					console.log(frm.doc.ingresos_mrc);
					console.log(frm.doc.suma_precio_de_planes);
					frappe.msgprint(__("La suma de los precios asignados a los servicios, no es igual al MRC o mensualidad igresado en el flujo"));
				}
				if (frm.doc.customer === undefined || frm.doc.customer === ""){
					frappe.msgprint(__("Debe Seleccionar un cliente antes de intentar hacer un contrato"));
				}
				if(frm.doc.status==="Open" && frm.doc.customer !== undefined && frm.doc.customer !== "" && parseFloat(frm.doc.ingresos_mrc.toFixed(2))===parseFloat(total.toFixed(2))) {
					frappe.call({
						"method": "erpnext.crm.doctype.opportunity.opportunity.crear_sus_por_items",
						"args": {
								"name": frm.doc.name,
							},
							callback: function(r){
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
				console.log("crear..")
				if (parseFloat(frm.doc.ingresos_mrc.toFixed(2))!=parseFloat(total.toFixed(2))){
					console.log(frm.doc.ingresos_mrc);
					console.log(frm.doc.suma_precio_de_planes);
					frappe.msgprint(__("La suma de los precios asignados a los servicios, no es igual al MRC o mensualidad igresado en el flujo"));
				}
				if (frm.doc.customer === undefined || frm.doc.customer === ""){
					frappe.msgprint(__("Debe Seleccionar un cliente antes de intentar hacer un contrato"));
				}
				if(frm.doc.status==="Open" && frm.doc.customer !== undefined && frm.doc.customer !== "" && parseFloat(frm.doc.ingresos_mrc.toFixed(2))===parseFloat(total.toFixed(2))) {
					frappe.call({
						"method": "erpnext.crm.doctype.opportunity.opportunity.crear_plan",
						"args": {
								"name": frm.doc.name,
							},
							callback: function(r){
								frm.reload_doc();				
						}
					})
				}
			});
		}
		if((frm.doc.opportunity_type === 'Venta de Equipo' && frm.doc.docstatus==0) || (frm.doc.ingresos_otc > 0 && frm.doc.docstatus==1) ){
			if(frm.doc.opportunity_type === 'Venta de Equipo'){
				frm.add_custom_button(__("Factura de Venta"), function() {				
					frappe.call({
						method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.factura_venta_de_equipos",
						args: {"oportunidad":frm.doc.name},
						callback: function(r) {
							//var doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", "Sales Invoice", r.message);	
							
						}
					});
				});
			}
			else{
				frm.add_custom_button(__("Factura de Venta"), function() {				
					frappe.call({
						method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.factura_venta_activacion",
						args: {"oportunidad":frm.doc.name},
						callback: function(r) {
							//var doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", "Sales Invoice", r.message);	
							
						}
					});
				});

			}	
		}

		if(!frm.doc.__islocal && frm.perm[0].write && frm.doc.docstatus==0) {
			if(frm.doc.status==="Open") {
					frappe.call({
						"method": "erpnext.crm.doctype.opportunity.opportunity.verificar_plan_creado",
						"args": {
								"name": frm.doc.name,
							},
							callback: function(r){
								if(r.message){
									frm.add_custom_button(__("Actualizar Contrato"), function() {
										frappe.call({
											"method": "erpnext.crm.doctype.opportunity.opportunity.actualizar_contrato",
											"args": {
													"name": frm.doc.name,
												},
												callback: function(r){
													let d = frappe.model.get_new_name('subscription-update');
													frappe.route_options = {
														'customer':frm.doc.customer,
														'gestion':r.message,   
														'desde_oportunidad':frm.doc.name,
														'no_de_contrato':frm.doc.name.replace("CRM-OPP","CORP")                      				
													};
													frappe.set_route(['Form', 'subscription-update', d]);					
											}
										})
									});
								}				
						}
					})
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
		// frm.set_value('flujo_neto',flt(frm.doc.total_de_ingresos)-flt(frm.doc.total_de_egresos))
		// frm.set_value('flujo',(flt(frm.doc.flujo_neto)/flt(frm.doc.total_de_ingresos))*100)
		// frm.trigger("calculate_total_egresos");
		// frm.trigger("calculate_total_ingresos");
		// frm.trigger("calculate_flujo_de_caja");
		// frm.trigger("calculate_total_otc");
		// frm.trigger("calculate_total");	
		frm.trigger("calculate_venta_de_equipos");
		frm.trigger("calculate_forma_de_pago");
		// frm.set_value('ejecutivo_ve', frm.doc.utilidad * (frm.doc.porcentaje_comision_ejecutivo_ve/100));
		// frm.set_value('g_venta_equipo',frm.doc.utilidad * (frm.doc.porcentaje_comision_gerencia_ve/100));
		// frm.set_value('margen_ibw',frm.doc.utilidad - frm.doc.ejecutivo_ve - frm.doc.g_venta_equipo);
		

	
			frm.set_value('flujo_neto',flt(frm.doc.total_de_ingresos)-flt(frm.doc.total_de_egresos))
			frm.set_value('flujo',(flt(frm.doc.flujo_neto)/flt(frm.doc.total_de_ingresos))*100)
			frm.trigger("calculate_total_egresos");
			frm.trigger("calculate_total_ingresos");
			frm.trigger("calculate_flujo_de_caja");
			frm.trigger("calculate_total_otc");
			frm.trigger("calculate_total");
	

	},
	before_save(frm){
	
		
		if(frm.doc.ingresos_mrc){
			frm.set_value('flujo_neto',flt(frm.doc.total_de_ingresos)-flt(frm.doc.total_de_egresos))
			frm.set_value('flujo',(flt(frm.doc.flujo_neto)/flt(frm.doc.total_de_ingresos))*100)
			frm.trigger("calculate_total_egresos");
			frm.trigger("calculate_total_ingresos");
			frm.trigger("calculate_flujo_de_caja");
			frm.trigger("calculate_total_otc");
			frm.trigger("calculate_total");
		}
		

	},
	after_save(frm){
		//frm.reload_doc();

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
		let total = 0, base_total = 0, suma_planes = 0, suma_nio=0;
		frm.doc.items.forEach(item => {
			total += item.amount;
			base_total += item.base_amount;
			suma_planes += item.precio_del_plan;
			suma_nio += item.precio_plan_nio;
		})
		frm.doc.otros_gastos_recurrentes.forEach(item => {
			total += item.amount;
			base_total += item.base_amount;
		})

		frm.set_value({
			'total': flt(total),
			'base_total': flt(base_total),
			'suma_precio_de_planes' :parseFloat(suma_planes.toFixed(2)),
			'suma_precio_de_planes_nio':flt(suma_nio)
		});
	},
	calculate_total_otc: function(frm) {
		let total = 0, base_total = 0;
		frm.doc.productos_otc.forEach(item => {
			total += item.amount;
			base_total += item.base_amount;
		})
		total = total + flt(frm.doc.comision_de_reov_gte_vs_corp) + flt(frm.doc.comision_de_reov_ejecutivo_vs_corp)
		base_total = base_total + ((flt(frm.doc.comision_de_reov_ejecutivo_vs_corp) + flt(frm.doc.comision_de_reov_gte_vs_corp)  )*flt(frm.doc.conversion_rate))
		frm.set_value({
			'total_otc': flt(total),
			'base_total_otc': flt(base_total)
		});
	},
	calculate_total_egresos: function(frm) {
		let total = (parseFloat(frm.doc.total)*Math.abs(frm.doc.plazo)) + parseFloat(frm.doc.total_otc) + parseFloat(frm.doc.com_vendedor) + parseFloat(frm.doc.comision_gerente) + parseFloat(frm.doc.comision_supervisor);
		frm.set_value('total_de_egresos',total);
		frm.set_value('total_de_egresos_nio', flt(frm.doc.conversion_rate) * flt(frm.doc.total_de_egresos))
	},
	calculate_total_ingresos: function(frm) {
		let total = (Math.abs(frm.doc.plazo) * parseFloat(frm.doc.mrc)) + parseFloat(frm.doc.otc);
		frm.set_value('total_de_ingresos',total);
		frm.set_value('total_de_ingresos_nio', flt(frm.doc.conversion_rate) * flt(frm.doc.total_de_ingresos))
	},
	calculate_venta_de_equipos: function(frm) {
		let costo_total_solucion = 0, utilidad = 0, precio_total = 0;
		frm.doc.ventas_de_equipos.forEach(item => {
			costo_total_solucion += item.costo_total_solucion;
			utilidad += item.utilidad;
			precio_total += item.precio_total;
		})
		frm.set_value({
			'costo_total_solucion': flt(costo_total_solucion),
			'utilidad': flt(utilidad),
			'subtotal': precio_total,
			'iva': flt(precio_total * 0.15),
			'total_equipos': flt(precio_total+(precio_total * 0.15)),
		});
			frm.set_value('ejecutivo_ve', utilidad * (frm.doc.porcentaje_comision_ejecutivo_ve/100));
			frm.set_value('g_venta_equipo',utilidad * (frm.doc.porcentaje_comision_gerencia_ve/100));
			frm.set_value('comision_preventa',utilidad * (frm.doc.porcentaje_comision_preventa/100));
			frm.set_value('margen_ibw',flt(utilidad - frm.doc.ejecutivo_ve - frm.doc.g_venta_equipo))

			
		},
	calculate_forma_de_pago: function(frm) {
		let porcentaje = 0, monto = 0;
		frm.doc.forma_de_pago_equipos.forEach(item => {
			porcentaje += item.porcentaje;
			monto += item.monto;
		})
		frm.set_value('total_monto',monto );
		frm.set_value('total_porcentaje',porcentaje);
		if(monto > frm.doc.costo_total_solucion || porcentaje > 100){
			msgprint("El monto excede al costo total")
		}
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
				flujo_neto =  flt(frm.doc.otc) - flt(frm.doc.total_otc) - flt(frm.doc.com_vendedor) - flt(frm.doc.comision_gerente) - flt(frm.doc.comision_supervisor)
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
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.calculate_tir","args":{'arr':flujo_neto_arr}, callback: function(r) {
					frm.set_value('tir',r.message)
			}})
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
		if(compresion === '0:0'){
			compresion = 'x:1'
		}
		compresion = compresion.replace(':1','');	
		let proveedor = row.proveedor;
		let unidad = row.tasa;
		if(proveedor === "IBW"){
			if (compresion==='x'){
				frappe.model.set_value(cdt, cdn, "rate", 0);
			}
			else{
				frappe.model.set_value(cdt, cdn, "rate", (unidad*uom)/compresion);
			}
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
	form_render: function(frm, cdt, cdn){
		//console.log("ENTRA")
		let row = frappe.get_doc(cdt,cdn);
		if (row.divisa_plan == 'NIO'){
			frm.fields_dict.items.grid.toggle_enable('precio_del_plan', false)
			frm.fields_dict.items.grid.toggle_enable('precio_plan_nio', true)

		}
		else{
			frm.fields_dict.items.grid.toggle_enable('precio_del_plan', true)
			frm.fields_dict.items.grid.toggle_enable('precio_plan_nio', false)
		}

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
	precio_plan_nio: function(frm,cdt,cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "precio_del_plan", flt(row.precio_plan_nio)/flt(frm.doc.conversion_rate));
	},
	precio_del_plan: function(frm,cdt,cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "precio_plan_nio", flt(frm.doc.conversion_rate) * flt(row.precio_del_plan));
	},
	divisa_plan:function(frm,cdt,cdn){
		let row = frappe.get_doc(cdt,cdn);
		if (row.divisa_plan == 'NIO'){
			frm.fields_dict.items.grid.toggle_enable('precio_del_plan', false)
			frm.fields_dict.items.grid.toggle_enable('precio_plan_nio', true)

		}
		else{
			frm.fields_dict.items.grid.toggle_enable('precio_del_plan', true)
			frm.fields_dict.items.grid.toggle_enable('precio_plan_nio', false)
		}
	}
})

frappe.ui.form.on("Opportunity Item OTC", {
	get_price: function(frm,cdt,cdn){
        let item = frappe.get_doc(cdt,cdn);
        	if (item.item) {
			frappe.call({
				'method': "erpnext.support.doctype.service_order.service_order.obtener_tasa_de_valoracion_por_item",
				'args': {
					'item_code':item.item,
				},
				callback: function(r) {
				    let precio = flt(r.message) || 0.0;
				    frappe.model.set_value(cdt, cdn, 'base_rate', precio);
				    let precio_usd = precio / flt(frm.doc.conversion_rate);
					frappe.model.set_value(cdt, cdn, 'rate', precio_usd);
				}
			});
			frm.trigger("calculate", cdt, cdn);

			if(item.item === 'Presupuesto de Tercero'){
				frm.fields_dict.productos_otc.grid.toggle_reqd('nombre_proveedor', true);
				frm.fields_dict.productos_otc.grid.toggle_reqd('presupuesto_de_tercero', true);

			}
			else{
				frm.fields_dict.productos_otc.grid.toggle_reqd('nombre_proveedor', false);
				frm.fields_dict.productos_otc.grid.toggle_reqd('presupuesto_de_tercero', false);
			}
		}

    },
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
	item:  function(frm, cdt, cdn) {
		frm.trigger("get_price", cdt, cdn);
	}
})


frappe.ui.form.on("Ventas de Equipos", {
	form_render: function(frm, cdt, cdn){
		//frappe.model.set_value(cdt, cdn, "porcentaje_de_utilidad",frm.doc.porcentaje_utilidad);	
		frm.trigger("calculate");

	},
	calculate: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		let porcentaje = row.porcentaje_de_utilidad/100
		let utilidad = row.costo_unitario * row.qty*porcentaje
	
		  
		frappe.model.set_value(cdt, cdn, "costo_total_solucion  ", row.costo_unitario * row.qty);	
		frappe.model.set_value(cdt, cdn, "utilidad", utilidad);
		frappe.model.set_value(cdt, cdn, "precio_total", flt(row.utilidad) + flt(row.costo_total_solucion));
		frappe.model.set_value(cdt, cdn, "precio_unitario", (flt(row.utilidad) + flt(row.costo_total_solucion)) / row.qty);
		
		frm.trigger("calculate_venta_de_equipos");
	},
	calculate2: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		
		
		frappe.model.set_value(cdt, cdn, "costo_total_solucion", row.costo_unitario * row.qty);	
		//frappe.model.set_value(cdt, cdn, "utilidad", (row.precio_unitario*row.qty)-row.costo_total_solucion);
		frappe.model.set_value(cdt, cdn, "precio_total", row.precio_unitario * row.qty);
		
		
		
		frm.trigger("calculate_venta_de_equipos");
	},
	costo_fob: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	internacion: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	costo_unitario:  function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	porcentaje_de_utilidad: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	qty: function(frm,cdt,cdn){
		frm.trigger("calculate", cdt, cdn);
	},
	precio_unitario: function(frm,cdt,cdn){
		frm.trigger("calculate2", cdt, cdn);
	}	
})

frappe.ui.form.on("Forma de Pago Equipos", {
	calcular_monto: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		let total = frm.doc.costo_total_solucion;		  
		frappe.model.set_value(cdt, cdn, "monto", total*(row.porcentaje/100));	
		frm.trigger("calculate_forma_de_pago");
	},
	calcular_porcentaje: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		let total = frm.doc.costo_total_solucion;		  
		frappe.model.set_value(cdt, cdn, "porcentaje", (row.monto*100)/total);
		frm.trigger("calculate_forma_de_pago");	
	},
	porcentaje: function(frm, cdt, cdn) {
		frm.trigger("calcular_monto", cdt, cdn);
	},
	monto: function(frm, cdt, cdn) {
		frm.trigger("calcular_porcentaje", cdt, cdn);
	},
})

frappe.ui.form.on("Gastos Recurrentes", {
	calculate: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "amount", row.rate * row.qty);
		frappe.model.set_value(cdt, cdn, "base_rate", flt(frm.doc.conversion_rate) * flt(row.rate));
		frappe.model.set_value(cdt, cdn, "base_amount", flt(frm.doc.conversion_rate) * flt(row.amount));
		frm.trigger("calculate_total");
		frm.trigger("calculate_total_egresos");
	},
	rate: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	qty: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
})

frappe.ui.form.on("Opportunity Prospect", {
	proovedor_f: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.proveedor_section === 'Tercero'){
			frm.fields_dict.opportunity_prospect.grid.toggle_display("nombre_proveedor", true);
		}
		else{
			frappe.model.set_value(cdt, cdn, "nombre_proveedor",'IBW');
			frm.fields_dict.opportunity_prospect.grid.toggle_display("nombre_proveedor", false);
		}
		
	},
	proveedor_section: function(frm, cdt, cdn) {
		frm.trigger("proovedor_f", cdt, cdn);
	},
	
})

frappe.ui.form.on("Opportunity", "porcentaje_comision_v", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.porcentaje_comision_v)
	total_mrc = total_mrc*(porcentaje/100)
	frm.set_value('com_vendedor',total_mrc)
	frm.trigger("calculate_total_egresos");
	frm.trigger("calculate_flujo_de_caja");

});
frappe.ui.form.on("Opportunity", "porcentaje_comision_gerente", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.porcentaje_comision_gerente)
	total_mrc = total_mrc*(porcentaje/100)
	frm.set_value('comision_gerente',total_mrc)
	frm.trigger("calculate_total_egresos");
	frm.trigger("calculate_flujo_de_caja");

});
frappe.ui.form.on("Opportunity", "porcentaje_comision_supervisor_", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.porcentaje_comision_supervisor_)
	total_mrc = total_mrc*(porcentaje/100)
	frm.set_value('comision_supervisor',total_mrc)
	frm.trigger("calculate_total_egresos");
	frm.trigger("calculate_flujo_de_caja");

});
frappe.ui.form.on("Opportunity", "descuento_ingreso_mrc", function(frm) {
	let total_mrc = frm.doc.ingresos_mrc
	let porcentaje = Math.abs(frm.doc.descuento_ingreso_mrc)
	total_mrc = total_mrc - total_mrc*(porcentaje/100)
	frm.set_value('mrc',total_mrc)
	frm.trigger("calculate_flujo_de_caja");


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
	let porcentaje2 = Math.abs(frm.doc.porcentaje_comision_gerente)
	total_mrc2 = total_mrc2*(porcentaje2/100)
	frm.set_value('comision_gerente',total_mrc2)

	let total_mrc3 = frm.doc.ingresos_mrc
	let porcentaje3 = Math.abs(frm.doc.porcentaje_comision_supervisor_)
	total_mrc3 = total_mrc3*(porcentaje3/100)
	frm.set_value('comision_supervisor',total_mrc3)

	frm.trigger("calculate_total_egresos");
	frm.trigger("calculate_flujo_de_caja");



});
frappe.ui.form.on("Opportunity", "ingresos_otc", function(frm) {
	let total_otc = frm.doc.ingresos_otc
	let porcentaje = Math.abs(frm.doc.descuento_ingreso_otc)
	total_otc = total_otc - total_otc*(porcentaje/100)
	frm.set_value('otc',total_otc)
	frm.trigger("calculate_flujo_de_caja");

});
frappe.ui.form.on("Opportunity", "descuento_ingreso_otc", function(frm) {
	let total_otc = frm.doc.ingresos_otc
	let porcentaje = Math.abs(frm.doc.descuento_ingreso_otc)
	total_otc = total_otc - total_otc*(porcentaje/100)
	frm.set_value('otc',total_otc)
	frm.trigger("calculate_flujo_de_caja");

});
frappe.ui.form.on("Opportunity", "total_otc", function(frm) {
	frm.trigger("calculate_total_egresos");
	frm.trigger("calculate_flujo_de_caja");

});
frappe.ui.form.on("Opportunity", "total", function(frm) {
	frm.trigger("calculate_total_egresos");
	frm.trigger("calculate_flujo_de_caja");

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
frappe.ui.form.on("Opportunity", "porcentaje_comision_ejecutivo_ve", function(frm) {
	frm.set_value('comision_preventa', frm.doc.utilidad * (frm.doc.porcentaje_comision_preventa/100));
	frm.set_value('ejecutivo_ve', frm.doc.utilidad * (frm.doc.porcentaje_comision_ejecutivo_ve/100));
	frm.set_value('g_venta_equipo',frm.doc.utilidad * (frm.doc.porcentaje_comision_gerencia_ve/100));
	frm.set_value('margen_ibw',frm.doc.utilidad - frm.doc.ejecutivo_ve - frm.doc.g_venta_equipo - frm.doc.comision_preventa);
 
});
frappe.ui.form.on("Opportunity", "porcentaje_comision_gerencia_ve", function(frm) {
	frm.set_value('comision_preventa', frm.doc.utilidad * (frm.doc.porcentaje_comision_preventa/100));
	frm.set_value('ejecutivo_ve', frm.doc.utilidad * (frm.doc.porcentaje_comision_ejecutivo_ve/100));
	frm.set_value('g_venta_equipo',frm.doc.utilidad * (frm.doc.porcentaje_comision_gerencia_ve/100));
	frm.set_value('margen_ibw',frm.doc.utilidad - frm.doc.ejecutivo_ve - frm.doc.g_venta_equipo - frm.doc.comision_preventa);
});
frappe.ui.form.on("Opportunity", "porcentaje_comision_preventa", function(frm) {
	frm.set_value('comision_preventa', frm.doc.utilidad * (frm.doc.porcentaje_comision_preventa/100));
	frm.set_value('ejecutivo_ve', frm.doc.utilidad * (frm.doc.porcentaje_comision_ejecutivo_ve/100));
	frm.set_value('g_venta_equipo',frm.doc.utilidad * (frm.doc.porcentaje_comision_gerencia_ve/100));
	frm.set_value('margen_ibw',frm.doc.utilidad - frm.doc.ejecutivo_ve - frm.doc.g_venta_equipo - frm.doc.comision_preventa);
});
frappe.ui.form.on("Opportunity", "comision_de_reov_gte_vs_corp", function(frm) {
	frm.trigger("calculate_total_otc");
});
frappe.ui.form.on("Opportunity", "comision_de_reov_ejecutivo_vs_corp", function(frm) {
	frm.trigger("calculate_total_otc");
});


// cargar planes de actualizacion de contrato
// frappe.ui.form.on("Opportunity", "opportunity_type", function(frm) {
// 	frappe.call({
// 		"method": "erpnext.crm.doctype.opportunity.opportunity.actualizar_contrato_planes",
// 		"args": {
// 				"cliente": frm.doc.customer,
// 			},
// 			callback: function(r){
// 				frm.reload_doc()					
// 		}
// 	})
// });

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

		// this.frm.set_query("item_code", "items", function() {
		// 	return {
		// 		query: "erpnext.controllers.queries.item_query",
		// 		filters: {'is_sales_item': 1}
		// 	};
		// });

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

// cur_frm.cscript.item_code = function(doc, cdt, cdn) {
// 	var d = locals[cdt][cdn];
// 	if (d.item_code) {
// 		return frappe.call({
// 			method: "erpnext.crm.doctype.opportunity.opportunity.get_item_details",
// 			args: {"item_code":d.item_code},
// 			callback: function(r, rt) {
// 				if(r.message) {
// 					$.each(r.message, function(k, v) {
// 						frappe.model.set_value(cdt, cdn, k, v);
// 					});
// 					refresh_field('image_view', d.name, 'items');
// 				}
// 			}
// 		})
// 	}
// }
