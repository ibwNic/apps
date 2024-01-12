// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on('Service Order', {
	refresh: function(frm) {
		
		if(frm.doc.tipo_de_orden !== 'INSTALACION' &&  frm.doc.tipo_de_orden !== 'INSTALACION OTC' && frm.doc.tipo_de_orden !== 'TRASLADO' && frm.doc.tipo_de_orden !== 'SITE SURVEY'){
			frm.toggle_display("coordenadas", false);
		}
		// if(!(["INSTALACION","DESINSTALACION","REACTIVACION","TRASLADO"].includes(frm.doc.tipo_de_orden ))){
		// 	frm.toggle_display("equipo_orden_servicio", false);
		// }
		if(!(["INSTALACION","Liquidacion de Materiales Atrasada","INSTALACION DE TORRES","DESINSTALACION","DESINSTALACION RCPE","TV ADICIONAL","CABLEADO","TRASLADO","REACTIVACION","APROVISIONAMIENTO","INSTALACION OTC"].includes(frm.doc.tipo_de_orden ))){
			frm.toggle_display("equipo_orden_servicio", false);
			frm.toggle_display("productos",false)
			frm.toggle_display("materiales_usados",false)
					
		}
		else{

			if (frm.doc.tecnico && frm.doc.tipo_de_orden !== 'DESINSTALACION'){
				let div_boton = document.querySelector("#boton-balance");
				var boton = document.createElement("button");
				boton.className = "btn btn-success mt-3"; 
	
				boton.onclick =  function () { 
					let tecnico_balance = frm.doc.tecnico;
					tecnico_balance = tecnico_balance.replace(" ","%20")
					window.location.href='https://ibwni-crm.ibw.com/app/query-report/Balance%20de%20Inventario%20por%20T%C3%A9cnico?tecnico='  + tecnico_balance;
					
				}
				boton.innerText = "Ver Inventario de " + frm.doc.tecnico;
				div_boton.appendChild(boton);
	
			}

			frm.set_df_property('almacen_filtro', 'read_only',false);

			// if(["TV ADICIONAL","CABLEADO","TRASLADO"].includes(frm.doc.tipo_de_orden )){
			// 	frm.set_df_property('equipo_orden_servicio', 'read_only', true);
			// }
		}

		if(frm.doc.portafolio == 'DIALUP'){
			frm.toggle_display("correo", true);
		}

		if(frm.doc.tipo_de_orden !== "PRESUPUESTO"){
			frm.toggle_display("bom_de_materiales", false);
			frm.toggle_display("total_bom_nio", false);
			frm.toggle_display("total_bom_usd", false);
		}	
		if(frm.doc.workflow_state === 'Atendido'){
			frm.set_df_property('razon_pendiente', 'read_only',false);
		}
		else{
			frm.set_df_property('razon_pendiente', 'read_only', true);
		}		
		if(frm.doc.tipo_de_orden !== 'TRASLADO'){
			frm.toggle_display("direccion_de_traslado", false);
			frm.toggle_display("longitud_traslado", false);
			frm.toggle_display("latitud_traslado", false);
			frm.toggle_display("nuevo_nodo", false);
		}
		else{
			if(frm.doc.tercero !== undefined && frm.doc.tipo === 'Customer'){
				frappe.call({
				"method": "erpnext.accounts.doctype.subscription.subscription.get_addresses_user","args":{'party': frm.doc.tercero}, callback: function(r) {
				//para filtrar en una tabla secundaria:
				console.log(r.message)
					frm.set_query('direccion_de_traslado', function(d){            			
						return {
								filters: {
									name: ["in", r.message]
								}
							}
						})
				}
			})
			}
		}
		if(frm.doc.tipo_de_orden === "DESINSTALACION" || frm.doc.tipo_de_orden === "REACTIVACION"   || frm.doc.tipo_de_orden === 'DESINSTALACION RCPE'){
			
			frm.toggle_display("productos", false);
			frm.toggle_display("almacen_filtro",false);
			if(frm.doc.tipo_de_orden === "REACTIVACION"){
				frm.toggle_display("materiales_usados",false);
				//frm.set_df_property('equipo_orden_servicio', 'read_only', true);	
			}
		}

		if(frm.doc.tipo_de_orden !== "SITE SURVEY" && frm.doc.tipo_de_orden !== "PRESUPUESTO"){
			frm.toggle_display("factible", false);
			
			frm.toggle_display("tipo_de_servicio", false);
		}
		if(frm.doc.tipo_de_orden ===  'SITE SURVEY'){
			frm.set_df_property('portafolio', 'reqd', 1)
		}
		
		if(frm.doc.tipo_de_orden !== "SUSPENSION" && frm.doc.tipo_de_orden !== "CORTE"){
			frm.toggle_display("so_detalle_clientes_suspendidos", false);
		}
		if(frm.doc.venta_en_caliente === 0){
			frm.set_df_property('fecha_seguimiento', 'read_only', true);
			frm.set_df_property('fecha_pendiente', 'read_only', true);
			frm.set_df_property('fecha_atendido', 'read_only', true);
			frm.set_df_property('fecha_finalizado', 'read_only', true);

		}else{
			frm.set_df_property('fecha_solicitud', 'read_only', false);
		}
		frm.set_query('tecnico', function(d){
			return {
				filters: {
					 activo: 1
				}
			}
		})
		frm.fields_dict.cuadrilla_tecnica.grid.get_field("tecnico").get_query = function(doc, cdt, cdn){
		
			frappe.model.set_value(cdt, cdn, "fecha_asignacion", frappe.datetime.now_datetime());
			return {
				filters: {		
					activo:1
				}
			}
		}
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol",
				callback: function(r){
					//console.log(r.message)
					if(!(r.message.includes("Precios"))){
						frm.toggle_display("total_bom_nio", false);
						frm.toggle_display("total_bom_usd", false);
						// mostrar u ocultar campo de tabla secundaria
						frm.fields_dict['bom_de_materiales'].grid.set_column_disp("precio", false);	
						frm.fields_dict['bom_de_materiales'].grid.set_column_disp("total", false);	
						frm.fields_dict['bom_de_materiales'].grid.set_column_disp("precio_nio", false);	
						frm.fields_dict['bom_de_materiales'].grid.set_column_disp("total_nio", false);
						frm.fields_dict.bom_de_materiales.grid.toggle_display("precio", false);
						frm.fields_dict.bom_de_materiales.grid.toggle_display("total", false);
						frm.fields_dict.bom_de_materiales.grid.toggle_display("precio_nio", false);
						frm.fields_dict.bom_de_materiales.grid.toggle_display("total_nio", false);
						}
						if(r.message.includes("O&M") && !(r.message.includes("Back Office")) && !(r.message.includes("Administrador Tecnicos"))){
							frm.toggle_display("fecha_seguimiento", false);
							frm.toggle_display("fecha_solicitud", false);
							frm.toggle_display("fecha_pendiente", false);
							frm.toggle_display("fecha_atendido", false);
							frm.toggle_display("fecha_finalizado", false);
							frm.toggle_display("ordered_on_stock", false);
						}		
			}
		});

		if(frm.doc.tipo_de_orden === 'INSTALACION' && frm.doc.workflow_state != 'Finalizado'){
			frm.add_custom_button(__('Crear Sub-Orden'), function() {
				var d = new frappe.ui.Dialog({
					title: __("Seleccionar tipo de Sub Orden"),
					fields: [
						{"fieldname":"tipo_de_orden", "fieldtype":"Select", "label":__("Tipo"), "options":["CONSTRUCCION DE RED","ENRUTAMIENTO","ENTREGA DE SERVICIO","CONSTRUCCION DE TORRES", "INSTALACION DE TORRES"], "reqd": "1"},					
						{"fieldname":"fetch", "label":__("Crear Orden de Trabajo"), "fieldtype":"Button"}
					]
				});
			
				d.get_input("fetch").on("click", function() {
					var values = d.get_values();
					if(!values) return;
					console.log(values.tipo_de_orden)

					frappe.call({
						"method": "erpnext.support.doctype.service_order.service_order.crear_sub_orden","args":{
							"tipo_de_orden":values.tipo_de_orden,
							"name":frm.doc.name
						},
							callback: function(r){
									
						}
					});

				});
				d.show();
			});
		}
		else{
			let roles = frappe.call({
				"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol","async": false, 
					callback: function(r){	
						console.log(r)
						if( r.message.includes("Support Team")){
							frm.add_custom_button(__('Crear Sub-Orden'), function() {
								var d = new frappe.ui.Dialog({
									title: __("Seleccionar tipo de Sub Orden"),
									fields: [
										{"fieldname":"tipo_de_orden", "fieldtype":"Select", "label":__("Tipo"), "options":["Liquidacion de Materiales Atrasada"], "reqd": "1"},					
										{"fieldname":"fetch", "label":__("Crear Orden de Trabajo"), "fieldtype":"Button"}
									]
								});
							
								d.get_input("fetch").on("click", function() {
									var values = d.get_values();
									if(!values) return;
									console.log(values.tipo_de_orden)
				
									frappe.call({
										"method": "erpnext.support.doctype.service_order.service_order.crear_sub_orden","args":{
											"tipo_de_orden":values.tipo_de_orden,
											"name":frm.doc.name
										},
											callback: function(r){
													
										}
									});
				
								});
								d.show();
							});
						}									
				}
			});

	

			frm.toggle_display("subordenes", false);
		}



		if((frm.doc.workflow_state == 'Finalizado')  && frm.doc.tipo_de_orden === 'INSTALACION'){
			frm.add_custom_button(__('Crear Encuesta'), function() {
				var d = new frappe.ui.Dialog({
					title: __("Seleccionar Encuesta"),
					fields: [
						{"fieldname":"encuesta", "fieldtype":"Link", "label":__("Encuesta"), "options":"Encuestas", "reqd": "1"},					
						{"fieldname":"fetch", "label":__("Obtener Encuesta"), "fieldtype":"Button"}
					]
				});
				//filtrar en cuadro de dialogo				
				d.get_field("encuesta").get_query = function(){
					frappe.call({
						method: "erpnext.support.doctype.service_order.service_order.filtrar_encuesta","args":{"doctype":frm.doc.doctype,"name":frm.doc.name},
						callback: function(r) {					
							localStorage.setItem("filtro2", r.message);
						}
					});
					var presupuesto = d.get_value("encuesta"), filters = {'name': ["in", localStorage.getItem("filtro2").split(',')]};
						if (presupuesto){ filters['encuesta'] = presupuesto; }
						return {'filters': filters};
								
				};
				d.get_input("fetch").on("click", function() {
					var values = d.get_values();
					if(!values) return;
					frappe.call({
						method: "erpnext.support.doctype.service_order.service_order.obtener_preguntas",
						args: values,
						callback: function(r) {
							let result = r.message;
							let preguntas = []
							preguntas.push({"fieldname":"nombre", "fieldtype":"Data", "label":__("Nombre y Apellido"), "reqd": "1"});
							for(let i = 0; i < result.length; i++){
								preguntas.push({"fieldname":i, "fieldtype":"Select", "label":__(result[i][0]), "options":result[i][1].split("\n"), "reqd": "1"})
							}
							preguntas.push({"fieldname":"fetch", "label":__("Guardar"), "fieldtype":"Button"})
							console.log(preguntas)
							var d2 = new frappe.ui.Dialog({
								title: __("Responder encuesta"),
								fields: preguntas
							});
							d.hide();
							d2.show();
							d2.get_input("fetch").on("click", function() {
								var values = d2.get_values();
								if(!values) return;
								let argss = {
									"respuestas":values,
								}
								argss['doctype'] = frm.doc.doctype;
								argss['name'] = frm.doc.name;
								argss['id_encuesta'] = d.get_values().encuesta
								frappe.call({
									method: "erpnext.support.doctype.service_order.service_order.guardar_encuesta",
									args: argss,
									callback: function(r) {
										frm.reload_doc();
									}
								});
								d2.hide();
							});
						}
					});
				});
				d.show();
			});
		}
	},
	coordenadas: function(frm){
		let mapdata = JSON.parse(frm.doc.coordenadas).features[0];
		if(mapdata && mapdata.geometry.type == 'Point'){
			let lat = mapdata.geometry.coordinates[1];
			let lon = mapdata.geometry.coordinates[0];
			if(frm.doc.tipo_de_orden !== 'TRASLADO')
			{
				frm.set_value("latitud",lat);
				frm.set_value("longitud",lon);
			}
			else{
				frm.set_value("latitud_traslado",lat);
				frm.set_value("longitud_traslado",lon);
			}
		}
	},
	scan_barcode() {
		const barcode_scanner = new erpnext.utils.BarcodeScanner({frm:this.frm});
		barcode_scanner.process_scan();
	},
	before_save(frm){			
		if(frm.doc.equipo_orden_servicio && frm.doc.tipo_de_orden === 'INSTALACION'){

			let tecnicos=[]
			frm.doc.cuadrilla_tecnica.forEach(e => {
				tecnicos.push(e.tecnico)
			})
			tecnicos.push(frm.doc.tecnico)
			console.log(tecnicos)
			frm.doc.equipo_orden_servicio.forEach(e => {
				if (e.serial_no){						
					let x = frappe.call({
						"method": "erpnext.support.doctype.service_order.service_order.validar_equipo_almacen",
						"args":{
							"equipo":e.serial_no,
							"orden":frm.doc.name,
							"tecnicos":tecnicos								
						},
						"async": false,
						callback: function(r){	
							console.log(r.message)	
						}
					});						
					if( x.responseJSON.message !== 'pasa' ){
						 frappe.throw("El equipo " + x.responseJSON.message + " no pertenece a ninguna bodega de los tecnicos seleccionados")
					}						
				}					
			});	
		}
		// if(frm.doc.productos){
		// 	frm.doc.productos.forEach(e => {
		// 		if (e.serial_no.length > 0){						
		// 			let x = frappe.call({
		// 				"method": "erpnext.support.doctype.issue.issue.validar_equipo_almacen",
		// 				"args":{
		// 					"equipo":e.serial_no,
		// 					"orden":frm.doc.name								
		// 				},
		// 				"async": false,
		// 				callback: function(r){		
		// 				}
		// 			});						
		// 			if( x.responseJSON.message !== 'pasa' ){
		// 			 	frappe.throw("El equipo " + x.responseJSON.message + " no pertenece a ninguna bodega de los tecnicos seleccionados")
		// 			}						
		// 		}					
		// 	});	
		// }
				
	 },
});
