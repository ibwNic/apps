// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");
frappe.provide("erpnext.journal_entry");


frappe.ui.form.on("Journal Entry", {
	setup: function(frm) {
		frm.add_fetch("bank_account", "account", "account");
		frm.ignore_doctypes_on_cancel_all = ['Sales Invoice', 'Purchase Invoice'];
	},

	refresh: function(frm) {
		erpnext.toggle_naming_series();

		if(frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": moment(frm.doc.modified).format('YYYY-MM-DD'),
					"company": frm.doc.company,
					"finance_book": frm.doc.finance_book,
					"group_by": '',
					"show_cancelled_entries": frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, __('View'));
		}
		// Declaracion de las variables
		if(frm.doc.docstatus==1) {
			frm.add_custom_button(__('Reverse Journal Entry'), function() {
				return erpnext.journal_entry.reverse_journal_entry(frm);
			}, __('Actions'));
		}

		// Entrada Rapida Default Journal Entry
		// if (frm.doc.__islocal) {
		// 	frm.add_custom_button(__('Quick Entry'), function() {
		// 		return erpnext.journal_entry.quick_entry(frm);
		// 	});
		// }

		// hide /unhide fields based on currency
		erpnext.journal_entry.toggle_fields_based_on_currency(frm);

		if ((frm.doc.voucher_type == "Inter Company Journal Entry") && (frm.doc.docstatus == 1) && (!frm.doc.inter_company_journal_entry_reference)) {
			frm.add_custom_button(__("Create Inter Company Journal Entry"),
				function() {
					frm.trigger("make_inter_company_journal_entry");
				}, __('Make'));
		}

		// Series de Caja
		var series = {
			"frania.lainez@ibw.com": "D-",
			"hegarcia@ibw.com": "I-",
			"jacquelines.martinez@ibw.com": "H-",
			"glendy.garcia@ibw.com": "G-",
			// 'octavio.aguirre@ibw.com':"O-"
		};
		series[frappe.user.name] && frm.doc.__islocal && frm.set_value('naming_series', series[frappe.user.name]);
		frm.toggle_enable('naming_series', false);

		//#region Pagos Caja
		cur_frm.cscript.make_customer_payment = function(frm){
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
									cur_frm.set_value("regnumber", d.get_value("customer"));
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
										cur_frm.set_value("tc_banco", TCBanco);
									}
									
									cur_frm.trigger("validate");

									// No cambiar
									// series[frappe.user.name] && frm.doc.__islocal && frm.set_value('naming_series', series[frappe.user.name]);
									// frm.toggle_enable('naming_series', false);
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
				// series = {
				// 	"frania.lainez@ibw.com": "D-",
				// 	"hegarcia@ibw.com": "I-",
				// 	"jacquelines.martinez@ibw.com": "H-"
                // },
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



			// Para hacer filtros
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
				var total2 = totals[1]['amount_nio'];
				var total1 = totals[1]['amount_usd'];
				var tipopago = 0;
				var Monto_DigitadoNIO = false;
				var Monto_DigitadoUSD = false;
				var monedaNIO = false;
				var monedaUSD = false;
				console.log(total1,total2);
				console.log(montos);

				for(let i = 0; i < montos.length; i++){
					if (montos[i] == total2){
						Monto_DigitadoNIO = true;
					}
				}

				for(let i = 0; i < montos.length; i++){
					if (montos[i] == total1){
						Monto_DigitadoUSD = true;
					}
				}
				// monedaNIO = "No entra";
				// if (montos[2] == flt(total1,2)){
				// 	monedaNIO = true;
				// };



				// console.log(Monto_Digitado);
				// return 0
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
				}else if (Monto_DigitadoNIO == true && montos[1] === total2 || Monto_DigitadoNIO == true && montos[2] === total2){
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
		//#endregion

		//#region Creacion Anticipos
		cur_frm.cscript.CrearAnticipos = function(frm){

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

			function aplicar_Pagos(values){
				// if (montos.includes(total1) || montos.includes(total2)){
					// console.log("PAso");
					// var values = d.get_values();
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
					console.log(pm_args);
					console.log('Requisición Aplicar Anticipo');
					console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					frappe.call({
						'method': 'erpnext.api.crear_anticipo',
						'args': pm_args,
						'callback': function(res){
							if (res.message) {
								if (res.message.accounts.length && !res.message.messages.length){
									res.message.accounts.forEach(function(c){
										frm.add_child("accounts", c);
									});
									cur_frm.refresh_fields()
									cur_frm.set_value("posting_date", pm_args.fecha);
									cur_frm.set_value("multi_currency", 1);
									cur_frm.set_value("customer",pm_args.regnumber);
									cur_frm.set_value("tasa_de_cambio",pm_args.tc);
									cur_frm.set_value("regnumber", d.get_value("customer"));
									// cur_frm.set_value("monto_recibido_dolares", fields.montoUSD.get_value());
									// cur_frm.set_value("monto_recibido_cordobas", fields.montoNIO.get_value());
									// cur_frm.set_value("vuelto_en_dolares", Cambios.CambioUSD);
									// cur_frm.set_value("vuelto_en_cordobas", Cambios.CambioNIO);
									if (fields.montoUSD.get_value() == null && fields.montoNIO.get_value() == null) {
										cur_frm.set_df_property('monto_recibido_dolares', 'read_only', 1)
										cur_frm.set_df_property('monto_recibido_cordobas', 'read_only', 1)
										cur_frm.set_df_property('vuelto_en_dolares', 'read_only',1)
										cur_frm.set_df_property('vuelto_en_cordobas', 'read_only',1)
										cur_frm.set_value("tc_banco", TCBanco);
									}else{
										cur_frm.set_value("monto_recibido_dolares", fields.montoUSD.get_value());
										cur_frm.set_value("monto_recibido_cordobas", fields.montoNIO.get_value());
										cur_frm.set_value("vuelto_en_dolares", Cambios.CambioUSD);
										cur_frm.set_value("vuelto_en_cordobas", Cambios.CambioNIO);
										cur_frm.set_value("tc_banco", TCBanco);
									}
									cur_frm.set_value("meses_anticipo",d.get_value('Cantidad_Meses'));
									cur_frm.set_value("tipo_de_pago","Anticipo");
									cur_frm.set_value("title","Anticipo");
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
				// } else {
				// 	frappe.msgprint({
				// 		title: __('Advertencia'),
				// 		indicator: 'red',
				// 		message: __('No es igual a los montos totales!')
				// 	});
				// 	// frappe.msgprint("No es igual a los montos totales!");
				// };
			}

			function ValidarCamposDigitados (pm_args,tipopago,monedaNIO,monedaUSD,values){
				for(let i = 0; i < pm_args.pagos.length; i++){
					if (pm_args.pagos[i]['tipo_de_pago'] == "Efectivo"){
						console.log("Entra");
						// tipopago = true;
						if (pm_args.pagos[i]['moneda'] == "C$"){
							monedaNIO = true;
							tipopago = true;
						}
						if (pm_args.pagos[i]['moneda'] == "$"){
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

			function TituloName(name){
				d.fields_dict.TituloName.$wrapper.find("#Nombre").text(name);
			}

			function ObtenerTCBanco (){
				return TCBanco
			}

			function TCBAnco(tcB){
				d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#Banco").text(tcB);
					// wrapper.find('#Banco').text(tcB);
			}

			var d,
				ignore_event = false,
				TotalesUSD = 0,
				TotalesNIO = 0,
				TCBanco =0,
				montosC$ = [],
				montosUSD = [],
				montos = [],
				Cambios = {},
				payments = [],
				totals = [],
				fields = {},
				result= [],
				tc = [],
				series = {
					"frania.lainez@ibw.com": "D-",
					"hegarcia@ibw.com": "I-",
					"jacquelines.martinez@ibw.com": "H-"
				},
				pm_args = {},
				tmp_pm_tableAnticipo = `<table class="table table-condensed table-bordered">
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
					<td align="center">{{[row.moneda] }}</th>
					<td class="text-right">{{ format_currency(row.moneda === "$" ? flt(row.monto) : flt(row.monto) / flt(tc), "USD", 2) }}</th>
					<td class="text-right">{{ format_currency(row.moneda === "$" ? flt(row.monto) * flt(tc) : flt(row.monto), "NIO", 2) }}</th>
					<td><button class="btn btn-danger btn-xs remove" data-idx="{{ i }}">
						<span class="icon icon-remove">
							<svg class="icon icon-sm" style>
								<use class href="#icon-delete"></use>
							</svg>
						</span></button>
					</td>
				  </tr>
				  {% totals.pm_total_usd += (row.moneda === "$" ? flt(row.monto) : flt(row.monto) / flt(tc)) %}
				  {% totals.pm_total_nio += (row.moneda === "$" ? flt(row.monto) * flt(tc) : flt(row.monto,2)) %}
				  {% } %}
				</tbody>
				<tbody>
				  <tr>
					<th colspan="2" class="centrado">&nbsp; TOTAL A</th>
					<th class="text-right" id="pm_total_usd">{{ format_currency(totals.pm_total_usd, "USD", 2) }}</th>
					<th class="text-right" id="pm_total_nio">{{ format_currency(totals.pm_total_nio, "NIO", 2) }}</th>
					<th>&nbsp;</th>
				  </tr>
				</tbody>
			 </table>`;


			function set_sum_Totales_Anticipos(data){
				// console.log(data['total_FacturaUSD']);
				var amounts = {'TotalNIO': 0.0, 'TotalUSD': 0.0};

				amounts.TotalNIO += data['Total_FacturaNIO'];
				amounts.TotalUSD += data['total_FacturaUSD'] ;

				montos.push(flt(amounts.TotalNIO,2));
				montos.push(flt(amounts.TotalUSD,2));
				// console.log(montos);
				// render_totals_table();
				// SumaFormaPagos();
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
				pm_args['deudas'] = [];
				pm_args['deudas'].push({'link_doctype':'Anticipo', 'link_name': 'ANTICIPO-001','MontoFac':TotalesNIO});
				pm_args.pagos = payments;
				console.log(tc[0]);
			}

			function toggle_actionCambio(fields, wrapper){
				fields.forEach(function(df){
					df.$input.on('change', function(){
						// if (!wrapper.find("#actionLimpiarText").hasClass("hidden")){
						// 	wrapper.find('#actionLimpiarText').addClass('hidden');
						// }
	
						// for(var i = 0, l = fields.length; i<l; i++){
						// 	if (!fields[i].get_value()) return;
						// }
						wrapper.find('#actionLimpiarText').removeClass('hidden');
					});
				});
			}

				function create_payments_areaAnticipo(){
					var mode_of_payment_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Select',
							options: ['','Cheque','Efectivo','Tarjetas de credito'],
							fieldname: 'mode_of_payment',
							label: 'Tipo de Pago',
							// placeholder: 'Tipo de Pago',
							reqd: 1
						},
						parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#mode_of_payment_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					mode_of_payment_field.make_input();
					fields.mode_of_payment = mode_of_payment_field;

					var currency_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Select',
							options: ['','C$','$'],
							fieldname: 'currency',
							label: 'Moneda',
							// placeholder: 'Moneda',
							reqd: 0
						},
						parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#currency_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					currency_field.make_input();
					fields.currency = currency_field;

					var amount_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Float',
							precision: 2,
							fieldname: 'amount',
							label: 'Monto',
							placeholder: 'Monto',
							reqd: 1
						},
						parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#amount_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					amount_field.make_input();
					fields.amount = amount_field;

					var CambioUSD = frappe.ui.form.make_control({
						df: {
								fieldtype: 'Float',
								precision: 2,
								fieldname: 'montoUSD',
								label: 'USD',
								placeholder: 'Monto $'
							},
							parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#change_usd_wrapper").empty(),
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
								console.log(payments);
								var sumUSD = 0;
								var tc=0;
								var converNIO = 0;
								var converUSD = 0;
								var cambioUSD = 0;
								var res = 0;
								for(let i = 0; i < payments.length; i++){
									if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "$"){
										sumUSD += payments[i]['monto'];
									}
								}

								if(sumUSD > 0){
									// converNIO = sumUSD *  flt(d.get_value("conversion_rate"),2);
									tc = ObtenerTCBanco();
									converNIO = sumUSD *  tc;
									// converUSD = flt(CambioUSD.get_value(),2) *  flt(d.get_value("conversion_rate"),2);
									converUSD = CambioUSD.get_value() * tc;
									res = flt((-1)* (converNIO - converUSD),2);
									cambioUSD = flt(CambioUSD.get_value() - sumUSD,2);
									console.log(res);
									if(CambioUSD.get_value() < sumUSD){
										frappe.msgprint({
											title: __('Advertencia'),
											indicator: 'red',
											message: __('El monto digitado no debe ser menor, al efectivo que recibio!')
										});
										CambioUSD.$input.val(null).trigger("change");
										// ResultCambioUSD.$input.val(null).trigger("change");
									}else{
										// ResultCambioUSD.$input.val(res).trigger("change");
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
									CambioUSD.$input.val(null).trigger("change");
									// ResultCambioUSD.$input.val(null).trigger("change");
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
							parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#change_nio_wrapper").empty(),
							frm: frm,
							doctype: frm.doctype,
							docname: frm.docname,
							only_input: true
						});
						ResultCambioUSD.make_input();
						fields.ResultUSD = ResultCambioUSD;

						var CambioNIO = frappe.ui.form.make_control({
							df: {
								fieldtype: 'Float',
								precision: 2,
								fieldname: 'montoNIO',
								label: 'montoNIO',
								placeholder: 'Monto C$',
								reqd: 0
							},
							parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#CambioNIO_wrapper").empty(),
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
								console.log(payments);
								var sumNIO = 0;
								var res = 0;
								var HaytipoPagoEfectivo = false;
								for(let i = 0; i < payments.length; i++){
									if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "C$"){
										sumNIO += payments[i]['monto'];
									}
								}
								console.log(sumNIO);
								if(sumNIO > 0){
									res = flt((-1)* (sumNIO - CambioNIO.get_value()),2);
									// console.log(res);
									if(CambioNIO.get_value() < sumNIO){
										frappe.msgprint({
											title: __('Advertencia'),
											indicator: 'red',
											message: __('El monto digitado no debe ser menor, al efectivo que recibio!')
										});
										CambioNIO.$input.val(null).trigger("change");
										ResultCambioNIO.$input.val(null).trigger("change");
									}else{
										ResultCambioNIO.$input.val(res).trigger("change");
										Cambios.CambioNIO = res;
									}
								}else{
									frappe.msgprint({
										title: __('Advertencia'),
										indicator: 'red',
										message: __('No recibio ningun tipo de pago que sea efectivo!')
									});
									CambioNIO.$input.val(null).trigger("change");
									ResultCambioNIO.$input.val(null).trigger("change");
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
							parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#ResultCambioNIO_wrapper").empty(),
							frm: frm,
							doctype: frm.doctype,
							docname: frm.docname,
							only_input: true,

						});
						ResultCambioNIO.make_input();
						fields.ResultNIO = ResultCambioNIO;

						var ResultCambioUSD_USD = frappe.ui.form.make_control({
							df: {
								fieldtype: 'Float',
								precision: 2,
								fieldname: 'ResultCambioUSD_USD',
								label: 'USD',
								placeholder: 'Vuelto $',
								read_only: 1
							},
							parent: d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#change_usd_usd_wrapper").empty(),
							frm: frm,
							doctype: frm.doctype,
							docname: frm.docname,
							only_input: true
						});
						ResultCambioUSD_USD.make_input();
						fields.ResultUSD_USD = ResultCambioUSD_USD;

					//////////////////////////////////////////////////////////////////////////////////////////////////////////

					toggle_action([mode_of_payment_field, currency_field, amount_field],
					d.fields_dict.FormasDePagos_wrapper.$wrapper);

					d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#action").off("click").on("click", function(){
						if (d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#action").hasClass("hidden")) return;

						payments.push({
							"tipo_de_pago": mode_of_payment_field.get_value(),
							"moneda": currency_field.get_value(),
							"monto": amount_field.get_value()
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
						mode_of_payment_field.$input.val(null).trigger("change");
						currency_field.$input.val(null).trigger("change");
						amount_field.$input.val(null).trigger("change");
					});

					// Validacion de boton limppiar
					toggle_actionCambio([CambioNIO, ResultCambioUSD_USD, ResultCambioUSD,CambioUSD,ResultCambioNIO],
						d.fields_dict.FormasDePagos_wrapper.$wrapper);
	
					d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#actionLimpiarText").off("click").on("click", function(){
						if (d.fields_dict.FormasDePagos_wrapper.$wrapper.find("#actionLimpiarText").hasClass("hidden")) return;
						CambioNIO.$input.val(null).trigger("change");
						ResultCambioUSD_USD.$input.val(null).trigger("change");
						ResultCambioUSD.$input.val(null).trigger("change");
						CambioUSD.$input.val(null).trigger("change");
						ResultCambioNIO.$input.val(null).trigger("change");
						fields.montoUSD.set_value(null);
						fields.montoNIO.set_value(null);
						// Cambios.CambioUSD.set_value(null);
						// Cambios.CambioNIO.set_value(null);
		});
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
					title: __("Anticipos"),
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
										frappe.call({
											// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
											'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.Factura_pendiente',
											'args': {
												'Customer': d.get_value('customer')
											},
											'callback': function(res){
												// d.fields_dict.colectores.df.description = res.message.name || '';
												// d.fields_dict.colectores.set_description();
												// d.set_value("serie", res.message.serie);
												console.log(res.message)
												if (res.message == "Pendiente"){
													frappe.msgprint({
														title: __('Advertencia'),
														indicator: 'red',
														message: __('Lo sentimos tiene facturas pendientes, le recomendamos cancelarlas!')
													});
													d.set_value("customer",null);
												}else{
													get_exchange();
													create_payments_areaAnticipo();
													// var nombre = frappe.db.get_value('Customer',d.get_value('customer'),'customer_name');
													frappe.db.get_value('Customer', d.get_value('customer'), 'customer_name').then(r => {
														let values = r.message;
														TituloName(values.customer_name);
													})
													
													// const fecha = new Date();
													// const añoActual = fecha.getFullYear();
													// const hoy = fecha.getDate();
													// const mesActual = fecha.getMonth() + 1;
													// var fechaHoy = hoy + '-' + mesActual + '-'+añoActual;
													
													// console.log(fechaHoy);
													// frappe.db.get_value('Currency Exchange',{'date':fechaHoy.toString()}, 'lafise').then(r => {
													// 	let values = r.message;
													// 	// TituloName(values.customer_name);
														
													// 	TCBanco = values.lafise
													// })

													frappe.call({
														'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.TCBANCO',
														'callback': function(res){
															console.log(res.message)
															TCBanco = res.message;
															TCBAnco(TCBanco);
														}
													});
													
													
													frappe.call({
														// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
														'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.SumaDeAnticiposFactura',
														'args': {
															'Customer': d.get_value('customer')
														},
														'callback': function(res){
															// format_currency(amounts.actual_nio, 'NIO', 2)
															// [null].concat(data.tipos_de_pago)
															// TASA
															console.log(res.message[0][1]);
															var conver = 0, tc = 0,res1=0, iva=0,total=0,iva2=0,total2=0;
															if(res.message[0][1] == "USD"){
																iva = res.message[0][0] * 0.15;
																// console.log(res.message[0][0]);
																total = res.message[0][0] + iva;
																d.set_value("Monto_de_Factura",total);

																// res1 = res.message[0];
																// console.log(res1)
																// conver = flt(d.get_value("conversion_rate") * res1[0], 2);
																// console.log(conver)
																// iva2 = conver * 0.15;
																// console.log(iva2)
																total2 = flt(flt(total,2)*d.get_value("conversion_rate"),2)
																// console.log()
																d.set_value("Monto_de_FacturaNIO",flt(total2,2));
															}else{
																console.log(res.message[0])
																d.set_value("Monto_de_Factura",0);
																iva = res.message[0][0] * 0.15;
																total = res.message[0][0] + iva;
																d.set_value("Monto_de_FacturaNIO",total);
															}
															// d.set_value("Monto_de_Factura",res.message[0]);
														}
													});
												}
											}
										});
									}
								},
							// on_make: d.get_value('customer').refresh(),
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Float",
							label: "Monto Factura $",
							precision: 2,
							// options: "Customer",
							fieldname: "Monto_de_Factura",
							read_only: 1,
						},
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Float",
							label: "Monto Factura C$",
							precision: 2,
							// options: "Customer",
							fieldname: "Monto_de_FacturaNIO",
							read_only: 1,
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Deudas")
						},
						{
							fieldtype: "Int",
							label: "# de Meses de Anticipo",
							precision: 1,
							// options: "Customer",
							fieldname: "Cantidad_Meses",
							// on_make: ,
							change: function () {
								var res = 0;
								var res1 = 0;
								var data = {'total_FacturaUSD':0.0, 'Total_FacturaNIO':0.0};
								// d.get_value('Cantidad_Meses');
								// d.get_value('Monto_de_Factura');

								res = flt(d.get_value('Cantidad_Meses') * d.get_value('Monto_de_Factura'));
								// res1 = flt(d.get_value('Cantidad_Meses') * d.get_value('Monto_de_FacturaNIO'),4);
								res1 = flt(res * d.get_value('conversion_rate'),2);
								data.total_FacturaUSD = res;
								data.Total_FacturaNIO = res1;
								set_sum_Totales_Anticipos(data);
								// d.set_value("Monto_de_FacturaNIO",total);
								d.set_value('TotalNIO',res1);
								d.set_value('TotalUSD',res);
							}
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
							default: frappe.datetime.get_today(),
							fieldname: "posting_date",
							read_only: 1
							// on_make: assign_df_to_input,
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						{
							fieldtype: "Float",
							label: "Total $",
							precision: 2,
							read_only: 1,
							// options: "Customer",
							fieldname: "TotalUSD",
							// on_make: assign_df_to_input,
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Total")
						},
						{
							fieldtype: "Float",
							label: "Total C$",
							precision: 2,
							// options: "Customer",
							fieldname: "TotalNIO",
							read_only: 1,
							// on_make: assign_df_to_input,
							// change: get_outstanding_details
						},
						{
							// fieldtype: "Column Break",
							fieldtype: "Section Break",
							label: __("Forma de Pagos")
						},
						{
							fieldtype: "HTML",
							fieldname: "FormasDePagos_wrapper",
							options: `<div class=row>
					  <div class="col-sm-12 col-md-12 col-lg-12 col-xl-12">
					  	<div class="row">
							<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4 style="padding-left: 0px;""> Tipo de pago</div>
							<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" style="padding-left: 0px;"> Moneda</div>
				  		</div>

						 <div class="row">
							<div class="col-sm-12 col-md-4 col-lg-4 col-xl-4" id="mode_of_payment_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-2 col-lg-2 col-xl-2" id="currency_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-3 col-lg-3  col-xl-3" id="amount_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-2 col-lg-2 col-xl-2" id="action_wrapper" style="padding-left: 0px;">
								<button class="btn btn-primary hidden" role="button" id="action">Agregar</button>
							</div>
						 </div>
						 <div class="row" id="payments_wrapper"></div>
						 <br>
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
					],
					primary_action_label: 'Crear Anticipo',
					primary_action(values) {
						console.log(values);
						d.hide();
					},
					secondary_action_label: "Cancel"
				});
			d.show();
			d.$wrapper.find(".modal-dialog").css({"top":"5%"});
			d.$wrapper.find(".modal-content").css({"width": "120%","left": "-10%"});

			//VALIDACION  DE ANTICIPACION
			d.get_primary_btn().text('Crear Anticipo').off('click').on('click', function(){
				// console.log(TotalesNIO);
				// SumaFormaPagos();
				console.log(totals);
				// Validacion de montos
				var total1 = flt(totals[0]['MontoNIO'],2);
				var total2 = totals[0]['MontoUSD'];
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

				if (Monto_DigitadoNIO == true && Monto_DigitadoUSD == true){
					var values = d.get_values();
					ValidarCamposDigitados(pm_args,tipopago,monedaNIO,monedaUSD,values);

				}else if (Monto_DigitadoUSD == true){
					var values = d.get_values();
					ValidarCamposDigitados(pm_args,tipopago,monedaNIO,monedaUSD,values);
				}else {
					frappe.msgprint({
						title: __('Advertencia'),
						indicator: 'red',
						message: __('No es igual a los montos totales!')
					});
					// frappe.msgprint("No es igual a los montos totales!");
				};
				

			});
		}
		//#endregion
		
		//#region Aplicar Anticipos
		cur_frm.cscript.AplicarAnticipos = function(frm){

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
				pm_args['deudas'] = [];
				pm_args['deudas'].push({'link_doctype':'Sales Invoice', 'link_name': d.get_value('Factura')});
				pm_args.pagos = payments;
				console.log(tc[0]);
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
					title: __("Aplicar Anticipos"),
					fields: [
						{
							fieldtype: "Link",
							label: "Cliente",
							options: "Customer",
							fieldname: "customer",
							change:  function(){
									if(d.get_value('customer')){
										frappe.call({
											// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
											'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.ChecarAnticipo',
											'args': {
												'Customer': d.get_value('customer')
											},
											'callback': function(res){

												console.log(res.message)
												if (res.message == 0){
													frappe.msgprint({
														title: __('Advertencia'),
														indicator: 'red',
														message: __('Lo sentimos, no tiene un anticipo resgistrado!')
													});
													d.set_value("customer",null);
												}else{
													get_exchange();
													// create_payments_areaAnticipo();
													d.set_value("Monto_de_Factura",res.message[0][3]);
													d.set_value("Anticipo",res.message[0][0]);

													frappe.call({
														'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.Factura_Anticipos',
														'args': {
															'Customer': d.get_value('customer')
														},
														'callback': function(r){
															console.log(r.message[0][0])
														d.set_value('Monto_de_FacturaNIO',r.message[0][1])
														d.set_value('Factura',r.message[0][0])
														}
													});
													mostrarFactura(res.message[0][3]);



													// frappe.call({
													// 	// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
													// 	'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.SumaDeAnticiposFactura',
													// 	'args': {
													// 		'Customer': d.get_value('customer')
													// 	},
													// 	'callback': function(res){
													// 		// format_currency(amounts.actual_nio, 'NIO', 2)
													// 		// [null].concat(data.tipos_de_pago)
													// 		console.log(res.message[0][1]);
													// 		var conver = 0, tc = 0,res1=0, iva=0,total=0,iva2=0,total2=0;
													// 		if(res.message[0][1] == "USD"){
													// 			iva = res.message[0][0] * 0.15;
													// 			// console.log(res.message[0][0]);
													// 			total = res.message[0][0] + iva;
													// 			d.set_value("Monto_de_Factura",total);

													// 			res1 = res.message[0];
													// 			conver = flt(d.get_value("conversion_rate") * res1[0],2);
													// 			iva2 = conver * 0.15;
													// 			total2 = conver + iva2;
													// 			d.set_value("Monto_de_FacturaNIO",total2);
													// 		}else{
													// 			console.log(res.message[0])
													// 			d.set_value("Monto_de_Factura",0);
													// 			iva = res.message[0][0] * 0.15;
													// 			total = res.message[0][0] + iva;
													// 			d.set_value("Monto_de_FacturaNIO",total);
													// 		}
													// 		// d.set_value("Monto_de_Factura",res.message[0]);
													// 	}
													// });
												}
											}
										});
									}
								},
							// on_make: d.get_value('customer').refresh(),
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Float",
							label: "Monto Anticipo C$",
							precision: 2,
							// options: "Customer",
							fieldname: "Monto_de_Factura",
							read_only: 1,
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Deudas")
						},
						{
							fieldtype: "Data",
							label: "Anticipo",
							// precision: 2,
							// options: "Customer",
							fieldname: "Anticipo",
							read_only: 1,
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Data",
							label: "Factura",
							// precision: 2,
							// options: "Customer",
							fieldname: "Factura",
							read_only: 1,
						},
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Float",
							label: "Monto Factura $",
							precision: 2,
							// options: "Customer",
							fieldname: "Monto_de_FacturaNIO",
							read_only: 1,
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
			d.show();
			d.$wrapper.find(".modal-dialog").css({"top":"5%"});
			d.$wrapper.find(".modal-content").css({"width": "120%","left": "-10%"});

			//VALIDACION  DE ANTICIPO
			d.get_primary_btn().text('Aplicar Anticipo').off('click').on('click', function(){
				// console.log(TotalesNIO);
				// SumaFormaPagos();
				// console.log(totals);
				// // Validacion de montos
				// var total1 = totals[0]['MontoNIO'];
				// var total2 = totals[0]['MontoUSD'];
				// console.log(total1,total2);
				// console.log(montos);

				// montos.includes(total1);
				// if (montos.includes(total1) || montos.includes(total2)){
					console.log("PAso");
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
					pm_args._ui_ = true;
					console.log(pm_args);
					console.log('Requisición Aplicar Anticipo');
					console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					frappe.call({
						'method': 'erpnext.api.aplicar_Anticipos',
						'args': pm_args,
						'callback': function(res){
							if (res.message) {
								if (res.message.accounts.length && !res.message.messages.length){
									res.message.accounts.forEach(function(c){
										frm.add_child("accounts", c);
									});
									cur_frm.refresh_fields()
									cur_frm.set_value("posting_date", pm_args.fecha);
									cur_frm.set_value("multi_currency", 1);
									// cur_frm.set_value("customer",pm_args.regnumber);
									cur_frm.set_value("tasa_de_cambio",pm_args.tc);
									// cur_frm.set_value("meses_anticipo",d.get_value('Cantidad_Meses'));
									cur_frm.set_value("codigoanticipo",d.get_value('Anticipo'));
									cur_frm.set_value("tipo_de_pago","Aplicar Anticipo");
									// cur_frm.set_value("title","Anticipo");
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
		//#endregion

		//#region Depositos en Garantia
		cur_frm.cscript.CrearDepositoGarantia = function(frm){
			function ValidarCamposDigitados (pm_args,tipopago,monedaNIO,monedaUSD,values){
				for(let i = 0; i < pm_args.pagos.length; i++){
					if (pm_args.pagos[i]['tipo_de_pago'] == "Efectivo"){
						console.log("Entra");
						// tipopago = true;
						if (pm_args.pagos[i]['moneda'] == "C$"){
							monedaNIO = true;
							tipopago = true;
						}
						if (pm_args.pagos[i]['moneda'] == "$"){
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

			function aplicar_Pagos (values){
				// var values = d.get_values();
				// console.log(pm_args);
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
					pm_args._ui_ = true;
					console.log(pm_args);
					console.log('Requisición Aplicar Deposito');
					console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					frappe.call({
						'method': 'erpnext.api.crear_deposito',
						'args': pm_args,
						'callback': function(res){
							if (res.message) {
								if (res.message.accounts.length && !res.message.messages.length){
									res.message.accounts.forEach(function(c){
										frm.add_child("accounts", c);
									});
									cur_frm.refresh_fields()
									cur_frm.set_value("posting_date", pm_args.fecha);
									cur_frm.set_value("multi_currency", 1);
									cur_frm.set_value("customerdeposito",pm_args.regnumber);
									cur_frm.set_value("tasa_de_cambiodeposito",pm_args.tc);
									cur_frm.set_value("regnumber", d.get_value("customer"));
									// cur_frm.set_value("monto_recibido_dolares", fields.montoUSD.get_value());
									// cur_frm.set_value("monto_recibido_cordobas", fields.montoNIO.get_value());
									// cur_frm.set_value("vuelto_en_dolares", Cambios.CambioUSD);
									// cur_frm.set_value("vuelto_en_cordobas", Cambios.CambioNIO);
									// cur_frm.set_value("meses_anticipo",d.get_value('Cantidad_Meses'));
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
										cur_frm.set_value("tc_banco", TCBanco);
									}
									cur_frm.set_value("tipo_de_pago","Deposito");
									cur_frm.set_value("title","Deposito");
									cur_frm.trigger("validate");


									// No cambiar
									// series[frappe.user.name] && frm.doc.__islocal && frm.set_value('naming_series', series[frappe.user.name]);
									// frm.toggle_enable('naming_series', false);
									d.hide();
								} else {
									frappe.msgprint(res.message.messages.join("<br/>"));
								}
							}
						}
					});
			}

			function ObtenerTCBanco (){
				return TCBanco
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

			function TituloName(name){
				d.fields_dict.TituloName.$wrapper.find("#Nombre").text(name);
			}

			function toggle_actionCambio(fields, wrapper){
				fields.forEach(function(df){
					df.$input.on('change', function(){
						// if (!wrapper.find("#actionLimpiarText").hasClass("hidden")){
						// 	wrapper.find('#actionLimpiarText').addClass('hidden');
						// }

						// for(var i = 0, l = fields.length; i<l; i++){
						// 	if (!fields[i].get_value()) return;
						// }
						wrapper.find('#actionLimpiarText').removeClass('hidden');
					});
				});
			}

			function TCBAnco(tcB){
				d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#Banco").text(tcB);
					// wrapper.find('#Banco').text(tcB);
			}

			var d,
				TCBanco,
				ignore_event = false,
				TotalesUSD = 0,
				TotalesNIO = 0,
				montosC$ = [],
				montosUSD = [],
				montos = [],
				payments = [],
				totals = [],
				fields = {},
				result= [],
				Cambios = {},
				tc = [],
				series = {
					"frania.lainez@ibw.com": "D-",
					"hegarcia@ibw.com": "I-",
					"jacquelines.martinez@ibw.com": "H-"
                },
				pm_args = {},
				tmp_pm_tableAnticipo = `<table class="table table-condensed table-bordered">
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
					<td align="center">{{[row.moneda] }}</th>
					<td class="text-right">{{ format_currency(row.moneda === "$" ? flt(row.monto) : flt(row.monto) / flt(tc), "USD", 2) }}</th>
					<td class="text-right">{{ format_currency(row.moneda === "$" ? flt(row.monto) * flt(tc) : flt(row.monto), "NIO", 2) }}</th>
					<td><button class="btn btn-danger btn-xs remove" data-idx="{{ i }}"><span class="icon icon-remove"></span></button></td>
				  </tr>
				  {% totals.pm_total_usd += (row.moneda === "$" ? flt(row.monto) : flt(row.monto) / flt(tc)) %}
				  {% totals.pm_total_nio += (row.moneda === "$" ? flt(row.monto) * flt(tc) : flt(row.monto)) %}
				  {% } %}
				</tbody>
				<tbody>
				  <tr>
					<th colspan="2" class="centrado">&nbsp; TOTAL A</th>
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

				montos.push(flt(amounts.TotalNIO,2));
				montos.push(flt(amounts.TotalUSD,2));
				console.log(montos);
				// render_totals_table();
				// SumaFormaPagos();
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
				pm_args['deudas'] = [];
				pm_args['deudas'].push({'link_doctype':'Deposito', 'link_name': 'Deposito','MontoDeposito':flt(TotalesNIO,2)});
				pm_args.pagos = payments;
				console.log(tc[0]);
			}

				function create_payments_areaAnticipo(){
					var mode_of_payment_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Select',
							options: ['','Cheque','Efectivo','Tarjetas de credito'],
							fieldname: 'mode_of_payment',
							label: 'Tipo de Pago',
							// placeholder: 'Tipo de Pago',
							reqd: 1
						},
						parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#mode_of_payment_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					mode_of_payment_field.make_input();
					fields.mode_of_payment = mode_of_payment_field;

					var currency_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Select',
							options: ['','C$','$'],
							fieldname: 'currency',
							label: 'Moneda',
							// placeholder: 'Moneda',
							reqd: 0
						},
						parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#currency_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					currency_field.make_input();
					fields.currency = currency_field;

					var amount_field = frappe.ui.form.make_control({
						df: {
							fieldtype: 'Float',
							precision: 2,
							fieldname: 'amount',
							label: 'Monto',
							placeholder: 'Monto',
							reqd: 1
						},
						parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#amount_wrapper").empty(),
						frm: frm,
						doctype: frm.doctype,
						docname: frm.docname,
						only_input: true
					});
					amount_field.make_input();
					fields.amount = amount_field;

					var CambioUSD = frappe.ui.form.make_control({
						df: {
								fieldtype: 'Float',
								precision: 2,
								fieldname: 'montoUSD',
								label: 'USD',
								placeholder: 'Monto $'
							},
							parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#change_usd_wrapper").empty(),
							frm: frm,
							doctype: frm.doctype,
							docname: frm.docname,
							only_input: true
						});
						CambioUSD.make_input();
						CambioUSD.$input.on('change', function(){
							if (CambioUSD.get_value()) {
								// frappe.msgprint("OK");
								console.log(payments);
								var sumUSD = 0;
								var tc=0;
								var converNIO = 0;
								var converUSD = 0;
								var cambioUSD = 0;
								var res = 0;
								for(let i = 0; i < payments.length; i++){
									if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "$"){
										sumUSD += payments[i]['monto'];
										// if (payments[i]['moneda'] == "usd") {
										// 	sumUSD += payments[i]['monto'];
										// }
									}
								}

								if(sumUSD > 0){
									// converNIO = sumUSD *  flt(d.get_value("conversion_rate"),2);
									tc = ObtenerTCBanco();
									converNIO = sumUSD *  tc;
									// converUSD = flt(CambioUSD.get_value(),2) *  flt(d.get_value("conversion_rate"),2);
									converUSD = CambioUSD.get_value() * tc;
									res = flt((-1)* (converNIO - converUSD),2);
									cambioUSD = flt(CambioUSD.get_value() - sumUSD,2);
									console.log(res);
									if(CambioUSD.get_value() < sumUSD){
										frappe.msgprint({
											title: __('Advertencia'),
											indicator: 'red',
											message: __('El monto digitado no debe ser menor, al efectivo que recibio!')
										});
										CambioUSD.$input.val(null).trigger("change");
										ResultCambioUSD.$input.val(null).trigger("change");
									}else{
										ResultCambioUSD.$input.val(res).trigger("change");
										ResultCambioUSD_USD.$input.val(cambioUSD).trigger("change");
										Cambios.CambioUSD = cambioUSD;
									}
								}else{
									frappe.msgprint({
										title: __('Advertencia'),
										indicator: 'red',
										message: __('No recibio ningun tipo de pago que sea efectivo!')
									});
									CambioUSD.$input.val(null).trigger("change");
									// ResultCambioUSD.$input.val(null).trigger("change");
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
							parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#change_nio_wrapper").empty(),
							frm: frm,
							doctype: frm.doctype,
							docname: frm.docname,
							only_input: true
						});
						ResultCambioUSD.make_input();
						fields.ResultUSD = ResultCambioUSD;

						var CambioNIO = frappe.ui.form.make_control({
							df: {
								fieldtype: 'Float',
								precision: 2,
								fieldname: 'montoNIO',
								label: 'montoNIO',
								placeholder: 'Monto C$',
								reqd: 0
							},
							parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#CambioNIO_wrapper").empty(),
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
								console.log(payments);
								var sumNIO = 0;
								var res = 0;
								var HaytipoPagoEfectivo = false;
								for(let i = 0; i < payments.length; i++){
									if (payments[i]['tipo_de_pago'] == "Efectivo" && payments[i]['moneda'] == "C$"){
										sumNIO += payments[i]['monto'];
									}
								}
								console.log(sumNIO);
								if(sumNIO > 0){
									res = flt((-1)* (sumNIO - CambioNIO.get_value()),2);
									// console.log(res);
									if(CambioNIO.get_value() < sumNIO){
										frappe.msgprint({
											title: __('Advertencia'),
											indicator: 'red',
											message: __('El monto digitado no debe ser menor, al efectivo que recibio!')
										});
										CambioNIO.$input.val(null).trigger("change");
										ResultCambioNIO.$input.val(null).trigger("change");
									}else{
										ResultCambioNIO.$input.val(res).trigger("change");
										Cambios.CambioNIO = res;
									}
								}else{
									frappe.msgprint({
										title: __('Advertencia'),
										indicator: 'red',
										message: __('No recibio ningun tipo de pago que sea efectivo!')
									});
									CambioNIO.$input.val(null).trigger("change");
									ResultCambioNIO.$input.val(null).trigger("change");
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
							parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#ResultCambioNIO_wrapper").empty(),
							frm: frm,
							doctype: frm.doctype,
							docname: frm.docname,
							only_input: true,

						});
						ResultCambioNIO.make_input();
						fields.ResultNIO = ResultCambioNIO;
						
						var ResultCambioUSD_USD = frappe.ui.form.make_control({
							df: {
								fieldtype: 'Float',
								precision: 2,
								fieldname: 'ResultCambioUSD_USD',
								label: 'USD',
								placeholder: 'Vuelto $',
								read_only: 1
							},
							parent: d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#change_usd_usd_wrapper").empty(),
							frm: frm,
							doctype: frm.doctype,
							docname: frm.docname,
							only_input: true
						});
						ResultCambioUSD_USD.make_input();
						fields.ResultUSD_USD = ResultCambioUSD_USD;

					//////////////////////////////////////////////////////////////////////////////////////////////////////////

					toggle_action([mode_of_payment_field, currency_field, amount_field],
					d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper);

					d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#action").off("click").on("click", function(){
						if (d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#action").hasClass("hidden")) return;

						payments.push({
							"tipo_de_pago": mode_of_payment_field.get_value(),
							"moneda": currency_field.get_value(),
							"monto": amount_field.get_value()
						});
						// console.log(currency_field.get_value());
						SumaFormaPagos();
						function render_payments(){
							d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#payments_wrapper").html(
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
						mode_of_payment_field.$input.val(null).trigger("change");
						currency_field.$input.val(null).trigger("change");
						amount_field.$input.val(null).trigger("change");
					});

					toggle_actionCambio([CambioNIO, ResultCambioUSD_USD, ResultCambioUSD,CambioUSD,ResultCambioNIO],
						d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper);
	
					d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#actionLimpiarText").off("click").on("click", function(){
						if (d.fields_dict.FormasDePagosDeposito_wrapper.$wrapper.find("#actionLimpiarText").hasClass("hidden")) return;
						CambioNIO.$input.val(null).trigger("change");
						ResultCambioUSD_USD.$input.val(null).trigger("change");
						ResultCambioUSD.$input.val(null).trigger("change");
						CambioUSD.$input.val(null).trigger("change");
						ResultCambioNIO.$input.val(null).trigger("change");
					});
				}

				function get_exchange() {
					frappe.call({
						'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.get_divisa',
						'args':{
							'from_currency':"USD",
							'to_currency': "NIO"
						},
						'callback': function(res){
							// console.log(res.message);
							d.set_value("conversion_rate",res.message);
							tc.push(res.message);
							console.log(tc);
						}
					})
				}

				d = new frappe.ui.Dialog({
					title: __("Deposito en Garantia"),
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
										get_exchange();
										// set_sum_Totales_Anticipos(data);
										// render_payments();
										create_payments_areaAnticipo();

										frappe.call({
											'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.TCBANCO',
											'callback': function(res){
												console.log(res.message)
												
												TCBanco = res.message;
												TCBAnco(TCBanco);
											}
										});

										frappe.db.get_value('Customer', d.get_value('customer'), 'customer_name').then(r => {
											let values = r.message;
											TituloName(values.customer_name);
										})
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
										// 			create_payments_areaAnticipo();
										// 			d.set_value("Monto_de_Factura",res.message[0][3]);
										// 			d.set_value("Anticipo",res.message[0][0]);
										// 			// frappe.call({
										// 			// 	// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
										// 			// 	'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.SumaDeAnticiposFactura',
										// 			// 	'args': {
										// 			// 		'Customer': d.get_value('customer')
										// 			// 	},
										// 			// 	'callback': function(res){
										// 			// 		// format_currency(amounts.actual_nio, 'NIO', 2)
										// 			// 		// [null].concat(data.tipos_de_pago)
										// 			// 		console.log(res.message[0][1]);
										// 			// 		var conver = 0, tc = 0,res1=0, iva=0,total=0,iva2=0,total2=0;
										// 			// 		if(res.message[0][1] == "USD"){
										// 			// 			iva = res.message[0][0] * 0.15;
										// 			// 			// console.log(res.message[0][0]);
										// 			// 			total = res.message[0][0] + iva;
										// 			// 			d.set_value("Monto_de_Factura",total);

										// 			// 			res1 = res.message[0];
										// 			// 			conver = flt(d.get_value("conversion_rate") * res1[0],2);
										// 			// 			iva2 = conver * 0.15;
										// 			// 			total2 = conver + iva2;
										// 			// 			d.set_value("Monto_de_FacturaNIO",total2);
										// 			// 		}else{
										// 			// 			console.log(res.message[0])
										// 			// 			d.set_value("Monto_de_Factura",0);
										// 			// 			iva = res.message[0][0] * 0.15;
										// 			// 			total = res.message[0][0] + iva;
										// 			// 			d.set_value("Monto_de_FacturaNIO",total);
										// 			// 		}
										// 			// 		// d.set_value("Monto_de_Factura",res.message[0]);
										// 			// 	}
										// 			// });
										// 		}
										// 	}
										// });
									}
								},
							// on_make: d.get_value('customer').refresh(),
							// change: get_outstanding_details
						},
						// {
						// 	fieldtype: "Column Break"
						// },
						// {
						// 	fieldtype: "Float",
						// 	label: "Monto $",
						// 	precision: 2,
						// 	// options: "Customer",
						// 	fieldname: "MontoUSD",
						// 	// read_only: 1,
						// 	change: function(){
						// 		if(d.get_value('MontoUSD')){
						// 			var montoNIO = 0;
						// 			montoNIO = flt(tc[0] * d.get_value('MontoUSD'),2);
						// 			console.log(tc);
						// 			d.set_value('MontoNIO',montoNIO);
						// 		}
						// 	}
						// },
						// {
						// 	fieldtype: "Column Break"
						// },
						// {
						// 	fieldtype: "Float",
						// 	label: "Monto C$",
						// 	precision: 2,
						// 	// options: "Customer",
						// 	fieldname: "MontoNIO",
						// 	// read_only: 1,
						// 	change: function(){
						// 		if(d.get_value('MontoNIO')){
						// 			var montoUSD = 0;
						// 			montoUSD = flt(d.get_value('MontoNIO') / tc[0],2);
						// 			console.log(tc);
						// 			d.set_value('MontoUSD',montoUSD);
						// 		}
						// 	}
						// },
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Deudas")
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
							// label: __("Deudas")
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
						// 	fieldtype: "Data",
						// 	label: "Anticipo",
						// 	// precision: 2,
						// 	// options: "Customer",
						// 	fieldname: "Anticipo",
						// 	read_only: 1,
						// },
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
						// {
						// 	fieldtype: "Section Break",
						// },
						// {
						// 	fieldtype: "Column Break"
						// 	// fieldtype: "Section Break",
						// 	// label: __("Total")
						// },
						// {
						// 	fieldtype: "Date",
						// 	label: "Fecha",
						// 	default: frappe.datetime.get_today(),
						// 	fieldname: "posting_date",
						// 	read_only: 1
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
							fieldname: "FormasDePagosDeposito_wrapper",
							options: `<div class=row>
					  <div class="col-sm-12 col-md-12 col-lg-12 col-xl-12">
					    <div class="row">
							<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4 style="padding-left: 0px;""> Tipo de pago</div>
							<div class="col-sm-4 col-md-4 col-lg-4 col-xl-4" style="padding-left: 0px;"> Moneda</div>
						</div>

						 <div class="row">
							<div class="col-sm-12 col-md-4 col-lg-4 col-xl-4" id="mode_of_payment_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-2 col-lg-2 col-xl-2" id="currency_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-3 col-lg-3  col-xl-3" id="amount_wrapper" style="padding-left: 0px;"></div>
							<div class="col-sm-12 col-md-2 col-lg-2 col-xl-2" id="action_wrapper" style="padding-left: 0px;">
								<button class="btn btn-primary hidden" role="button" id="action">Agregar</button>
							</div>
						 </div>
						 <div class="row" id="payments_wrapper"></div>
						 <br>
						 <div class="row">
							<div class="col-sm-12 col-md-12 col-lg-12 col-xl-12 text-center" style="padding-left: 0px;" >
								<h5>TC Banco</h5>
							</div>
							<div class="col-sm-12 col-md-12 col-lg-12 col-xl-12 text-center" style="padding-left: 0px;">
									<h5 id="Banco"></h5>
							</div>
							</br>

							<div class="col-sm-12 col-md-5 col-lg-5 col-xl-5" style="padding-left: 0px;">Cambio</div>
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
					],
					primary_action_label: 'Crear Deposito',
					primary_action(values) {
						console.log(values);
						d.hide();
					},
					// // secondary_action_label: "Cancel"
				});
			d.show();
			d.$wrapper.find(".modal-dialog").css({"top":"5%"});
			d.$wrapper.find(".modal-content").css({"width": "120%","left": "-10%"});

			//VALIDACION  DE DEPOSITO DE GARANTIA
			d.get_primary_btn().text('Crear Deposito').off('click').on('click', function(){
				// console.log(TotalesNIO);
				// SumaFormaPagos();
				console.log(totals);
				console.log(pm_args.pagos);
				// Validacion de montos
				var total1 = totals[0]['MontoNIO'];
				var total2 = totals[0]['MontoUSD'];
				var tipopago = 0;
				var monedaNIO = false;
				var monedaUSD = false;
				var Monto_DigitadoNIO = false;
				var Monto_DigitadoUSD = false;
				console.log(total1,total2);
				console.log(montos);

				// for(let i = 0; i < montos.length; i++){
				// 	if (montos[i] == total1){
				// 		Monto_DigitadoNIO = true;
				// 	}
				// }

				// for(let i = 0; i < montos.length; i++){
				// 	if (montos[i] == total2){
				// 		Monto_DigitadoUSD = true;
				// 	}
				// }
				
				var values = d.get_values();
				ValidarCamposDigitados(pm_args,tipopago,monedaNIO,monedaUSD,values);  

				// if (Monto_DigitadoNIO == true && Monto_DigitadoUSD == true){
				// 	var values = d.get_values();
				// 	ValidarCamposDigitados(pm_args,tipopago,monedaNIO,monedaUSD,values);  
				// }else {
				// 	frappe.msgprint({
				// 		title: __('Advertencia'),
				// 		indicator: 'red',
				// 		message: __('No es igual a los montos totales!')
				// 	});
				// 	// frappe.msgprint("No es igual a los montos totales!");
				// };
				// montos.includes(total1);
				// if (montos.includes(total1) || montos.includes(total2)){
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
					// console.log('Requisición Aplicar Deposito');
					// console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					// frappe.call({
					// 	'method': 'erpnext.api.crear_deposito',
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
					// 				cur_frm.set_value("customerdeposito",pm_args.regnumber);
					// 				cur_frm.set_value("tasa_de_cambiodeposito",pm_args.tc);
					// 				// cur_frm.set_value("meses_anticipo",d.get_value('Cantidad_Meses'));
					// 				cur_frm.set_value("tipo_de_pago","Deposito");
					// 				cur_frm.set_value("title","Deposito");
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
		//#endregion

		//#region Aplicar Deposito en Garantia
		cur_frm.cscript.AplicarDepositoDeposito = function(frm){

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
				pm_args['deudas'] = [];
				pm_args['deudas'].push({'link_doctype':'Sales Invoice', 'link_name': d.get_value('Factura')});
				pm_args.pagos = payments;
				console.log(tc[0]);
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
					title: __("Aplicar Depositos de Garantia"),
					fields: [
						{
							fieldtype: "Link",
							label: "Cliente",
							options: "Customer",
							fieldname: "customer",
							change:  function(){
									if(d.get_value('customer')){
										frappe.call({
											// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
											'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.ChecarDeposito',
											'args': {
												'Customer': d.get_value('customer')
											},
											'callback': function(res){
												console.log(res.message)
												if (res.message == 0){
													frappe.msgprint({
														title: __('Advertencia'),
														indicator: 'red',
														message: __('Lo sentimos, no tiene un Deposito resgistrado!')
													});
													d.set_value("customer",null);
												}else{
													get_exchange();
													// create_payments_areaAnticipo();
													d.set_value("Monto_de_Factura",res.message[0][3]);
													d.set_value("Deposito",res.message[0][0]);

													frappe.call({
														'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.Factura_Anticipos',
														'args': {
															'Customer': d.get_value('customer')
														},
														'callback': function(r){
															console.log(r.message[0][0])
														d.set_value('Monto_de_FacturaNIO',r.message[0][1])
														d.set_value('Factura',r.message[0][0])
														}
													});
													mostrarFactura(res.message[0][3]);



													// frappe.call({
													// 	// erpnext.support.doctype.issue.issue.get_plan_Susc_cust"
													// 	'method': 'erpnext.accounts.doctype.journal_entry.journal_entry.SumaDeAnticiposFactura',
													// 	'args': {
													// 		'Customer': d.get_value('customer')
													// 	},
													// 	'callback': function(res){
													// 		// format_currency(amounts.actual_nio, 'NIO', 2)
													// 		// [null].concat(data.tipos_de_pago)
													// 		console.log(res.message[0][1]);
													// 		var conver = 0, tc = 0,res1=0, iva=0,total=0,iva2=0,total2=0;
													// 		if(res.message[0][1] == "USD"){
													// 			iva = res.message[0][0] * 0.15;
													// 			// console.log(res.message[0][0]);
													// 			total = res.message[0][0] + iva;
													// 			d.set_value("Monto_de_Factura",total);

													// 			res1 = res.message[0];
													// 			conver = flt(d.get_value("conversion_rate") * res1[0],2);
													// 			iva2 = conver * 0.15;
													// 			total2 = conver + iva2;
													// 			d.set_value("Monto_de_FacturaNIO",total2);
													// 		}else{
													// 			console.log(res.message[0])
													// 			d.set_value("Monto_de_Factura",0);
													// 			iva = res.message[0][0] * 0.15;
													// 			total = res.message[0][0] + iva;
													// 			d.set_value("Monto_de_FacturaNIO",total);
													// 		}
													// 		// d.set_value("Monto_de_Factura",res.message[0]);
													// 	}
													// });
												}
											}
										});
									}
								},
							// on_make: d.get_value('customer').refresh(),
							// change: get_outstanding_details
						},
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Float",
							label: "Monto Deposito C$",
							precision: 2,
							// options: "Customer",
							fieldname: "Monto_de_Factura",
							read_only: 1,
						},
						{
							fieldtype: "Column Break"
							// fieldtype: "Section Break",
							// label: __("Deudas")
						},
						{
							fieldtype: "Data",
							label: "Deposito en Garantia",
							// precision: 2,
							// options: "Customer",
							fieldname: "Deposito",
							read_only: 1,
						},
						{
							fieldtype: "Section Break",
						},
						{
							fieldtype: "Data",
							label: "Factura",
							// precision: 2,
							// options: "Customer",
							fieldname: "Factura",
							read_only: 1,
						},
						{
							fieldtype: "Column Break"
						},
						{
							fieldtype: "Float",
							label: "Monto Factura $",
							precision: 2,
							// options: "Customer",
							fieldname: "Monto_de_FacturaNIO",
							read_only: 1,
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
			d.show();
			d.$wrapper.find(".modal-dialog").css({"top":"5%"});
			d.$wrapper.find(".modal-content").css({"width": "120%","left": "-10%"});

			//VALIDACION  DE APLICAR DEPOSTIO DE GARANTIA
			d.get_primary_btn().text('Aplicar Deposito en Garantia').off('click').on('click', function(){
				// console.log(TotalesNIO);
				// SumaFormaPagos();
				// console.log(totals);
				// // Validacion de montos
				// var total1 = totals[0]['MontoNIO'];
				// var total2 = totals[0]['MontoUSD'];
				// console.log(total1,total2);
				// console.log(montos);

				// montos.includes(total1);
				// if (montos.includes(total1) || montos.includes(total2)){
					console.log("PAso");
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
					pm_args._ui_ = true;
					console.log(pm_args);
					console.log('Requisición Aplicar Deposito de Garantia');
					console.log(Object.keys(pm_args).map(function(k) { return k + ': ' + JSON.stringify(pm_args[k]) }).join('\n'));
					frappe.call({
						'method': 'erpnext.api.aplicar_DepositosDeGarantia',
						'args': pm_args,
						'callback': function(res){
							if (res.message) {
								if (res.message.accounts.length && !res.message.messages.length){
									res.message.accounts.forEach(function(c){
										frm.add_child("accounts", c);
									});
									cur_frm.refresh_fields()
									cur_frm.set_value("posting_date", pm_args.fecha);
									cur_frm.set_value("multi_currency", 1);
									// cur_frm.set_value("customer",pm_args.regnumber);
									cur_frm.set_value("tasa_de_cambio",pm_args.tc);
									// cur_frm.set_value("meses_anticipo",d.get_value('Cantidad_Meses'));
									cur_frm.set_value("codigodeposito",d.get_value('Deposito'));
									cur_frm.set_value("tipo_de_pago","Aplicar Deposito");
									// cur_frm.set_value("title","Anticipo");
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
		//#endregion

		//#region Reversion
		cur_frm.cscript.AplicarReversion = function(frm){
			// console.log(frm.doc.name)
			frappe.call({
				args: {
					"AsientoContable": frm.doc.name
				},
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.Obtener_cuentas",
				callback: function (r) {
					console.log(r.message)
						if (r.message) {
							var doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", doc.doctype, doc.name);
					}
				}
			});
			
		
			// frappe.call({
			// 	"method": "erpnext.accounts.doctype.journal_entry.journal_entry.Obtener_cuentas",
			// 	"args": {
			// 	"AsientoContable": frm.doc.name
			// 	},
			// 	callback: function (r) {
			// 		console.log(r.messages)
			// 		// if (r.message) {
			// 		// 	var doc = frappe.model.sync(r.message)[0];
			// 		// 	frappe.set_route("Form", doc.doctype, doc.name);
			// 		// }
			// 	}
			// })
			
		}
		//#endregion

		//#region Botones Personalizados
	    if (frm.doc.docstatus === 0){
            frm.add_custom_button('Crear Pago', function(){
                cur_frm.cscript.make_customer_payment(frm);
            });
        }

		if (frm.doc.docstatus === 0){
            frm.add_custom_button('Crear Anticipo', function(){
                cur_frm.cscript.CrearAnticipos(frm);
            });
        }

		if (frm.doc.docstatus === 0){
            frm.add_custom_button('Crear Deposito en Garantia', function(){
                cur_frm.cscript.CrearDepositoGarantia(frm);
            });
        }

		frappe.call({
			"method": "erpnext.crm.doctype.opportunity.opportunity.consultar_rol",
		}).then(r =>{
				console.log(r.message)
				if((r.message.includes("Administrador Caja"))){
					if (frm.doc.docstatus === 1){
						frm.add_custom_button('Aplicar reversion', function(){
							cur_frm.cscript.AplicarReversion(frm);
						}, __("Finanzas"));
					}

					if (frm.doc.docstatus === 0){
					    frm.add_custom_button('Aplicar Deposito en Garantia', function(){
					        cur_frm.cscript.AplicarDepositoDeposito(frm);
					    }, __("Finanzas"));
					}

					if (frm.doc.docstatus === 0){
					    frm.add_custom_button('Aplicar Anticipo', function(){
					        cur_frm.cscript.AplicarAnticipos(frm);
					    }, __("Finanzas"));
					}
				}
			}

		);
		//#endregion
	},

	//#region Journal Entry Default frappe on
	make_inter_company_journal_entry: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __("Select Company"),
			fields: [
				{
					'fieldname': 'company',
					'fieldtype': 'Link',
					'label': __('Company'),
					'options': 'Company',
					"get_query": function () {
						return {
							filters: [
								["Company", "name", "!=", frm.doc.company]
							]
						};
					},
					'reqd': 1
				}
			],
		});
		d.set_primary_action(__('Create'), function() {
			d.hide();
			var args = d.get_values();
			frappe.call({
				args: {
					"name": frm.doc.name,
					"voucher_type": frm.doc.voucher_type,
					"company": args.company
				},
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.make_inter_company_journal_entry",
				callback: function (r) {
					if (r.message) {
						var doc = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					}
				}
			});
		});
		d.show();
	},

	multi_currency: function(frm) {
		erpnext.journal_entry.toggle_fields_based_on_currency(frm);
	},

	posting_date: function(frm) {
		if(!frm.doc.multi_currency || !frm.doc.posting_date) return;

		$.each(frm.doc.accounts || [], function(i, row) {
			erpnext.journal_entry.set_exchange_rate(frm, row.doctype, row.name);
		})
	},

	company: function(frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Company",
				filters: {"name": frm.doc.company},
				fieldname: "cost_center"
			},
			callback: function(r){
				if(r.message){
					$.each(frm.doc.accounts || [], function(i, jvd) {
						frappe.model.set_value(jvd.doctype, jvd.name, "cost_center", r.message.cost_center);
					});
				}
			}
		});

		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	voucher_type: function(frm){

		if(!frm.doc.company) return null;

		if((!(frm.doc.accounts || []).length) || ((frm.doc.accounts || []).length === 1 && !frm.doc.accounts[0].account)) {
			if(in_list(["Bank Entry", "Cash Entry"], frm.doc.voucher_type)) {
				return frappe.call({
					type: "GET",
					method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_default_bank_cash_account",
					args: {
						"account_type": (frm.doc.voucher_type=="Bank Entry" ?
							"Bank" : (frm.doc.voucher_type=="Cash Entry" ? "Cash" : null)),
						"company": frm.doc.company
					},
					callback: function(r) {
						if(r.message) {
							// If default company bank account not set
							if(!$.isEmptyObject(r.message)){
								update_jv_details(frm.doc, [r.message]);
							}
						}
					}
				});
			}
		}
	},

	from_template: function(frm){
		if (frm.doc.from_template){
			frappe.db.get_doc("Journal Entry Template", frm.doc.from_template)
				.then((doc) => {
					frappe.model.clear_table(frm.doc, "accounts");
					frm.set_value({
						"company": doc.company,
						"voucher_type": doc.voucher_type,
						"naming_series": doc.naming_series,
						"is_opening": doc.is_opening,
						"multi_currency": doc.multi_currency
					})
					update_jv_details(frm.doc, doc.accounts);
				});
		}
	}
	//#endregion
});


//#region Scripts Journal Enty Default 
var update_jv_details = function(doc, r) {
	$.each(r, function(i, d) {
		var row = frappe.model.add_child(doc, "Journal Entry Account", "accounts");
		row.account = d.account;
		row.balance = d.balance;
	});
	refresh_field("accounts");
}

erpnext.accounts.JournalEntry = class JournalEntry extends frappe.ui.form.Controller {
	onload() {
		this.load_defaults();
		this.setup_queries();
		this.setup_balance_formatter();
		erpnext.accounts.dimensions.setup_dimension_filters(this.frm, this.frm.doctype);
	}

	onload_post_render() {
		cur_frm.get_field("accounts").grid.set_multiple_add("account");
	}

	load_defaults() {
		//this.frm.show_print_first = true;
		if(this.frm.doc.__islocal && this.frm.doc.company) {
			frappe.model.set_default_values(this.frm.doc);
			$.each(this.frm.doc.accounts || [], function(i, jvd) {
				frappe.model.set_default_values(jvd);
			});
			var posting_date = this.frm.doc.posting_date;
			if(!this.frm.doc.amended_from) this.frm.set_value('posting_date', posting_date || frappe.datetime.get_today());
		}
	}

	setup_queries() {
		var me = this;

		me.frm.set_query("account", "accounts", function(doc, cdt, cdn) {
			return erpnext.journal_entry.account_query(me.frm);
		});

		me.frm.set_query("party_type", "accounts", function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];

			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
				filters: {
					'account': row.account
				}
			}
		});

		me.frm.set_query("reference_name", "accounts", function(doc, cdt, cdn) {
			var jvd = frappe.get_doc(cdt, cdn);

			// journal entry
			if(jvd.reference_type==="Journal Entry") {
				frappe.model.validate_missing(jvd, "account");
				return {
					query: "erpnext.accounts.doctype.journal_entry.journal_entry.get_against_jv",
					filters: {
						account: jvd.account,
						party: jvd.party
					}
				};
			}

			var out = {
				filters: [
					[jvd.reference_type, "docstatus", "=", 1]
				]
			};

			if(in_list(["Sales Invoice", "Purchase Invoice"], jvd.reference_type)) {
				out.filters.push([jvd.reference_type, "outstanding_amount", "!=", 0]);
				// Filter by cost center
				if(jvd.cost_center) {
					out.filters.push([jvd.reference_type, "cost_center", "in", ["", jvd.cost_center]]);
				}
				// account filter
				frappe.model.validate_missing(jvd, "account");
				var party_account_field = jvd.reference_type==="Sales Invoice" ? "debit_to": "credit_to";
				out.filters.push([jvd.reference_type, party_account_field, "=", jvd.account]);

				if (in_list(['Debit Note', 'Credit Note'], doc.voucher_type)) {
					out.filters.push([jvd.reference_type, "is_return", "=", 1]);
				}
			}

			if(in_list(["Sales Order", "Purchase Order"], jvd.reference_type)) {
				// party_type and party mandatory
				frappe.model.validate_missing(jvd, "party_type");
				frappe.model.validate_missing(jvd, "party");

				out.filters.push([jvd.reference_type, "per_billed", "<", 100]);
			}

			if(jvd.party_type && jvd.party) {
				var party_field = "";
				if(jvd.reference_type.indexOf("Sales")===0) {
					var party_field = "customer";
				} else if (jvd.reference_type.indexOf("Purchase")===0) {
					var party_field = "supplier";
				}

				if (party_field) {
					out.filters.push([jvd.reference_type, party_field, "=", jvd.party]);
				}
			}

			return out;
		});
	}

	setup_balance_formatter() {
		const formatter = function(value, df, options, doc) {
			var currency = frappe.meta.get_field_currency(df, doc);
			var dr_or_cr = value ? ('<label>' + (value > 0.0 ? __("Dr") : __("Cr")) + '</label>') : "";
			return "<div style='text-align: right'>"
				+ ((value==null || value==="") ? "" : format_currency(Math.abs(value), currency))
				+ " " + dr_or_cr
				+ "</div>";
		};
		this.frm.fields_dict.accounts.grid.update_docfield_property('balance', 'formatter', formatter);
		this.frm.fields_dict.accounts.grid.update_docfield_property('party_balance', 'formatter', formatter);
	}

	reference_name(doc, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if(d.reference_name) {
			if (d.reference_type==="Purchase Invoice" && !flt(d.debit)) {
				this.get_outstanding('Purchase Invoice', d.reference_name, doc.company, d);
			} else if (d.reference_type==="Sales Invoice" && !flt(d.credit)) {
				this.get_outstanding('Sales Invoice', d.reference_name, doc.company, d);
			} else if (d.reference_type==="Journal Entry" && !flt(d.credit) && !flt(d.debit)) {
				this.get_outstanding('Journal Entry', d.reference_name, doc.company, d);
			}
		}
	}

	get_outstanding(doctype, docname, company, child, due_date) {
		var me = this;
		var args = {
			"doctype": doctype,
			"docname": docname,
			"party": child.party,
			"account": child.account,
			"account_currency": child.account_currency,
			"company": company
		}

		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_outstanding",
			args: { args: args},
			callback: function(r) {
				if(r.message) {
					$.each(r.message, function(field, value) {
						frappe.model.set_value(child.doctype, child.name, field, value);
					})
				}
			}
		});
	}

	accounts_add(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		$.each(doc.accounts, function(i, d) {
			if(d.account && d.party && d.party_type) {
				row.account = d.account;
				row.party = d.party;
				row.party_type = d.party_type;
			}
		});

		// set difference
		if(doc.difference) {
			if(doc.difference > 0) {
				row.credit_in_account_currency = doc.difference;
				row.credit = doc.difference;
			} else {
				row.debit_in_account_currency = -doc.difference;
				row.debit = -doc.difference;
			}
		}
		cur_frm.cscript.update_totals(doc);

		erpnext.accounts.dimensions.copy_dimension_from_first_row(this.frm, cdt, cdn, 'accounts');
	}

};

cur_frm.script_manager.make(erpnext.accounts.JournalEntry);

cur_frm.cscript.update_totals = function(doc) {
	var td=0.0; var tc =0.0;
	var accounts = doc.accounts || [];
	for(var i in accounts) {
		td += flt(accounts[i].debit, precision("debit", accounts[i]));
		tc += flt(accounts[i].credit, precision("credit", accounts[i]));
	}
	var doc = locals[doc.doctype][doc.name];
	doc.total_debit = td;
	doc.total_credit = tc;
	doc.difference = flt((td - tc), precision("difference"));
	refresh_many(['total_debit','total_credit','difference']);
}

cur_frm.cscript.get_balance = function(doc,dt,dn) {
	cur_frm.cscript.update_totals(doc);
	cur_frm.call('get_balance', null, () => { cur_frm.refresh(); });
}

cur_frm.cscript.validate = function(doc,cdt,cdn) {
	cur_frm.cscript.update_totals(doc);
}

frappe.ui.form.on("Journal Entry Account", {
	party: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if(!d.account && d.party_type && d.party) {
			if(!frm.doc.company) frappe.throw(__("Please select Company"));
			return frm.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_party_account_and_balance",
				child: d,
				args: {
					company: frm.doc.company,
					party_type: d.party_type,
					party: d.party,
					cost_center: d.cost_center
				}
			});
		}
	},
	cost_center: function(frm, dt, dn) {
		erpnext.journal_entry.set_account_balance(frm, dt, dn);
	},

	account: function(frm, dt, dn) {
		erpnext.journal_entry.set_account_balance(frm, dt, dn);
	},

	debit_in_account_currency: function(frm, cdt, cdn) {
		erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	},

	credit_in_account_currency: function(frm, cdt, cdn) {
		erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	},

	debit: function(frm, dt, dn) {
		cur_frm.cscript.update_totals(frm.doc);
	},

	credit: function(frm, dt, dn) {
		cur_frm.cscript.update_totals(frm.doc);
	},

	exchange_rate: function(frm, cdt, cdn) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var row = locals[cdt][cdn];

		if(row.account_currency == company_currency || !frm.doc.multi_currency) {
			frappe.model.set_value(cdt, cdn, "exchange_rate", 1);
		}

		erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
	}
})

frappe.ui.form.on("Journal Entry Account", "accounts_remove", function(frm) {
	cur_frm.cscript.update_totals(frm.doc);
});

$.extend(erpnext.journal_entry, {
	toggle_fields_based_on_currency: function(frm) {
		var fields = ["currency_section", "account_currency", "exchange_rate", "debit", "credit"];

		var grid = frm.get_field("accounts").grid;
		if(grid) grid.set_column_disp(fields, frm.doc.multi_currency);

		// dynamic label
		var field_label_map = {
			"debit_in_account_currency": "Debit",
			"credit_in_account_currency": "Credit"
		};

		$.each(field_label_map, function (fieldname, label) {
			frm.fields_dict.accounts.grid.update_docfield_property(
				fieldname,
				'label',
				frm.doc.multi_currency ? (label + " in Account Currency") : label
			);
		})
	},

	set_debit_credit_in_company_currency: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];

		frappe.model.set_value(cdt, cdn, "debit",
			flt(flt(row.debit_in_account_currency)*row.exchange_rate, precision("debit", row)));

		frappe.model.set_value(cdt, cdn, "credit",
			flt(flt(row.credit_in_account_currency)*row.exchange_rate, precision("credit", row)));

		cur_frm.cscript.update_totals(frm.doc);
	},

	set_exchange_rate: function(frm, cdt, cdn) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var row = locals[cdt][cdn];

		if(row.account_currency == company_currency || !frm.doc.multi_currency) {
			row.exchange_rate = 1;
			erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
		} else if (!row.exchange_rate || row.exchange_rate == 1 || row.account_type == "Bank") {
			frappe.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_exchange_rate",
				args: {
					posting_date: frm.doc.posting_date,
					account: row.account,
					account_currency: row.account_currency,
					company: frm.doc.company,
					reference_type: cstr(row.reference_type),
					reference_name: cstr(row.reference_name),
					debit: flt(row.debit_in_account_currency),
					credit: flt(row.credit_in_account_currency),
					exchange_rate: row.exchange_rate
				},
				callback: function(r) {
					if(r.message) {
						row.exchange_rate = r.message;
						erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
					}
				}
			})
		} else {
			erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
		}
		refresh_field("exchange_rate", cdn, "accounts");
	},

	quick_entry: function(frm) {
		var naming_series_options = frm.fields_dict.naming_series.df.options;
		var naming_series_default = frm.fields_dict.naming_series.df.default || naming_series_options.split("\n")[0];

		var dialog = new frappe.ui.Dialog({
			title: __("Quick Journal Entry"),
			fields: [
				{fieldtype: "Currency", fieldname: "debit", label: __("Amount"), reqd: 1},
				{fieldtype: "Link", fieldname: "debit_account", label: __("Debit Account"), reqd: 1,
					options: "Account",
					get_query: function() {
						return erpnext.journal_entry.account_query(frm);
					}
				},
				{fieldtype: "Link", fieldname: "credit_account", label: __("Credit Account"), reqd: 1,
					options: "Account",
					get_query: function() {
						return erpnext.journal_entry.account_query(frm);
					}
				},
				{fieldtype: "Date", fieldname: "posting_date", label: __("Date"), reqd: 1,
					default: frm.doc.posting_date},
				{fieldtype: "Small Text", fieldname: "user_remark", label: __("User Remark")},
				{fieldtype: "Select", fieldname: "naming_series", label: __("Series"), reqd: 1,
					options: naming_series_options, default: naming_series_default},
			]
		});

		dialog.set_primary_action(__("Save"), function() {
			var btn = this;
			var values = dialog.get_values();

			frm.set_value("posting_date", values.posting_date);
			frm.set_value("user_remark", values.user_remark);
			frm.set_value("naming_series", values.naming_series);

			// clear table is used because there might've been an error while adding child
			// and cleanup didn't happen
			frm.clear_table("accounts");

			// using grid.add_new_row() to add a row in UI as well as locals
			// this is required because triggers try to refresh the grid

			var debit_row = frm.fields_dict.accounts.grid.add_new_row();
			frappe.model.set_value(debit_row.doctype, debit_row.name, "account", values.debit_account);
			frappe.model.set_value(debit_row.doctype, debit_row.name, "debit_in_account_currency", values.debit);

			var credit_row = frm.fields_dict.accounts.grid.add_new_row();
			frappe.model.set_value(credit_row.doctype, credit_row.name, "account", values.credit_account);
			frappe.model.set_value(credit_row.doctype, credit_row.name, "credit_in_account_currency", values.debit);

			frm.save();

			dialog.hide();
		});

		dialog.show();
	},

	account_query: function(frm) {
		var filters = {
			company: frm.doc.company,
			is_group: 0
		};
		if(!frm.doc.multi_currency) {
			$.extend(filters, {
				account_currency: frappe.get_doc(":Company", frm.doc.company).default_currency
			});
		}
		return { filters: filters };
	},

	reverse_journal_entry: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.make_reverse_journal_entry",
			frm: cur_frm
		})
	},
});

$.extend(erpnext.journal_entry, {
	set_account_balance: function(frm, dt, dn) {
		var d = locals[dt][dn];
		if(d.account) {
			if(!frm.doc.company) frappe.throw(__("Please select Company first"));
			if(!frm.doc.posting_date) frappe.throw(__("Please select Posting Date first"));

			return frappe.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_account_balance_and_party_type",
				args: {
					account: d.account,
					date: frm.doc.posting_date,
					company: frm.doc.company,
					debit: flt(d.debit_in_account_currency),
					credit: flt(d.credit_in_account_currency),
					exchange_rate: d.exchange_rate,
					cost_center: d.cost_center
				},
				callback: function(r) {
					if(r.message) {
						$.extend(d, r.message);
						erpnext.journal_entry.set_debit_credit_in_company_currency(frm, dt, dn);
						refresh_field('accounts');
					}
				}
			});
		}
	},
});
//#endregion