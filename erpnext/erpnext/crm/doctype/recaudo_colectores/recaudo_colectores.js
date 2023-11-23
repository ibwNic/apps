// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Recaudo colectores', {
	refresh: function(frm) {
		if (frm.doc.colector == null){
			var user = frappe.session.user;
			console.log(user)
			frappe.db.get_value("Colectores", {"email": user},"name",function(res){
				console.log(res)
				frm.set_value('colector',res.name)
			})
		}

		if (frm.doc.fecha){
			frappe.db.get_value("Currency Exchange", {"date": frm.doc.fecha},"paralela",function(res){
				console.log(res.paralela)
				frm.set_value('tc',res.paralela)
			})
		}

		// if (frm.doc.fecha == null){
		// 	const hoy = new Date();
		// 	frm.set_value("fecha",hoy.toLocaleDateString('zh-Hans-CN'))
		// 	frm.set_df_property('fecha', 'read_only', 1)
		// }

		cur_frm.cscript.AgragarPago = function(frm){
			// console.log(frm.doc.cliente);
			function Crear_PagoBatch(pm_args,values){
				[
					['customer', 'regnumber'],
					['sales_invoice', 'factura'],
					['conversion_rate', 'tc'],
					['posting_date', 'fecha']
				].forEach(function(pair){
					var v = values[pair[0]];
					if (v) pm_args[pair[1]] = v;
				});
				console.log(pm_args)
				console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					// AQUI
				frappe.call({
					'method': "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.agregar_pago",
					'args': pm_args,
					'callback': function (r) {
						// console.log(r.message)
							if (r.message) {
								// console.log(r.message)
								if(r.message === 'Ok'){
									frappe.show_alert({
										message:__('Se agrego pago.'),
										indicator:'green'
									}, 5);
									frm.reload_doc();
								}else{
									frappe.msgprint({
										title: __('Advertencia'),
										indicator: 'Red',
										message: __('ERROR')
									});
								}
						}
					}
				});
				
			}
		
			function toggle_action(fields, wrapper){
				fields.forEach(function(df){
					df.$input.on('change', function(){
						if (!wrapper.find("#action").hasClass("hidden")){
							wrapper.find('#action').addClass('hidden');
						}
		
						for(var i = 0, l = fields.length; i<l; i++){
							if (!fields[i].get_value()) return;
						}
						wrapper.find('#action').removeClass('hidden');
					});
				});
			}
		
			var d,
			Talonario,
				ignore_event = false,
				TotalesUSD = 0,
				TotalesNIO = 0,
				montosC$ = [],
				montosUSD = [],
				FacturaYMonto = [],
				montos = [],
				payments = [],
				facturaSelect = [],
				payments2 = [],
				totals = [],
				fields = {},
				result= [],
				tc = [],
				series = {
					"leyda.calderon@ibw.com": "F-",
					"hegarcia@ibw.com": "I-"
				},
				pm_args = {};
		
		
		
			function set_sum_Totales_Anticipos(data){
				console.log(data['total_FacturaUSD']);
				var amounts = {'TotalNIO': 0.0, 'TotalUSD': 0.0};
		
				amounts.TotalNIO += data['Total_FacturaNIO'];
				amounts.TotalUSD += data['total_FacturaUSD'] ;
		
				montos.push(amounts.TotalNIO);
				montos.push(amounts.TotalUSD);
				console.log(montos);
				// render_totals_table();
				// SumaFormaPagos();
			}
		
			function TituloName(name){
				d.fields_dict.TituloName.$wrapper.find("#Nombre").text(name);
			}
		
				function assign_df_to_input(df){
					df.refresh();
					df.$input.data('df', df);
				}
		
				function get_exchange() {
					frappe.call({
						'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.get_divisa',
						'args':{
							'from_currency':"USD",
							'to_currency': "NIO"
						},
						'callback': function(res){
							console.log(res.message);
							d.set_value("conversion_rate",res.message);
							tc.push(res.message);
						}
					})
				}
		
				d = new frappe.ui.Dialog({
					title: __("Agregar Pago"),
					fields: [
						{
							fieldtype: "HTML",
							fieldname: "TituloName",
							options: `<div class="row">
								<div class="col-sm-12 col-md-12 col-lg-12 col-xl-12 text-center">
									<h3 id="Nombre"> </h3>
								</div>
							</div>`
						},
						{
							fieldtype: "Section Break"
						},
						{
							fieldtype: "Float",
							fieldname: "conversion_rate",
							precision: 4,
							label: "TC",
							read_only: 1,
							on_make: assign_df_to_input,
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						{
							fieldtype: "Date",
							label: "Fecha",
							// default: frappe.datetime.get_today(),
							fieldname: "posting_date",
							read_only: 1,
							on_make: assign_df_to_input
							// change: get_outstanding_details
						},
						{
							fieldtype: "Section Break"
						},
						{
							fieldtype: "Link",
							label: "Cliente",
							options: "Customer",
							fieldname: "customer",
							reqd: 1,
							on_make: assign_df_to_input,
							change:  function(){
									if(d.get_value('customer')){
										// get_outstanding_details();
										// TituloName(res.message.cliente.nombre);
										frappe.db.get_value('Customer', d.get_value('customer'), 'customer_name').then(r => {
											let values = r.message;
											TituloName(values.customer_name);
										})
									}
								},
							// on_make: d.get_value('customer').refresh(),
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						{
							fieldtype: "Link",
							label: "Factura",
							options: "Sales Invoice",
							fieldname: "sales_invoice",
							reqd: 1,
							on_make: assign_df_to_input,
							change:  function(){
									frappe.db.get_value("Sales Invoice", {"name": d.get_value("sales_invoice")},"customer",function(res){
										res.customer;
										console.log(res.customer);
										d.set_value("customer", res.customer);
									})

									frappe.call({
										'method': "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.montos_facturas",
										'args': {'name':d.get_value("sales_invoice"),'parent':frm.doc.name},
										'callback': function (r) {
											console.log(r.message)
											console.log(r.message)
												if (r.message) {
													d.set_value("montoFactNIO", r.message[0]);
													d.set_value("montoFactUSD", r.message[1]);
											}
										}
									});

									frappe.call({
										'method': "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.numero_notalario",
										'callback': function (r) {
											console.log(r.message)
											var numero_de_recibo_actual = r.message['numero_de_recibo_actual'];
											var fin = r.message['fin'];
											if (Number(numero_de_recibo_actual) > Number(fin) ){
												frappe.msgprint({
													title: __('Advertencia'),
													indicator: 'green',
													message: __("Ya llego a su numero maximo de recibos")
												});
												// d.set_value("sales_invoice", null);
												d.set_value("Recibo", null);
									
											}else{
												Talonario = r.message['name']
												d.set_value("Recibo", r.message['numero_de_recibo_actual']);
											}
											
										}
									})
							}
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Float",
							label: "Monto Pendiente C$",
							fieldname: "montoFactNIO",
							// reqd: 1,
							precision:2,
							read_only: 1,
							on_make: assign_df_to_input
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						{
							fieldtype: "Float",
							label: "Monto Pediente $",
							fieldname: "montoFactUSD",
							// reqd: 1,
							precision:2,
							read_only: 1,
							on_make: assign_df_to_input
							// change: get_outstanding_details
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Data",
							label: "N° Recibo",
							// options: 'Account',
							fieldname: "Recibo",
							reqd: 1,
							read_only: 1
						},
						// {
						// 	fieldtype: "Column Break"
						// },
						// {
						// 	fieldtype: "Link",
						// 	label: "Colector",
						// 	options: "Colectores",
						// 	fieldname: "Colector",
						// 	reqd: 1,
						// 	read_only: 1
						// },
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Check",
							label: "Cheque",
							default: false,
							fieldname: "cheque",
							// read_only: 1,
							on_make: assign_df_to_input,
							change: function(){
								console.log(d.get_value('cheque'))
								if (d.get_value('cheque') === 1){
									console.log('ok')
									d.set_df_property('Num_cheque', 'hidden', 0);
									// d.set_df_property('Fecha_Cheque', 'hidden',0);
									d.set_df_property('nombre_banco', 'hidden', 0);
								}
								else{
									d.set_df_property('Num_cheque', 'hidden', 1);
									// d.set_df_property('Fecha_Cheque', 'hidden',1);
									d.set_df_property('nombre_banco', 'hidden', 1);
								}
							}
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Data",
							label: "N° Cheque",
							default: false,
							fieldname: "Num_cheque",
							// read_only: 1,
							// hidden:1,
							on_make: assign_df_to_input
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						// {
						// 	fieldtype: "Date",
						// 	label: "Fecha de Referencia",
						// 	fieldname: "Fecha_Cheque",
						// 	// hidden:1,
						// 	// reqd: 1,
						// 	// precision:2,
						// 	// read_only: 1,
						// 	on_make: assign_df_to_input
						// 	// change: get_outstanding_details
						// },
						// {
						// 	fieldtype: "Column Break"
						// 	// fieldtype: "Section Break",
						// 	// label: __("Total")
						// },
						{
							fieldtype: "Select",
							label: "Nombre del Banco",
							fieldname: "nombre_banco",
							options:['BAC','BDF','BANCENTRO','AVANZ','FICOHSA','BCN'],
							// reqd: 1,
							// precision:2,
							// read_only: 1,
							on_make: assign_df_to_input
							// change: get_outstanding_details
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Float",
							label: "Monto C$",
							fieldname: "montoNIO",
							// reqd: 1,
							precision:2,
							// read_only: 1,
							on_make: assign_df_to_input
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						{
							fieldtype: "Float",
							label: "Monto $",
							fieldname: "montoUSD",
							columns: 6,
							// reqd: 1,
							precision:2,
							// read_only: 1,
							on_make: assign_df_to_input
							// change: get_outstanding_details
						},
					],
					primary_action_label: 'Agregar Pago',
					primary_action(values) {
						// console.log(values);
						d.hide();
					},
					secondary_action_label: "Cancel"
				});
		
			// Para hacer filtros
			d.get_field("sales_invoice").get_query = function(){
				var customer = d.get_value("customer"), filters = {'docstatus': 1, 'outstanding_amount': ['!=', 0]};
				if (customer){ filters['customer'] = customer; };
				return {'filters': filters};
			};

			// d.get_field("Colector").get_query = function(){
			// 	var filters = {'collector_type': 'Colector'};
			// 	// if (customer){ filters['customer'] = customer; };
			// 	return {'filters': filters};
			// };
			
			d.set_value('posting_date',frm.doc.fecha)
			d.set_value('conversion_rate',frm.doc.tc)
			d.set_value('Colector',frm.doc.colector)
			d.show();
			d.set_df_property('Num_cheque', 'hidden', 1);
			// d.set_df_property('Fecha_Cheque', 'hidden',1);
			d.set_df_property('nombre_banco', 'hidden', 1);
			// d.$wrapper.find(".modal-dialog").css({"width": "100%","left": "-10%","top": "10%"});
			d.$wrapper.find(".modal-content").css({"width": "100%"});

			//VALIDACION  DE DEPOSITOS DE BANCOS  DEL BOTON
			d.get_primary_btn().text('Agregar Pago').off('click').on('click', function(){
				
				var sum = flt((d.get_value('montoUSD') * flt(d.get_value('conversion_rate'),4)) + flt(d.get_value('montoNIO'),2),2)

				if(d.get_value('sales_invoice')){
					frappe.call({
						'method': "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.montos_facturas",
						'args': {'name':d.get_value("sales_invoice"),'parent':frm.doc.name},
						'callback': function (r) {
							console.log(r.message)
							console.log(r.message)
								if (r.message) {
									d.set_value("montoFactNIO", r.message[0]);
									d.set_value("montoFactUSD", r.message[1]);
							}
						}
					});
				}
				if(d.get_value('customer') == '' && d.get_value('sales_invoice') == '' && d.get_value('Recibo') == '' && d.get_value('montoNIO') == '' && d.get_value('montoUSD') == '' && d.get_value('Colector') == ''){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('Debe de digitar los campos requeridos!')
					});
				}else if(d.get_value('customer') == ''){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No ha seleccionado un cliente!')
					});
				}else if(d.get_value('sales_invoice') == ''){
						frappe.msgprint({
							title: __('Advertencia'),
							indicator: 'red',
							message: __('No ha seleccionado un Factura!')
						});
				}else if(d.get_value('Recibo') == ''){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('Debe digitar el numero de recibo!')
					});
				}else if(d.get_value('montoNIO') == '' && d.get_value('montoUSD') == ''){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('Debe de digitar un monto!')
					});
				
					
				}else if(flt(d.get_value('montoNIO'),2) && flt(d.get_value('montoNIO'),2)  <= 0 ){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No puede ingresar montos menor a cero')
					});
						
				}else if(flt(d.get_value('montoNIO'),2) > flt(d.get_value('montoFactNIO'),2) ){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No puede ingresar monto mayores a la factura')
					});
				}else if(d.get_value('montoUSD') && d.get_value('montoUSD')  <= 0 ){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No puede ingresar montos menor a cero')
					});
						
				}else if(d.get_value('montoUSD') > d.get_value('montoFactUSD') ){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No puede ingresar monto mayores a la factura')
					});
				}else if(d.get_value('Colector') == ''){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('Debe de digitar el colector!')
					});
				}else{

					if(d.get_value('cheque') && d.get_value('Num_cheque') == ''){
						frappe.msgprint({
							title: __('Advertencia'),
							indicator: 'red',
							message: __('Debe de digitar el numero de Cheque!')
						});
					}
					// else if(d.get_value('cheque') && d.get_value('Fecha_Cheque') == null){
					// 	frappe.msgprint({
					// 		title: __('Advertencia'),
					// 		indicator: 'red',
					// 		message: __('Debe de digitar la fecha del cheque!')
					// 	});
					// }
					else if(d.get_value('cheque') && d.get_value('nombre_banco') == ''){
						frappe.msgprint({
							title: __('Advertencia'),
							indicator: 'red',
							message: __('Debe de digitar el nombre del Banco!')
						});
					}else if(d.get_value('montoUSD') && d.get_value('montoNIO') && sum > flt(d.get_value('montoFactNIO'),2)){
						frappe.msgprint({
							title: __('Advertencia'),
							indicator: 'red',
							message: __('No puede ingresar monto mayores a la factura')
						});
					}
					else {
						// pm_args.pagos = payments;
						// pm_args.codigo_nota_credito = frm.doc.name; 
						pm_args['Recibo'] = d.get_value('Recibo');
						pm_args['NumCheque'] = d.get_value('Num_cheque');
						pm_args['ChequeChek'] = d.get_value('cheque');
						// console.log(d.get_value('cheque'))
						// pm_args['Colector'] = d.get_value('Colector');
						pm_args['Colector'] = frm.doc.colector;
						pm_args['NameBatch'] = frm.doc.name;
						pm_args['montoNIO'] = d.get_value('montoNIO');
						pm_args['montoUSD'] = d.get_value('montoUSD');
						pm_args['Num_cheque'] = d.get_value('Num_cheque');
						// pm_args['Fecha_Cheque'] = d.get_value('Fecha_Cheque');
						pm_args['nombre_banco'] = d.get_value('nombre_banco');
						pm_args['talonario'] = Talonario;
						pm_args['talonarioNum'] = d.get_value('Recibo');
						// pm_args['moneda'] = d.get_value('moneda');
						
						var values = d.get_values();
						Crear_PagoBatch(pm_args,values);
						d.hide();
					}	
				}
			});
		}

		if (frm.doc.docstatus === 0){
			frm.add_custom_button('Agregar Pago', function(){
                cur_frm.cscript.AgragarPago(frm);
            });
		}

		

		// var user = frappe.session.user;
		frappe.call({
			"method": "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.consultar_rol",
		}).then(r =>{
				console.log(r.message)
				// rol = r.message;
				if((r.message.includes("Administrador Caja")) || (r.message.includes("Cajero"))  ){
					// console.log('Etn')
					// cur_frm.cscript.AplicarPagos = function (frm){
					// 	frappe.call({
					// 		'method': "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.aplicar_pagos_colector",
					// 		'args': {
					// 			'id_batch':frm.doc.name
					// 		},
					// 		freeze: true,
					// 		freeze_message: "Aplicando pagos, por favor espere ...",
					// 		// 'args': frm.doc.name,
					// 		'callback': function (r) {
					// 			console.log(r.message)
					// 			if (r.message === 'Ok'){
					// 				frappe.show_alert({
					// 					message:__('Se aplicaron los pagos.'),
					// 					indicator:'green'
					// 				}, 20);
					// 				frm.reload_doc();
			
					// 			} else{
					// 				frappe.show_alert({
					// 					message:__('ERROR pagos ya estaban aplicados.'),
					// 					indicator:'red'
					// 				}, 20);
					// 				frm.reload_doc();
					// 			}
								
					// 		}
					// 	});
					// }
			
					cur_frm.cscript.Comprobar_Fac = function (frm) {
						var pm_args = {};
						pm_args['idbatch'] = frm.doc.name;
			
						if (pm_args.length === 0){
							frappe.msgprint({
								title: __('Advertencia'),
								indicator: 'Red',
								message: __('No ha creado el recaudo')
							});
						}else{
							validar_facturas(pm_args);
						}
			
						function validar_facturas(pm_args){
							frappe.call({
								'method': "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.Validar_FActuras_Batch",
								'args': pm_args,
								'callback': function (r) {
									console.log(r.message.messages)
										if (r.message) {
											// console.log(r.message)
											if(r.message.messages.length){
												var res = r.message.messages;
												// const result = r.message.messages.join('\n');
												
												frappe.msgprint({
													title: __('Advertencia'),
													// indicator: 'Red',
													message: __(res.join("<br/>"))
												});
												cur_frm.set_value("validado", 1);
												// frappe.msgprint(res)
												// frm.reload_doc();
											}else{
												frappe.msgprint({
													title: __('Advertencia'),
													indicator: 'Red',
													message: __('ERROR')
												});
											}
									}
								}
							});
						}
						
					}

					
					// frm.add_custom_button('Aplicar Pagos', function(){
					// 	cur_frm.cscript.AplicarPagos(frm);
					// });
					
		
				
					frm.add_custom_button('Comprobar Facturas', function(){
						cur_frm.cscript.Comprobar_Fac(frm);
					});
					
					
				}
		})

	},

	after_save:function(frm) {
		// console.log('LLEga')
		var recaudo = frm.doc.recaudo
		console.log(frm.doc)
		if (recaudo.length >= 0 && frm.doc.docstatus == 0){
			frappe.call({
				'method': "erpnext.crm.doctype.recaudo_colectores.recaudo_colectores.eliminar_monto",
				'args': {
					'name':frm.doc.name
				},
				// freeze: true,
				// freeze_message: "Aplicando pagos, por favor espere ...",
				// // 'args': frm.doc.name,
				'callback': function (r) {
					console.log(r.message)
					if (r.message){
						frappe.show_alert({
							message:__('Pago eliminado.'),
							indicator:'green'
						}, 15);
						frm.reload_doc();
	
					} else{
						frappe.show_alert({
							message:__('ERROR pagos ya estaban aplicados.'),
							indicator:'red'
						}, 15);
					}
					
				}
			});
			// frm.reload_doc();
		}
		// frm.reload_doc();
		
	}
});

frappe.ui.form.on("Recaudo colectores", "fecha", function(frm){
	if (frm.doc.fecha){
		frappe.db.get_value("Currency Exchange", {"date": frm.doc.fecha},"paralela",function(res){
			console.log(res.paralela)
			frm.set_value('tc',res.paralela)
		})
	}
});