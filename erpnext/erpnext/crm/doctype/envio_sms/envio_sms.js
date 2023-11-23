// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Envio SMS', {
	refresh: function(frm) {
		frm.fields_dict.portafolios.grid.get_field("portafolios").get_query = function(doc, cdt, cdn){
			return {
				filters: {
					item_group: ["in", ['Corporativo','PYME','Residencial']]
				}
			}
		}

		frm.set_query('departamento', function(d){
			return {
				filters: {
					 tipo_territorio: "Departamento"
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
					 tipo_territorio: "barrio"
				}
			}
		})

		if (frm.doc.docstatus === 0){
			if (frm.doc.numeros.length > 0) {
				frm.add_custom_button('Realizar Envio SMS', function(){
					frappe.call({
						'method': "erpnext.crm.doctype.envio_sms.envio_sms.enviar_mensajes_cobro",
						'args': {
							'name':frm.doc.name
						}, 
						freeze: true,
						freeze_message: "Realizando envio de SMS, por favor espere ...",
						'callback': function (r) {
							console.log(r.message)
							if (r.message === 'OK'){
								frappe.show_alert({
									message:__('Envio de SMS Realizados'),
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
					'method': "erpnext.crm.doctype.envio_sms.envio_sms.generar_vista_previa",
					'args': {
						'name':frm.doc.name
					}, 
					freeze: true,
					freeze_message: "Generando vista previa, por favor espere ...",
					'callback': function (r) {
						console.log(r.message)
						if (r.message === 'OK'){
							frappe.show_alert({
								message:__('Vista Previa Generada'),
								indicator:'green'
							}, 10);
							frm.reload_doc();
						}
					}
				});
            });
			if(frm.doc.tipo_sms==="Factura Emitida"){};
			frm.add_custom_button('Generar Archivos', function(){
				frappe.call({
					'method': "erpnext.crm.doctype.envio_sms.envio_sms.generar_archivos",
					'args': {
						'name':frm.doc.name
					}, 
					freeze: true,
					freeze_message: "Generando archivos, por favor espere ...",
					'callback': function (r) {
						console.log(r.message)
						if (r.message === 'OK'){
							frappe.show_alert({
								message:__('Archivos generados'),
								indicator:'green'
							}, 10);
							frm.reload_doc();
						}
					}
				});
			});
		}
	}, before_load(frm){
		if(frm.doc.total_sms==="Verificando..."){
			frappe.call({
				"method": "erpnext.crm.doctype.envio_sms.envio_sms.verificar_sms",
				"args": {
					"name": frm.doc.name,
				}
			}).then(r =>{
				var resp=r.message
				console.log(resp)
				frm.set_value('total_sms', resp)
			});
		}
	},after_save(frm) {
		frappe.call({
			"method": "erpnext.crm.doctype.envio_sms.envio_sms.obtener_exclusiones_sms",
			"args": {
				"name": frm.doc.name,
			}, freeze: true,
			callback: function(r){
				console.log(r.message)
				frm.reload_doc();
			}
		});
	}
});

frappe.ui.form.on("Envio SMS", "tipo_sms", function(frm){
	frappe.db.get_value("Formato SMS", {"tipo_sms": frm.doc.tipo_sms},"formato_sms",function(res){
		frm.set_value('preview_sms',res.formato_sms)
	})
	frappe.db.get_value("Formato SMS", {"tipo_sms": frm.doc.tipo_sms},"sms_predeterminado",function(res){
		frm.set_value('preset_sms',res.sms_predeterminado)
	})
});
