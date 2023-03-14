// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tecnico', {
	before_save(frm){
		let len = 0;
		frm.doc.almacenes_de_tecnico.forEach(e => {
			len = len + 1;
		});
		if (len > 2){
			throw "No puede insertar más de dos almacenes"
		}
	},
	after_save(frm){
		let condition = false;
		frm.doc.almacenes_de_tecnico.forEach(e => {
			if(e.almacen.toUpperCase().includes("USADO")){
				condition  = true;
			}
		});
		if(!condition){
			msgprint("El técnico debe tener una bodega de equipos usados");
		}
	}
});
