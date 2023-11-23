// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// modificado 20/01/23 15:18
frappe.ui.form.on('Suspensiones', {
	refresh: function(frm) {
		if(frm.doc.territory === 'Nicaragua' && frm.doc.municipio === 'Nicaragua' && frm.doc.barrio === 'Nicaragua'){
			frappe.call({
				"method": "erpnext.accounts.doctype.suspensiones.suspensiones.limpiar_campos_territorio",
				"args": {
					"name": frm.doc.name,
				},
				freeze: true,
				callback: function(r){
					frm.reload_doc();
				}
			})
		}
		if(frm.doc.docstatus === 0){
			if  (frm.doc.detalle_suspension.length > 0){
				frm.add_custom_button(__('Iniciar Proceso de Suspencion'), function(){
					frappe.call({
						"method": "erpnext.accounts.doctype.suspensiones.suspensiones.process_de_Suspencion",
						"args": {
							"name": frm.doc.name,
						},
						freeze: true,
						freeze_message: "Realizando Suspension de servicios, por favor espere ...",
						callback: function(r){
							console.log(r.message)
							frm.reload_doc();
						}
					})
				});	
			}
	
			frm.add_custom_button(__('Generar Vista Previa'), function(){
				frappe.call({
					"method": "erpnext.accounts.doctype.suspensiones.suspensiones.generar_vista_previa",
					"args": {
						"name": frm.doc.name,
					},
					freeze: true,
					freeze_message: "Generando vista previa, por favor espere ...",
					callback: function(r){
						console.log(r.message)
						frm.reload_doc();
					}
				})
			});
		}			
	},
});
