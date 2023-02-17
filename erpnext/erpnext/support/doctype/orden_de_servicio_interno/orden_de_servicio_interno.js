// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Orden de Servicio Interno', {
	refresh: function(frm) {
		if(frm.doc.workflow_state !== 'Abierto'){
			frm.set_df_property('fecha_inicio', 'read_only', true);
		}
		let tecnico ='';	 
		 if (frm.doc.tecnico === undefined) {
		     tecnico = 'random'}
	     else{
	         tecnico = frm.doc.tecnico
	     }
	     frappe.call({
        		"method": "erpnext.support.doctype.service_order.service_order.filtrar_productos_disponibles", "args":{"tecnico":tecnico},
        		 callback: function(r) {
        		     //console.log(r.message)
        		       frm.fields_dict.materiales_detalles.grid.get_field("material").get_query = function(doc, cdt, cdn){
                			return {
                				filters: {
                					item_code:["in", r.message]  
                				}
                			}
                		}
                	}
		        });
		if(frm.doc.tipo_de_orden !== 'INSTALACIÓN DE NODO'){
			frm.toggle_display("nodo", false);
		}
		else{
			frm.toggle_display("nodo", true);
		}

		if(frm.doc.tipo_de_orden == "GESTIÓN ADMINISTRATIVA")
		{
		  set_field_options("gestion", ["RETIRO DE MATERIALES/EQUIPOS","RETIRO DE ENCOMIENDAS","TRASLADO DE PERSONAL",
										"APOYO A INGENIERÍA","APOYO A VTA. DE EQUIPOS","APOYO AL TALLER","GESTION DE PAGO"])
		}
		else if(frm.doc.tipo_de_orden == "MANTENIMIENTO INTERNO")
		{
			set_field_options("gestion", ["AIRE ACONDICIONADO","PINTURA","SEGURIDAD","NOC","ELÉCTRICO","REPARACIÓN TECHO/PARED"])
		}
		else if(frm.doc.tipo_de_orden == "VENTANA DE MANTENIMIENTO")
		{
			set_field_options("gestion", ["SERVICIOS FIBRA", "SERVICIOS GPON", "SERVICIOS HFC", "DIALUP/EMAIL", "EQUIPOS", "IMOVIL", "PUNTO A PUNTO", "PUNTO MULTIPUNTO", "LTE", "IPTV"])
		}
		else if(frm.doc.tipo_de_orden == "INSTALACIÓN DE NODO"){
			set_field_options("gestion", ["GPON INT RESIDENCIAL","GPON TV RESIDENCIAL","GPON CORPORATIVO","GPON TV CORPORATIVO","GPON INT PYME","GPON TV PYME","HFC","PUNTO A PUNTO", "PUNTO MULTIPUNTO"])
			
		}
		else{
			set_field_options("gestion", [" "])
		}

		frm.set_query('departamento', function(d){
			return {
				filters: {
					 tipo_territorio: "Departamento",
					 name: ["not in", ["Nicaragua"]]
				}
			}
		})
				frm.set_query('municipio', function(d){
			return {
				filters: {
					 tipo_territorio: "Municipio"
				}
			}
		})
			frm.set_query('barrio', function(d){
			return {
				filters: {
					 tipo_territorio: "Barrio"
				}
			}
		})
	}
});
frappe.ui.form.on("Orden de Servicio Interno", "tipo_de_orden", function(frm) {
	if(frm.doc.tipo_de_orden !== 'INSTALACIÓN DE NODO'){
		frm.toggle_display("nodo", false);
	}
	else{
		frm.toggle_display("nodo", true);
	}
	if(frm.doc.tipo_de_orden == "GESTIÓN ADMINISTRATIVA")
	{
	  set_field_options("gestion", ["RETIRO DE MATERIALES/EQUIPOS","RETIRO DE ENCOMIENDAS","TRASLADO DE PERSONAL",
									"APOYO A INGENIERÍA","APOYO A VTA. DE EQUIPOS","APOYO AL TALLER","GESTION DE PAGO"])
	}
	else if(frm.doc.tipo_de_orden == "MANTENIMIENTO INTERNO")
	{
		set_field_options("gestion", ["AIRE ACONDICIONADO","PINTURA","SEGURIDAD","NOC","ELÉCTRICO","REPARACIÓN TECHO/PARED"])
	}
	else if(frm.doc.tipo_de_orden == "VENTANA DE MANTENIMIENTO")
	{
		set_field_options("gestion", ["SERVICIOS FIBRA", "SERVICIOS GPON", "SERVICIOS HFC", "DIALUP/EMAIL", "EQUIPOS", "IMOVIL", "PUNTO A PUNTO", "PUNTO MULTIPUNTO", "LTE", "IPTV"])
	}
	else if(frm.doc.tipo_de_orden == "INSTALACIÓN DE NODO"){
		set_field_options("gestion", ["GPON INT RESIDENCIAL","GPON TV RESIDENCIAL","GPON CORPORATIVO","GPON TV CORPORATIVO","GPON INT PYME","GPON TV PYME","HFC","PUNTO A PUNTO", "PUNTO MULTIPUNTO"])
	}
	else{
		set_field_options("gestion", [" "])
	}
});

frappe.ui.form.on("Orden de Servicio Interno", "departamento", function(frm) {
	frm.set_query('municipio', function(d){
	return {
		filters: {
			tipo_territorio: "Municipio",
			 "parent_territory": frm.doc.departamento,
		}
	}
})

});

frappe.ui.form.on("Orden de Servicio Interno", "municipio", function(frm) {
frm.set_query('barrio', function(d){
	return {
		filters: {
			tipo_territorio: "Barrio",
		   "parent_territory": frm.doc.municipio
		}
	}
})
});