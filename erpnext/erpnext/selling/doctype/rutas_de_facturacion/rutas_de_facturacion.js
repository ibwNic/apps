// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Rutas de Facturacion', {
	refresh: function(frm) {
		
	// 	frappe.call({
	// 	"method": "erpnext.selling.doctype.rutas_de_facturacion.rutas_de_facturacion.get_barrios", callback: function(r) {

    // }})

	frm.set_query('territory', function(d){
		return {
			filters: {
				 tipo_territorio: ["in",["Departamento","Municipio"]]
			}
		}
	})
	if(frm.doc.territory !== undefined){
		frm.fields_dict.barrios.grid.get_field("barrios").get_query = function(doc, cdt, cdn){
			return {
				filters: {
					'tipo_territorio':"Barrio",
					'parent_territory': ["like","%"+frm.doc.territory+"%"]
				}
			}
		}
	}

	}
});

frappe.ui.form.on("Barrios y Rutas", {
form_render: function(frm, cdt, cdn){
	let row = frappe.get_doc(cdt,cdn);
	console.log(row.barrios)
	if(row.barrios == 'Nicaragua'){
		frappe.model.set_value(cdt, cdn, "barrios", null);
	}
},})