// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Finalizacion de Planes Suspendidos', {
	refresh: function(frm) {

		if(frm.doc.detalle_de_planes && frm.doc.docstatus == 0){
			frm.add_custom_button(__('Obtener estado de planes'), function(){
				frappe.call({
					"method": "erpnext.accounts.doctype.finalizacion_de_planes_suspendidos.finalizacion_de_planes_suspendidos.obtener_estado_de_planes",
					"args": {
						"name": frm.doc.name
					},
					freeze: true,
					callback: function(r){
						frm.reload_doc();
					}
				})
	
			});
		}

	}
});
