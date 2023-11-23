// Copyright (c) 2023, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Aprovisionamiento IPTv', {
	refresh: function(frm) {
		if (frm.doc.estado == "Inactivo"){
			frm.add_custom_button('Registrar Cliente', function(){
				var mac = frm.doc.dispositivos
				if (mac.length > 0){
					var pm_args = {};

					pm_args.Regnumber = frm.doc.name;
					// LLama la funcion de habilitar cliente
					frappe.call({
						'method': "frappe.custom.doctype.aprovisionamiento_iptv.aprovisionamiento_iptv.Registrar_Cliente",
						'args': pm_args,
						'callback': function (r) {
							console.log(r.message)
							if (r.message) {
								var res = r.message.messages;
								frappe.msgprint({
									title: __('Advertencia'),
									// indicator: 'Red',
									message: __(res.join("<br/>"))
								});
								frm.reload_doc();
							}
						}
					});
				}else{
					frappe.msgprint({
						title: __('Advertencia'),
						// indicator: 'Red',
						message: __("Debe de ingresar al menos un dispositivo")
					});
				}
			});
		}
		
		if (frm.doc.estado == "Activo" || frm.doc.estado == "Suspendido"){
			frm.add_custom_button('Eliminar Cliente', function(){
				var pm_args = {};
	
				pm_args.Regnumber = frm.doc.name;
				// LLama la funcion de habilitar cliente
				frappe.call({
					'method': "frappe.custom.doctype.aprovisionamiento_iptv.aprovisionamiento_iptv.Eliminar_Cliente",
					'args': pm_args,
					'callback': function (r) {
						console.log(r.message)
						if (r.message) {
							var res = r.message.messages;
							frappe.msgprint({
								title: __('Advertencia'),
								// indicator: 'Red',
								message: __(res.join("<br/>"))
							});
							frm.reload_doc();
						}
					}
				});
			});
		}

		if (frm.doc.estado == "Activo"){
			frm.add_custom_button('Suspender', function(){
				var pm_args = {};
	
				pm_args.Regnumber = frm.doc.name;
				// LLama la funcion de habilitar cliente
				frappe.call({
					'method': "frappe.custom.doctype.aprovisionamiento_iptv.aprovisionamiento_iptv.Deshabilitar_Cliente",
					'args': pm_args,
					'callback': function (r) {
						console.log(r.message)
						if (r.message) {
							var res = r.message.messages;
							frappe.msgprint({
								title: __('Advertencia'),
								// indicator: 'Red',
								message: __(res.join("<br/>"))
							});
							frm.reload_doc();
						}
					}
				});
			});
			
		}

		if (frm.doc.estado == "Suspendido"){
			frm.add_custom_button('Activar', function(){
				var pm_args = {};
	
				pm_args.Regnumber = frm.doc.name;
				// LLama la funcion de habilitar cliente
				frappe.call({
					'method': "frappe.custom.doctype.aprovisionamiento_iptv.aprovisionamiento_iptv.Habilitar_Cliente",
					'args': pm_args,
					'callback': function (r) {
						console.log(r.message)
						if (r.message) {
							var res = r.message.messages;
							frappe.msgprint({
								title: __('Advertencia'),
								// indicator: 'Red',
								message: __(res.join("<br/>"))
							});
							frm.reload_doc();
						}
					}
				});
			});
			
		}
	}
});


// frappe.ui.form.on("Aprovisionamiento IPTv", "estado", function(frm){
// 	console.log("Entra")
// 	// if (frm.doc.estado == 'Activo'){
// 	// 	var pm_args = {};

// 	// 	pm_args.Regnumber = frm.doc.identificador;
// 	// 	// LLama la funcion de habilitar cliente
// 	// 	frappe.call({
// 	// 		'method': "frappe.custom.doctype.aprovisionamiento_iptv.aprovisionamiento_iptv.Habilitar_Cliente",
// 	// 		'args': pm_args,
// 	// 		'callback': function (r) {
// 	// 			console.log(r.message)
// 	// 			if (r.message) {
// 	// 				var res = r.message.messages;
// 	// 				frappe.msgprint({
// 	// 					title: __('Advertencia'),
// 	// 					// indicator: 'Red',
// 	// 					message: __(res.join("<br/>"))
// 	// 				});
// 	// 			}
// 	// 		}
// 	// 	});
// 	// }
// 	// if (frm.doc.estado == 'Suspendido'){
// 	// 	var pm_args = {};

// 	// 	pm_args.Regnumber = frm.doc.identificador;
// 	// 	// LLama la funcion de habilitar cliente
// 	// 	frappe.call({
// 	// 		'method': "frappe.custom.doctype.aprovisionamiento_iptv.aprovisionamiento_iptv.Deshabilitar_Cliente",
// 	// 		'args': pm_args,
// 	// 		'callback': function (r) {
// 	// 			console.log(r.message)
// 	// 			if (r.message) {
// 	// 				var res = r.message.messages;
// 	// 				frappe.msgprint({
// 	// 					title: __('Advertencia'),
// 	// 					// indicator: 'Red',
// 	// 					message: __(res.messages.join("<br/>"))
// 	// 				});
// 	// 			}
// 	// 		}
// 	// 	});
// 	// }
// });