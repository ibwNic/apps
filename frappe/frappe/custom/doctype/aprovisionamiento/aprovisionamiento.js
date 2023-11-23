// Copyright (c) 2022, Frappe Technologies and contributors
// For license information, please see license.txt
// console.log(frm.doc.name)	

frappe.ui.form.on('Aprovisionamiento', {
	refresh: function(frm) {

		if(frm.doc.provisor === ""){
			frm.add_custom_button(__('Gpon'), function(){
				
				let x = frappe.call({
					"method": "frappe.custom.doctype.aprovisionamiento.aprovisionamiento.vlan_masivo",
					"args":{
						'equipo': frm.doc.name
						},
					"async": false, 
					callback: function(r){	
						console.log(r.message)	
					}
					})
				
				console.log(x.responseJSON.message)	
				if (x.responseJSON.message){
					let result = x.responseJSON.message
					let opciones = []
					let values = []
					for(let i = 0; i < result.length; i++){
						opciones.push(result[i][0]);
						values.push(result[i][1]);
					}
				var d = new frappe.ui.Dialog({
					title: __("Selecione la Vlan"),
					fields: [											
						{"fieldname":"Vlan", "fieldtype":"Select", "label":__("Vlan"), "options":[opciones], "reqd": "1"},
						
						{"fieldname":"Velocidad", "fieldtype":"Select", "label":__("Velocidad"), "options":['30M','40M','50M'], "reqd": "1"},
						{"fieldname":"fetch", "label":__("Aprovisonar Equipo"), "fieldtype":"Button"}
					]
				});
				d.get_input("fetch").on("click", function() {
					var argumentos = d.get_values();
					argumentos["id"] = values[opciones.indexOf(argumentos["Vlan"])];
					argumentos["mac"] = frm.doc.name;
					if(!argumentos) return;
					console.log(argumentos)
					// frappe.call({
					// 	method: "frappe.custom.doctype.aprovisionamiento.aprovisionamiento.obtener_script",
					// 	args: argumentos,
					// 	callback: function(r) {
					// 		console.log(r.message)
								

					// 	}
					// });
				});
				d.show();
			}
	
			});
		}


		if (frm.doc.provisor === "Hfc" && frm.doc.provisor_speed_id){
			
				frappe.call({		
						
					method: "frappe.custom.doctype.aprovisionamiento.aprovisionamiento.velocidad_hfc",
					args: {"provisor_speed_id":frm.doc.provisor_speed_id},
					callback: function(r) {
						frm.set_value("velocidad", r.message[0])
						frm.set_value("cmts", r.message[1])
					}
			   });
		
		}
	}
});
frappe.ui.form.on("Aprovisionamiento", "activacion_forzosa", function(frm) {
	if(frm.doc.activacion_forzosa){
		frm.set_value("fecha_activacion_forzosa", frappe.datetime.now_datetime())
	}
	else{
		frm.set_value("fecha_activacion_forzosa", null)

	}
});
