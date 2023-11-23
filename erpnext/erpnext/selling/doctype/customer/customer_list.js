frappe.listview_settings['Customer'] = {

	add_fields: ["customer_name", "estado_cliente", "cedula","portafolio", "customer_group"],


	get_indicator: function(doc) {
		console.log(doc.estado_cliente)
		if(doc.estado_cliente === 'NUEVO') {
			//console.log("entra")
			return [__("NUEVO"), "gray"];
		} else if(doc.estado_cliente === 'ACTIVO') {
			return [__("ACTIVO"), "green"];
		} else if(doc.estado_cliente === 'SUSPENDIDO') {
			return [__("SUSPENDIDO"), "orange"];
		} else if(doc.estado_cliente === 'SUSPENDIDO (Manual)') {
			return [__("SUSPENDIDO (Manual)"), "orange"];
		} else if(doc.estado_cliente === 'SUSPENDIDO (Temporal)') {
			return [__("SUSPENDIDO (Temporal)"), "orange"];
		} else if(doc.estado_cliente === 'TERMINADO') {
			return [__("TERMINADO"), "red"];
		}
	}
};
