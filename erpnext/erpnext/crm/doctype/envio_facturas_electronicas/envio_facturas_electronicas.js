// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Envio Facturas Electronicas', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 0){
			if  (frm.doc.envios.length > 0) {
				frm.add_custom_button('Realizar Envio Correos', function(){
					frappe.call({
						'method': "erpnext.crm.doctype.envio_facturas_electronicas.envio_facturas_electronicas.enviar_facturas",
						'args': {
							'name':frm.doc.name
						}, 
						freeze: true,
						freeze_message: "Enviando Facturas Electronicas, por favor espere ...",
						'callback': function (r) {
							console.log(r.message)
							if (r.message === 'OK'){
								frappe.show_alert({
									message:__('Numeros Generados'),
									indicator:'green'
								}, 10);
								frm.reload_doc();
							}
						}
					});
				});
			}
			
			frm.add_custom_button('Generar Vista Previa', function(){
                frappe.call({
					'method': "erpnext.crm.doctype.envio_facturas_electronicas.envio_facturas_electronicas.generar_vista_previa",
					'args': {
						'name':frm.doc.name
					}, 
					freeze: true,
					freeze_message: "Generando vista previa, por favor espere ...",
					'callback': function (r) {
						console.log(r.message)
						if (r.message === 'OK'){
							frappe.show_alert({
								message:__('Vista previa generada'),
								indicator:'green'
							}, 10);
							frm.reload_doc();
						}
					}
				});
            });
		}
	}
});
