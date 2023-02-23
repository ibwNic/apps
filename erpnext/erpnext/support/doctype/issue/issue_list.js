frappe.listview_settings['Issue'] = {
	colwidths: {"subject": 6},
	add_fields: ['priority'],
	filters: [["status", "=", "Open"]],
	onload: function(listview) {
		var method = "erpnext.support.doctype.issue.issue.set_multiple_status";

		listview.page.add_action_item(__("Set as Open"), function() {
			listview.call_for_selected_items(method, {"status": "Open"});
		});

		listview.page.add_action_item(__("Set as Closed"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});
		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol",
				callback: function(r){			
					if(r.message.includes("O&M")){
                        
                        frappe.call({
                            "method": "erpnext.support.doctype.service_order.service_order.filtrar_ordenes_OyM",
                                callback: function(r){	
                                    if(r.message){
                                        localStorage.removeItem("tecnico")
                                        localStorage.setItem("tecnico",r.message)
                                        msgprint("Filtros aplicados para " + localStorage.getItem("tecnico"))
                                    }                           
                            }
                        });
					}
                    else{
                        localStorage.removeItem("tecnico")
                    } 
				
			}
		});
        if(localStorage.getItem("tecnico")){
            frappe.route_options = {
                'tecnico': ['=', localStorage.getItem("tecnico")]
            };
        }
	},
	get_indicator: function(doc) {
		if (doc.status === 'Open') {
			const color = {
				'Low': 'yellow',
				'Medium': 'orange',
				'High': 'red'
			};
			return [__(doc.status), color[doc.priority] || 'red', `status,=,Open`];
		} else if (doc.status === 'Closed') {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else {
			return [__(doc.status), "gray", "status,=," + doc.status];
		}
	}
}
