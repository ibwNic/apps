// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pago Batch', {
	refresh: function(frm) {
		// frm.toggle_display(['priority', 'due_date'], frm.doc.status === 'Open');
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
					'method': "erpnext.api.agregar_pago_batch",
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
			factura,
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
					title: __("Agregar Cliente"),
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
							default: frappe.datetime.get_today(),
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
							}
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
							// read_only: 1
						},
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Link",
							label: "Colector",
							options: "Colectores",
							fieldname: "Colector",
							reqd: 1
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Check",
							label: "Cheque",
							default: false,
							fieldname: "cheque",
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
							fieldtype: "Data",
							label: "N° Cheque",
							default: false,
							fieldname: "Num_cheque",
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

			d.get_field("Colector").get_query = function(){
				var filters = {'collector_type': 'Colector'};
				// if (customer){ filters['customer'] = customer; };
				return {'filters': filters};
			};
			
			d.set_value('conversion_rate',frm.doc.tasa_de_cambio)
			d.show();

			//VALIDACION  DE DEPOSITOS DE BANCOS  DEL BOTON
			d.get_primary_btn().text('Agregar Pago').off('click').on('click', function(){
		
				
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
					}else if(d.get_value('Colector') && d.get_value('Recibo') == ''){
						frappe.msgprint({
							title: __('Advertencia'),
							indicator: 'red',
							message: __('Debe de digitar el numero de Recibo!')
						});
					}else {
						// pm_args.pagos = payments;
						// pm_args.codigo_nota_credito = frm.doc.name; 
						pm_args['Recibo'] = d.get_value('Recibo');
						pm_args['NumCheque'] = d.get_value('Num_cheque');
						pm_args['ChequeChek'] = d.get_value('cheque');
						pm_args['Colector'] = d.get_value('Colector');
						pm_args['NameBatch'] = frm.doc.name;
						pm_args['montoNIO'] = d.get_value('montoNIO');
						pm_args['montoUSD'] = d.get_value('montoUSD');
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

		cur_frm.cscript.AplicarPagos = function (){
			console.log(frm.doc.name)
			frappe.call({
				'method': "erpnext.api.aplicar_batch",
				'args': {
					'id_batch':frm.doc.name
				},
				// 'args': frm.doc.name,
				'callback': function (r) {
					// console.log(r.message)
						if (r.message) {
							console.log(r.message)
							if(r.message === 'Ok')
							{	
								
								// // frm.set_value('aplicado',1);
								// // frm.set_value('docstatus',1);
								// // doc.db_set('docstatus',1)
								// // frm.set_value('docstatus',1);
								// frm.save('Submit');
								// frappe.msgprint({
								// 	title: __('Sastifactorio'),
								// 	indicator: 'green',
								// 	message: __('Se aplicaron pagos')
								// });
								// frm.reload_doc();
							}
					}
				}
			});
		}

		if (frm.doc.docstatus === 0){
			frm.add_custom_button('Aplicar Pagos', function(){
                cur_frm.cscript.AplicarPagos(frm);
            });
		}

	}
});