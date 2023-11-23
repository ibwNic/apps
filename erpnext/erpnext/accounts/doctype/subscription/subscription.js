// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// modificado 18/01/23
frappe.ui.form.on('Subscription', {
	setup: function(frm) {
		frm.set_query('party_type', function() {
			return {
				filters : {
					name: ['in', ['Customer', 'Supplier']]
				}
			}
		});

		frm.set_query('cost_center', function() {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
	},
	
	refresh: function(frm) {

		frappe.call({
			"method": "erpnext.accounts.doctype.subscription.subscription.get_work_orders",
			"args": {
				"name": frm.doc.name,
				   },
				callback: function(r){
					console.log(r.message)
					const data = document.querySelector("#ordenesOS");
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
						<td><a style="color:#4E8CF2; text-decoration: underline;" href="https://ibwni-crm.ibw.com/app/service-order/{{row[0]}}"><b>{{row[0]}}</b></a></td>
						<td>{{row[1]}}</td>
						<td>{{row[5]}}</td>
						<td>{{row[9]}}</td>
						<td>{{row[4]}}</td>
						<td>{{row[13]}}</td>
						<td>{{row[16]}}</td>
						<td>{{row[23]}}</td>
						<td>{{row[2]}}</td>
						<td>{{row[27]}}</td>	
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

		if(frm.doc.campana !== undefined){
			if(!frm.doc.campana.includes("eferido")){
				frm.toggle_display("referido_por", false);
			}
			else{
				frm.toggle_display("referido_por", true); 
				frm.set_query('referido_por', function() {
					return {
						filters : {
							estado_cliente: 'ACTIVO'
						}
					}
				});
			}
		}
		else{
			frm.toggle_display("referido_por", false);

		}
		
		 
		// frm.fields_dict.plans.grid.get_field("estado_plan").get_query = function(doc, cdt, cdn){
		// 	let row = frappe.get_doc(cdt, cdn);
		// 	let estado = row.estado_plan;
		// 	console.log(estado)
		// }
		
		//let f=frappe.db.get_value("Customer", {"name": frm.doc.party},"sales_tax_template")

		// if (f.message!==frm.doc.sales_tax_template){
		// 	frm.set_value('sales_tax_template',f.message)
		// }
		if(frm.doc.workflow_state !== 'Terminado'){
			frappe.db.get_value("Customer", {"name": frm.doc.party},"sales_tax_template",function(res){ 
				res.sales_tax_template; }).then(r =>{ var rest=r.message;
					if (rest.sales_tax_template!=frm.doc.sales_tax_template){
						frm.set_value('sales_tax_template',rest.sales_tax_template)
						//console.log("hola")
					}	
				 })
		}
		

		// if(!frm.is_new()){
		// 	if(frm.doc.status !== 'Cancelled'){
		// 		frm.add_custom_button(
		// 			__('Cancel Subscription'),
		// 			() => frm.events.cancel_this_subscription(frm)
		// 		);
		// 		frm.add_custom_button(
		// 			__('Fetch Subscription Updates'),
		// 			() => frm.events.get_subscription_updates(frm)
		// 		);
		// 	}
		// 	else if(frm.doc.status === 'Cancelled'){
		// 		frm.add_custom_button(
		// 			__('Restart Subscription'),
		// 			() => frm.events.renew_this_subscription(frm)
		// 		);
		// 	}
		// }
		if(frm.doc.workflow_state === 'Activo' || frm.doc.workflow_state === 'Suspendido'){
			frm.add_custom_button(__('Finalizar Plan'), function() {
				// let arreglo = []
				// for(let i = 0; i< frm.doc.plans.length; i++){
				// 	arreglo.push([frm.doc.plans[i].plan, frm.doc.plans[i].name])
				// 	// arreglo[frm.doc.plans[i].plan] =  frm.doc.plans[i].name
				// }
				//console.log(arreglo)
				var d = new frappe.ui.Dialog({
					title: __("Finalizar Plan"),
					fields: [
						 {"fieldname":"plan", "fieldtype":"Link", "label":__("Planes"), "options":"Subscription Plan Detail","reqd": "1",	
						get_query: () => {
							return {
								filters: {
									parent: frm.doc.name									
								}
							}
						}
					},
						{"fieldname":"motivo", "fieldtype":"Select", "label":__("Motivo"), "options":["Falta de Pago",
						"Cierre de Empresa",
						"Incorformidad con el Servicio",
						"Falta de Uso",
						"Contrato Temporal",
						"Motivo de Viaje",
						"Cierre Auto / Cliente con 3 meses Suspendido",
						"TRASLADO/FALTA DE COBERTURA",
						"MEJOR OFERTA DE COMPETENCIA (OTROS)",
						"INCONFORMIDAD CON LA GRILLA",
						"FALTA DE EQUIPO",
						"Inconformidad con el Soporte",
						"Económico",
						"Inconformidad Técnica",
						"Plan Duplicado",
						"Fallecimiento",
						"Venta Mal Asesorada",
						"Contrato no renovado",
						"Cambio de Proveedor",
						"Cierre de Proyecto",
						"Cierre por Upgrade",
						"Cambio de Tarifa",
						"Cambio de Servicio",
						"Cambio de Tipo de Servicio",						
						], "reqd": "1"},					
						{"fieldname":"fetch", "label":__("Finalizar"), "fieldtype":"Button"}
					]
				});
				// d.fields_dict.staff_type.df.options = {"parent":frm.doc.name};	

				d.get_input("fetch").on("click", function() {
					var values = d.get_values();
					if(!values) return;
					console.log(values)
					frappe.call({
						
					 	method: "erpnext.accounts.doctype.subscription.subscription.finalizacion_de_plan",
					 	args: values,
					 	callback: function(r) {
					 		console.log(r.message)
							frm.reload_doc();
				
					 	}
					});
				});
				d.show();
			}, );
			frm.add_custom_button(__('Actualizar Contrato'), function() {
				let d = frappe.model.get_new_name('subscription-update');
            	frappe.route_options = {
            		'customer':frm.doc.party,
            		'nombre_de_cliente': frm.doc.nombre_del_cliente,
					'contrato':frm.doc.name,
            	};
            	frappe.set_route(['Form', 'subscription-update', d]);
			})
			
		}

		// if(frappe.user.has_role('System Manager')){
		// 	frm.add_custom_button(__('Orden de Recuperacion de Materiales'), function() {
		// 		var d = new frappe.ui.Dialog({
		// 			title: __("Finalizar Plan"),
		// 			fields: [
		// 				 {"fieldname":"plan", "fieldtype":"Link", "label":__("Planes"), "options":"Subscription Plan Detail","reqd": "1",	
		// 				get_query: () => {
		// 					return {
		// 						filters: {
		// 							parent: frm.doc.name									
		// 						}
		// 					}
		// 				}
		// 			},				
		// 				{"fieldname":"fetch", "label":__("Finalizar"), "fieldtype":"Button"}
		// 			]
		// 		});
		// 		// d.fields_dict.staff_type.df.options = {"parent":frm.doc.name};	

		// 		d.get_input("fetch").on("click", function() {
		// 			var values = d.get_values();
		// 			if(!values) return;
		// 			console.log(values)
		// 			frappe.call({						
		// 			 	method: "erpnext.accounts.doctype.subscription.subscription.crear_orden_Desinstalacion2",
		// 			 	args: values,
		// 			 	callback: function(r) {
		// 			 		console.log(r.message)
		// 					frm.reload_doc();				
		// 			 	}
		// 			});
		// 		});
		// 		d.show();
		// 	}, __("Ordenes de Trabajo") );}

		if(frm.doc.workflow_state === 'Instalado'){
		frm.add_custom_button(__('Crear Factura B'), function(){

			frappe.call({
				"method": "erpnext.accounts.doctype.subscription.subscription.process_de_Facturacion",
				"args": {
					"name": frm.doc.name
				},
				freeze: true,
				callback: function(r){
					// console.log(r.message)
					frm.reload_doc();
				}
			})

		});
	}
	if(frm.doc.workflow_state === 'Activo'){
		frm.add_custom_button(__('Crear Factura Recurrente B'), function(){
			frappe.call({
				"method": "erpnext.accounts.doctype.subscription.subscription.process_de_Facturacion_Recurrente_B",
				"args": {
					"name": frm.doc.name
				},
				freeze: true,
				callback: function(r){
					// console.log(r.message)
					frm.reload_doc();
				}
			})

		});
	}

	if(frm.doc.workflow_state === 'Instalado' && frm.doc.subscription_update){
		frm.add_custom_button(__('Crear Factura B'), function(){

			frappe.call({
				"method": "erpnext.accounts.doctype.subscription.subscription.process_de_Facturacion",
				"args": {
					"name": frm.doc.name
				},
				freeze: true,
				callback: function(r){
					// console.log(r.message)
					frm.reload_doc();
				}
			})

		});
	}

},

	cancel_this_subscription: function(frm) {
		const doc = frm.doc;
		frappe.confirm(
			__('This action will stop future billing. Are you sure you want to cancel this subscription?'),
			function() {
				frappe.call({
					method:
					"erpnext.accounts.doctype.subscription.subscription.cancel_subscription",
					args: {name: doc.name},
					callback: function(data){
						if(!data.exc){
							frm.reload_doc();
						}
					}
				});
			}
		);
	},

	renew_this_subscription: function(frm) {
		const doc = frm.doc;
		frappe.confirm(
			__('You will lose records of previously generated invoices. Are you sure you want to restart this subscription?'),
			function() {
				frappe.call({
					method:
					"erpnext.accounts.doctype.subscription.subscription.restart_subscription",
					args: {name: doc.name},
					callback: function(data){
						if(!data.exc){
							frm.reload_doc();
						}
					}
				});
			}
		);
	},

	get_subscription_updates: function(frm) {
		const doc = frm.doc;
		
		frappe.call({
			method:
			"erpnext.accounts.doctype.subscription.subscription.get_subscription_updates",
			args: {name: doc.name},
			freeze: true,
			callback: function(data){
				if(!data.exc){
					frm.reload_doc();
				}
			}
		});
	}
});

frappe.ui.form.on("Subscription", "campana", function(frm) {
	if(!frm.doc.campana.includes("eferido")){
		frm.toggle_display("referido_por", false);
	}
	else{
		frm.toggle_display("referido_por", true);  
		frm.set_df_property('tipo_gestion', 'read_only', false);
	}
});
	
// frappe.ui.form.on('Subscription Plan Detail', {
// 	form_render: function(frm,cdt,cdn) {
// 	   let item = locals[cdt][cdn]; 
// 	   frm.fields_dict.plans.grid.toggle_display("activar", false);
// 	   frm.fields_dict.plans.grid.toggle_display("tv_adicional", false);
// 	   frm.fields_dict.plans.grid.toggle_display("factura_tv_adicional", false);
// 	   frm.fields_dict.plans.grid.toggle_display("crear_traslado", false);
// 		// if(item.estado_plan != "SUSPENDIDO: Manual" && item.estado_plan != "SUSPENDIDO: Temporal"){
// 		// 	frm.fields_dict.plans.grid.toggle_display("activar", false);
// 		// }
// 		// else{
// 		// 	frm.fields_dict.plans.grid.toggle_display("activar", true);
// 		// }
// 		// if(item.plan != "Servicio TV HFC" && item.plan != "TV Combo GPON" && item.plan != "TV Combo HFC"){
// 		// 	frm.fields_dict.plans.grid.toggle_display("tv_adicional", false);
// 		// 	frm.fields_dict.plans.grid.toggle_display("factura_tv_adicional", false);
// 		// }
// 		// else{
// 		// 	frm.fields_dict.plans.grid.toggle_display("tv_adicional", true);
// 		// 	frm.fields_dict.plans.grid.toggle_display("factura_tv_adicional", true);
// 		// }
// 	},
// });