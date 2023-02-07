// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pago Sin Identificar', {
	refresh: function(frm) {

		cur_frm.cscript.AplicarDepostos = function(frm){
			// console.log(frm.doc.cliente);
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
				ignore_event = false,
				TotalesUSD = 0,
				TotalesNIO = 0,
				montosC$ = [],
				montosUSD = [],
				montos = [],
				payments = [],
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

			function render_totals_table(){
				totals.length = 0;
				var tc = flt(d.get_value("conversion_rate"));
				if (d.fields_dict.debits_wrapper.$wrapper.find("#total_usd").length){
					totals.push({
						symbol: '-',
						description: 'Deuda',
						amount_usd: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_usd').text()),
						// amount_nio: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_nio').text()),
						amount_nio: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_actual_nio').text()),
						amount_nioF: norm(d.fields_dict.debits_wrapper.$wrapper.find('#total_nio').text()),
					});
				} else {
                    totals.push({
						symbol: '-',
						description: 'Deuda',
						amount_usd: 0.0,
						amount_nioF:0.0,
						amount_nio: 0.0,

                    });
				}

				if (d.fields_dict.totals_wrapper.$wrapper.find('#pm_total_usd').length){
                    totals.push({
						symbol: '+',
						description: 'Pagos',
						amount_usd: norm(d.fields_dict.totals_wrapper.$wrapper.find('#pm_total_usd').text()),
						amount_nioF: norm(d.fields_dict.totals_wrapper.$wrapper.find('#pm_total_nio').text()),
						amount_nio: norm(d.fields_dict.totals_wrapper.$wrapper.find('#pm_total_nio').text()),

					});
				} else {
                    totals.push({
						symbol: '+',
						description: 'Pagos',
						amount_usd: norm(d.fields_dict.totals_wrapper.$wrapper.find('#pm_total_usd').text()),
						amount_nioF: norm(d.fields_dict.totals_wrapper.$wrapper.find('#pm_total_nio').text()),
						amount_nio: norm(d.fields_dict.totals_wrapper.$wrapper.find('#pm_total_nio').text()),

                    });
				}

				// if (d.fields_dict.credits_wrapper.$wrapper.find("#total_usd").length){
				// 	totals.push({
				// 		symbol: '+',
				// 		description: 'Creditos',
				// 		amount_usd: norm(d.fields_dict.credits_wrapper.$wrapper.find('#total_usd').text()),
				// 		amount_nioF: norm(d.fields_dict.credits_wrapper.$wrapper.find('#total_nio').text()),
				// 		amount_nio: norm(d.fields_dict.credits_wrapper.$wrapper.find('#total_nio').text()),

				// 	});
				// } else {
                //     totals.push({
				// 		symbol: '+',
				// 		description: 'Creditos',
				// 		amount_usd: 0.0,
				// 		amount_nioF: 0.0,
				// 		amount_nio: 0.0,

                //     });
				// }

				var sub_usd = totals.map(function(d){ return (d.symbol === "=" ? 0 : d.amount_usd) * (d.symbol === "-"? -1: 1) }).reduce(function(x, y){ return x + y }, 0),
					sub_nio = totals.map(function(d){ return (d.symbol === "=" ? 0 : d.amount_nio) * (d.symbol === "-"? -1: 1) }).reduce(function(x, y){ return x + y }, 0),
					amount_nioF = totals.map(function(d){ return (d.symbol === "=" ? 0 : d.amount_nioF) * (d.symbol === "-"? -1: 1) }).reduce(function(x, y){ return x + y }, 0);

				totals.push({
                    symbol: '=',
                    description: 'Saldo',
                    amount_usd: sub_usd < 0 ? Math.abs(sub_usd) : 0.0,
					amount_nioF: amount_nioF < 0 ? Math.abs(amount_nioF) : 0.0,
                    amount_nio: sub_nio < 0 ? Math.abs(sub_nio) : 0.0,

                });

				// var change_usd = flt(fields.change_usd.get_value()) + (flt(fields.change_nio.get_value()) / flt(d.get_value('conversion_rate'))),
				// 	change_nio = (flt(fields.change_usd.get_value()) * flt(d.get_value('conversion_rate'))) + flt(fields.change_nio.get_value());

				// var change_usd = 0,
				// change_nio = 0;

				// totals.push({
                //     symbol: '-',
                //     description: 'Cambio',
                //     amount_usd: change_usd,
                //     amount_nio: change_nio,
				// 	amount_nioF:change_nio
                // });

				var customer_usd = totals.map(function(d){ return (d.symbol === "=" ? 0 : d.amount_usd) * (d.symbol === "-"? -1: 1) }).reduce(function(x, y){ return x + y }, 0);
				// var customer_usd = totals.map(function(d){ return (d.symbol === "=" ? 0 : d.amount_usd) * (d.symbol === "-"? -1: 1) }).reduce(function(x, y){ return x + y }, 0),
				// 	customer_nio = totals.map(function(d){ return (d.symbol === "=" ? 0 : d.amount_nio) * (d.symbol === "-"? -1: 1) }).reduce(function(x, y){ return x + y }, 0);

                // totals.push({
                //     symbol: '=',
                //     description: 'Saldo a Favor',
                //     amount_usd: customer_usd > minimal_credit_amount ? customer_usd : 0.0,
                //     amount_nio: customer_usd > minimal_credit_amount ? customer_nio : 0.0,
				// 	amount_nioF:customer_usd > minimal_credit_amount ? customer_nio :0.0
                // });

				var diff_debit = flt(d.fields_dict.debits_wrapper.$wrapper.find('#total_diff').text()),
					diff_credit = flt(d.fields_dict.credits_wrapper.$wrapper.find('#total_diff').text());

				totals.push({
                    symbol: '-',
                    description: 'Diferencial Cambiario',
                    amount_usd: 0.0,
					amount_nioF: (diff_debit - diff_credit) + (customer_usd > 0 && customer_usd < minimal_credit_amount ? customer_usd * flt(d.get_value('conversion_rate')) : 0.0),
                    amount_nio: (diff_debit - diff_credit) + (customer_usd > 0 && customer_usd < minimal_credit_amount ? customer_usd * flt(d.get_value('conversion_rate')) : 0.0),

                });
				// console.log(totals);
                d.fields_dict.totals_wrapper.$wrapper.find("#totals_wrapper").html(frappe.render(tmp_tt_table, {"data": totals}));
				pm_args.pagos = payments;
			}

			function TituloName(name){
				d.fields_dict.TituloName.$wrapper.find("#Nombre").text(name);
			}

			function SumaFormaPagos() {
				var sumaMonto1 =0,sumaMonto2 = 0,sumaMonto1Conver = 0,sumaMonto2Conver = 0;
				console.log(payments);
				totals.length = 0;
				for(let i = 0; i < payments.length; i++){
					if (payments[i]['moneda'] == "C$"){
						console.log("Entra");
						sumaMonto1 += payments[i]['monto'];
						// sumaMonto1Conver = flt(sumaMonto1 * tc[0],2);
					}
					if (payments[i]['moneda'] == "$"){
						sumaMonto2 += payments[i]['monto'];
						// sumaMonto2Conver = flt(sumaMonto2 / tc[0],2);
					}
				}
				// console.log(sumaMonto1,sumaMonto1Conver);
				TotalesNIO = sumaMonto1 + (sumaMonto2 * tc[0]);
				TotalesUSD = flt(sumaMonto2 + sumaMonto1 / tc[0],2);
				// console.log(sumaMonto1,sumaMonto1Conver);
				// sumaMonto
				// console.log(sumaMonto1Conver);
				totals.push({
					MontoUSD: TotalesUSD,
					MontoNIO: TotalesNIO
				});
				// pm_args['deudas'] = [];
				// pm_args['deudas'].push({'link_doctype':'Sales Invoice', 'link_name': d.get_value('Factura')});
				// pm_args.pagos = payments;
				// console.log(tc[0]);
			}

				// function create_payments_areaAnticipo(){
				// 	// var mode_of_payment_field = frappe.ui.form.make_control({
				// 	// 	df: {
				// 	// 		fieldtype: 'Select',
				// 	// 		options: ['','Cheque','Efectivo','Tarjeta'],
				// 	// 		fieldname: 'mode_of_payment',
				// 	// 		label: 'Tipo de Pago',
				// 	// 		// placeholder: 'Tipo de Pago',
				// 	// 		reqd: 1
				// 	// 	},
				// 	// 	parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#mode_of_payment_wrapper").empty(),
				// 	// 	frm: frm,
				// 	// 	doctype: frm.doctype,
				// 	// 	docname: frm.docname,
				// 	// 	only_input: true
				// 	// });
				// 	// mode_of_payment_field.make_input();
				// 	// fields.mode_of_payment = mode_of_payment_field;

				// 	// var currency_field = frappe.ui.form.make_control({
				// 	// 	df: {
				// 	// 		fieldtype: 'Select',
				// 	// 		options: ['','C$','$'],
				// 	// 		fieldname: 'currency',
				// 	// 		label: 'Moneda',
				// 	// 		// placeholder: 'Moneda',
				// 	// 		reqd: 0
				// 	// 	},
				// 	// 	parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#currency_wrapper").empty(),
				// 	// 	frm: frm,
				// 	// 	doctype: frm.doctype,
				// 	// 	docname: frm.docname,
				// 	// 	only_input: true
				// 	// });
				// 	// currency_field.make_input();
				// 	// fields.currency = currency_field;

				// 	// var amount_field = frappe.ui.form.make_control({
				// 	// 	df: {
				// 	// 		fieldtype: 'Float',
				// 	// 		precision: 2,
				// 	// 		fieldname: 'amount',
				// 	// 		label: 'Monto',
				// 	// 		placeholder: 'Monto',
				// 	// 		reqd: 1
				// 	// 	},
				// 	// 	parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#amount_wrapper").empty(),
				// 	// 	frm: frm,
				// 	// 	doctype: frm.doctype,
				// 	// 	docname: frm.docname,
				// 	// 	only_input: true
				// 	// });
				// 	// amount_field.make_input();
				// 	// fields.amount = amount_field;

				// 	// var CambioUSD = frappe.ui.form.make_control({
				// 	// 	df: {
				// 	// 			fieldtype: 'Float',
				// 	// 			precision: 2,
				// 	// 			fieldname: 'montoUSD',
				// 	// 			label: 'USD',
				// 	// 			placeholder: 'Monto $'
				// 	// 		},
				// 	// 		parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#change_usd_wrapper").empty(),
				// 	// 		frm: frm,
				// 	// 		doctype: frm.doctype,
				// 	// 		docname: frm.docname,
				// 	// 		only_input: true
				// 	// 	});
				// 	// 	CambioUSD.make_input();
				// 	// 	CambioUSD.$input.on('change', function(){
				// 	// 		if (CambioUSD.get_value()) {
				// 	// 			// frappe.msgprint("OK");
				// 	// 			console.log(payments);
				// 	// 			var sumUSD = 0;
				// 	// 			var converNIO = 0;
				// 	// 			var converUSD = 0;
				// 	// 			var res = 0;
				// 	// 			for(let i = 0; i < payments.length; i++){
				// 	// 				if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "$"){
				// 	// 					sumUSD += payments[i]['monto'];
				// 	// 					// if (payments[i]['moneda'] == "usd") {
				// 	// 					// 	sumUSD += payments[i]['monto'];
				// 	// 					// }
				// 	// 				}
				// 	// 			}

				// 	// 			if(sumUSD > 0){
				// 	// 				converNIO = sumUSD *  flt(d.get_value("conversion_rate"),2);
				// 	// 				converUSD = flt(CambioUSD.get_value(),2) *  flt(d.get_value("conversion_rate"),2);
				// 	// 				res = flt((-1)* (converNIO - converUSD),2);
				// 	// 				console.log(res);
				// 	// 				if(CambioUSD.get_value() <= sumUSD){
				// 	// 					frappe.msgprint({
				// 	// 						title: __('Advertencia'),
				// 	// 						indicator: 'red',
				// 	// 						message: __('El monto digitado no debe ser menor, al efectivo que recibio!')
				// 	// 					});
				// 	// 					CambioUSD.$input.val(null).trigger("change");
				// 	// 					ResultCambioUSD.$input.val(null).trigger("change");
				// 	// 				}else{
				// 	// 					ResultCambioUSD.$input.val(res).trigger("change");
				// 	// 				}
				// 	// 			}else{
				// 	// 				frappe.msgprint({
				// 	// 					title: __('Advertencia'),
				// 	// 					indicator: 'red',
				// 	// 					message: __('No recibio ningun tipo de pago que sea efectivo!')
				// 	// 				});
				// 	// 				CambioUSD.$input.val(null).trigger("change");
				// 	// 				ResultCambioUSD.$input.val(null).trigger("change");
				// 	// 			}
				// 	// 		}
				// 	// 	});
				// 	// 	fields.montoUSD = CambioUSD;

				// 	// 	var ResultCambioUSD = frappe.ui.form.make_control({
				// 	// 		df: {
				// 	// 			fieldtype: 'Float',
				// 	// 			precision: 2,
				// 	// 			fieldname: 'ResultUSD',
				// 	// 			label: 'USD',
				// 	// 			placeholder: 'Vuelto C$',
				// 	// 			read_only: 1
				// 	// 		},
				// 	// 		parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#change_nio_wrapper").empty(),
				// 	// 		frm: frm,
				// 	// 		doctype: frm.doctype,
				// 	// 		docname: frm.docname,
				// 	// 		only_input: true
				// 	// 	});
				// 	// 	ResultCambioUSD.make_input();
				// 	// 	fields.ResultUSD = ResultCambioUSD;

				// 	// 	var CambioNIO = frappe.ui.form.make_control({
				// 	// 		df: {
				// 	// 			fieldtype: 'Float',
				// 	// 			precision: 2,
				// 	// 			fieldname: 'montoNIO',
				// 	// 			label: 'montoNIO',
				// 	// 			placeholder: 'Monto C$',
				// 	// 			reqd: 0
				// 	// 		},
				// 	// 		parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#CambioNIO_wrapper").empty(),
				// 	// 		frm: frm,
				// 	// 		doctype: frm.doctype,
				// 	// 		docname: frm.docname,
				// 	// 		only_input: true
				// 	// 	});
				// 	// 	CambioNIO.make_input();
				// 	// 	CambioNIO.$input.on('change', function(){
				// 	// 		// render_totals_table();
				// 	// 		// pm_args.cambios = [];

				// 	// 		if (CambioNIO.get_value()) {
				// 	// 			// frappe.msgprint("OK");
				// 	// 			console.log(payments);
				// 	// 			var sumNIO = 0;
				// 	// 			var res = 0;
				// 	// 			var HaytipoPagoEfectivo = false;
				// 	// 			for(let i = 0; i < payments.length; i++){
				// 	// 				if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "C$"){
				// 	// 					sumNIO += payments[i]['monto'];
				// 	// 				}
				// 	// 			}
				// 	// 			console.log(sumNIO);
				// 	// 			if(sumNIO > 0){
				// 	// 				res = flt((-1)* (sumNIO - CambioNIO.get_value()),2);
				// 	// 				// console.log(res);
				// 	// 				if(CambioNIO.get_value() <= sumNIO){
				// 	// 					frappe.msgprint({
				// 	// 						title: __('Advertencia'),
				// 	// 						indicator: 'red',
				// 	// 						message: __('El monto digitado no debe ser menor, al efectivo que recibio!')
				// 	// 					});
				// 	// 					CambioNIO.$input.val(null).trigger("change");
				// 	// 					ResultCambioNIO.$input.val(null).trigger("change");
				// 	// 				}else{
				// 	// 					ResultCambioNIO.$input.val(res).trigger("change");
				// 	// 				}
				// 	// 			}else{
				// 	// 				frappe.msgprint({
				// 	// 					title: __('Advertencia'),
				// 	// 					indicator: 'red',
				// 	// 					message: __('No recibio ningun tipo de pago que sea efectivo!')
				// 	// 				});
				// 	// 				CambioNIO.$input.val(null).trigger("change");
				// 	// 				ResultCambioNIO.$input.val(null).trigger("change");
				// 	// 			}

				// 	// 		}
				// 	// 		// if (change_nio_field.get_value()) {
				// 	// 		// 	pm_args.cambios.push({'monto': flt(change_nio_field.get_value()), 'moneda': 'nio'});
				// 	// 		// }
				// 	// 	});
				// 	// 	fields.montoNIO = CambioNIO;

				// 	// 	var ResultCambioNIO = frappe.ui.form.make_control({
				// 	// 		df: {
				// 	// 			fieldtype: 'Float',
				// 	// 			precision: 2,
				// 	// 			fieldname: 'ResultNIO',
				// 	// 			label: 'montoNIO',
				// 	// 			placeholder: 'Vuelto C$',
				// 	// 			reqd: 0,
				// 	// 			read_only: 1
				// 	// 		},
				// 	// 		parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#ResultCambioNIO_wrapper").empty(),
				// 	// 		frm: frm,
				// 	// 		doctype: frm.doctype,
				// 	// 		docname: frm.docname,
				// 	// 		only_input: true,

				// 	// 	});
				// 	// 	ResultCambioNIO.make_input();
				// 	// 	fields.ResultNIO = ResultCambioNIO;

				// 	//////////////////////////////////////////////////////////////////////////////////////////////////////////

				// 	// toggle_action([mode_of_payment_field, currency_field, amount_field],
				// 	// d.fields_dict.FormasDePagos_wrapper.$wrapper);



				// 	// d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#action").off("click").on("click", function(){
				// 	// 	// if (d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#action").hasClass("hidden")) return;

				// 	// 	// payments.push({
				// 	// 	// 	"tipo_de_pago": mode_of_payment_field.get_value(),
				// 	// 	// 	"moneda": currency_field.get_value(),
				// 	// 	// 	"monto": amount_field.get_value()
				// 	// 	// });
				// 	// 	// // console.log(currency_field.get_value());
				// 	// 	// SumaFormaPagos();
				// 	// 	// function render_payments(){
				// 	// 	// 	d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#payments_wrapper").html(
				// 	// 	// 		frappe.render(tmp_pm_tableAnticipo, {"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0})
				// 	// 	// 	).find("button.remove").off('click').on('click', function(){
				// 	// 	// 		var idx = cint($(this).data('idx'));
				// 	// 	// 		payments.splice(idx,1);
				// 	// 	// 		render_payments();
				// 	// 	// 		SumaFormaPagos();
				// 	// 	// 		// render_totals_table();
				// 	// 	// 	});
				// 	// 	// };
				// 	// 	// render_payments();
				// 	// 	// // tc.push(d.get_value("conversion_rate"));
				// 	// 	// // console.log(tc[0]);
				// 	// 	// mode_of_payment_field.$input.val(null).trigger("change");
				// 	// 	// currency_field.$input.val(null).trigger("change");
				// 	// 	// amount_field.$input.val(null).trigger("change");
				// 	// });
				// }
				function set_sum_on_check(wrapper, dc, data){
					wrapper.find('input[type="checkbox"]').on('change', function(){
						var amounts = {'usd': 0.0, 'nio': 0.0, 'actual_nio': 0.0, 'diff': 0.0};
						// var montos = {'usd': 0.0, 'nio': 0.0, 'actual_nio': 0.0};
						// var montos = [];
						pm_args[dc] = [];
						wrapper.find('input[type="checkbox"]:checked').each(function(){
							pm_args[dc].push({'link_doctype': $(this).data('doctype'), 'link_name': $(this).val()});
							frappe.utils.filter_dict(data, {'name': $(this).val()}).forEach(function(d){
								amounts.usd += d.deuda.usd;
								amounts.nio += d.deuda.nio;
								amounts.actual_nio += d.actual.nio;
								amounts.diff += d.actual.diferencial;
							});
						});
						montos.length = 0;
						montos.push(flt(amounts.usd,2));
						montos.push(flt(amounts.nio,2));
						montos.push(flt(amounts.actual_nio,2));
						// montosUSD.push(amounts.usd);
						// montosC$.push(amounts.actual_nio);
						// montosC$.push(amounts.nio);
						wrapper.find('#total_usd').text(format_currency(amounts.usd, 'USD', 2));
						wrapper.find('#total_nio').text(format_currency(amounts.nio, 'NIO', 2));
						wrapper.find('#total_actual_nio').text(format_currency(amounts.actual_nio, 'NIO', 2));
						wrapper.find('#total_diff').text(amounts.diff.toFixed(2));
						// wrapper.find('#Banco').text(tcB);
						// console.log(montos);
						// selectMonto(montos);
						render_totals_table();
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
								d.set_value('conversion_rate', res.message.saldo.tc);
								d.fields_dict.customer.df.description = res.message.cliente.nombre || '';
								d.fields_dict.customer.set_description();
								minimal_credit_amount = res.message.monto_minimo_credito;
								setTimeout(function(){ ignore_event = false; }, 500);
								create_payments_area(res.message);
							}
						}
					});
				}


				function mostrarFactura(MotoAnticipo){
					// if (d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#action").hasClass("hidden")) return;
					payments.length = 0;
					payments.push({
						"tipo_de_pago": " ",
						"moneda": " ",
						"monto": MotoAnticipo
					});
					// console.log(currency_field.get_value());
					SumaFormaPagos();
					function render_payments(){
						d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#payments_wrapper").html(
							frappe.render(tmp_pm_tableAnticipo, {"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0})
						).find("button.remove").off('click').on('click', function(){
							var idx = cint($(this).data('idx'));
							payments.splice(idx,1);
							render_payments();
							SumaFormaPagos();
							// render_totals_table();
						});
					};
					render_payments();
					// tc.push(d.get_value("conversion_rate"));
					// console.log(tc[0]);
					// mode_of_payment_field.$input.val(null).trigger("change");
					// currency_field.$input.val(null).trigger("change");
					// amount_field.$input.val(null).trigger("change");
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
							change:  function(){
									if(d.get_value('customer')){
										get_outstanding_details();
										// TituloName(res.message.cliente.nombre);
										frappe.db.get_value('Customer', d.get_value('customer'), 'customer_name').then(r => {
											let values = r.message;
											TituloName(values.customer_name);
										})
										// console.log(d.get_value('customer').customer_name)
										// frappe.call({
										// 	// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
										// 	'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.ChecarAnticipo',
										// 	'args': {
										// 		'Customer': d.get_value('customer')
										// 	},
										// 	'callback': function(res){

										// 		console.log(res.message)
										// 		if (res.message == 0){
										// 			frappe.msgprint({
										// 				title: __('Advertencia'),
										// 				indicator: 'red',
										// 				message: __('Lo sentimos, no tiene un anticipo resgistrado!')
										// 			});
										// 			d.set_value("customer",null);
										// 		}else{
										// 			get_exchange();
										// 			// create_payments_areaAnticipo();
										// 			d.set_value("Monto_de_Factura",res.message[0][3]);
										// 			d.set_value("Anticipo",res.message[0][0]);

										// 			frappe.call({
										// 				'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.Factura_Anticipos',
										// 				'args': {
										// 					'Customer': d.get_value('customer')
										// 				},
										// 				'callback': function(r){
										// 					console.log(r.message[0][0])
										// 				d.set_value('Monto_de_FacturaNIO',r.message[0][1])
										// 				d.set_value('Factura',r.message[0][0])
										// 				}
										// 			});
										// 			mostrarFactura(res.message[0][3]);
										// 		}
										// 	}
										// });
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
							// on_make: assign_df_to_input,
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

						// {
						// 	fieldtype: "Int",
						// 	label: "# de Meses de Anticipo",
						// 	precision: 1,
						// 	// options: "Customer",
						// 	fieldname: "Cantidad_Meses",
						// 	// on_make: ,
						// 	change: function () {
						// 		var res = 0;
						// 		var res1 = 0;
						// 		var data = {'total_FacturaUSD':0.0, 'Total_FacturaNIO':0.0};
						// 		d.get_value('Cantidad_Meses');
						// 		d.get_value('Monto_de_Factura');

						// 		res = flt(d.get_value('Cantidad_Meses') * d.get_value('Monto_de_Factura'),2);
						// 		res1 = flt(d.get_value('Cantidad_Meses') * d.get_value('Monto_de_FacturaNIO'),2);
						// 		data.total_FacturaUSD = res;
						// 		data.Total_FacturaNIO = res1;
						// 		set_sum_Totales_Anticipos(data);
						// 		// d.set_value("Monto_de_FacturaNIO",total);
						// 		d.set_value('TotalNIO',res1);
						// 		d.set_value('TotalUSD',res);
						// 	}
						// },
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
							default: frappe.datetime.get_today(),
							fieldname: "posting_date",
							read_only: 1
							// on_make: assign_df_to_input,
							// change: get_outstanding_details
						},
						// {
						// 	fieldtype: "Column Break"
						// 	// fieldtype: "Section Break",
						// 	// label: __("Total")
						// },
						// {
						// 	fieldtype: "Float",
						// 	label: "Total $",
						// 	precision: 2,
						// 	read_only: 1,
						// 	// options: "Customer",
						// 	fieldname: "TotalUSD",
						// 	// on_make: assign_df_to_input,
						// 	// change: get_outstanding_details
						// },
						// {
						// 	fieldtype: "Column Break"
						// 	// fieldtype: "Section Break",
						// 	// label: __("Total")
						// },
						// {
						// 	fieldtype: "Float",
						// 	label: "Total C$",
						// 	precision: 2,
						// 	// options: "Customer",
						// 	fieldname: "TotalNIO",
						// 	read_only: 1,
						// 	// on_make: assign_df_to_input,
						// 	// change: get_outstanding_details
						// },
						{
							// fieldtype: "Column Break",
							fieldtype: "Section Break",
							label: __("Forma de Pagos")
						},
						// {
						// // fieldtype: 'Select',
						// // options: [null].concat(data.tipos_de_pago),
						// // fieldname: 'mode_of_payment',
						// // label: 'Tipo de Pago',
						// // // // placeholder: 'Tipo de Pago',
						// // reqd: 1
						// 	fieldtype: 'Select',
						// 	label: 'Tipo de Pago',
						// 	options: ['Efectivo','Cheque','Tarjeta de Credito'],
						// 	fieldname: "mode_of_payment",
						// 	reqd: 1
						// 	// on_make: assign_df_to_input,
						// 	// change: get_outstanding_details
						// },
						// {
						// 	fieldtype: "Column Break",
						// 	// fieldtype: "Section Break",
						// },
						// {
						// 	fieldtype: 'Select',
						// 	label: 'Moneda',
						// 	options: ['C$','$'],
						// 	fieldname: "currency",
						// 	reqd: 1
						// 	// on_make: assign_df_to_input,
						// 	// change: get_outstanding_details
						// },
						// {
						// 	fieldtype: "Column Break",
						// 	// fieldtype: "Section Break",
						// },
						// {
						// 	fieldtype: 'Float',
						// 	label: 'Monto',
						// 	precision: 2,
						// 	// options: ['C$','$'],
						// 	fieldname: "Monto",
						// 	reqd: 1
						// 	// on_make: assign_df_to_input,
						// 	// change: get_outstanding_details
						// },
						// {
						// 	// fieldtype: "Column Break",
						// 	fieldtype: "Section Break",
						// },
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
			d.set_value('Banco',frm.doc.banco)
			d.set_value('Banco',frm.doc.banco)
			d.set_value('conversion_rate',frm.doc.tasa_de_cambio)
			
			d.show();
			d.$wrapper.find(".modal-dialog").css({"width": "100%","left": "-10%","top": "10%"});
			d.$wrapper.find(".modal-content").css({"width": "160%"});
			// d.$wrapper.find(".modal-dialog").css({"top":"5%"});
			// d.$wrapper.find(".modal-content").css({"width": "120%","left": "-10%"});

			//VALIDACION  DE DEPOSITOS DE BANCOS
			d.get_primary_btn().text('Aplicar Deposito').off('click').on('click', function(){
				// console.log(TotalesNIO);
				// var dc; 
				if (d.get_value('customer') && d.get_value('sales_invoice')){
					payments.push({'link_doctype':'Sales Invoice', 'link_name': d.get_value('sales_invoice')});
					payments2.push({"tipo_de_pago":"Deposito","moneda":d.get_value('moneda'),"monto":d.get_value('Monto')});
					// pm_args['deudas'] = [];
					// pm_args['pagos'] = [];
					pm_args.deudas = payments;
					pm_args.pagos = payments2;

					// pm_args['deudas'].push({'link_doctype':'Sales Invoice', 'link_name': d.get_value('sales_invoice')});
					// pm_args['pagos'].push({"tipo_de_pago":"Deposito","moneda":d.get_value('moneda'),"monto":d.get_value('Monto')});
					pm_args['cuentaBanco'] = d.get_value('cuenta');
					// pagos: [{"tipo_de_pago":"Deposito","moneda":"usd","monto":34.5}]
					// pm_args.pagos = payments;
					var values = d.get_values();
					[
						['customer', 'regnumber'],
						['sales_invoice', 'factura'],
						['conversion_rate', 'tc'],
						['posting_date', 'fecha']
					].forEach(function(pair){
						var v = values[pair[0]];
						if (v) pm_args[pair[1]] = v;
					});
					// console.log(values);
					// console.log(pm_args);
					// var arg = JSON.parse(pm_args);
					var jsonCompleto = JSON.stringify(pm_args);
					console.log(jsonCompleto);
					console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					
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

					d.hide();
				}else{
					frappe.msgprint({
								title: __('Advertencia'),
								indicator: 'red',
								message: __('Debe de seleccionar un cliente!')
							});
				}
				
				// SumaFormaPagos();
				// console.log(totals);
				// // Validacion de montos
				// var total1 = totals[0]['MontoNIO'];
				// var total2 = totals[0]['MontoUSD'];
				// console.log(total1,total2);
				// console.log(montos);
				
				// var js = {};
				// coche.color = "blanco";
				// coche.km = 100000;
				// coche.esNuevo = false;
				// coche.rueda = rueda;

				


				// montos.includes(total1);
				// if (montos.includes(total1) || montos.includes(total2)){
					// PARA APLICAR DEPOSITO
					// console.log("PAso");
					// var values = d.get_values();
					// [
					// 	['customer', 'regnumber'],
					// 	['sales_invoice', 'factura'],
					// 	['conversion_rate', 'tc'],
					// 	['posting_date', 'fecha']
					// ].forEach(function(pair){
					// 	var v = values[pair[0]];
					// 	if (v) pm_args[pair[1]] = v;
					// });
					// pm_args._ui_ = true;
					// console.log(pm_args);
					// console.log('Requisición Aplicar Anticipo');
					// console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					// frappe.call({
					// 	'method': 'erpnext.api.aplicar_Anticipos',
					// 	'args': pm_args,
					// 	'callback': function(res){
					// 		if (res.message) {
					// 			if (res.message.accounts.length && !res.message.messages.length){
					// 				res.message.accounts.forEach(function(c){
					// 					frm.add_child("accounts", c);
					// 				});
					// 				cur_frm.refresh_fields()
					// 				cur_frm.set_value("posting_date", pm_args.fecha);
					// 				cur_frm.set_value("multi_currency", 1);
					// 				// cur_frm.set_value("customer",pm_args.regnumber);
					// 				cur_frm.set_value("tasa_de_cambio",pm_args.tc);
					// 				// cur_frm.set_value("meses_anticipo",d.get_value('Cantidad_Meses'));
					// 				cur_frm.set_value("codigoanticipo",d.get_value('Anticipo'));
					// 				cur_frm.set_value("tipo_de_pago","Aplicar Anticipo");
					// 				// cur_frm.set_value("title","Anticipo");
					// 				cur_frm.trigger("validate");


					// 				// No cambiar
					// 				series[frappe.user.name] && frm.doc.__islocal && frm.set_value('naming_series', series[frappe.user.name]);
					// 				frm.toggle_enable('naming_series', false);
					// 				d.hide();
					// 			} else {
					// 				frappe.msgprint(res.message.messages.join("<br/>"));
					// 			}
					// 		}
					// 	}
					// });
				// } else {
				// 	frappe.msgprint({
				// 		title: __('Advertencia'),
				// 		indicator: 'red',
				// 		message: __('No es igual a los montos totales!')
				// 	});
				// 	// frappe.msgprint("No es igual a los montos totales!");
				// };

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
