// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Rutas de Facturacion', {
	refresh: function(frm) {
		
		frappe.call({
		"method": "erpnext.selling.doctype.rutas_de_facturacion.rutas_de_facturacion.get_barrios", callback: function(r) {

    }})

	}
});
