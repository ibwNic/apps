// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bitacora de Planes', {
	refresh: function(frm) {

		var userRoles = frappe.boot.user.roles;
		console.log(userRoles)


		if((!userRoles.includes("Cobranza") && !userRoles.includes("Back Office") ) || userRoles.includes("Departamentos" )){
			frappe.db.get_value("Customer", {"name": frm.doc.cliente},"customer_group",function(res){ 
				res.customer_group; }).then(r =>{ var rest=r.message; 
				if(rest.customer_group!="Individual"){
					frm.toggle_display("costo", false);
				}
			})
		}

	}
});


