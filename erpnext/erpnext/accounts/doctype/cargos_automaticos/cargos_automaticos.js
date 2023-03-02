// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cargos Automaticos', {
	refresh: function(frm) {
		frappe.ui.form.on("Cargos Automaticos", "fecha", function(frm){
			if (frm.doc.tasa_de_cambio == null){
				frappe.db.get_value("Currency Exchange", {"date": frm.doc.fecha},"paralela",function(res){
					frm.set_value('tasa_de_cambio',res.paralela)
				})
			}
		});
	}
});
