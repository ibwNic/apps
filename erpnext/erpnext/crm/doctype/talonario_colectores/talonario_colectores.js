// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Talonario Colectores', {
	refresh: function(frm) {
			frm.set_query('colector', function(d){
				return {
					filters: {
						collector_type:'Colector'
					}
				}
		})
}})
