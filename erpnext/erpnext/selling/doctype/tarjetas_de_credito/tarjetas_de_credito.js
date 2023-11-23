// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tarjetas de Credito', {
	refresh: function(frm) {
		frappe.ui.form.on("Tarjetas de Credito", "cliente", function(frm){
			if (frm.doc.tasa_de_cambio == null){
				// Tasa de CAmbio a la paralela, con depende a la fecha de deposito.
				frappe.db.get_value("Customer", {"name": frm.doc.cliente},"customer_name",function(res){
					// res.customer_name;
					// console.log(res.customer);
					frm.set_value('nombre',res.customer_name)
					// d.set_value("customer", res.customer);
				})
			}
		});

		frappe.ui.form.on("Tarjetas de Credito", "cliente", function(frm){
			if (frm.doc.tasa_de_cambio == null){
				// Tasa de CAmbio a la paralela, con depende a la fecha de deposito.
				frappe.db.get_value("Customer", {"name": frm.doc.cliente},"customer_group",function(res){
					// res.customer_name;
					// console.log(res.customer);
					frm.set_value('tipo_de_cliente',res.customer_group)
					// d.set_value("customer", res.customer);
				})
			}
		});
	}
});
