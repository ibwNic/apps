// frappe.listview_settings['Subscription'] = {
// 	get_indicator: function(doc) {
// 		if(doc.status === 'Trialling') {
// 			return [__("Trialling"), "green"];
// 		} else if(doc.status === 'Active') {
// 			return [__("Active"), "green"];
// 		} else if(doc.status === 'Completed') {
// 				return [__("Completed"), "green"];
// 		} else if(doc.status === 'Past Due Date') {
// 			return [__("Past Due Date"), "orange"];
// 		} else if(doc.status === 'Unpaid') {
// 			return [__("Unpaid"), "red"];
// 		} else if(doc.status === 'Cancelled') {
// 			return [__("Cancelled"), "gray"];
// 		}
// 	}
// };
frappe.listview_settings['Subscription'] = {
	// onload: function(listview) {	
	// 		frappe.route_options = {
	// 			"owner": ["like", "%jey%"]
	// 		};
	// },
	
	get_indicator: function(doc) {
		if(doc.workflow_state === 'Grabado') {
			return [__("Grabado"), "gray"];
		} else if(doc.workflow_state === 'Activo') {
			return [__("Activo"), "green"];
		} else if(doc.workflow_state === 'Suspendido') {
				return [__("Suspendido"), "orange"];
		} else if(doc.workflow_state === 'Terminado') {
			return [__("Terminado"), "red"];
		} else if(doc.workflow_state === 'Instalado') {
			return [__("Instalado"), "blue"];
		} 
	}
};
