// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pago Sin Identificar', {
	refresh: function(frm) {
		// if (frm.doc.saldo === 0){
		// 	frappe.db.set_value('Pago Sin Identificar', frm.doc.name, {
		// 		'docstatus': 1,
		// 		'aplicado': 1
		// 	})
		// 	// frm.set_value('aplicado',1);
		// }

		
		cur_frm.cscript.AplicarDepostos = function(frm){
			// console.log(frm.doc.cliente);
			function Crear_Deposito(pm_args,values){
				[
					['customer','regnumber'],
					['sales_invoice', 'factura'],
					['conversion_rate', 'tc'],
					['posting_date', 'fecha']
				].forEach(function(pair){
					var v = values[pair[0]];
					if (v) pm_args[pair[1]] = v;
				});

				pm_args.observacion = frm.doc.referencia;
				console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					// AQUI
				frappe.call({
					'method': "erpnext.api.Aplicar_Deposito_Banco",
					'args': pm_args,
					'callback': function (r) {
						// console.log(r.message)
							if (r.message) {
								// console.log(r.message)
								var doc = frappe.model.sync(r.message)[0];
								frappe.set_route("Form", doc.doctype, doc.name);
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
				pm_args = {},
				tmp_dc_table = `<table class="table table-condensed table-bordered">
			   <thead>
				 <tr>
				   <tr>
					   <th>&nbsp;</th>
					   <th>ID Factura</th>
					   <th>Fecha</th>
					   <th class="text-right">Deuda $</th>
					   <th class="text-right">TC</th>
					   <th class="text-right">Deuda C$</th>
					   <th class="text-right">C$ Segun  TC {{ data.saldo.tc }}</th>
					   <th class="text-right">Dif. Cambiario</th>
				   </tr>
				 </tr>
			   </thead>
			   <tbody>
				 {% for (var row of data[dc]) { %}
				 <tr>
					 <td><input type="checkbox" class="link_name" value="{{row.name}}" data-doctype="{{ row.doctype }}" /></td>
					 <td><a href="#Form/{{ row.doctype }}/{{ row.name }}" target="_newtab">{{ row.name }}</a></td>
					 <td>{{ frappe.datetime.str_to_user(row.fecha) }}</td>
					 <td class="text-right">{{ format_currency(row.deuda.usd, "USD", 2) }}</td>
					 <td class="text-right">{{ row.deuda.tc }}</td>
					 <td class="text-right">{{ format_currency(row.deuda.nio, "NIO", 2) }}</td>
					 <td class="text-right">{{ format_currency(row.actual.nio, "NIO", 2) }}</td>
					 <td class="text-right">{{ row.actual.diferencial }}</td>
				 </tr>
				 {% } %}
			   </tbody>
			   <tbody>
				  <tr>
					<th colspan="3" class="centrado">&nbsp; TOTAL </th>
					<th id="total_usd" class="text-right"></th>
					<th>&nbsp;</th>
					<th id="total_nio" class="text-right"></th>
					<th id="total_actual_nio" class="text-right"></th>
					<th id="total_diff" class="text-right"></th>
				  <tr>
			   </tbody>
			</table>`,
			tmp_pm_table = `<table class="table table-condensed table-bordered">
			   <thead>
				 <tr>
				   <th>Factura</th>
				   <th>Moneda</th>
				   <th class="text-right">Monto $</th>
				   <th class="text-right">Monto C$</th>
				   <th class="text-right">&nbsp;</th>
				 </tr>
			   </thead>
			   <tbody>
				 {% var totals = {"pm_total_usd": 0.0, "pm_total_nio": 0.0}; %}
				 {% for (var i = 0, l = data.length; i < l; i++) { %}
				 {% var row = data[i]; %}
				 <tr>
				   <td>{{ row.Factura }}</th>
				   <td>{{ {"NIO": "C$", "USD": "$"}[row.moneda] }}</th>
				   <td class="text-right">{{ format_currency(row.moneda === "USD" ? flt(row.monto) : flt(row.monto) / flt(tc,2), "USD", 2) }}</th>
				   <td class="text-right">{{ format_currency(row.moneda === "USD" ? flt(row.monto) * flt(tc) : flt(row.monto), "NIO", 2) }}</th>
				   <td><button class="btn btn-danger btn-xs remove" data-idx="{{ i }}"><span class="icon icon-remove">
				 	<svg class="icon icon-sm" style>
						<use class href="#icon-delete"></use>
					</svg>
				   </span></button>
				   </td>
				 </tr>
				 {% totals.pm_total_usd += (row.moneda === "USD" ? flt(row.monto) : flt(row.monto) / flt(tc)) %}
				 {% totals.pm_total_nio += (row.moneda === "USD" ? flt(row.monto) * flt(tc) : flt(row.monto)) %}
				 {% } %}
			   </tbody>
			   <tbody>
				 <tr>
				   <th colspan="2" class="centrado">&nbsp; TOTAL FACTURA</th>
				   <th class="text-right" id="pm_total_usd">{{ format_currency(totals.pm_total_usd, "USD", 2) }}</th>
				   <th class="text-right" id="pm_total_nio">{{ format_currency(totals.pm_total_nio, "NIO", 2) }}</th>
				   <th>&nbsp;</th>
				 </tr>
			   </tbody>
			</table>`;



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

			// Aqui para asignar el otro Js
			function render_totals_table(){
				// totals.length = 0;
				// var tc = flt(d.get_value("conversion_rate"));
				// if (d.fields_dict.debits_wrapper.$wrapper.find("#total_usd").length){
				// 	totals.push({
				// 		symbol: '-',
				// 		description: 'Deuda',
				// 		amount_usd: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_usd').text()),
				// 		// amount_nio: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_nio').text()),
				// 		amount_nio: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_actual_nio').text()),
				// 		amount_nioF: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_nio').text()),
				// 	});
				// } else {
                //     totals.push({
				// 		symbol: '-',
				// 		description: 'Deuda',
				// 		amount_usd: 0.0,
				// 		amount_nioF:0.0,
				// 		amount_nio: 0.0,

                //     });
				// }
				// pm_args.pagos = payments
				// d.fields_dict.totals_wrapper.$wrapper.find("#totals_wrapper").html(frappe.render(tmp_pm_table));
			}


			function TituloName(name){
				d.fields_dict.TituloName.$wrapper.find("#Nombre").text(name);
			}

			function SumaFormaPagos() {
				var sumaMonto1 = 0,sumaMonto2 = 0;
				console.log(payments);
				totals.length = 0;
				for(let i = 0; i < payments.length; i++){
					if (payments[i]['moneda'] == "NIO"){
						console.log("Entra");
						sumaMonto1 += payments[i]['monto'];
						// sumaMonto1Conver = flt(sumaMonto1 * tc[0],2);
					}
					if (payments[i]['moneda'] == "USD"){
						console.log("Entra");
						sumaMonto2 += payments[i]['monto'];
						// sumaMonto2Conver = flt(sumaMonto2 / tc[0],2);
					}
				}
				// console.log(sumaMonto1,sumaMonto1Conver);
				// TotalesNIO = sumaMonto1 + (sumaMonto2 * tc[0]);
				// TotalesUSD = flt(sumaMonto2 + sumaMonto1 / tc[0],2);
				TotalesNIO = flt(sumaMonto1);
				TotalesUSD = flt(sumaMonto2);

				totals.push({
					MontoUSD: TotalesUSD,
					MontoNIO: TotalesNIO
				});
				// pm_args['deudas'] = [];
				// pm_args['deudas'].push({'link_doctype':'Sales Invoice', 'link_name': d.get_value('Factura')});
				pm_args.pagos = payments;
				// console.log(tc[0]);
			}

				function set_sum_on_check(wrapper, dc, datas){
					wrapper.find('input[type="checkbox"]').on('change', function(){
						var amounts = {'usd': 0.0, 'nio': 0.0, 'actual_nio': 0.0, 'diff': 0.0};
						// var montos = {'usd': 0.0, 'nio': 0.0, 'actual_nio': 0.0};
						// var montos = [];
						pm_args[dc] = [];
						factura = [];
						wrapper.find('input[type="checkbox"]:checked').each(function(){
							pm_args[dc].push({'link_doctype': $(this).data('doctype'), 'link_name': $(this).val()});
							factura.push($(this).val());
							frappe.utils.filter_dict(datas, {'name': $(this).val()}).forEach(function(d){
								amounts.usd += d.deuda.usd;
								amounts.nio += d.deuda.nio;
								amounts.actual_nio += d.actual.nio;
								amounts.diff += d.actual.diferencial;
							});
						});
						// montos.length = 0;
						montos.push(flt(amounts.usd,2));
						montos.push(flt(amounts.nio,2));
						montos.push(flt(amounts.actual_nio,2));
						montos.push(amounts.name);
						// montosUSD.push(amounts.usd);
						// montosC$.push(amounts.actual_nio);
						// montosC$.push(amounts.nio);
						console.log(amounts);
						d.fields_dict.debits_wrapper.$wrapper.find("#total_usd").text(format_currency(amounts.usd, 'USD', 2));
						d.fields_dict.debits_wrapper.$wrapper.find("#total_nio").text(format_currency(amounts.nio, 'NIO', 2));
						d.fields_dict.debits_wrapper.$wrapper.find("#total_actual_nio").text(format_currency(amounts.actual_nio, 'NIO', 2));
						d.fields_dict.debits_wrapper.$wrapper.find("#total_diff").text(amounts.diff.toFixed(2));
						// wrapper.find('#total_usd').text(format_currency(amounts.usd, 'USD', 2));
						// wrapper.find('#total_nio').text(format_currency(amounts.nio, 'NIO', 2));
						// wrapper.find('#total_actual_nio').text(format_currency(amounts.actual_nio, 'NIO', 2));
						// wrapper.find('#total_diff').text(amounts.diff.toFixed(2));

						// selectMonto(montos);
						// render_totals_table();
						var data = factura;
						create_payments_area(data);
						// SumaFormaPagos();
					});
				}

				function get_outstanding_details(){
					if (ignore_event) return;
					var df = $(this).data('df'), args = {};
					// console.log($(this))
					// if (!df.get_value()) return;

					var a =[
						['customer', 'name'],
						['sales_invoice', 'factura'],
						['conversion_rate', 'tc'],
						['posting_date', 'fecha']
					].forEach(function(pair){
						var v = d.get_value(pair[0]);
						if (v) args[pair[1]] = v;
					});


					if (!d.get_value("customer")) {
						d.fields_dict.customer.df.description = '';
						d.fields_dict.customer.set_description();
						return;
					}

					d.fields_dict.debits_wrapper.$wrapper.empty();
					// d.fields_dict.credits_wrapper.$wrapper.empty();

					console.log('Requisición Consulta Deuda');
					console.log(Object.keys(args).map(function(k) { return k + ': '+ JSON.stringify(args[k]) }).join('\n'));
					// console.log(args);
					frappe.call({
						'method': 'erpnext.api.consulta_deuda',
						'args': args,
						'freeze': true,
						'freeze_message': 'Buscando informaciones!',
						callback: function(res){
							console.log(res.message.deudas);
							if(res.message.error){
								let error = res.message.error
								frappe.msgprint({
									title: __('Advertencia'),
									indicator: 'green',
									message: __(error)
								});
								d.set_value("customer",null);
							}
							
							if(res.message.deudas.length == 0){
								frappe.msgprint({
									title: __('Advertencia'),
									indicator: 'green',
									message: __('No tiene facturas pendientes!')
								});
								d.set_value("customer",null);
							}
							if (res && res.message) {
								if (res.message.deudas.length) {
									d.fields_dict.debits_wrapper.$wrapper.html(frappe.render(
										tmp_dc_table, {data: res.message, dc: "deudas"}
									));
									set_sum_on_check(d.fields_dict.debits_wrapper.$wrapper, 'deudas', res.message.deudas);
									// TCBAnco(res.message.TCBanco);
									// TCBanco = res.message.TCBanco;
									// TituloName(res.message.cliente.nombre);
								}
								// if (res.message.creditos.length) {
								// 	d.fields_dict.credits_wrapper.$wrapper.html(frappe.render(
								// 		tmp_doc_table, {data: res.message, dc: "creditos"}
								// 	));
								// 	set_sum_on_check(d.fields_dict.credits_wrapper.$wrapper, 'creditos', res.message.creditos);
								// }
								// frappe.render(totals_wrapper, {data: res.message});
								ignore_event = true;
								// d.set_value('conversion_rate', res.message.saldo.tc);
								// d.fields_dict.customer.df.description = res.message.cliente.nombre || '';
								// d.fields_dict.customer.set_description();
								// // minimal_credit_amount = res.message.monto_minimo_credito;
								setTimeout(function(){ ignore_event = false; }, 500);

								// Mandarle la data al texbox
								// create_payments_area(res.message);
							}
						}
					});
				}


				// function mostrarFactura(MotoAnticipo){
				// 	// if (d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#action").hasClass("hidden")) return;
				// 	payments.length = 0;
				// 	payments.push({
				// 		"tipo_de_pago": " ",
				// 		"moneda": " ",
				// 		"monto": MotoAnticipo
				// 	});
				// 	// console.log(currency_field.get_value());
				// 	// SumaFormaPagos();
				// 	function render_payments(){
				// 		d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#payments_wrapper").html(
				// 			frappe.render(tmp_pm_tableAnticipo, {"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0})
				// 		).find("button.remove").off('click').on('click', function(){
				// 			var idx = cint($(this).data('idx'));
				// 			payments.splice(idx,1);
				// 			render_payments();
				// 			// SumaFormaPagos();
				// 			// render_totals_table();
				// 		});
				// 	};
				// 	render_payments();
				// 	// tc.push(d.get_value("conversion_rate"));
				// 	// console.log(tc[0]);
				// 	// mode_of_payment_field.$input.val(null).trigger("change");
				// 	// currency_field.$input.val(null).trigger("change");
				// 	// amount_field.$input.val(null).trigger("change");
				// }

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

				function create_payments_area(data){
					// const filteredUsers = Object.keys(data);
					// console.log(filteredUsers);
					// console.log(data);
					var mode_of_payment_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Select',
							options: [null].concat(data),
							fieldname: 'mode_of_payment',
							label: 'Tipo de Pago',
							// placeholder: 'Tipo de Pago',
							reqd: 1
						},
						parent: d.fields_dict.totals_wrapper.$wrapper.find("#mode_of_payment_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					mode_of_payment_field.make_input();
					fields.mode_of_payment = mode_of_payment_field;

					// Haciendo filtro
					// var MontoSelect = frappe.ui.form.make_control({
					// 	df: {
					// 		fieldtype: 'tick',
					// 		options: 0,
					// 		fieldname: 'pagosmixtos',
					// 		label: 'Pagos mixtos',
					// 		// placeholder: 'Tipo de Pago',
					// 		reqd: 0
					// 	},
					// 	parent: d.fields_dict.totals_wrapper.$wrapper.find("#pagosmixtos_wrapper").empty(),
					// 	frm: frm,
					// 	doctype: frm.doctype,
					// 	docname: frm.docname,
					// 	only_input: true
					// });
					// mode_of_payment_field.make_input();
					// fields.mode_of_payment = mode_of_payment_field;


					// var currency_field = frappe.ui.form.make_control({
					// 	df: {
					// 		fieldtype: 'Select',
					// 		options: ['USD','NIO'],
					// 		fieldname: 'currency',
					// 		label: 'Moneda',
					// 		// placeholder: 'Moneda',
					// 		reqd: 0
					// 	},
					// 	parent: d.fields_dict.totals_wrapper.$wrapper.find("#currency_wrapper").empty(),
					// 	frm: frm,
					// 	doctype: frm.doctype,
					// 	docname: frm.docname,
					// 	only_input: true
					// });
					// currency_field.make_input();
					// fields.currency = currency_field;

					// Personalizado
					// var amount_field = frappe.ui.form.make_control({
					// 	df: {
					// 		fieldtype: 'Select',
					// 		// precision: 2,
					// 		options: [""],
					// 		fieldname: 'amount',
					// 		label: 'Monto',
					// 		// placeholder: 'Monto',
					// 		reqd: 0
					// 	},
					// 	parent: d.fields_dict.totals_wrapper.$wrapper.find("#amount_wrapper").empty(),
					// 	frm: frm,
					// 	doctype: frm.doctype,
					// 	docname: frm.docname,
					// 	only_input: true,
					// 	read_only: true
					// });
					// amount_field.make_input();
					// fields.amount = amount_field;

					var amount_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Float',
							precision: 2,
							fieldname: 'amount',
							label: 'Monto',
							placeholder: 'Monto',
							reqd: 1
						},
						parent: d.fields_dict.totals_wrapper.$wrapper.find("#amount_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					amount_field.make_input();
					fields.amount = amount_field;


					///////////////////////////////////////////////////////////////////

					// var CambioNIO = frappe.ui.form.make_control({
					// 	df: {
					// 		fieldtype: 'Float',
					// 		precision: 2,
					// 		fieldname: 'montoNIO',
					// 		label: 'montoNIO',
					// 		placeholder: 'Monto C$',
					// 		reqd: 0
					// 	},
					// 	parent: d.fields_dict.totals_wrapper.$wrapper.find("#CambioNIO_wrapper").empty(),
					// 	frm: frm,
					// 	doctype: frm.doctype,
					// 	docname: frm.docname,
					// 	only_input: true
					// });
					// CambioNIO.make_input();
					// CambioNIO.$input.on('change', function(){
					// 	// render_totals_table();
					// 	// pm_args.cambios = [];

					// 	if (CambioNIO.get_value()) {
					// 		// frappe.msgprint("OK");

					// 		var sumNIO = 0;
					// 		var res = 0;
					// 		var HaytipoPagoEfectivo = false;
					// 		for(let i = 0; i < payments.length; i++){
					// 			if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "nio"){
					// 				sumNIO += payments[i]['monto'];
					// 				// HaytipoPagoEfectivo = true;
					// 				// if(payments[i]['moneda'] == "nio"){
					// 				// 	sumNIO += payments[i]['monto'];
					// 				// }
					// 			}
					// 			// else{
					// 			// 	HaytipoPagoEfectivo = false;
					// 			// }
					// 		}
					// 		console.log(sumNIO);
					// 		if(sumNIO > 0){
					// 			res = flt((-1)* (sumNIO - CambioNIO.get_value()),2);
					// 			// console.log(res);
					// 			if(CambioNIO.get_value() < sumNIO){
					// 				frappe.msgprint({
					// 					title: __('Advertencia'),
					// 					indicator: 'red',
					// 					message: __('El monto digitado en Cordobas no debe ser menor, al efectivo que recibio!')
					// 				});
					// 				CambioNIO.$input.val(null).trigger("change");
					// 			}else{
					// 				// ResultCambioNIO.set_value(res);
					// 				ResultCambioNIO.$input.val(res).trigger("change");
					// 				// fields.ResultNIO.set_value(res);
					// 				Cambios.CambioNIO = res;
					// 			}
					// 		}else{
					// 			frappe.msgprint({
					// 				title: __('Advertencia'),
					// 				indicator: 'red',
					// 				message: __('No recibio ningun tipo de pago que sea efectivo en Cordobas!')
					// 			});
					// 			CambioNIO.$input.val(null).trigger("change");
					// 		}

					// 	}
					// 	// if (change_nio_field.get_value()) {
					// 	// 	pm_args.cambios.push({'monto': flt(change_nio_field.get_value()), 'moneda': 'nio'});
					// 	// }
					// });
					// fields.montoNIO = CambioNIO;

					// var ResultCambioNIO = frappe.ui.form.make_control({
					// 	df: {
					// 		fieldtype: 'Float',
					// 		precision: 2,
					// 		fieldname: 'ResultNIO',
					// 		label: 'montoNIO',
					// 		placeholder: 'Vuelto C$',
					// 		reqd: 0,
					// 		read_only: 1
					// 	},
					// 	parent: d.fields_dict.totals_wrapper.$wrapper.find("#ResultCambioNIO_wrapper").empty(),
					// 	frm: frm,
					// 	doctype: frm.doctype,
					// 	docname: frm.docname,
					// 	only_input: true,

					// });
					// ResultCambioNIO.make_input();
					// fields.ResultNIO = ResultCambioNIO;

					// //////////////////////////////////////////////////////////////////

					// var CambioUSD = frappe.ui.form.make_control({
					// 	df: {
					// 			fieldtype: 'Float',
					// 			precision: 2,
					// 			fieldname: 'montoUSD',
					// 			label: 'USD',
					// 			placeholder: 'Monto $'
					// 		},
					// 		parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_usd_wrapper").empty(),
					// 		frm: frm,
					// 		doctype: frm.doctype,
					// 		docname: frm.docname,
					// 		only_input: true
					// 	});
					// 	CambioUSD.make_input();
					// 	CambioUSD.$input.on('change', function(){
					// 		if (CambioUSD.get_value()) {
					// 			// frappe.msgprint("OK");
					// 			montosUSD = CambioUSD.get_value();
					// 			// console.log();
					// 			// console.log(payments);
					// 			var sumUSD = 0;
					// 			var tc=0;
					// 			var converNIO = 0;
					// 			var converUSD = 0;
					// 			var cambioUSD = 0;
					// 			var res = 0;
					// 			for(let i = 0; i < payments.length; i++){
					// 				if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "usd"){
					// 					sumUSD += payments[i]['monto'];
					// 					// if (payments[i]['moneda'] == "usd") {
					// 					// 	sumUSD += payments[i]['monto'];
					// 					// }
					// 				}
					// 			}

					// 			if(sumUSD > 0){
					// 				// converNIO = sumUSD *  d.get_value("conversion_rate");
					// 				tc = ObtenerTCBanco();
					// 				converNIO = sumUSD *  tc;

					// 				// converUSD = CambioUSD.get_value() *  d.get_value("conversion_rate");
					// 				converUSD = CambioUSD.get_value() * tc;
					// 				res = flt((-1)* (converNIO - converUSD),2);
					// 				cambioUSD = flt(CambioUSD.get_value() - sumUSD,2);
					// 				console.log(res);
					// 				if(CambioUSD.get_value() < sumUSD){
					// 					frappe.msgprint({
					// 						title: __('Advertencia'),
					// 						indicator: 'red',
					// 						message: __('El monto digitado en Dolares no debe ser menor, al efectivo que recibio!')
					// 					});
					// 					// ResultCambioUSD.$input.val(null).trigger("change");
					// 					CambioUSD.$input.val(null).trigger("change");
					// 				}else{
					// 					ResultCambioUSD.$input.val(res).trigger("change");
					// 					ResultCambioUSD_USD.$input.val(cambioUSD).trigger("change");
					// 					Cambios.CambioUSD = cambioUSD;
					// 				}
					// 			}else{
					// 				frappe.msgprint({
					// 					title: __('Advertencia'),
					// 					indicator: 'red',
					// 					message: __('No recibio ningun tipo de pago que sea efectivo en Dolares!')
					// 				});
					// 				// ResultCambioUSD.$input.val(null).trigger("change");
					// 				CambioUSD.$input.val(null).trigger("change");
					// 				// ResultCambioUSD_USD.$input.val(cambioUSD).trigger("change");
					// 			}
					// 		}
					// 	});
					// 	fields.montoUSD = CambioUSD;

					// 	var ResultCambioUSD = frappe.ui.form.make_control({
					// 		df: {
					// 			fieldtype: 'Float',
					// 			precision: 2,
					// 			fieldname: 'ResultUSD',
					// 			label: 'USD',
					// 			placeholder: 'Vuelto C$',
					// 			read_only: 1
					// 		},
					// 		parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_nio_wrapper").empty(),
					// 		frm: frm,
					// 		doctype: frm.doctype,
					// 		docname: frm.docname,
					// 		only_input: true
					// 	});
					// 	ResultCambioUSD.make_input();
					// 	fields.ResultUSD = ResultCambioUSD;

					// 	var ResultCambioUSD_USD = frappe.ui.form.make_control({
					// 		df: {
					// 			fieldtype: 'Float',
					// 			precision: 2,
					// 			fieldname: 'ResultCambioUSD_USD',
					// 			label: 'USD',
					// 			placeholder: 'Vuelto $',
					// 			read_only: 1
					// 		},
					// 		parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_usd_usd_wrapper").empty(),
					// 		frm: frm,
					// 		doctype: frm.doctype,
					// 		docname: frm.docname,
					// 		only_input: true
					// 	});
					// 	ResultCambioUSD_USD.make_input();
					// 	fields.ResultUSD_USD = ResultCambioUSD_USD;



					toggle_action([mode_of_payment_field, amount_field],
						d.fields_dict.totals_wrapper.$wrapper);



						// console.log(amount_field.get_value());
					//AQUI
					d.fields_dict.totals_wrapper.$wrapper.find("#action").off("click").on("click", function(){
						if (d.fields_dict.totals_wrapper.$wrapper.find("#action").hasClass("hidden")) return;

						payments.push({
							"Factura": mode_of_payment_field.get_value(),
							"moneda": frm.doc.moneda,
							"monto": amount_field.get_value()
						});
						facturaSelect.push(mode_of_payment_field.get_value());
						// console.log(facturaSelect);
						// if ()
						let resultToReturn = false;
						resultToReturn = facturaSelect.some((element, index) => {
							return facturaSelect.indexOf(element) !== index
						});

						if (resultToReturn) {
							frappe.msgprint({
								title: __('Error'),
								indicator: 'red',
								message: __('Factura ingresada!')
							});
							payments.pop();
							facturaSelect.pop()
							
							
							mode_of_payment_field.$input.val(null).trigger("change");
							// currency_field.$input.val(null).trigger("change");
							amount_field.$input.val(null).trigger("change");
							
						}
						else {
								// console.log('No hay elementos duplicados ');
								SumaFormaPagos();
								function render_payments(){
									d.fields_dict.totals_wrapper.$wrapper.find("#payments_wrapper").html(
										frappe.render(tmp_pm_table, {"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0})
									).find("button.remove").off('click').on('click', function(){
										var idx = cint($(this).data('idx'));
										payments.splice(idx,1);
										facturaSelect.splice(idx,1);
										render_payments();
										SumaFormaPagos();
										// render_totals_table();
									});
								};
								render_payments();

								// render_totals_table();
								mode_of_payment_field.$input.val(null).trigger("change");
								// currency_field.$input.val(null).trigger("change");
								amount_field.$input.val(null).trigger("change");
						}
						// render_payments();

					});
					// Validacion de boton limpiar
					// toggle_actionCambio([CambioNIO, ResultCambioUSD_USD, ResultCambioUSD,CambioUSD,ResultCambioNIO],
					// 	d.fields_dict.totals_wrapper.$wrapper);

					// d.fields_dict.totals_wrapper.$wrapper.find("#actionLimpiarText").off("click").on("click", function(){
					// 	if (d.fields_dict.totals_wrapper.$wrapper.find("#actionLimpiarText").hasClass("hidden")) return;
					// 	CambioNIO.$input.val(null).trigger("change");
					// 	ResultCambioUSD_USD.$input.val(null).trigger("change");
					// 	ResultCambioUSD.$input.val(null).trigger("change");
					// 	CambioUSD.$input.val(null).trigger("change");
					// 	ResultCambioNIO.$input.val(null).trigger("change");
					// });
				}

				d = new frappe.ui.Dialog({
					title: __("Aplicar Depositos"),
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
							fieldtype: "Link",
							label: "Cliente",
							options: "Customer",
							fieldname: "customer",
							on_make: assign_df_to_input,
							change:  function(){
									if(d.get_value('customer')){
										get_outstanding_details();
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
						},
						{
							fieldtype: "Link",
							label: "Factura",
							options: "Sales Invoice",
							fieldname: "sales_invoice",
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
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Currency",
							label: "Monto",
							precision: 2,
							options: "moneda",
							fieldname: "Monto",
							read_only: 1,
							// change: function () {
							// 	if(d.get_value('customer')){

							// 	}
							// }
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Link",
							label: "Cuenta",
							options: 'Account',
							fieldname: "cuenta",
							read_only: 1
						},
						// {
						// 	fieldtype: "Select",
						// 	label: "Banco",
						// 	options: ['1.01.001.002.001.003-Bancentro Córdobas 100208377 - NI','1.01.001.002.002.004-Bancentro Dólares No101209210 - NI','1.01.001.002.001.004-BAC Córdobas No.351000488 - NI','1.01.001.002.002.003-BAC Dolares No 360871727 - NI','1.01.001.002.001.005-BANPRO CORDOBAS - NI','1.01.001.002.002.002-BANPRO DOLARES - NI','1.01.001.002.001.001-BDF Córdobas Nº100010030014661 - NI'],
						// 	fieldname: "Banco",
						// 	reqd: 1
						// },
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Data",
							label: "Banco",
							// precision: 2,
							// options: "Customer",
							fieldname: "Banco",
							read_only: 1,
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Deudas")
						},
						{
							fieldtype: 'Select',
							label: 'Moneda',
							options: ['USD','NIO'],
							fieldname: "moneda",
							reqd: 1,
							read_only: 1
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Float",
							fieldname: "conversion_rate",
							precision: 4,
							label: "TC",
							read_only: 1,
							// on_make: assign_df_to_input,
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
							// read_only: 1
							// on_make: assign_df_to_input,
							// change: get_outstanding_details
						},
						{
							// fieldtype: "Column Break",
							fieldtype: "Section Break",
							label: __("Forma de Pagos")
						},
						{
							fieldtype: "Section Break",
							label: __("Deudas")
						},
						{
							fieldtype: "HTML",
							fieldname: "debits_wrapper",
							options: `<div class="row">
							<div id="debits_wrapper" class="col-sm-12 col-md-12 col-lg-12 col-xl-12"></div>
							</div>`
						},
						{
							fieldtype: "Section Break",
							label: "Pagos<span class='pull-right'>Totales</span>"
						},
						{
							 fieldtype: "HTML",
							 fieldname: "totals_wrapper",
							 options: `<div class=row>
					   <div class="col-sm-12 col-md-6 col-lg-6 col-xl-6">
						<div class="row">
							<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4 style="padding-left: 0px;""> Tipo de pago</div>

						</div>

					   <div class="row">
								<div class="col-sm-12 col-md-4 col-lg-4 col-xl-4" id="mode_of_payment_wrapper" style="padding-left: 0px;"></div>

								<div class="col-sm-4 col-md-3 col-lg-3  col-xl-3" id="amount_wrapper" style="padding-left: 0px;"></div>
								<div class="col-sm-2 col-md-2 col-lg-2 col-xl-2" id="action_wrapper" style="padding-left: 0px;">
									<button class="btn btn-primary hidden" role="button" id="action">Agregar</button>
								</div>
							</div>
							<br>
							<div class="row" id="payments_wrapper"></div>
													  
					   </div>
					   		<div class="col-sm-12 col-md-6 col-lg-6 col-xl-6" style="padding-right: 0px;" id="totals_wrapper"></div>
				   		</div>`
						},
					],
					primary_action_label: 'Aplicar Anticipo',
					primary_action(values) {
						console.log(values);
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


			// d.set_value('customer',frm.doc.cliente)
			d.set_value('Monto',frm.doc.monto)
			d.set_value('moneda',frm.doc.moneda)
			d.set_value('cuenta',frm.doc.cuentas)
			// d.set_value('Banco',frm.doc.banco)
			d.set_value('Banco',frm.doc.banco)
			d.set_value('conversion_rate',frm.doc.tasa_de_cambio)
			// d.set_value('posting_date',frm.doc.fecha_deposito)

			d.show();
			d.$wrapper.find(".modal-dialog").css({"width": "100%","left": "-10%","top": "10%"});
			d.$wrapper.find(".modal-content").css({"width": "160%"});
			// d.$wrapper.find(".modal-dialog").css({"top":"5%"});
			// d.$wrapper.find(".modal-content").css({"width": "120%","left": "-10%"});

			//VALIDACION  DE DEPOSITOS DE BANCOS  DEL BOTON
			d.get_primary_btn().text('Aplicar Deposito').off('click').on('click', function(){

				console.log(totals);
				// pm_args.pagos = payments;
				console.log(Object.keys(pm_args).length === 0);
				
				// console.log(pm_args.deudas.length,pm_args.pagos.length);
				// return 0
				// console.log(pm_args.length);
				if (Object.keys(pm_args).length === 0){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No ha seleccionado facturas!')
					});

				}
				// if (pm_args.deudas.length){
				// 	frappe.msgprint({
				// 		title: __('Advertencia'),
				// 		indicator: 'red',
				// 		message: __('Debe de digistar todas las facturas que selecciono con su monto!')
				// 	});
				// 	return 0
				// }

				// pm_args.pagos = payments;
				console.log(pm_args.deudas.length,pm_args.pagos.length);
				if (pm_args.deudas.length != pm_args.pagos.length){
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('Debe de digistar todas las facturas que selecciono con su monto!')
					});
					// return 0
				}else {
					if (frm.doc.moneda == 'USD'){
						if( totals[0]['MontoUSD'] > 0 && totals[0]['MontoUSD'] <= frm.doc.monto){
							pm_args.pagos = payments;
							pm_args.ID_pago_ZZ = frm.doc.name; 
							pm_args['cuentaBanco'] = d.get_value('cuenta');
							pm_args.numero_de_recibo = frm.doc.numero_de_referencia;
							pm_args.posting_date = frm.doc.fecha_deposito;
							
							var values = d.get_values();
							Crear_Deposito(pm_args,values);
							d.hide();
						}else{
							frappe.msgprint({
								title: __('Advertencia'),
								indicator: 'red',
								message: __('El monto TOTAL FACTURA, no puede ser mayor al monto depositado!')
							});
						}
					}else if (frm.doc.moneda == 'NIO'){
						if(totals[0]['MontoNIO'] <= frm.doc.monto){
							console.log('Entra');
							pm_args.pagos = payments;
							pm_args.ID_pago_ZZ = frm.doc.name; 
							pm_args['cuentaBanco'] = d.get_value('cuenta');
							pm_args.numero_de_recibo = frm.doc.numero_de_referencia;
							pm_args.posting_date = frm.doc.fecha_deposito;
							
							var values = d.get_values();
							Crear_Deposito(pm_args,values);
							d.hide();
						}else{
							frappe.msgprint({
								title: __('Advertencia'),
								indicator: 'red',
								message: __('El monto TOTAL FACTURA, no puede ser mayor al monto depositado!')
							});
						}
					}else{
						frappe.msgprint({
							title: __('Error '),
							indicator: 'red',
							message: __('No ha registrado ningun un deposito')
						});
					}
				}

				
				
			});
		}

		if (frm.doc.docstatus === 0){
            frm.add_custom_button('Aplicar Deposito', function(){
                cur_frm.cscript.AplicarDepostos(frm);
            });
        }
	}
});

frappe.ui.form.on("Pago Sin Identificar", "fecha_deposito", function(frm){
	if (frm.doc.tasa_de_cambio == null){
		// Tasa de CAmbio a la paralela, con depende a la fecha de deposito.
		frappe.db.get_value("Currency Exchange", {"date": frm.doc.fecha_deposito},"paralela",function(res){
			res.paralela;
			// console.log(res.customer);
			frm.set_value('tasa_de_cambio',res.paralela)
			// d.set_value("customer", res.customer);
		})
	}
});

frappe.ui.form.on("Pago Sin Identificar", "monto", function(frm){
	if (frm.doc.saldo== null || frm.doc.saldo){
		frm.set_value('saldo',frm.doc.monto);
	}
	
});

frappe.ui.form.on('Pago Sin Identificar', {
    // frm passed as the first parameter
    after_save(frm) {
        cur_frm.set_df_property('monto', 'read_only',1)
		cur_frm.set_df_property('saldo', 'read_only',1)
	
    }
})