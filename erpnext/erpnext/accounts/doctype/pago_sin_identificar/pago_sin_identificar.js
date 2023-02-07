// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pago Sin Identificar', {
	refresh: function(frm) {

		

		cur_frm.cscript.AplicarDepostio = function(frm){
            function aplicar_Pagos (values){
					// var values = d.get_values();
					// console.log(pm_args);
					[
						['customer', 'regnumber'],
						['sales_invoice', 'factura'],
						['conversion_rate', 'tc'],
						['posting_date', 'fecha']
					].forEach(function(pair){
						var v = values[pair[0]];
						if (v) pm_args[pair[1]] = v;
					});
					pm_args._ui_ = true;

					console.log('Requisición Aplicar Pago');
					console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					console.log(Cambios);
					frappe.call({
						'method': 'erpnext.api.aplicar_pago',
						'args': pm_args,
						'callback': function(res){
							console.log(res.message);
							if (res.message) {
								if (res.message.accounts.length && !res.message.messages.length){
									res.message.accounts.forEach(function(c){
										frm.add_child("accounts", c);
									});
									cur_frm.refresh_fields()
									cur_frm.set_value("posting_date", pm_args.fecha);
									cur_frm.set_value("multi_currency", 1);
									// cur_frm.set_value("monto_recibido_dolares", fields.montoUSD.get_value());
									// cur_frm.set_value("monto_recibido_cordobas", fields.montoNIO.get_value());
									if (fields.montoUSD.get_value() == null && fields.montoNIO.get_value() == null) {
										cur_frm.set_df_property('monto_recibido_dolares', 'read_only', 1)
										cur_frm.set_df_property('monto_recibido_cordobas', 'read_only', 1)
										cur_frm.set_df_property('vuelto_en_dolares', 'read_only',1)
										cur_frm.set_df_property('vuelto_en_cordobas', 'read_only',1)
									}else{
										cur_frm.set_value("monto_recibido_dolares", fields.montoUSD.get_value());
										cur_frm.set_value("monto_recibido_cordobas", fields.montoNIO.get_value());
										cur_frm.set_value("vuelto_en_dolares", Cambios.CambioUSD);
										cur_frm.set_value("vuelto_en_cordobas", Cambios.CambioNIO);
									}
									
									cur_frm.trigger("validate");

									// No cambiar
									series[frappe.user.name] && frm.doc.__islocal && frm.set_value('naming_series', series[frappe.user.name]);
									frm.toggle_enable('naming_series', false);
									d.hide();
								} else {
									frappe.msgprint(res.message.messages.join("<br/>"));
								}
							}
						}
					});
			}

			function ValidarCamposDigitados (pm_args,tipopago,monedaNIO,monedaUSD,values){
				for(let i = 0; i < pm_args.pagos.length; i++){
					if (pm_args.pagos[i]['tipo_de_pago'] == "Efectivo"){
						console.log("Entra");
						// tipopago = true;
						if (pm_args.pagos[i]['moneda'] == "nio"){
							monedaNIO = true;
							tipopago = true;
						}
						if (pm_args.pagos[i]['moneda'] == "usd"){
							monedaUSD = true;
							tipopago = true;
						}
					}
				}
				// Recibio en efectivo
				if (tipopago == true ) {

					if (monedaNIO && monedaUSD) {
						if(fields.montoUSD.get_value() == null && fields.montoNIO.get_value() == null){
							frappe.msgprint("Debe de Digitar los monto que recibo de Dolares y Cordobas");
						}else if (fields.montoUSD.get_value() == null){
							frappe.msgprint("Debe de Digitar el monto que recibo de Dolares");
						}else if (fields.montoNIO.get_value() == null) {
							frappe.msgprint("Debe de Digitar el monto que recibo de Cordobas");
						} else {
							// frappe.msgprint("PAso");
							// var values = d.get_values();
							aplicar_Pagos(values);
						}
					}else if (monedaNIO) {
						if (fields.montoNIO.get_value() == null){
							frappe.msgprint("Debe de Digitar el monto que recibo en Cordobas");
						}else{
							// frappe.msgprint("PAso");
							// var values = d.get_values();
							aplicar_Pagos(values);
						}
					}
					else if(monedaUSD){
						if (fields.montoUSD.get_value() == null){
							frappe.msgprint("Debe de Digitar el monto que recibo de Dolares");
						}else{
							// frappe.msgprint("PAso");
							// var values = d.get_values();
							aplicar_Pagos(values);
						}
					}
				}else{
					// frappe.msgprint("Es otro tipo de pago");
					// var values = d.get_values();
					aplicar_Pagos(values);
				}
			}

			function ObtenerTCBanco (){
				return TCBanco
			}

			var d,
				ignore_event = false,
				TCBanco =0,
				montosC$,
				montosUSD,
				montos = [],
				payments = [],
				totals = [],
				Cambios = {},
				fields = {},
				pm_args = {},
				minimal_credit_amount = 0.0,
				series = {
					"leyda.calderon@ibw.com": "F-",
					"hegarcia@ibw.com": "I-",
					"jacquelines.martinez@ibw.com": "H-"
                },
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
				   <th>Tipo de Pago</th>
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
				   <td>{{ row.tipo_de_pago }}</th>
				   <td>{{ {"nio": "C$", "usd": "$"}[row.moneda] }}</th>
				   <td class="text-right">{{ format_currency(row.moneda === "usd" ? flt(row.monto) : flt(row.monto) / flt(tc,2), "USD", 2) }}</th>
				   <td class="text-right">{{ format_currency(row.moneda === "usd" ? flt(row.monto) * flt(tc) : flt(row.monto), "NIO", 2) }}</th>
				   <td><button class="btn btn-danger btn-xs remove" data-idx="{{ i }}"><span class="icon icon-remove">
				 	<svg class="icon icon-sm" style>
						<use class href="#icon-delete"></use>
					</svg>
				   </span></button>
				   </td>
				 </tr>
				 {% totals.pm_total_usd += (row.moneda === "usd" ? flt(row.monto) : flt(row.monto) / flt(tc)) %}
				 {% totals.pm_total_nio += (row.moneda === "usd" ? flt(row.monto) * flt(tc) : flt(row.monto)) %}
				 {% } %}
			   </tbody>
			   <tbody>
				 <tr>
				   <th colspan="2" class="centrado">&nbsp; TOTAL 2</th>
				   <th class="text-right" id="pm_total_usd">{{ format_currency(totals.pm_total_usd, "USD", 2) }}</th>
				   <th class="text-right" id="pm_total_nio">{{ format_currency(totals.pm_total_nio, "NIO", 2) }}</th>
				   <th>&nbsp;</th>
				 </tr>
			   </tbody>
			</table>`,
			tmp_tt_table = `<table class="table table-condensed table-bordered">
				<thead>
					<tr>
						<th colspan="2">&nbsp;</th>
						<th class="text-right">Monto $</th>
						<th class="text-right">Monto C$ TC Factura</th>
						<th class="text-right">Monto C$ TC del dia</th>
					</tr>
				</thead>
				<tbody>
					{% var cls = {"=": "", "+": "text-success", "-": "text-danger"} %}
					{% for (var row of data) { %}
					<tr>
						<td class="{{ cls[row.symbol] }}">{{ row.symbol }}</td>
						<td class="{{ cls[row.symbol] }}">{{ row.description }}</td>
						<td class="text-right {{ cls[row.symbol] }}">{{ format_currency(row.amount_usd, "USD", 2) }}</td>
						<td class="text-right {{ cls[row.symbol] }}">{{ format_currency(row.amount_nioF, "NIO", 2) }}</td>
						<td class="text-right {{ cls[row.symbol] }}">{{ format_currency(row.amount_nio, "NIO", 2) }}</td>
					</tr>
					{% } %}
				</tbody>
			</table>`;

			function assign_df_to_input(df){
				df.refresh();
				df.$input.data('df', df);
			}

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

			function TCBAnco(tcB){
				d.fields_dict.totals_wrapper.$wrapper.find("#Banco").text(tcB);
					// wrapper.find('#Banco').text(tcB);
				
			}

			function TituloName(name){
				d.fields_dict.TituloName.$wrapper.find("#Nombre").text(name);
			}

			function norm(v){
				return flt((v.split("$ ")[1]||"").replace(/\,/gi, ""));
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
				d.fields_dict.credits_wrapper.$wrapper.empty();

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
								TCBAnco(res.message.TCBanco);
								TCBanco = res.message.TCBanco;
								TituloName(res.message.cliente.nombre);
							}
							if (res.message.creditos.length) {
								d.fields_dict.credits_wrapper.$wrapper.html(frappe.render(
									tmp_dc_table, {data: res.message, dc: "creditos"}
								));
								set_sum_on_check(d.fields_dict.credits_wrapper.$wrapper, 'creditos', res.message.creditos);
							}
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

			function toggle_actionCambio(fields, wrapper){
				fields.forEach(function(df){
					df.$input.on('change', function(){
						wrapper.find('#actionLimpiarText').removeClass('hidden');
					});
				});
			}

			function create_payments_area(data){
				var mode_of_payment_field = frappe.ui.form.make_control({
					df: {
						fieldtype: 'Select',
						options: [null].concat(data.tipos_de_pago),
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


				var currency_field = frappe.ui.form.make_control({
					df: {
						fieldtype: 'Select',
						options: [null].concat(data.monedas),
						fieldname: 'currency',
						label: 'Moneda',
						// placeholder: 'Moneda',
						reqd: 0
					},
					parent: d.fields_dict.totals_wrapper.$wrapper.find("#currency_wrapper").empty(),
					frm: frm,
					doctype: frm.doctype,
					docname: frm.docname,
					only_input: true
				});
				currency_field.make_input();
				fields.currency = currency_field;

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

				var CambioNIO = frappe.ui.form.make_control({
					df: {
						fieldtype: 'Float',
						precision: 2,
						fieldname: 'montoNIO',
						label: 'montoNIO',
						placeholder: 'Monto C$',
						reqd: 0
					},
					parent: d.fields_dict.totals_wrapper.$wrapper.find("#CambioNIO_wrapper").empty(),
					frm: frm,
					doctype: frm.doctype,
					docname: frm.docname,
					only_input: true
				});
				CambioNIO.make_input();
				CambioNIO.$input.on('change', function(){
                    // render_totals_table();
                    // pm_args.cambios = [];

					if (CambioNIO.get_value()) {
						// frappe.msgprint("OK");

						var sumNIO = 0;
						var res = 0;
						var HaytipoPagoEfectivo = false;
						for(let i = 0; i < payments.length; i++){
							if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "nio"){
								sumNIO += payments[i]['monto'];
								// HaytipoPagoEfectivo = true;
								// if(payments[i]['moneda'] == "nio"){
								// 	sumNIO += payments[i]['monto'];
								// }
							}
							// else{
							// 	HaytipoPagoEfectivo = false;
							// }
						}
						console.log(sumNIO);
						if(sumNIO > 0){
							res = flt((-1)* (sumNIO - CambioNIO.get_value()),2);
							// console.log(res);
							if(CambioNIO.get_value() < sumNIO){
								frappe.msgprint({
									title: __('Advertencia'),
									indicator: 'red',
									message: __('El monto digitado en Cordobas no debe ser menor, al efectivo que recibio!')
								});
								CambioNIO.$input.val(null).trigger("change");
							}else{
								// ResultCambioNIO.set_value(res);
								ResultCambioNIO.$input.val(res).trigger("change");
								// fields.ResultNIO.set_value(res);
								Cambios.CambioNIO = res;
							}
						}else{
							frappe.msgprint({
								title: __('Advertencia'),
								indicator: 'red',
								message: __('No recibio ningun tipo de pago que sea efectivo en Cordobas!')
							});
							CambioNIO.$input.val(null).trigger("change");
						}

					}
					// if (change_nio_field.get_value()) {
					// 	pm_args.cambios.push({'monto': flt(change_nio_field.get_value()), 'moneda': 'nio'});
					// }
                });
				fields.montoNIO = CambioNIO;

				var ResultCambioNIO = frappe.ui.form.make_control({
					df: {
						fieldtype: 'Float',
						precision: 2,
						fieldname: 'ResultNIO',
						label: 'montoNIO',
						placeholder: 'Vuelto C$',
						reqd: 0,
						read_only: 1
					},
					parent: d.fields_dict.totals_wrapper.$wrapper.find("#ResultCambioNIO_wrapper").empty(),
					frm: frm,
					doctype: frm.doctype,
					docname: frm.docname,
					only_input: true,

				});
				ResultCambioNIO.make_input();
				fields.ResultNIO = ResultCambioNIO;

				//////////////////////////////////////////////////////////////////

				var CambioUSD = frappe.ui.form.make_control({
					df: {
							fieldtype: 'Float',
							precision: 2,
							fieldname: 'montoUSD',
							label: 'USD',
							placeholder: 'Monto $'
						},
						parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_usd_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					CambioUSD.make_input();
					CambioUSD.$input.on('change', function(){
						if (CambioUSD.get_value()) {
							// frappe.msgprint("OK");
							montosUSD = CambioUSD.get_value();
							// console.log();
							// console.log(payments);
							var sumUSD = 0;
							var tc=0;
							var converNIO = 0;
							var converUSD = 0;
							var cambioUSD = 0;
							var res = 0;
							for(let i = 0; i < payments.length; i++){
								if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "usd"){
									sumUSD += payments[i]['monto'];
									// if (payments[i]['moneda'] == "usd") {
									// 	sumUSD += payments[i]['monto'];
									// }
								}
							}

							if(sumUSD > 0){
								// converNIO = sumUSD *  d.get_value("conversion_rate");
								tc = ObtenerTCBanco();
								converNIO = sumUSD *  tc;
								
								// converUSD = CambioUSD.get_value() *  d.get_value("conversion_rate");
								converUSD = CambioUSD.get_value() * tc;
								res = flt((-1)* (converNIO - converUSD),2);
								cambioUSD = flt(CambioUSD.get_value() - sumUSD,2);
								console.log(res);
								if(CambioUSD.get_value() < sumUSD){
									frappe.msgprint({
										title: __('Advertencia'),
										indicator: 'red',
										message: __('El monto digitado en Dolares no debe ser menor, al efectivo que recibio!')
									});
									// ResultCambioUSD.$input.val(null).trigger("change");
									CambioUSD.$input.val(null).trigger("change");
								}else{
									ResultCambioUSD.$input.val(res).trigger("change");
									ResultCambioUSD_USD.$input.val(cambioUSD).trigger("change");
									Cambios.CambioUSD = cambioUSD;
								}
							}else{
								frappe.msgprint({
									title: __('Advertencia'),
									indicator: 'red',
									message: __('No recibio ningun tipo de pago que sea efectivo en Dolares!')
								});
								// ResultCambioUSD.$input.val(null).trigger("change");
								CambioUSD.$input.val(null).trigger("change");
								// ResultCambioUSD_USD.$input.val(cambioUSD).trigger("change");
							}
						}
					});
					fields.montoUSD = CambioUSD;

					var ResultCambioUSD = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Float',
							precision: 2,
							fieldname: 'ResultUSD',
							label: 'USD',
							placeholder: 'Vuelto C$',
							read_only: 1
						},
						parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_nio_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					ResultCambioUSD.make_input();
					fields.ResultUSD = ResultCambioUSD;

					var ResultCambioUSD_USD = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Float',
							precision: 2,
							fieldname: 'ResultCambioUSD_USD',
							label: 'USD',
							placeholder: 'Vuelto $',
							read_only: 1
						},
						parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_usd_usd_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					ResultCambioUSD_USD.make_input();
					fields.ResultUSD_USD = ResultCambioUSD_USD;

                /////////////////////////////////////////////////////////////////
				// var change_usd_field = frappe.ui.form.make_control({
				// df: {
				// 		fieldtype: 'Float',
				// 		precision: 2,
				// 		fieldname: 'change_usd',
				// 		label: 'USD',
				// 		placeholder: '$'
				// 	},
				// 	parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_usd_wrapper").empty(),
				// 	frm: frm,
				// 	doctype: frm.doctype,
				// 	docname: frm.docname,
				// 	only_input: true
				// });
				// change_usd_field.make_input();
				// change_usd_field.$input.on('change', function(){
                //     render_totals_table();
                //     pm_args.cambios = [];
				// 	if (change_usd_field.get_value()) {
                //         pm_args.cambios.push({'monto': flt(change_usd_field.get_value()), 'moneda': 'usd'});
				// 	}
				// 	if (change_nio_field.get_value()) {
				// 		pm_args.cambios.push({'monto': flt(change_nio_field.get_value()), 'moneda': 'nio'});
				// 	}
                // });
				// fields.change_usd = change_usd_field;

				// var change_nio_field = frappe.ui.form.make_control({
				// 	df: {
				// 		fieldtype: 'Float',
				// 		precision: 2,
				// 		fieldname: 'change_nio',
				// 		label: 'USD',
				// 		placeholder: 'C$'
				// 	},
				// 	parent: d.fields_dict.totals_wrapper.$wrapper.find("#change_nio_wrapper").empty(),
				// 	frm: frm,
                //     doctype: frm.doctype,
				// 	docname: frm.docname,
				// 	only_input: true
				// });
				// change_nio_field.make_input();
				// change_nio_field.$input.on('change', function(){
				// 	render_totals_table();
				// 	pm_args.cambios = [];
				// 	if (change_usd_field.get_value()) {
                //         pm_args.cambios.push({'monto': flt(change_usd_field.get_value()), 'moneda': 'usd'});
				// 	}
				// 	if (change_nio_field.get_value()) {
				// 		pm_args.cambios.push({'monto': flt(change_nio_field.get_value()), 'moneda': 'nio'});
				// 	}
				// });
				// fields.change_nio = change_nio_field;

				toggle_action([mode_of_payment_field, currency_field, amount_field],
					d.fields_dict.totals_wrapper.$wrapper);



					// console.log(amount_field.get_value());
				//AQUI
				d.fields_dict.totals_wrapper.$wrapper.find("#action").off("click").on("click", function(){
					if (d.fields_dict.totals_wrapper.$wrapper.find("#action").hasClass("hidden")) return;

					payments.push({
						"tipo_de_pago": mode_of_payment_field.get_value(),
						"moneda": currency_field.get_value(),
						"monto": amount_field.get_value()
					});

					function render_payments(){
						d.fields_dict.totals_wrapper.$wrapper.find("#payments_wrapper").html(
							frappe.render(tmp_pm_table, {"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0})
						).find("button.remove").off('click').on('click', function(){
							var idx = cint($(this).data('idx'));
							payments.splice(idx,1);
							render_payments();
							render_totals_table();
						});
					};
					render_payments();
					render_totals_table();
					mode_of_payment_field.$input.val(null).trigger("change");
					currency_field.$input.val(null).trigger("change");
					amount_field.$input.val(null).trigger("change");

					// IMPORTANTE
					// console.log({"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0});

					///////////////////////////////////////////////////////////////////
					// var num = amount_field.get_value();
					// console.log(num);
					// if(montos.includes(num)){
					// 		console.log("Valida el arreglo");
					// 		if (d.fields_dict.totals_wrapper.$wrapper.find("#action").hasClass("hidden")) return;

					// 	payments.push({
					// 		"tipo_de_pago": mode_of_payment_field.get_value(),
					// 		"moneda": currency_field.get_value(),
					// 		"monto": amount_field.get_value()
					// 	});

					// 	function render_payments(){
					// 		d.fields_dict.totals_wrapper.$wrapper.find("#payments_wrapper").html(
					// 			frappe.render(tmp_pm_table, {"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0})
					// 		).find("button.remove").off('click').on('click', function(){
					// 			var idx = cint($(this).data('idx'));
					// 			payments.splice(idx,1);
					// 			render_payments();
					// 			render_totals_table();
					// 		});
					// 	};
					// 	console.log({"data": payments, "tc": flt(d.get_value("conversion_rate")) || 1.0});
					// 	render_payments();
					// 	render_totals_table();
					// 	mode_of_payment_field.$input.val(null).trigger("change");
					// 	currency_field.$input.val(null).trigger("change");
					// 	amount_field.$input.val(null).trigger("change");
					// }else {
					// 	frappe.msgprint('Lo sentimos no es igual a los montos totales');
					// 	console.log("No paso");
					// 	// render_payments();
					// 	// render_totals_table();
					// 	mode_of_payment_field.$input.val(null).trigger("change");
					// 	currency_field.$input.val(null).trigger("change");
					// 	amount_field.$input.val(null).trigger("change");
					// }
					//////////////////////////////////////////////////////////////////////////


				});
				// Validacion de boton limppiar
				toggle_actionCambio([CambioNIO, ResultCambioUSD_USD, ResultCambioUSD,CambioUSD,ResultCambioNIO],
					d.fields_dict.totals_wrapper.$wrapper);

				d.fields_dict.totals_wrapper.$wrapper.find("#actionLimpiarText").off("click").on("click", function(){
					if (d.fields_dict.totals_wrapper.$wrapper.find("#actionLimpiarText").hasClass("hidden")) return;
					CambioNIO.$input.val(null).trigger("change");
					ResultCambioUSD_USD.$input.val(null).trigger("change");
					ResultCambioUSD.$input.val(null).trigger("change");
					CambioUSD.$input.val(null).trigger("change");
					ResultCambioNIO.$input.val(null).trigger("change");
				});
			}

			d = new frappe.ui.Dialog({
				title: __("Aplicar Pago"),
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
						change: get_outstanding_details
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
						fieldtype: "Date",
						label: "Fecha",
						default: frappe.datetime.get_today(),
						fieldname: "posting_date",
						on_make: assign_df_to_input,
						read_only: 1,
						// change: get_outstanding_details
					},
					{
						fieldtype: "Column Break"
					},
					{
						fieldtype: "Float",
						fieldname: "conversion_rate",
						label: "TC",
						read_only: 1,
						on_make: assign_df_to_input,
						change: get_outstanding_details
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
					// {
					// 	fieldtype: "Section Break",
					// 	label: __("Créditos")
					// },
					{
						fieldtype: "HTML",
						fieldname: "credits_wrapper",
						options: `<div class="row">
				 <div id="credits_wrapper" class="col-sm-12 col-md-12 col-lg-12 col-xl-12"></div>
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
						<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" style="padding-left: 0px;"> Moneda</div>
					</div>

				   <div class="row">
							<div class="col-sm-12 col-md-4 col-lg-4 col-xl-4" id="mode_of_payment_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-2 col-md-2 col-lg-2 col-xl-2" id="currency_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-4 col-md-3 col-lg-3  col-xl-3" id="amount_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-2 col-md-2 col-lg-2 col-xl-2" id="action_wrapper" style="padding-left: 0px;">
								<button class="btn btn-primary hidden" role="button" id="action">Agregar</button>
							</div>
						</div>
						<br>
						<div class="row" id="payments_wrapper"></div>
						<div class="row">
							
							<div class="col-sm-12 col-md-12 col-lg-12 col-xl-12 text-center" style="padding-left: 0px;" >
								<h5>TC Banco</h5>
							</div>
							<div class="col-sm-12 col-md-12 col-lg-12 col-xl-12 text-center" style="padding-left: 0px;">
								<h5 id="Banco"></h5>
							</div>
							</br>
							<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" style="padding-left: 0px;">RECIBIDO</div>
								<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" style="padding-left: 0px;">Vuelto en C$</div>
								<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" style="padding-left: 0px;">Vuelto en $</div>
					  </div>
					  <div class="row" id="change_wrapper">
						 <div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" id="change_usd_wrapper" style="padding-left: 0px;"></div>
						 <div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" id="change_nio_wrapper" style="padding-left: 0px;"></div>
						 <div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" id="change_usd_usd_wrapper" style="padding-left: 0px;"></div>
						 <div class="col-sm-4 col-md-4 col-lg-4 col-xl-4 mt-2" id="CambioNIO_wrapper" style="padding-left: 0px;"></div>
						 <div class="col-sm-4 col-md-4 col-lg-4 col-xl-4 mt-2" id="ResultCambioNIO_wrapper" style="padding-left: 0px;"></div>
						 <div class="col-sm-4 col-md-4 col-lg-4 col-xl-4 mt-2"  id="actionLimpiarText_wrapper" style="padding-left: 0px;">
						 	<button class="btn btn-primary hidden" role="button" id="actionLimpiarText">Limpiar</button>
						 </div>
				  </div>
				   </div>
				   <div class="col-sm-12 col-md-6 col-lg-6 col-xl-6" style="padding-right: 0px;" id="totals_wrapper"></div>
			   </div>`
					}
					// {
					// 	label: __("Dados Adicionales"),
					// 	fieldtype: "Section Break"
					// },
					// {
					// 	label: __("Colector"),
					// 	fieldtype: "Link",
					// 	options: "colectores",
					// 	fieldname: "name",
					// 	change: function(){
					// 		if (!d.get_value("name")) {
					// 			d.fields_dict.colectores.df.description = '';
					// 			d.fields_dict.colectores.set_description();
					// 			d.set_value("serie", "");
					// 			d.set_value("__newname", "");
					// 		} else {
					// 			frappe.call({
					// 				'method': 'frappe.client.get_value',
					// 				'args': {
					// 					'doctype': 'colectores',
					// 					'fieldname': ['name', 'serie'],
					// 					'filters': {'name': d.get_value('colectores')}
					// 				},
					// 				'callback': function(res){
					// 					d.fields_dict.colectores.df.description = res.message.name || '';
					// 					d.fields_dict.colectores.set_description();
					// 					d.set_value("serie", res.message.serie);
					// 				}
					// 			});
					// 		}
					// 	}
					// },
					// {
					// 	fieldtype: 'Column Break'
					// },
					// {
					// 	label: __("Serie Colector"),
					// 	fieldtype: "Data",
					// 	fieldname: "serie"
					// },
					// {
					// 	fieldtype: 'Column Break'
					// },
					// {
					// 	label: __("Nro del Comprovante del Collector"),
					// 	fieldtype: "Int",
					// 	fieldname: "__newname"
					// },
				],
				primary_action_label: __("Create Payment"),
				primary_action: function(){
					d.hide();
				},
				secondary_action_label: __("Cancel")
			}),




			d.get_field("sales_invoice").get_query = function(){
				var customer = d.get_value("customer"), filters = {'docstatus': 1, 'outstanding_amount': ['!=', 0]};
				if (customer){ filters['customer'] = customer; };
				return {'filters': filters};
			};


			// d.get_field("Colectores").get_query = function(){
			// 	return {'filters': {'collector_type': 'Colector'}};
			// }

			d.show();
			d.$wrapper.find(".modal-dialog").css({"width": "100%","left": "-10%","top": "10%"});
			d.$wrapper.find(".modal-content").css({"width": "160%"});

			// PAGOS VALIDACION
			d.get_primary_btn().text('Crear Pago').off('click').on('click', function(){
				// console.log(totals[1]);
				// Validacion de montos
				var total1 = totals[1]['amount_nio'];
				var total2 = totals[1]['amount_usd'];
				var tipopago = 0;
				var Monto_DigitadoNIO = false;
				var Monto_DigitadoUSD = false;
				var monedaNIO = false;
				var monedaUSD = false;
				console.log(total1,total2);
				console.log(montos);

				for(let i = 0; i < montos.length; i++){
					if (montos[i] == total1){
						Monto_DigitadoNIO = true;
					}
				}

				for(let i = 0; i < montos.length; i++){
					if (montos[i] == total2){
						Monto_DigitadoUSD = true;
					}
				}
				// monedaNIO = "No entra";
				// if (montos[2] == flt(total1,2)){
				// 	monedaNIO = true;
				// };



				// console.log(Monto_Digitado);

				// montos.includes(total1);
				// if (montos.includes(total1) || montos.includes(total2))
				if (Monto_DigitadoNIO == true && Monto_DigitadoUSD == true){
					// console.log(pm_args.pagos);
					var values = d.get_values();
					ValidarCamposDigitados(pm_args,tipopago,monedaNIO,monedaUSD,values);
					// for(let i = 0; i < pm_args.pagos.length; i++){
					// 	if (pm_args.pagos[i]['tipo_de_pago'] == "Efectivo"){
					// 		console.log("Entra");
					// 		// tipopago = true;
					// 		if (pm_args.pagos[i]['moneda'] == "nio"){
					// 			monedaNIO = true;
					// 			tipopago = true;
					// 		}
					// 		if (pm_args.pagos[i]['moneda'] == "usd"){
					// 			monedaUSD = true;
					// 			tipopago = true;
					// 		}

					// 		// sumaMonto1Conver = flt(sumaMonto1 * tc[0],2);
					// 	}
					// 	// if (payments[i]['moneda'] == "$"){
					// 	// 	sumaMonto2 += payments[i]['monto'];
					// 	// 	// sumaMonto2Conver = flt(sumaMonto2 / tc[0],2);
					// 	// }
					// }


					// // console.log(tipopago);
					// // Recibio en efectivo
					// if (tipopago == true ) {

					// 	if (monedaNIO && monedaUSD) {
					// 		if(fields.montoUSD.get_value() == null && fields.montoNIO.get_value() == null){
					// 			frappe.msgprint("Debe de Digitar los monto que recibo de Dolares y Cordobas");
					// 		}else if (fields.montoUSD.get_value() == null){
					// 			frappe.msgprint("Debe de Digitar el monto que recibo de Dolares");
					// 		}else if (fields.montoNIO.get_value() == null) {
					// 			frappe.msgprint("Debe de Digitar el monto que recibo de Cordobas");
					// 		} else {
					// 			// frappe.msgprint("PAso");
					// 			var values = d.get_values();
					// 			aplicar_Pagos(values);
					// 		}
					// 	}else if (monedaNIO) {
					// 		if (fields.montoNIO.get_value() == null){
					// 			frappe.msgprint("Debe de Digitar el monto que recibo en Cordobas");
					// 		}else{
					// 			// frappe.msgprint("PAso");
					// 			var values = d.get_values();
					// 			aplicar_Pagos(values);
					// 		}
					// 	}
					// 	else if(monedaUSD){
					// 		if (fields.montoUSD.get_value() == null){
					// 			frappe.msgprint("Debe de Digitar el monto que recibo de Dolares");
					// 		}else{
					// 			// frappe.msgprint("PAso");
					// 			var values = d.get_values();
					// 			aplicar_Pagos(values);
					// 		}
					// 	}

					// 	// if (fields.montoUSD.get_value() == null){
					// 	// 	frappe.msgprint("Debe de Digitar el monto que recibo de Dolares");
					// 	// }else if (fields.montoNIO.get_value() == null) {
					// 	// 	frappe.msgprint("Debe de Digitar el monto que recibo de Cordobas");
					// 	// } else {
					// 	// 	frappe.msgprint("PAso");
					// 	// }


					// }else{
					// 	// frappe.msgprint("Es otro tipo de pago");
					// 	var values = d.get_values();
					// 	aplicar_Pagos(values);
					// }


						// if pm_args.pagos
					// var values = d.get_values();
					// console.log(pm_args);
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

					// console.log('Requisición Aplicar Pago');
					// console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					// console.log(fields.montoUSD.get_value());
					// frappe.call({
					// 	'method': 'erpnext.api.aplicar_pago',
					// 	'args': pm_args,
					// 	'callback': function(res){
					// 		console.log(res.message);
					// 		if (res.message) {
					// 			if (res.message.accounts.length && !res.message.messages.length){
					// 				res.message.accounts.forEach(function(c){
					// 					frm.add_child("accounts", c);
					// 				});
					// 				cur_frm.refresh_fields()
					// 				cur_frm.set_value("posting_date", pm_args.fecha);
					// 				cur_frm.set_value("multi_currency", 1);
					// 				cur_frm.set_value("monto_recibido_dolares", fields.montoUSD.get_value());
					// 				cur_frm.set_value("monto_recibido_cordobas", fields.montoNIO.get_value());
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
				}else if (Monto_DigitadoNIO == true && montos.includes(total1)){
					var values = d.get_values();
					ValidarCamposDigitados(pm_args,tipopago,monedaNIO,monedaUSD,values);
				} else {
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No es igual a los montos totales!')
					});
					// frappe.msgprint("No es igual a los montos totales!");
				};

			});
		};

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
				tmp_pm_tableAnticipo = `<table class="table table-condensed table-bordered">
				<thead>
				  <tr>
				  	<th> </th>
					<th class="text-right">Monto $</th>
					<th class="text-right">Monto C$</th>
				  </tr>
				</thead>
				<tbody>
				  {% var totals = {"pm_total_usd": 0.0, "pm_total_nio": 0.0}; %}
				  {% for (var i = 0, l = data.length; i < l; i++) { %}
				  {% var row = data[i]; %}
				  <tr>
				  	<th> </th>
					<td class="text-right">{{ format_currency(row.moneda === "$" ? flt(row.monto) : flt(row.monto) / flt(tc), "USD", 2) }}</th>
					<td class="text-right">{{ format_currency(row.moneda === "$" ? flt(row.monto) * flt(tc) : flt(row.monto), "NIO", 2) }}</th>
				  </tr>
				  {% totals.pm_total_usd += (row.moneda === "$" ? flt(row.monto) : flt(row.monto) / flt(tc)) %}
				  {% totals.pm_total_nio += (row.moneda === "$" ? flt(row.monto) * flt(tc) : flt(row.monto)) %}
				  {% } %}
				</tbody>
				<tbody>
				  <tr>
					<th class="centrado">&nbsp; TOTAL</th>
					<th class="text-right" id="pm_total_usd">{{ format_currency(totals.pm_total_usd, "USD", 2) }}</th>
					<th class="text-right" id="pm_total_nio">{{ format_currency(totals.pm_total_nio, "NIO", 2) }}</th>

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
							fieldtype: "HTML",
							fieldname: "FormasDePagos_wrapper",
							options: `<div class=row>
					  <div class="col-sm-12 col-md-12 col-lg-12 col-xl-12">
						 <div class="row">
							<div class="col-sm-12 col-md-4 col-lg-4 col-xl-4" id="mode_of_payment_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-2 col-lg-2 col-xl-2" id="currency_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-3 col-lg-3  col-xl-3" id="amount_wrapper" style="padding-left: 0px;"></div>

						 </div>
						 <div class="row" id="payments_wrapper"></div>
						 <div class="col-sm-12 col-md-5 col-lg-5 col-xl-5" style="padding-left: 0px;">Cambio</div>
						 <div class="row" id="change_wrapper">
							<div class="col-sm-12 col-md-5 col-lg-5 col-xl-5" id="change_usd_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-5 col-lg-5 col-xl-5" id="change_nio_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-5 col-lg-5 col-xl-5 mt-2" id="CambioNIO_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-5 col-lg-5 col-xl-5 mt-2" id="ResultCambioNIO_wrapper" style="padding-left: 0px;"></div>
					 </div>
					  </div>
					  <div class="col-sm-12 col-md-6 col-lg-6 col-xl-6" style="padding-right: 0px;" id="totals_wrapper"></div>
				  </div>`
					   }
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
			d.$wrapper.find(".modal-dialog").css({"top":"5%"});
			d.$wrapper.find(".modal-content").css({"width": "120%","left": "-10%"});

			//VALIDACION  DE ANTICIPACION
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
