// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on('Service Order', {
	refresh: function(frm) {
		if(frm.doc.workflow_state === 'Atendido'){
			frm.set_df_property('razon_pendiente', 'read_only',false);
		}
		else{
			frm.set_df_property('razon_pendiente', 'read_only', true);
		}
		frm.set_query('tecnico', function(d){
			return {
				filters: {
					 activo: 1
				}
			}
		})
		frm.fields_dict.cuadrilla_tecnica.grid.get_field("tecnico").get_query = function(doc, cdt, cdn){
			return {
				filters: {		
					activo:1
				}
			}
		}
		if(frm.doc.tipo_de_orden !== "PRESUPUESTO"){
			frm.toggle_display("bom_de_materiales", false);
			frm.toggle_display("total_bom_nio", false);
			frm.toggle_display("total_bom_usd", false);
		}
		if(!(["INSTALACION","DESINSTALACION","REACTIVACION","TRASLADO"].includes(frm.doc.tipo_de_orden ))){
			frm.toggle_display("equipo_orden_servicio", false);
		}
		if(frm.doc.tipo_de_orden !== 'TRASLADO'){
			frm.toggle_display("dirección_de_traslado", false);
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
					frm.set_query('dirección_de_traslado', function(d){            			
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
		if(frm.doc.tipo_de_orden === "DESINSTALACION" || frm.doc.tipo_de_orden === "REACTIVACION"){
			frm.set_df_property('equipo_orden_servicio', 'read_only', frm.doc.__islocal ? 0 : 1);
			// frm.set_df_property('nodo', 'read_only', frm.doc.__islocal ? 0 : 1);
		}

		if(frm.doc.tipo_de_orden !== "SITE SURVEY" && frm.doc.tipo_de_orden !== "PRESUPUESTO"){
			frm.toggle_display("factible", false);
		}
		if(frm.doc.tipo_de_orden !== "SUSPENSION"){
			frm.toggle_display("so_detalle_clientes_suspendidos", false);
		}
		if(frm.doc.venta_en_caliente === 0){
			frm.set_df_property('fecha_seguimiento', 'read_only', frm.doc.__islocal ? 0 : 1);
			frm.set_df_property('fecha_pendiente', 'read_only', frm.doc.__islocal ? 0 : 1);
			frm.set_df_property('fecha_atendido', 'read_only', frm.doc.__islocal ? 0 : 1);
			frm.set_df_property('fecha_finalizado', 'read_only', frm.doc.__islocal ? 0 : 1);

		}else{
			frm.set_df_property('fecha_solicitud', 'read_only', false);
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
						frm.fields_dict.bom_de_materiales.grid.toggle_display("precio", false);
						frm.fields_dict.bom_de_materiales.grid.toggle_display("total", false);
	
						}
						if(r.message.includes("O&M") && !(r.message.includes("Back Office")) && !(r.message.includes("Administrador Tecnicos"))){
							frm.toggle_display("fecha_seguimiento", false);
							frm.toggle_display("fecha_solicitud", false);
							frm.toggle_display("fecha_pendiente", false);
							frm.toggle_display("fecha_atendido", false);
							frm.toggle_display("fecha_finalizado", false);
							frm.toggle_display("ordered_on_stock", false);
							frm.toggle_display("direccion_de_instalacion", false);
							frm.toggle_display("cuadrilla_tecnica", false);
						}		
			}
		});

		if(frm.doc.workflow_state === 'Finalizado' && frm.doc.tipo_de_orden === 'INSTALACION'){
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
							//console.log(localStorage.getItem("filtro2")  )
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
										//console.log(r.message)	
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
	}
});
