// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('AveriasMasivas', {
	refresh: function(frm) {
		if(frm.doc.workflow_state !== "Finalizado"){
			frm.add_custom_button(__("Crear Orden de Servicio Interno"), function() {
				let d = frappe.model.get_new_name('orden-de-servicio-interno');
				frappe.route_options = {
					'averia_masiva':frm.doc.name,
					'descripcion':"AVERIA MASIVA" ,    
					'tipo_de_orden': "VENTANA DE MANTENIMIENTO",
					'nodo':frm.doc.nodos                     				
				};
				frappe.set_route(['Form', 'orden-de-servicio-interno', d]);
			});
		}
		
	}
});
