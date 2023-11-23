frappe.listview_settings["Orden de Servicio Interno"] = {
	onload: function(listview) {
        frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol",
				callback: function(r){			
					if(r.message.includes("O&M")){
                        
                        frappe.call({
                            "method": "erpnext.support.doctype.service_order.service_order.filtrar_ordenes_OyM",
                                callback: function(r){	
                                    if(r.message !== undefined){
                                        console.log(r.message)
                                        localStorage.removeItem("tecnico")
                                        localStorage.setItem("tecnico",r.message)
                                       // msgprint("Filtros aplicados para " + localStorage.getItem("tecnico"))
                                    } 
                                    else{
                                        localStorage.removeItem("tecnico")
                                    }                          
                            }
                        });
					}
                    else{
                        localStorage.removeItem("tecnico")
                    } 
				
			}
		});      
	},
};