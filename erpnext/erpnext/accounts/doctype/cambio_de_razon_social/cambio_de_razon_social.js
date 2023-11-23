// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cambio de Razon Social', {
	refresh: function(frm) {
		frappe.call({
			"method": "erpnext.accounts.doctype.subscription_update.subscription_update.filtrar_gestiones",})
			.then(r=>{
						frm.set_query('gestion', function(d){
				
							return {
								filters: {
									customer: frm.doc.cliente,
									name: ["not in", r.message],
									workflow_state:'Escalado'
								}
							}
						})
				})
	}
});
