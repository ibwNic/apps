// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salida de Bodega ERP', {
	refresh: function(frm) {
		if(!frm.doc.__islocal){
			frm.add_custom_button(__('Generar Vista Previa'), function(){
				frappe.call({
					"method": "erpnext.stock.doctype.salida_de_bodega_erp.salida_de_bodega_erp.generar_vista_previa",
					"args": {
						"name": frm.doc.name,
					},
					freeze: true,
					callback: function(r){
						console.log(r.message)
						frm.reload_doc();
					}
				})
			});
		}
	}
});
