// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cargos Automaticos', {
	refresh: function(frm) {
		console.log(frm.doc.docstatus)
		if (frm.doc.docstatus == 0){
			if (frm.doc.detalle){
				var det = frm.doc.detalle
				console.log(det)
				if (det.length > 0){
					frm.add_custom_button('Redireccionar Pagos al Batch', function(){
						if (frm.doc.no_recibo){
							var pm_args = {};
							pm_args.name = frm.doc.name
				
								// pm_args.Regnumber = frm.doc.name;
								// LLama la funcion de habilitar cliente
								frappe.call({
									'method': "erpnext.accounts.doctype.cargos_automaticos.cargos_automaticos.Redireccionar_pago",
									'args': pm_args
								});
						}else{
							frappe.msgprint('Debe de ingresar primero el numero de recibo');
						}
						
						
						
					});	
					
					frm.add_custom_button('Generar archivo BAC', function(){
						console.log("OK")
						var pm_args = {};
						pm_args.name = frm.doc.name
						console.log(pm_args)
						frappe.call({
							'args': pm_args,
							'method': "erpnext.accounts.doctype.cargos_automaticos.cargos_automaticos.Descargar_ArchivoBAC",
							// "type": "GET",
						// 	'callback': function(res){
						// 		// console.log(res.message.tex);
						// 		if(res){
									
						// 		}
								
						//   }
						});
						window.location.href = "https://ibwni-crm.ibw.com/api/method/erpnext.accounts.doctype.cargos_automaticos.cargos_automaticos.Descargar_ArchivoBAC?name=" + frm.doc.name
						// frm.reload_doc();
						
						
					});
				}

				
			}

			

			frm.add_custom_button('Generar Pagos Automaticos', function(){
				console.log("OK")
				var pm_args = {};
				pm_args.name = frm.doc.name
				console.log(pm_args)
				frappe.call({
					'args': pm_args,
					'method': "erpnext.accounts.doctype.cargos_automaticos.cargos_automaticos.Mostrar_cargo_aplicar",
					// "type": "GET",
				// 	'callback': function(res){
				// 		// console.log(res.message.tex);
				// 		if(res){
							
				// 		}
						
				//   }
				});
				// window.location.href = "https://ibwni-crm.ibw.com/api/method/erpnext.accounts.doctype.cargos_automaticos.cargos_automaticos.Mostrar_cargo_aplicar?name=" + frm.doc.name
				frm.reload_doc();
				
				
			});
		}
		
	},
	
	// after_save:function(frm) {
	// 	var tbldetalle = frm.doc.detalle
	// 	if ( tbldetalle.length > 0){
			
	// 	}
	// }
	

});

frappe.ui.form.on("Cargos Automaticos", "fecha", function(frm){
	console.log('Entra')
	if (frm.doc.tasa_de_cambio == 0 || frm.doc.tasa_de_cambio == null ){
		
		frappe.db.get_value("Currency Exchange", {"date": frm.doc.fecha},"paralela",function(res){
			console.log(res)
			frm.set_value('tasa_de_cambio',res.paralela)
		})
	}
});