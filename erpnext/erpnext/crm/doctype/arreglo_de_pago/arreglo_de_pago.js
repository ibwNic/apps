// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Arreglo de Pago', {
	refresh: function(frm) {
		cur_frm.cscript.AplicarNotaCredito = function(frm){		
			// console.log("Llega")
			frappe.route_options = {
				regnumber: cur_frm.doc.regnumber,
				cod_arreglo_pago: cur_frm.doc.name
			  };
		
			frappe.set_route('Form', 'Nota de Credito', 'new nota de credito');
		}

		if(frm.doc.requiere_nota_de_credito && frm.doc.tipo_de_arreglo === 'RECUPERACION'){
			frm.add_custom_button('Aplicar Nota de Credito', function(){
				cur_frm.cscript.AplicarNotaCredito(frm);
			});
		}

		if(frm.doc.tipo_de_arreglo == 'PAGO PARCIAL'){
			frm.toggle_display('seleccione_factura', true);
			frm.set_df_property('seleccione_factura', 'reqd', 1)
				// 	   frm.fields_dict.plans.grid.toggle_display("activar", false);
			
		}else{
			frm.toggle_display('seleccione_factura', false);
			frm.set_df_property('seleccione_factura', 'reqd', 0)
		}

		if(frm.doc.tipo_de_arreglo == 'RECUPERACION'){
			frm.toggle_display('requiere_nota_de_credito', true);
			frm.toggle_display('nota_de_credito', true);
				// 	   frm.fields_dict.plans.grid.toggle_display("activar", false);
			
		}else{
			frm.toggle_display('requiere_nota_de_credito', false);
			frm.toggle_display('nota_de_credito', false);
		}

		if (frm.doc.regnumber && frm.doc.tipo_de_arreglo == 'PAGO PARCIAL'){
			frm.set_query('seleccione_factura', function(d){
				return {
					filters: {
							'customer': frm.doc.regnumber
					}
				}
			})
		}

		if(frm.doc.fecha_de_vencimiento!=""){
			
			const hoy = new Date();

			function sumarDias(fecha, dias){
				fecha.setDate(fecha.getDate() + dias);
				return fecha;
			}
			// console.log(sumarDias(hoy, 15));

			const fec = sumarDias(hoy, 16)
			console.log(fec.toLocaleDateString('zh-Hans-CN'))
			
			frm.set_value("fecha_de_vencimiento",fec.toLocaleDateString('zh-Hans-CN'))
		}

		if(frm.doc.regnumber!=''){
			frm.add_custom_button('Crear Calendario de Pago', function(){
				frappe.call({
					"method": "erpnext.crm.doctype.arreglo_de_pago.arreglo_de_pago.generar_calendario",
					"args": {
					"name": frm.doc.name
						}
				}).then(r =>{
						//  frm.doc.refresh()
						 frm.refresh()
						})
			});
		}
	}
});

frappe.ui.form.on("Arreglo de Pago", "regnumber", function(frm){
	frappe.call({
		"method": "erpnext.crm.doctype.arreglo_de_pago.arreglo_de_pago.get_facturas",
		"args": {
		"regnumber": frm.doc.regnumber
			}
	}).then(r =>{
			 let values = r.message;
				frm.set_value("cantidad_de_facturas", values[0][0]);
				frm.set_value("saldo_total", values[0][1]);
			})
});

frappe.ui.form.on("Arreglo de Pago", "tipo_de_arreglo", function(frm){
	if(frm.doc.tipo_de_arreglo != "RECUPERACION"){
		cur_frm.set_df_property('requiere_nota_de_credito','read_only',1);
	} else {
		cur_frm.set_df_property('requiere_nota_de_credito','read_only',0);
	}
});