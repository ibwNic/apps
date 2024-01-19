import frappe
import json
from frappe.desk.doctype.tag.tag import DocTags
import six
from frappe import _
from frappe.utils import flt, cint, today
from datetime import datetime
from frappe import ValidationError, _, qb, scrub, msgprint
from zeep import client
import requests
from erpnext.crm.doctype.opportunity.opportunity import consultar_rol
from frappe.utils import flt, add_days,	add_months

from frappe.desk.query_report import run

import smtplib
from os.path import basename
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#region get_exchange_rate
@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, date=None, alternative=True, throw=False):
	if from_currency == to_currency:
		return 1

	exchange1 = '{0}-{1} {2}'.format(
		from_currency, to_currency,
		date or today()
	)
	exchange2 = '{1}-{0} {2}'.format(
		from_currency, to_currency,
		date or today()
	)

	for (ex, divide) in ((exchange1, 0), (exchange2, 1)):
		# flt redondea
		# Daily Exchange Rate
		value = flt(frappe.db.get_value(
			'Currency Exchange',
			ex,
			# 'exchange_rate' if not alternative else 'alternative_exchange_rate'
			'exchange_rate' if not alternative else 'paralela'
		))
		if value:
			if divide:
				value = 1.0 / value
			break

	if not value:
		if not throw:
			frappe.msgprint(frappe._(
				"Unable to find exchange rate for {0} to {1} on {2}".format(
					from_currency, to_currency,
					date or today()
				)
			))
		else:
			# Demas
			frappe.msgprint(frappe._(
				"Unable to find exchange rate for {0} to {1} on {2}".format(
					from_currency, to_currency,
					date or today()
				)
			))
		return 0.0
	return value
#endregion

#region get_exchange_rate
@frappe.whitelist()
def prueba():
	return 'No'
#endregion

# Trunca un flotante
def truncate(num, n):
    integer = int(num * (10**n))/(10**n)
    return float(integer)

@frappe.whitelist()
def validacion_de_Arreglo_Pendiente(name):
	arreglo = frappe.db.get_value('Arreglo de Pago',
				fieldname='name',
				filters={'regnumber': name, 'docstatus': 0})

	if arreglo:
		return {'error': 'El Cliente tiene arreglo de pago, le recomendamos cancelarlas!'}

#region consulta_deuda
# Regnumber es name del doctype Customers
@frappe.whitelist()
def consulta_deuda(name=None, factura=None, fecha=None, tc=None):
	if not fecha:
		fecha = today()

	if not tc or not flt(tc):
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)

	# return tc
	# En Customers el name es el regnumber
	# El name sin el SCI
	# regnumber = name.replace('SCI-','')
	if factura:
		if not frappe.db.exists('Sales Invoice',{'name':factura}):
			return {
				'status': 'error',
				'message': 'No invoice founds with ID {}'.format(factura)
			}
		else:
			regnumber = frappe.db.get_value('Sales Invoice', factura, 'customer')
	elif name:
		regnumber = frappe.get_doc('Customer',name)
		regnumber = regnumber.name

	customers = frappe.get_doc('Customer',regnumber)

	# return customers

	if not customers:
		return {
			'status': 'error',
			'message': 'No customers found with ID {}'.format(regnumber)
		}
	# elif len(customers) > 1:
	# 	return {
	# 		'status': 'error',
	# 		'message': '{} customers found fot the given ID {}'.format(len(customers), regnumber)
	# 	}
	else:
		# customer = customers[0].name
		customer = customers.name

	#validacion de arreglo de Pago
	va = validacion_de_Arreglo_Pendiente(name)
	
	if va:
		return va

	
	fecha = today()

	account_data = run('Cuentas por Cobrar del Cliente', {
		'report_date': add_months(fecha, 1),
		'customer': customer,
		'ageing_based_on': 'Posting Date',
		'company': 'IBW-NI',
		'range1': 30,
		'range2': 60,
		'range3': 90
	})

	# return account_data
	# columns = list(map(frappe.scrub, [r.split(':')[0] for r in account_data['result'][0]]))
	# data = list(map(frappe._dict, [zip(columns, row) for row in account_data['result']]))
	# return account_data['result']
    #     #import pdb; pdb.set_trace()

	# if data and "Total" in data[-1].values():
	# 	data.pop(-1)

	saldo = {'usd': 0.0, 'tc': tc}
	deudas = []
	creditos = []
	MontosSeleccion = []
	# MontosSeleccion = [23,600]

	# account_data['result']
	con = 0
	# return account_data['result'][0]["total_outstanding_amount"]
	# return len(account_data['result'])-1
	# for row in account_data['result']:
	# 	return row
	# 	return row['voucher_no']
	# 	if flt(row['total_outstanding_amount'], 2) < 0:
	# 		creditos.append(render_row(row, tc))

	# 	if flt(row['total_outstanding_amount'], 2) > 0:
	# 		if factura and account_data["result"][con]["voucher_no"] == factura:
	# 		if factura and flt(row['voucher_no']) == factura:
	# 			continue
	# 		return row,tc
	# 		deuda = render_row(row, tc)
	# 		saldo['usd'] += deuda['actual']['usd']
	# 		deudas.append(deuda)
	# 	if(con == int(len(account_data['result'])-1)):
	# 		break
	# 	con += 1

	l=len(account_data['result'])-1

	for r in range(0,l):
		# return row
		# return row['voucher_no']
		if flt(account_data['result'][r]["total_outstanding_amount"], 2) < 0:
			creditos.append(new_render_row(account_data['result'][r], tc))

		if flt(account_data['result'][r]["total_outstanding_amount"], 2) > 0:
			if flt(account_data['result'][r]["outstanding_amount"], 2) > 0:
				# if factura and account_data["result"][con]["voucher_no"] == factura:
				if factura and flt(account_data['result'][r]["voucher_no"]) == factura:
					continue
				# return row,tc
				deuda = new_render_row(account_data['result'][r], tc)
				saldo['usd'] += deuda['actual']['usd']
				deudas.append(deuda)

	# return deudas[0]["name"]

	# if deudas:
	# 	FactCordobas = frappe.db.get_value('Sales Invoice', {'name': deudas[0]["name"]}, 'debit_to')
	# 	# return FactCordobas
	# 	if FactCordobas == "DEUDORES VARIOS - NI":
	# 			dF=len(deudas)
	# 			# return d
	# 			# return deudas[0]["actual"]
	# 			for r in range(0,dF):
	# 				deudas[r]["actual"]['tc'] = 1
	# 				deudas[r]["actual"]['nio'] = 0
	# 				deudas[r]["actual"]['usd'] = 0
	# 				deudas[r]["actual"]['diferencial'] = 0
	# 				deudas[r]["deuda"]['usd'] = 0

	# D=len(deudas)
	# # for r in range(0,D):
	# # 	if flt(deudas['result'][r]["total_outstanding_amount"], 2) < 0:
	# # 		creditos.append(render_row(account_data['result'][r], tc))
	# return deudas
	# return account_data['result']
	# return deudas,deudas
	metodos_de_pagos = list(set(map(lambda d: d.parent,
		frappe.get_all('Mode of Payment Account', {'usuario': frappe.session.user},'parent'))))

	saldo['nio'] = new_compute_nio(**saldo)
	# return saldo

	return {
        'cliente': {
			'regnumber': regnumber,
			'nombre': frappe.db.get_value('Customer', {'name': ['like', '%'+regnumber]}, 'customer_name')
        },
		'saldo': saldo,
		'deudas': deudas,
		'creditos': creditos,
		# Hizo un pase raro, que se le va enviar un valor estatico 5 "miniminal_credit_amount".
		# 'monto_minimo_credito': flt(frappe.db.get_value('Accounts Settings', 'Accounts Settings', 'miniminal_credit_amount')),
		'monto_minimo_credito': flt(5),
        'tipos_de_pago': metodos_de_pagos,
		'monedas': [
			{'value': 'nio', 'label': 'C$'},
			{'value': 'usd', 'label': '$'}
		],
		'TCBanco': frappe.db.get_value('Currency Exchange',{'date':today()}, 'lafise')
	}
#endregion

#region new_render_row
def new_render_row(row, tc):
	ret = {'doctype': row['voucher_type'], 'name': row['voucher_no'], 'comentarios': row['remarks'], 'fecha': row['posting_date'], 'moneda_cuenta': row['moneda_cuenta']}
	deuda = new_get_deuda(row['voucher_type'], row['voucher_no'], row['moneda_cuenta'])
	actual = new_get_actual(deuda, tc, row['moneda_cuenta'])
	ret['deuda'] = deuda
	ret['actual'] = actual
	return ret

def new_compute_nio(usd, tc):
	return flt(flt(usd, 2) * flt(tc, 9), 2)

def new_compute_usd(nio, tc):
	return flt(flt(nio, 2) / flt(tc, 9), 2)

def new_compute_tc(usd, nio, rev=False):
	if not rev:
		return flt(nio / usd, 9)
	else:
		return flt(usd / nio, 9)

def new_get_deuda(voucher_type, voucher_no, moneda):
	if voucher_type == 'Sales Invoice':
		outstanding, tc, currency, tc_factura = frappe.db.get_value(voucher_type, voucher_no, ['outstanding_amount', 'conversion_rate', 'currency', 'tc_facturas'])

		if moneda == currency and moneda == "USD":
			ret = {
			'usd': flt(outstanding, 2),
			'tc': flt(tc, 5)
			}
			ret['nio'] = new_compute_nio(**ret)
		
		if moneda == currency and moneda == "NIO":
			ret = {
			'usd': new_compute_usd(flt(outstanding, 2),flt(tc_factura, 5)),
			'nio': flt(outstanding, 2),
			'tc': flt(tc_factura, 5)
			}
			# ret['usd'] = new_compute_usd(**ret)

		if moneda != currency and moneda == "NIO":
			ret = {
			'usd': new_compute_usd(flt(outstanding, 2),flt(tc_factura, 5)),
			'nio': flt(outstanding, 2),
			'tc': flt(tc_factura, 5)
			}
			# ret['usd'] = new_compute_usd(**ret)

		# ret = {
		# 	'usd': flt(outstanding, 2),
		# 	'tc': flt(tc, 5)
		# }
		# ret['nio'] = compute_nio(**ret)
	elif voucher_type == 'Journal Entry':
		outstanging = 0.0
		tc = 0.0
		ret = {}

	return ret

def new_get_actual(deuda, tc, moneda):
	ret = {
		'usd': deuda.get('usd'),
		'tc': tc
	}
	if moneda=="NIO":
		ret['nio']=deuda.get('nio')
	else:
		ret['nio'] = new_compute_nio(**ret)

	ret['diferencial'] = flt(ret['nio'] - deuda['nio'], 2)
	return ret
#endregion

#region render_row
def render_row(row, tc):
	ret = {'doctype': row['voucher_type'], 'name': row['voucher_no'], 'comentarios': row['remarks'], 'fecha': row['posting_date']}
	deuda = get_deuda(row['voucher_type'], row['voucher_no'])
	actual = get_actual(deuda, tc)
	ret['deuda'] = deuda
	ret['actual'] = actual
	return ret

def compute_nio(usd, tc):
	return flt(flt(usd, 2) * flt(tc, 9), 4)

def compute_usd(nio, tc):
	return flt(flt(nio, 2) / flt(tc, 9), 2)

def compute_tc(usd, nio, rev=False):
	if not rev:
		return flt(nio / usd, 9)
	else:
		return flt(usd / nio, 9)

def get_deuda(voucher_type, voucher_no):
	if voucher_type == 'Sales Invoice':
		outstanding, tc = frappe.db.get_value(voucher_type, voucher_no, ['outstanding_amount', 'conversion_rate'])
		ret = {
			'usd': flt(outstanding, 2),
			'tc': flt(tc, 5)
		}
		ret['nio'] = compute_nio(**ret)
	elif voucher_type == 'Journal Entry':
		outstanging = 0.0
		tc = 0.0
		ret = {}

	return ret

def get_actual(deuda, tc):
	ret = {
		'usd': deuda.get('usd'),
		'tc': tc
	}
	ret['nio'] = compute_nio(**ret)
	ret['diferencial'] = flt(ret['nio'] - deuda['nio'], 2)
	return ret
#endregion


#region aplicar_pago
@frappe.whitelist()
def aplicar_pago(regnumber=None, fecha=None, tc=None,deudas=None, creditos=None, pagos=None, cambios=None, aplicable=None, metadata=None, _ui_=False):
	local_user = frappe.session.user
	# return type(deudas),type(pagos)

	if isinstance(metadata, six.string_types):
		# lo convierte en un diccionario
		metadata = json.loads(metadata)

	# Asiganar a la metadata de Interfaz
	if regnumber:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# tc = tc.replace('\"','')

	# return customer
	# Dealer
	if metadata and 'colector' and 'IDdealer' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			# return 'No existe cierre'
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Colector
		# return 'Hay uno abierto'
	elif metadata and 'colector' in metadata:
		# Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})
		# Por el momento dejo pasar pagos, pero esta en la condicion Tercero
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})

		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Caja
	else:
		rol = consultar_rol()
		# return rol
		if rol and not 'Administrador Caja' in rol:
			Tercero = frappe.db.get_value('User',{'email':local_user})
			# return Tercero
			if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
				# return "OK"
				frappe.new_doc('Daily Closing Voucher').update({
					'posting_date': today(),
					'company': 'IBW-NI',
					'remarks': 'Cierre de Caja {}'.format(Tercero),
					'tipo': 'User',
					'tercero': Tercero
				}).insert()

	if not fecha:
		fecha = today()
	else:
		fecha = fecha.replace('\"','')

	# Tasa de cambio paralela
	if not tc:
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)

	messages = []
	accounts = []
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)
	if isinstance(creditos, six.string_types):
		creditos = json.loads(creditos, object_pairs_hook=frappe._dict)
	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	if isinstance(cambios, six.string_types):
		cambios = json.loads(cambios, object_pairs_hook=frappe._dict)
	if isinstance(aplicable, six.string_types):
		aplicable = json.loads(aplicable, object_pairs_hook=frappe._dict)

	if deudas:
		messages += validate_list_of_dicts(deudas, 'deudas', ('link_doctype', 'link_name'))
	if creditos:
		messages += validate_list_of_dicts(creditos, 'creditos', ('link_doctype', 'link_name'))
	if pagos:
		messages += validate_list_of_dicts(pagos, 'pagos', ('tipo_de_pago', 'moneda', 'monto'), ('referencia',))
	if cambios:
		messages += validate_list_of_dicts(cambios, 'cambios', ('moneda', 'monto'))

	if not regnumber and not deudas and not (creditos or pagos):
		return {
			'status': 'error',
			'message': 'You should provide at least the regnumber or deudas and/or creditos or pagos'
		}
	elif not regnumber:
		if not creditos and not pagos:
			return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}

	if not regnumber:
		return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	else:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# Falta depurar
	
	if deudas:
		validate_party_entries(deudas, accounts, messages, tc, 'c', customer=customer)
	if creditos:
		validate_party_entries(creditos, accounts, messages, tc, 'd', customer=customer)
	if pagos:
		validate_payment_entries(pagos, accounts, messages, tc, 'd')
	if cambios:
		validate_payment_entries( list(map(lambda d: d.update({'tipo_de_pago': 'Efectivo'}), cambios)), accounts, messages, tc, 'c')

	# return accounts
	# return tc
	# Importante
	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']


	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return tc

	# condicion de pagos parciales
	if flt(sum_debits,2) < flt(sum_credits,2):
		# si hay Pago en cordobas
		if hayNIO == "NIO":
			# Pago parcial para Cordobas
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['credit_in_account_currency'] = flt(flt(acc.get('credit', 0.0),2) / flt(acc.get('exchange_rate'), 4), 4)
				acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
				acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
		else:
			# Pago parcial para dolares
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				if acc['account_currency'] == "NIO":
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(acc.get('exchange_rate', 1.0), 4)
				else:
					# return accounts
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(tc, 4)
					# acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2)
					acc['exchange_rate'] = flt(tc,4)
					if accounts[1]['account_currency'] == "USD":
						acc['account_currency_pago'] = accounts[1]['account_currency']
					else:
						acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
	else:
	# # No se efectua la conversacion del monto con la tasa de cambio
	# # Pagos con forme de la factura

		# return accounts

		if hayNIO == "NIO" and flt(sum_debits,2) == flt(sum_credits,2):
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			# return facs
			for acc in facs:
				ac = accounts[0]["credit_in_account_currency"]
				t= flt(ac,2)*flt(tc,4)
				acc['credit'] = abs(t)
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					# Tasa de cambio una decima menor
					acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = "USD"
					acc['exchange_rate'] = tc
				# break
		else:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			for acc in facs:
				# Validacion de que punto tomar
				# acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
				# El monto en dolares en cuenta de Factura
				acc['credit_in_account_currency'] = acc['credit_in_account_currency']
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['account_currency_pago'] = accounts[1]['account_currency']
				# if  accounts[1]['account_currency'] == "USD":
				# 	if hayNIO=="USD":
				# 		acc['exchange_rate'] = flt(tc,4)
				# else:
				# 	acc['account_currency_pago'] = None
				# break

	# return accounts

	diff = None
	diff_amount = None
	# hayNIOExc="USD"
	# #import pdb; pdb.set_trace()
	# # Guarda  un nuevo documento
	# return accounts
	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

		# hayNIOExc="USD"

		# for a in tdoc.get("accounts"):
		# 	if a.account_currency == "NIO":
		# 		hayNIOExc = a.account_currency
		# 		break

	# return tdoc.get("accounts")
	# return diff_amount

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# reemplaza el 5 > abs(flt(frappe.db.get_value('Accounts Settings', 'Accounts Settings', 'miniminal_credit_amount')))
	# 	if diff_amount > 0 and flt(diff_amount, 2) / flt(tc) > 5:
	# # 		#  Facturación Cobrada por Anticipado - IBWNI
	# 		diff = list(filter(lambda e: e['account'] == u'2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI', accounts))
	# 		if not diff:
	# # 			#  Facturación Cobrada por Anticipado - IBWNI
	# 			account = frappe.db.get_value('Account', filters={'name': ['like', '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI']})
	# 			if not regnumber:
	# 				account = account.replace(' - ', ' ZZ - ')
	# 			diff = {
	# 				'account': account,
	# 				'account_currency': 'USD',
	# 				'account_type': 'Payable',
	# 				'credit_in_account_currency': 0.0,
	# 				'credit': 0.0,
	# 				'debit_in_account_currency': 0.0,
	# 				'debit': 0.0,
	# 				'exchange_rate': 0.0,
	# 				'party_type': 'Customer',
	# 				'party': get_cliente_id(regnumber),
	# 				'is_advance': 'Yes'
	# 			}
	# 			accounts.append(diff)
	# 		else:
	# 			diff = diff[0]

	# 		diff['credit'] = flt(abs(diff_amount), 2)
	# 		diff['credit_in_account_currency'] = compute_usd(abs(diff_amount), tc)
	# 		diff['exchange_rate'] = compute_tc(diff['credit_in_account_currency'], diff['credit'])
	# 	else:
		# Generar utilidades
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	if _ui_:
		return {
			'accounts': accounts,
			'messages': messages
		}
	if messages:
		return {
			'status': 'error',
			'error': u'\n'.join(messages)
		}
	else:
		doc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'mode_of_payment': pagos[0]['tipo_de_pago'],
			# 'user_remark': 'Recibo de pago' + fecha,
			'ui': _ui_
		})

		if not regnumber:
			doc.user_remark = 'Pago ZZ'

		if metadata:
			if 'colector' in metadata:
				#  Collector toma una cuenta
				metadata['collector'] = frappe.db.get_value('Colectores', filters={'colectorid': metadata.pop('colector')})
				# return metadata
			if 'IDdealer' in metadata:
				metadata['dealer'] = frappe.db.get_value('Colectores', filters={'iddealer':metadata.pop('IDdealer')})
			if 'recibo' in metadata:
				metadata['user_remark'] = metadata.pop('recibo')
				# return metadata
				doc.update(metadata)
		# return metadata
		try:
			doc.save()
			if 'dealer' in metadata and 'collector' in metadata:
				id_Name_Dealer = metadata['dealer']
				estado = False
			elif 'collector' in metadata:
				id_Name_Dealer = metadata['collector']
				estado = False
			else:
				id_Name_Dealer = None
				estado = True

			res = registrarPagoEnElCierre(doc,id_Name_Dealer, estado)

			if isinstance(res, str):
				frappe.db.rollback()
				return res

			doc.flags.ignore_submit_comment = True
			doc.submit()
			frappe.db.commit()
			if not regnumber:
				DocTags(doc.doctype).add(doc.name, 'ZZ')
				frappe.db.commit()
		except Exception as e:
			if doc.name and doc.docstatus:
				if not regnumber:
					DocTags(doc.doctype).add(doc.name, 'ZZ')
					frappe.db.commit()
				return doc.name.split("-")[1]
			return {
				'status': 'error',
				'error': e,
				'doc': doc.as_json()
			}

		frappe.db.commit()
		frappe.set_user(local_user)

		return doc.name.split("-")[1]
#endregion

#region registrarPagoEnElCierre
def registrarPagoEnElCierre(pago, idDealer=0, for_owner=False):
	# Trae el doctype del cierre de caja
	cierre = obtenerCierre(idDealer, for_owner=for_owner)

	if cierre == 1:
		# error = "Debe de cerrar caja antes de empezar hacer transacciones"
		# frappe.db.set_value('Journal Entry', , 'docstatus', 0)
		return cierre

	party = None
	party_type = None
	nombre = ""
	for acc in pago.get("accounts"):
		if acc.party:
			party = acc.party
			party_type = acc.party_type or "Customer"
			nombre = frappe.db.get_value('Customer',party,'customer_name')


		# Detalle del cierre de caja es obsoleto porque se requiere de crear multiples cuentas
		# Agrega Detalle
		# if not cierre.get("details", {"account": acc.account}):
		# 	detail = cierre.append("details", {
		# 		"account": acc.account,
		# 		"currency": acc.account_currency,
		# 		"amount": 0.0,
		# 		"amount_in_company_currency": 0.0
		# 	})
		# else:
		# 	detail = cierre.get("details", {"account": acc.account})[0]

		# if not detail.currency:
		# 	detail.currency = acc.account_currency
		# if acc.debit:
		# 	detail.amount += acc.debit_in_account_currency
		# 	detail.amount_in_company_currency += acc.debit
		# else:
		# 	detail.amount -= acc.credit_in_account_currency
		# 	detail.amount_in_company_currency -= acc.credit

	# PARA ASIGNARLE EL NOMBRE DE ANTICIPO O DEPOSITO DE GARANTIA
	if pago.get("customerdeposito") or pago.get("customer"):
			if pago.get("customerdeposito"):
				codigoCliente = pago.get("customerdeposito")
			if pago.get("customer"):
				codigoCliente = pago.get("customer")
			nombre2 = frappe.db.get_value('Customer',codigoCliente,'customer_name')

	if nombre=="":
		nombre = frappe.db.get_value('Customer',pago.get("customer"),'customer_name')

	for a in range(1,len(pago.accounts)):
		if pago.accounts[a].tipo_de_cuenta=="Recibido":
			if pago.accounts[a].account_currency == "NIO":
			# Suma Cordobas
				if not cierre.get("totales_modo_de_pagos", {"modo_de_pago": pago.accounts[a].mode_of_payment}):
					cierre.append("totales_modo_de_pagos", {
						"modo_de_pago":pago.accounts[a].mode_of_payment,
						"nio":flt(pago.accounts[a].debit_in_account_currency,2),
						"usd":0.0
					})
				else:
					TotalesModoPago = cierre.get("totales_modo_de_pagos", {"modo_de_pago": pago.accounts[a].mode_of_payment})[0]
					TotalesModoPago.nio += pago.accounts[a].debit_in_account_currency

				cierre.append("references", {
					"document_type": pago.doctype,
					"document_name": pago.name,
					"voucher_type": pago.voucher_type,
					"voucher_status": "Submitted",
					"party_type": party_type or "Customer",
					"party": party or codigoCliente,
					"nombre":nombre or nombre2,
					"nio": flt(pago.accounts[a].debit_in_account_currency,2),
					"usd": 0.0,
					"modo_de_pago": pago.accounts[a].mode_of_payment
				})

			if pago.accounts[a].account_currency == "USD":
			# Suma Dolares
				if not cierre.get("totales_modo_de_pagos", {"modo_de_pago": pago.accounts[a].mode_of_payment}):
					cierre.append("totales_modo_de_pagos", {
						"modo_de_pago":pago.accounts[a].mode_of_payment,
						"nio":0.0,
						"usd":flt(pago.accounts[a].debit_in_account_currency,2)
					})
				else:
					TotalesModoPago = cierre.get("totales_modo_de_pagos", {"modo_de_pago": pago.accounts[a].mode_of_payment})[0]
					TotalesModoPago.usd += pago.accounts[a].debit_in_account_currency

				cierre.append("references", {
					"document_type": pago.doctype,
					"document_name": pago.name,
					"voucher_type": pago.voucher_type,
					"voucher_status": "Submitted",
					"party_type": party_type or "Customer",
					"party": party or codigoCliente,
					"nombre":nombre or nombre2,
					"nio": 0.0,
					"usd": flt(pago.accounts[a].debit_in_account_currency,2),
					"modo_de_pago": pago.accounts[a].mode_of_payment
				})

	# REGISTRAR PAGOS EN EL CIERRE EN LA TABLA MONTO RECIDOS
	if pago.monto_recibido_dolares:
		if not cierre.get("montosrecibidos", {"modo_de_pago": "Efectivo"}):
			if pago.monto_recibido_dolares and pago.monto_recibido_cordobas == 0 and pago.vuelto_en_cordobas and pago.vuelto_en_dolares:
				cierre.append("montosrecibidos", {
				"modo_de_pago":"Efectivo",
				"nio":flt(pago.vuelto_en_cordobas,2) *-1,
				"usd":flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
				})
			elif pago.monto_recibido_dolares and pago.monto_recibido_cordobas == 0 and pago.vuelto_en_cordobas and pago.vuelto_en_dolares == 0:
				cierre.append("montosrecibidos", {
				"modo_de_pago":"Efectivo",
				"nio":flt(pago.vuelto_en_cordobas,2) *-1,
				"usd":flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
				})
				# cierre.append("montosrecibidos")	
			else:
				cierre.append("montosrecibidos", {
					"modo_de_pago":"Efectivo",
					"nio":0.0,
					"usd":flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
				})
			# 	cierre.append("montosrecibidos")
		else:
			montosrecibidos = cierre.get("montosrecibidos", {"modo_de_pago": "Efectivo"})[0]
			montosrecibidos.usd += flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
			if pago.vuelto_en_cordobas and pago.monto_recibido_cordobas == 0:
				montosrecibidos.nio += flt(pago.vuelto_en_cordobas,2) *-1

	if pago.monto_recibido_cordobas:
		if not cierre.get("montosrecibidos", {"modo_de_pago": "Efectivo"}):
			if pago.monto_recibido_cordobas and pago.monto_recibido_dolares == 0 and pago.vuelto_en_dolares and pago.vuelto_en_cordobas:
				cierre.append("montosrecibidos", {
				"modo_de_pago":"Efectivo",
				"nio":flt(pago.vuelto_en_dolares,2) * -1,
				"usd":flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
				})
			elif pago.monto_recibido_cordobas and pago.vuelto_en_dolares and pago.vuelto_en_cordobas == 0:
				cierre.append("montosrecibidos", {
				"modo_de_pago":"Efectivo",
				"nio":flt(pago.vuelto_en_dolares,2) * -1,
				"usd":flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
				})
			else:
				cierre.append("montosrecibidos", {
					"modo_de_pago":"Efectivo",
					"nio":flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2),
					"usd":0.0
				})
		else:
			montosrecibidos = cierre.get("montosrecibidos", {"modo_de_pago": "Efectivo"})[0]
			montosrecibidos.nio += flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2)
			if pago.vuelto_en_dolares and pago.monto_recibido_dolares == 0:
				montosrecibidos.usd += flt(pago.vuelto_en_dolares,2) * -1

	# cierre.append("references", {
	# 	"document_type": pago.doctype,
	# 	"document_name": pago.name,
	# 	"voucher_type": pago.voucher_type,
	# 	"voucher_status": "Submitted",
	# 	"party_type": party_type or "Customer",
	# 	"party": party,
	# 	"currency": pago.total_amount_currency,
	# 	"amount": pago.total_amount
	# })

	cierre.flags.ignore_permissions = True
	cierre.save()

	return cierre
#endregion

#region movimentarPagoEnElCierre
#Cancelacion de pagos en cierre activo
def movimentarPagoEnElCierre(pago, idDealer=None, for_owner=False):
	#Obtiene el cierre de caja

	cierre = obtenerCierre(idDealer, for_owner=for_owner)
	# if cierre == 1:
	# 	raise Exception("Debe de cerrar caja antes de empezar hacer transacciones update")
	# return cierre
	if not cierre.get("references", {"document_type": pago.doctype, "document_name": pago.name}) and not for_owner:
		return {
			"response": "Error",
			"variables": ["idDealer"],
			"message": "Ya se cancelo el pago!"
			# "message": "El pago no pertenece al cajón activo, ¡no se puede cancelar!"
		}

	try:
		# reference = cierre.get("references", {'document_type': pago.doctype, "document_name": pago.name})[0]
		reference = cierre.get("references", {'document_type': pago.doctype, "document_name": pago.name})
		# return reference
	except IndexError:
		frappe.throw(frappe._("No se puede anular el Pago {0}, despues de haber cerrado la caja!").format(pago.name))

	# return len(reference)
	for a in range(0, len(reference)):
		try:
			cierre.references.remove(reference[a])
		except Exception as e:
			frappe.throw(frappe._("ERROR: {0}. Referencia: {1}").format(str(e), reference.name))

		# Elimina la referencia
		# reference = reference.update({"voucher_status": "Cancelled"})
		# cierre.append("cancelled", reference)
		# nombre = frappe.db.get_value('Customer',reference[a].get("party_type"),'customer_name')
		cierre.append("cancelled", {
			"document_type": pago.doctype,
			"document_name": pago.name,
			"voucher_type": pago.voucher_type,
			"voucher_status": "Cancelled",
			"party_type":reference[a].get("party_type"),
			"nombre":reference[a].get("nombre"),
			"party": reference[a].get("party"),
			"nio": reference[a].get("nio"),
			"usd": reference[a].get("usd"),
			"modo_de_pago": reference[a].get("modo_de_pago")
		})

	# return cierre
	# try:
	# 	cierre.references.remove(reference)
	# except Exception as e:
	# 	frappe.throw(frappe._("ERROR: {0}. Referencia: {1}").format(str(e), reference.name))

	# # Elimina la referencia
	# # reference = reference.update({"voucher_status": "Cancelled"})
	# # cierre.append("cancelled", reference)

	# cierre.append("cancelled", {
	# 	"document_type": pago.doctype,
	# 	"document_name": pago.name,
	# 	"voucher_type": pago.voucher_type,
	# 	"voucher_status": "Cancelled",
	# 	"party_type":reference.get("party_type"),
	# 	"party": reference.get("party"),
	# 	"currency": pago.total_amount_currency,
	# 	"amount": pago.total_amount
	# })

	# Detalle del cierre de caja es obsoleto porque se requiere de crear multiples cuentas
	# Elimina el detalle
	# for acc in pago.get("accounts"):
	# 	detail = cierre.get("details", {"account": acc.account})
	# 	if detail:
	# 		detail = detail[0]
	# 		if acc.debit:
	# 			detail.amount -= acc.debit_in_account_currency
	# 			detail.amount_in_company_currency -= acc.debit
	# 		else:
	# 			detail.amount += acc.credit_in_account_currency
	# 			detail.amount_in_company_currency += acc.credit

	# 		if not detail.amount or not detail.amount_in_company_currency:
	# 			cierre.details.remove(detail)

	# Elimina el Pago de monto totales
	for a in range(1,len(pago.accounts)):
		if pago.accounts[a].tipo_de_cuenta=="Recibido":
			ModosPagosTotales = cierre.get("totales_modo_de_pagos", {"modo_de_pago":pago.accounts[a].mode_of_payment})[0]


			if ModosPagosTotales:
				if pago.accounts[a].account_currency == "NIO":
				# Resta Cordobas
					ModosPagosTotales.nio -= pago.accounts[a].debit_in_account_currency

				if pago.accounts[a].account_currency == "USD":
				# Resta Dolares
					ModosPagosTotales.usd -= pago.accounts[a].debit_in_account_currency



	montosRecibidos = cierre.get("montosrecibidos", {"modo_de_pago":"Efectivo"})

	if montosRecibidos:
		if pago.monto_recibido_cordobas and pago.monto_recibido_dolares and pago.vuelto_en_cordobas and pago.vuelto_en_dolares:
			if montosRecibidos[0].nio > 0:
				montosRecibidos[0].nio -= flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2)

			if montosRecibidos[0].nio < 0:
				montosRecibidos[0].nio += flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2)

			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd -= flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
			
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd += flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)

		#Vueltos Mixtos Recibidos Dolares y vuelto cordobas
		if pago.monto_recibido_dolares and flt(pago.vuelto_en_cordobas,2) > 0 and pago.monto_recibido_cordobas == 0 and pago.vuelto_en_dolares == 0:
		# Resta 
			if montosRecibidos[0].nio > 0:
				montosRecibidos[0].nio -= flt(pago.vuelto_en_cordobas,2)
			
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd -= flt(pago.monto_recibido_dolares,2)
			
			if montosRecibidos[0].nio < 0:
				montosRecibidos[0].nio += flt(pago.vuelto_en_cordobas,2)
			
			if montosRecibidos[0].usd < 0:
				montosRecibidos[0].usd + flt(pago.monto_recibido_dolares,2)
		
		#Vueltos de pagos con Cordobas 
		if pago.monto_recibido_cordobas and pago.monto_recibido_dolares == 0 and pago.vuelto_en_cordobas and pago.vuelto_en_dolares == 0:
			if montosRecibidos[0].nio > 0:
				montosRecibidos[0].nio -= flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2)

			if montosRecibidos[0].nio < 0:
				montosRecibidos[0].nio += flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2)

		#Vueltos de pagos con Dolares
		if pago.monto_recibido_dolares and pago.vuelto_en_dolares and pago.vuelto_en_cordobas == 0 and pago.vuelto_en_cordobas == 0:
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd -= flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
			
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd += flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)

		#Vueltos Mixtos Recibidos Cordobas y vuelto Dolares.
		if pago.monto_recibido_cordobas and flt(pago.vuelto_en_dolares,2) > 0 and pago.monto_recibido_dolares == 0 and pago.vuelto_en_cordobas == 0:
		# Resta Cordobas
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd -= flt(pago.vuelto_en_dolares,2)
			
			if montosRecibidos[0].nio > 0:
				montosRecibidos[0].nio -= flt(pago.monto_recibido_cordobas,2)
			
			if montosRecibidos[0].usd < 0:
				montosRecibidos[0].usd += flt(pago.vuelto_en_dolares,2)
			
			if montosRecibidos[0].nio < 0:
				montosRecibidos[0].nio += flt(pago.monto_recibido_cordobas,2)
		
		#Vueltos Mixtos Recibidos Dolares y vuelto cordobas y dolares
		if pago.monto_recibido_dolares and flt(pago.vuelto_en_cordobas,2) > 0 and pago.monto_recibido_cordobas == 0 and flt(pago.vuelto_en_dolares,2) > 0:
		# Resta 
			if montosRecibidos[0].nio > 0:
				montosRecibidos[0].nio -= flt(pago.vuelto_en_cordobas,2)
			
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd -= flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)
			
			if montosRecibidos[0].nio < 0:
				montosRecibidos[0].nio += flt(pago.vuelto_en_cordobas,2)
			
			if montosRecibidos[0].usd < 0:
				montosRecibidos[0].usd + flt(pago.monto_recibido_dolares,2)-flt(pago.vuelto_en_dolares,2)

		#Vueltos Mixtos Recibidos Cordobas y vuelto Dolares y cordobas
		if pago.monto_recibido_cordobas and flt(pago.vuelto_en_dolares,2) > 0 and pago.monto_recibido_dolares == 0 and pago.vuelto_en_cordobas == 0:
		# Resta Cordobas
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd -= flt(pago.vuelto_en_dolares,2)
			
			if montosRecibidos[0].nio > 0:
				montosRecibidos[0].nio -= flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2)
			
			if montosRecibidos[0].usd < 0:
				montosRecibidos[0].usd += flt(pago.vuelto_en_dolares,2)
			
			if montosRecibidos[0].nio < 0:
				montosRecibidos[0].nio += flt(pago.monto_recibido_cordobas,2)-flt(pago.vuelto_en_cordobas,2)
		
		#Vueltos 0 con pagos completos CORDOBAS
		if pago.monto_recibido_cordobas and flt(pago.vuelto_en_dolares,2) == 0 and pago.monto_recibido_dolares == 0 and pago.vuelto_en_cordobas == 0:
		# # Resta Cordobas
			if montosRecibidos[0].nio > 0:
				montosRecibidos[0].nio -= flt(pago.monto_recibido_cordobas,2)

			if montosRecibidos[0].nio < 0:
				montosRecibidos[0].nio += flt(pago.monto_recibido_cordobas,2)

		#Vueltos 0 con pagos completos CORDOBAS BIEN
		if pago.monto_recibido_dolares and flt(pago.vuelto_en_cordobas,2) == 0 and pago.monto_recibido_cordobas == 0 and pago.vuelto_en_dolares == 0:
		# # Resta Cordobas
			if montosRecibidos[0].usd > 0:
				montosRecibidos[0].usd -= flt(pago.monto_recibido_dolares,2)

			if montosRecibidos[0].usd < 0:
				montosRecibidos[0].usd += flt(pago.monto_recibido_dolares,2)

	cierre.flags.ignore_permissions = True
	cierre.save()
	return cierre
#endregion

#region obtenerCierre
def obtenerCierre(idDealer=None, for_owner=False):
	if not for_owner:
		# return 'LLEGA'
		#  Collector. Revisar si es por id o por el nombre
		iddealer = frappe.db.exists("Colectores", {'name': ['like', '%' + str(idDealer)]})
		if not iddealer:
			return {
				'response': 'Error',
				'variable': ['idDealer'],
				'message': 'Dealer not found with ID {0}'.format(idDealer)
			}
		idDealer = iddealer
		dealer_name, TipoColector = frappe.db.get_value("Colectores", idDealer, ["name", "collector_type"])
		# return dealer_name, TipoColector
		if TipoColector == 'Dealer':
			dcv = frappe.db.exists("Daily Closing Voucher", {"tercero": dealer_name, "docstatus": 0})
			if dcv:
				doc = frappe.get_doc("Daily Closing Voucher", dcv)
		elif TipoColector == 'Colector':
			dcv = frappe.get_all("Daily Closing Voucher", "name", {"tercero": dealer_name, "docstatus": 0,"posting_date": today()})
			if not dcv:
				doc = abrirCierre(idDealer)
			else:
				doc = frappe.get_doc("Daily Closing Voucher", dcv[0].name)

		# if not for_owner:
		# 	dcv = frappe.get_all("Daily Closing Voucher", "name", {"tercero": dealer_name, "docstatus": 0,"posting_date": today()})
		# else:
		# 	dcv = frappe.get_all("Daily Closing Voucher", "name", {"tercero": dealer_name, "docstatus": 0, "posting_date": today()})

	else:
		dcv = frappe.get_list("Daily Closing Voucher", "name", {"owner": frappe.session.user, "docstatus": 0, "posting_date": today()})
		if dcv:
			doc = frappe.get_doc("Daily Closing Voucher", dcv[0].name)
			doc.flags.ignore_permissions = True
		else:
			doc = abrirCierre(0, True)

	return doc
#endregion

#region abrirCierre
# Apertura de cierre de caja
def abrirCierre(idDealer=0, for_owner=False):
	if not for_owner:
		#  Collector. Revisar si es por id o por el nombre
		iddealer = frappe.db.exists("Colectores", {'name': ['like', '%' + str(idDealer)]})
		if not iddealer:
			return {
				'response': 'Error',
				'variable': ['idDealer'],
				'message': 'Dealer not found with ID {0}'.format(idDealer)
			}
		idDealer = iddealer
		dealer_name= frappe.db.get_value("Colectores", idDealer, ["name"])

		# Validar fecha
		if not frappe.db.count("Daily Closing Voucher", {"tercero": dealer_name,"docstatus": 1, "posting_date":today()}):
			return 1
	else:
		# Validacion para el cierre de caja
		if not frappe.db.count("Daily Closing Voucher", {"owner": frappe.local.user, "docstatus": 1, "posting_date": today()}):
			acl = frappe.get_list("Account",["name", "is_group"], {"is_group": 1})
			if len(acl) == 0:
				frappe.throw("Usted not tiene configurada una caja maestra!<br>Contacte el personal de soporte!")
			# elif len(acl) > 1:
			# 	return 1

		# dealer_account = frappe.get_list("Account",["name", "is_group"], {"is_group": 1})[0].name

	doc = frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(frappe.session.user),
				'tipo': 'User',
				'tercero': frappe.session.user
			})


	# doc = frappe.new_doc("Daily Closing Voucher").update({
	# 	"transaction_date": today(),
	# 	"posting_date": today(),
	# 	"company": "IBW-NI",
	# 	"closing_account_head": dealer_account,
	# 	"remarks": "Cierre de Caja Dealer {}".format(dealer_name) if not for_owner else "Cierre de Caja {}".format(frappe.local.user)
	# })
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc
#endregion

#region obtenerCierreCaja
# Validacion para el cierre de Caja
@frappe.whitelist()
def obtenerCierreCaja(for_owner=False):
	if for_owner:
		# local_user = frappe.session.user

		# Tercero = frappe.db.get_value('User',{'email':local_user})
		# return Tercero
		HayCierreDia = frappe.get_list("Daily Closing Voucher","name", {"owner": frappe.local.user, "docstatus": 0,"posting_date": today()})
		# # Nama_CierreCierreAbierto = frappe.get_list("Daily Closing Voucher","name", {"owner": frappe.local.user, "docstatus": 0})
		# # No tiene cierre abiertos
		# return HayCierreDia
		if HayCierreDia:
			return 0
		else:
			# Si tiene cierre abierto, debe de cerrarlo antes.
			return 1
#endregion

#region Reversion de Pagos
# Reversion de Pagos
@frappe.whitelist()
def Obtener_cuentass(AsientoContable):
	je = frappe.get_doc('Journal Entry',AsientoContable)
	accounts=[]
	for acc in je.accounts:
		accouts = {
		'account' :	acc.account,
		'party_type':acc.party_type,
		'party': acc.party,
		'account_currency':acc.account_currency,
		'credit_in_account_currency':acc.debit_in_account_currency,
		'credit': acc.debit,
		'exchange_rate':acc.exchange_rate,
		'debit_in_account_currency':acc.credit_in_account_currency,
		'debit':acc.credit,
		'reference_name':acc.reference_name,
		'reference_type':acc.reference_type,
		'tipo_de_cuenta':acc.tipo_de_cuenta,
		'account_currency_pago':acc.account_currency_pago,
		'doctype':acc.doctype
		}
		accounts.append(accouts)

	l=len(accounts)

	for r in range(0,l):
		if accounts[r]['debit_in_account_currency'] == 0.0:
			accounts[r].pop('debit_in_account_currency')

		if accounts[r]['debit'] == 0.0:
			accounts[r].pop('debit')

		if accounts[r]['credit_in_account_currency'] == 0.0:
			accounts[r].pop('credit_in_account_currency')

		if accounts[r]['credit'] == 0.0:
			accounts[r].pop('credit')

		if accounts[r]['party'] == None:
			accounts[r].pop('party')

		if accounts[r]['party_type'] == None:
			accounts[r].pop('party_type')

		if accounts[r]['reference_name'] == None:
			accounts[r].pop('reference_name')

		if accounts[r]['reference_type'] == None:
			accounts[r].pop('reference_type')

		if accounts[r]['account_currency_pago'] == None:
			accounts[r].pop('account_currency_pago')




		# if accounts[r]['debit']:
		# 	accounts[r]['credit'] = accounts[r]['debit']
		# 	accounts[r].pop('debit')

		# if accounts[r]['credit_in_account_currency']:
		# 	accounts[r]['debit_in_account_currency'] = accounts[r]['credit_in_account_currency']
		# 	accounts[r].pop('credit_in_account_currency')

		# if accounts[r]['credit']:
		# 	accounts[r]['debit'] = accounts[r]['credit']
		# 	accounts[r].pop('credit')


	newJe = frappe.new_doc('Journal Entry')
	newJe.update({
		'posting_date': today(),
		'posting_time': today(),
		'accounts':accounts,
		'observacion': 'Se revertio el pago'
	})


	return {'docs': newJe.as_dict()}
	# return accounts
#endregion

#region  Validacion para el cierre de caja Interfaz
# Apertura de cierre de caja
def abrirCierreCaja(idDealer=0, for_owner=False):
	if for_owner:
		# Validacion para el cierre de caja
		if not frappe.db.count("Daily Closing Voucher", {"owner": frappe.local.user, "docstatus": 1, "posting_date": today()}):
			acl = frappe.get_list("Account",["name", "is_group"], {"is_group": 1})
			if len(acl) == 0:
				frappe.throw("Usted not tiene configurada una caja maestra!<br>Contacte el personal de soporte!")
			elif len(acl) > 1:
				return 1
	return 0
#endregion

def validate_list_of_dicts(obj, variable, mandatory, optional=()):
	if not isinstance(obj, (list, tuple, set)):
		return ["The {0} doesn't look like a list of mapping".format(variable)]
	ret = []
	for i, row in enumerate(obj, 1):
		# ret.append(row.keys())
		if not isinstance(row, dict):
			ret += ["The row {0} from {1} is not an mapping".format(i, variable)]
			continue
		# Pase raro
		diff_extra = (set(row.keys()) - set(mandatory)) - set(optional)
		# diff_extra = 'si'
		if diff_extra:
			ret += ["The row {0} from {1} have {2} invalid key(s) ({3})".format(i, variable, len(diff_extra), ", ".join(diff_extra))]

		diff_missing = (set(mandatory) - (set(row.keys()) - set(optional)))
		if diff_missing:
			ret += ["The row {0} from {1} have {2} missing key(s) ({3})".format(i, variable, len(diff_extra), ", ".join(diff_missing))]

	return ret

def validate_party_entries(entries, accounts, messages, tc, dc='c', customer=None):
	# return type(entries)
	customer_founds = set()
	if customer:
		customer_founds.add(customer)
	for entry in entries:
		if not frappe.db.exists(entry['link_doctype'], entry['link_name']):
			messages.append("The {0} {1} doesn't exists".format(entry["link_doctype"], entry["link_name"]))
		elif entry['link_doctype'] == 'Sales Invoice':
			invoice_customer = frappe.db.get_value(entry["link_doctype"], entry["link_name"], "customer")
			if not customer_founds:
				customer_founds.add(invoice_customer)
			elif entry['link_doctype'] == 'Journal Entry':
				customers_set, message = get_customer_from_journal_entry(entry['link_name'])
				if message:
					messages.append(message['message'])
				elif len(customers_set) > 1:
					messages.append('The {0} {1} belongs to {2} customers, you should pass regnumber!'.format(
						entry['link_doctype'],
						entry['link_name'],
						len(customers_set)))
				else:
					customer_founds.add(customers_set[0])
			
			get_party_account_row(entry, customer or list(customer_founds)[-1], accounts, tc, dc)
		if len(customer_founds) > 1:
			messages.append('Mismatch in deudas values, one payment cannot pay invoice(s) for {0} diferent customers ({1})'.format(
				len(customer_founds), ', '.join(customer_founds)))

def get_customer_from_journal_entry(je):
	ret = set()
	if not frappe.db.count('Journal Entry Account', {'parent': je, 'party_type': 'Customer', "reference_name": ["is", None]}):
		return ret, {
			'status': 'error',
			'message': "Journal Entry {0} doesn't belong to any customer".format(je)
		}
	else:
		for account in frappe.get_all("Journal Entry Account", fields=["party"], filters={"parent": je, "party_type": "Customer", "reference_name": ["is", None]}):
			ret.add(account.party)
		return ret, None

def get_party_account_row(entry, customer, accounts, tc, dc='c'):
	from erpnext.accounts.party import get_party_account, get_party_account_currency
	# list(entry)
	# print('Metodo 2')
	# print(type(entry))
	ret = {'party_type': 'Customer', 'party': customer, 'reference_type': entry.link_doctype, 'reference_name': entry.link_name}
	party_args = {'party_type': 'Customer', 'party': customer, 'company' :'IBW-NI'}
	account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
	prefix = 'credit' if dc == 'c' else 'debit'
	field = '{0}_in_account_currency'.format(prefix)
	ret.update({'account': account, 'account_currency': account_currency})
	if entry.link_doctype == "Sales Invoice":
		ret[field] = frappe.db.get_value(entry.link_doctype, entry.link_name, 'outstanding_amount')
		if account_currency == 'USD':
			er = frappe.db.get_value(entry.link_doctype, entry.link_name, 'conversion_rate')
		else:
			er = 1.0
			# Hice pase tasa tc
		ret[prefix] = compute_nio(ret[field], er)
        #frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
		#ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
		ret['exchange_rate'] = er
	accounts.append(ret)

	#diff_amount = flt(compute_nio(ret[field], tc) - ret[prefix], 2)
	#frappe.msgprint('<pre>{}</pre>'.format(diff_amount))
	diff_amount = flt(ret[field] - (ret[prefix] / er), 2)
	#frappe.msgprint('<pre>{}</pre>'.format(diff_amount))
	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# 6.22.010-Utilidades Cambiarias - NI
		# Filtra la variable Acccounts donde el tipo de cuetenta sea  Utilidades Cambiarias - IBWNI
		diff = list(filter(lambda e: e['account'] == 'Utilidades Cambiarias - IBWNI', accounts))
		if not diff:
			diff = {'account': 'Utilidades Cambiarias - IBWNI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0}
			accounts.append(diff)
		else:
			diff = diff[0]
		# ABS Funcion que transforma los numeros a positivos
		diff[p] += abs(diff_amount)
		diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

def validate_payment_entries(entries, accounts, messages, tc, dc='d'):
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in entries:
		currency = currency_map.get((entry.moneda or '').lower())
		if not currency:
			messages.append('The currency {0} is not recognized as an valid currency!'.format(entry.moneda))
		else:
			if not frappe.db.exists('Mode of Payment Account', {'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user}):
				messages.append("The active user don't have an properly configured account for mode of payment {0}".format(entry.tipo_de_pago))
			else:
				default_account = frappe.db.get_value('Mode of Payment Account',
					fieldname='default_account',
					filters={'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user})

				prefix = 'debit' if dc == 'd' else 'credit'
				field = '{0}_in_account_currency'.format(prefix)

				row = {'account': default_account, 'account_currency': currency, 'mode_of_payment':entry.tipo_de_pago}
				row[field] = flt(entry.monto, 2)

				if currency == 'NIO':
					er = 1.0
				else:
					# tc = tc.replace('\"','')
					er = tc
				# row[prefix] = compute_nio(row[field], er)
				# er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)

def get_cliente_id(regnumber):
	if regnumber is None:
		return
	customers = frappe.get_all('Customer', filters={'name': ['like', '%' + regnumber]})
	if customers:
		return customers[0].name

#region revertirPago API - BTN Cancelar
@frappe.whitelist(allow_guest=True)
def revertirPago(AprobadoIBW=None,AprobadoExterno=None):
	# return 'Ok'
	if not AprobadoIBW and not AprobadoIBW:
		return {
			'response': 'Error',
			'variables': ['AprobadoExterno', 'AprobadoIBW'],
			'message': 'No args provided'
		}

	if not AprobadoIBW:
		return {
			'response': 'Error',
			'variables': ['AprobadoExterno', 'AprobadoIBW'],
			'message': 'No args provided'
		}


	# if AprobadoExterno:
	# 	je = frappe.db.exists("Journal Entry", {'name': ['like', 'I-{}%'.format(AprobadoIBW)], 'cheque_no': AprobadoExterno})

	# elif all([AprobadoIBW, Recibo, CollectorID]):
	# 	# Falta valida si los tres campos pertence a la mismo pago
	# 	# frappe.db.exists({"Journal Entry": AprobadoIBW, "user_remark":Recibo, })
	# 	je = frappe.db.exists("Journal Entry", {'name': ['like', 'JV-{}%'.format(AprobadoIBW)]})
	# 	# return je
	# else:
	# 	je = frappe.db.exists("Journal Entry", {'name': ['like', 'JV-{}%'.format(AprobadoIBW)]})

	if all([AprobadoIBW, AprobadoExterno]):
		je = frappe.db.exists("Journal Entry", {'name': ['like', 'JV-{}%'.format(AprobadoIBW)]})
		# return je
	elif AprobadoIBW:
		je = frappe.db.exists("Journal Entry", {'name': ['like', 'JV-{}%'.format(AprobadoIBW)]})
	else:
		je = frappe.db.exists("Journal Entry", {'name': ['like', 'JV-{}%'.format(AprobadoIBW)]})

	# return je
	if not je:
		return {
			'response': 'Error',
			'variables': ['AprobadoExterno', 'AprobadoIBW'],
			'message': 'No existe pago'
		}
	else:
		try:
			jeDoc = frappe.get_doc("Journal Entry", je)
			# return jeDoc
			jeDoc.flags.ignore_permissions = True
			# Validar el tercer parametro
			# return jeDoc
			# res = movimentarPagoEnElCierre(jeDoc, jeDoc.collector,True)
			res = movimentarPagoEnElCierre(jeDoc, jeDoc.dealer,False)
			# cierre = obtenerCierre(jeDoc.collector, for_owner=False)
			# return res
			# idDealer = None
			# iddealer = frappe.db.exists("Colectores", {'name': ['like', '%' + str(jeDoc.collector)]})
			# idDealer = iddealer
			# dealer_name, dealer_name = frappe.db.get_value("Colectores", idDealer, ["name", "collector_type"])
			# return dealer_name,dealer_name
			# bien
			if isinstance(res, dict):
				frappe.db.rollback()
				return res
			jeDoc.flags.ignore_submit_comment = True
			jeDoc.cancel()
			frappe.db.commit()
		except Exception as e:
			return {
				'response': 'Error res',
				'variables': ['InternalError'],
				'messsage': str(e)
			}
		return 'OK'
#endregion

#region cierreTransaciones
@frappe.whitelist(allow_guest=True)
def cierreTransaciones(idDealer=None):
	# iddealer = frappe.db.exists("Colectores", {'name': ['like', '%' + str(idDealer.strip()).rjust(5, '0')]})
	iddealer = frappe.db.exists("Colectores", {'iddealer': idDealer})

	# return iddealer
	if not iddealer:
		return {
			'response': 'Error',
			'variable': ['idDealer'],
			'message': 'Dealer not found with ID {0}'.format(idDealer)
		}
	idDealer = iddealer
	# return idDealer
	dealer_name, dealer_account = frappe.db.get_value("Colectores", idDealer, ["name", "account"])
	# return dealer_name

	# if not  frappe.db.count("Daily Closing Voucher", {"tercero": dealer_name, "docstatus": 0}):
	# c = frappe.db.count("Daily Closing Voucher", {"tercero": dealer_name, "docstatus": 0,'owner':frappe.session.user,'tipo':'Colectores'})
	# return c,frappe.session.user
	# Checa si no hay en el cierre con esos parametros
	if not frappe.db.count("Daily Closing Voucher", {"tercero": dealer_name, "docstatus": 0,'owner':frappe.session.user,'tipo':'Colectores'}):
		return {
			'response': 'Error',
			'variable': ['idDealer'],
			'message': "Don't have transactions to date as {0}".format(today())
		}

	# return 'PAso'
	cierre = obtenerCierre(idDealer,False)
	# doc = frappe.get_doc('Daily Closing Voucher','CIERRE-2023-02-14-0000005')
	
	# return cierre
	cierre.flags.ignore_permissions = True

	try:
		cierre.run_method('validate')
		cierre.save()
		cierre.flags.ignore_submit_comment = True
		cierre.submit()

	except Exception as e:
		return {
			'response': 'Error',
			'variable': ['InternalError'],
			'message': str(e)
		}

	frappe.db.commit()
	# return doc.name.replace("CLS", "").replace("-", "")
	return "Ok"
#endregion

@frappe.whitelist(allow_guest=True)
def ConsultaDeCliente(CodigoCliente=None,NombreCompleto=None,NoIdentificacion=None,Factura=None):
	if CodigoCliente or NombreCompleto or NoIdentificacion or Factura:
		customers = set()
		if Factura:
			for row in frappe.get_all('Sales Invoice', fields='customer', filters={'name': ['like', '%'+Factura.strip()]}):
				if row.get("customer"):
					customers.add(row['customer'])
		if CodigoCliente:
			customers.add(CodigoCliente.strip())
		# return customers
		conditions = []
		if customers:
			conditions.append('{0}'.format(
			' OR '.join(['customer.name LIKE "%{0}%"'.format(c)for c in customers if c])))
		# return conditions
		if NombreCompleto:
			conditions.append('customer.customer_name like "%{0}%"'.format(frappe.db.escape(NombreCompleto.strip())))

		# return conditions
		customers = frappe.db.sql("""
		SELECT
			customer.name as `name`,
			customer.customer_name,
			customer.customer_type as customer_type,
			Round(sum(`sales_invoice`.`outstanding_amount`),2) as outstanding_amount,
			address.address_line1 as address,
			address.city as city,
			address.phone as phone,
			address.fax as business_phone,
			address.email_id as email_id,
			customer.cedula as cedula,
			customer.tax_id as ruc
		FROM `tabCustomer` customer
		LEFT JOIN `tabAddress` address ON address.address_title = customer.name and address.is_primary_address = 1
		LEFT JOIN `tabSales Invoice` sales_invoice ON sales_invoice.customer = customer.name and sales_invoice.docstatus = 1
		{cond}
		""".format(**{
			'cond': ("WHERE " + " AND ".join(conditions)) if conditions else ""
		}), as_dict=1)

		# return customers,conditions
		return {
			'response': 'OK',
			'data': [
				{
					'RegNumber': customer['name'].split('-')[-1],
					'FirstName': "".join(customer.get("customer_name", customer.get('name')).split(" ")[0]),
					'LastName': "".join(customer.get("customer_name", customer.get('name')).split(" ")[-1]),
					'Company': customer["customer_name"] if customer["customer_type"] != "Residencial" else "IBW",
					'TipoCliente': customer["customer_type"],
					'Saldo': customer["outstanding_amount"],
					'Address': customer["address"],
					'City': customer["city"],
					'HomePhone': customer["phone"],
					'MobilePhone': customer["phone"],
					'BusinessPhone': customer["business_phone"],
					'Email': customer["email_id"],
					'Cedula': customer["cedula"],
					'RUC': customer["ruc"]
				} for customer in customers if customer.get('name')
			]
		}
	else:
		return {
			'response': 'Error',
			'message': 'No args provided'
		}

#region Anticipos
#Anticipos
@frappe.whitelist()
def crear_anticipo(regnumber=None, fecha=None, tc=None,deudas=None, creditos=None, pagos=None, cambios=None, aplicable=None, metadata=None, _ui_=False):
	local_user = frappe.session.user

	if isinstance(metadata, six.string_types):
		# lo convierte en un diccionario
		metadata = json.loads(metadata)

	regnumber = regnumber.replace('\"','')
	# Asiganar a la metadata de Interfaz
	if regnumber:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# return customer
	# Dealer
	if metadata and 'colector' and 'IDdealer' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Colector
	elif metadata and 'colector' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})

		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Caja
	else:
		Tercero = frappe.db.get_value('User',{'email':local_user})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			# return "OK"
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'User',
				'tercero': Tercero
			}).insert()

	if not fecha:
		fecha = today()
	else:
		fecha = fecha.replace('\"','')

	# Tasa de cambio paralela
	if not tc:
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)

	messages = []
	accounts = []
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)
	if isinstance(creditos, six.string_types):
		creditos = json.loads(creditos, object_pairs_hook=frappe._dict)
	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	if isinstance(cambios, six.string_types):
		cambios = json.loads(cambios, object_pairs_hook=frappe._dict)
	if isinstance(aplicable, six.string_types):
		aplicable = json.loads(aplicable, object_pairs_hook=frappe._dict)

	if deudas:
		messages += validate_list_of_dicts(deudas, 'deudas', ('link_doctype', 'link_name',"MontoFac"))
	if creditos:
		messages += validate_list_of_dicts(creditos, 'creditos', ('link_doctype', 'link_name'))
	if pagos:
		messages += validate_list_of_dicts(pagos, 'pagos', ('tipo_de_pago', 'moneda', 'monto'), ('referencia',))
	if cambios:
		messages += validate_list_of_dicts(cambios, 'cambios', ('moneda', 'monto'))

	if not regnumber and not deudas and not (creditos or pagos):
		return {
			'status': 'error',
			'message': 'You should provide at least the regnumber or deudas and/or creditos or pagos'
		}
	elif not regnumber:
		if not creditos and not pagos:
			return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}

	if not regnumber:
		return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	else:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})
	# return messages
	# Falta depurar
	if deudas:
		# validate_party_entries(deudas, accounts, messages, tc, 'c', customer=customer)
		validate_party_entriesAnticipo(deudas, accounts, messages, tc, 'c', customer=customer)
	if creditos:
		validate_party_entries(creditos, accounts, messages, tc, 'd', customer=customer)
	if pagos:
		validate_payment_entries(pagos, accounts, messages, tc, 'd')
	if cambios:
		validate_payment_entries( list(map(lambda d: d.update({'tipo_de_pago': 'Efectivo'}), cambios)), accounts, messages, tc, 'c')

	# return accounts
	# Importante
	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.0) for d in accounts])
	# return accounts,sum_debits,sum_credits,messages
	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	# facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))
	facs = list(filter(lambda acc: acc.get("account") == "2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI", accounts))
	

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	# facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))
	facs = list(filter(lambda acc: acc.get("account") != "2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']


	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return accounts
	# condicion de pagos parciales
	if sum_debits < sum_credits:
		# si hay Pago en cordobas
		if hayNIO == "NIO":
			# Pago parcial para Cordobas
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['credit_in_account_currency'] = flt(flt(acc.get('credit', 0.0),2) / flt(acc.get('exchange_rate'), 4), 4)
				acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
				acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
		else:
			# Pago parcial para dolares
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				if acc['account_currency'] == "NIO":
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(acc.get('exchange_rate', 1.0), 4)
				else:
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(tc, 4)
					acc['exchange_rate'] = flt(tc,4)
					if accounts[1]['account_currency'] == "USD":
						acc['account_currency_pago'] = accounts[1]['account_currency']
					else:
						acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
	else:
	# # No se efectua la conversacion del monto con la tasa de cambio
	# # Pagos con forme de la factura

		# return accounts

		if hayNIO == "NIO" and sum_credits == sum_debits:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			# return facs
			for acc in facs:
				ac = accounts[0]["credit_in_account_currency"]
				t= flt(ac,2)*flt(tc,4)
				acc['credit'] = abs(t)
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = "USD"
					acc['exchange_rate'] = tc
				# break
		else:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			for acc in facs:
				# Validacion de que punto tomar
				acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					if hayNIO=="USD":
						acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = None
				# break

	# return accounts

	diff = None
	diff_amount = None
	hayNIOExc="USD"
	# #import pdb; pdb.set_trace()
	# # Guarda  un nuevo documento
	# return accounts
	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

		hayNIOExc="USD"

		for a in tdoc.get("accounts"):
			if a.account_currency == "NIO":
				hayNIOExc = a.account_currency
				break

	# return tdoc.get("accounts")
	# return diff_amount

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# reemplaza el 5 > abs(flt(frappe.db.get_value('Accounts Settings', 'Accounts Settings', 'miniminal_credit_amount')))
	# 	if diff_amount > 0 and flt(diff_amount, 2) / flt(tc) > 5:
	# # 		#  Facturación Cobrada por Anticipado - IBWNI
	# 		diff = list(filter(lambda e: e['account'] == u'2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI', accounts))
	# 		if not diff:
	# # 			#  Facturación Cobrada por Anticipado - IBWNI
	# 			account = frappe.db.get_value('Account', filters={'name': ['like', '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI']})
	# 			if not regnumber:
	# 				account = account.replace(' - ', ' ZZ - ')
	# 			diff = {
	# 				'account': account,
	# 				'account_currency': 'USD',
	# 				'account_type': 'Payable',
	# 				'credit_in_account_currency': 0.0,
	# 				'credit': 0.0,
	# 				'debit_in_account_currency': 0.0,
	# 				'debit': 0.0,
	# 				'exchange_rate': 0.0,
	# 				'party_type': 'Customer',
	# 				'party': get_cliente_id(regnumber),
	# 				'is_advance': 'Yes'
	# 			}
	# 			accounts.append(diff)
	# 		else:
	# 			diff = diff[0]

	# 		diff['credit'] = flt(abs(diff_amount), 2)
	# 		diff['credit_in_account_currency'] = compute_usd(abs(diff_amount), tc)
	# 		diff['exchange_rate'] = compute_tc(diff['credit_in_account_currency'], diff['credit'])
	# 	else:
		# Generar utilidades
		if diff_amount > 0:
			if hayNIOExc == "NIO":
				# Utilidades Cambiarias - IBWNI
				diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

				if not diff:
				#  Utilidades Cambiarias - IBWNI
					diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
					accounts.append(diff)
				else:
					diff = diff[0]

				diff[p] += abs(diff_amount)
				diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

				# return accounts
				if diff and diff['debit'] and diff['credit']:
					if diff['debit'] > diff['credit']:
						diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
						diff['debit'] -= diff['credit']
						diff['credit_in_account_currency'] = diff['credit'] = 0.0
					else:
						diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
						diff['credit'] -= diff['debit']
						diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			if hayNIOExc == "NIO":
					# Utilidades Cambiarias - IBWNI
					diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

					if not diff:
					##  Utilidades Cambiarias - IBWNI
						diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
						accounts.append(diff)
					else:
						diff = diff[0]

					diff[p] += abs(diff_amount)
					diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

					# return accounts
					if diff and diff['debit'] and diff['credit']:
						if diff['debit'] > diff['credit']:
							diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
							diff['debit'] -= diff['credit']
							diff['credit_in_account_currency'] = diff['credit'] = 0.0
						else:
							diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
							diff['credit'] -= diff['debit']
							diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	if _ui_:
		return {
			'accounts': accounts,
			'messages': messages
		}
	if messages:
		return {
			'status': 'error',
			'error': u'\n'.join(messages)
		}
	else:
		doc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'mode_of_payment': pagos[0]['tipo_de_pago'],
			'user_remark': 'Aplicacion de Pago ' + fecha,
			'ui': _ui_
		})

		if not regnumber:
			doc.user_remark = 'Pago ZZ'

		if metadata:
			if 'colector' in metadata:
				#  Collector toma una cuenta
				metadata['collector'] = frappe.db.get_value('Colectores', filters={'colectorid': metadata.pop('colector')})
				# return metadata
			if 'dealer' in metadata:
				metadata['dealer'] = frappe.db.get_value('Colectores', filters={'iddealer':metadata.pop('dealer')})
			if 'recibo' in metadata:
				metadata['ensure_name'] = metadata.pop('recibo')
				# return metadata
				doc.update(metadata)

		try:
			doc.save()
			if 'dealer' in metadata and 'collector' in metadata:
				id_Name_Dealer = metadata['dealer']
				estado = False
			elif 'collector' in metadata:
				id_Name_Dealer = metadata['collector']
				estado = False
			else:
				id_Name_Dealer = None
				estado = True

			res = registrarPagoEnElCierre(doc,id_Name_Dealer, estado)

			if isinstance(res, str):
				frappe.db.rollback()
				return res

			doc.flags.ignore_submit_comment = True
			doc.submit()
			frappe.db.commit()
			if not regnumber:
				DocTags(doc.doctype).add(doc.name, 'ZZ')
				frappe.db.commit()
		except Exception as e:
			if doc.name and doc.docstatus:
				if not regnumber:
					DocTags(doc.doctype).add(doc.name, 'ZZ')
					frappe.db.commit()
				return doc.name.split("-")[1]
			return {
				'status': 'error',
				'error': e,
				'doc': doc.as_json()
			}

		frappe.db.commit()
		frappe.set_user(local_user)

		return doc.name.split("-")[1]

def get_party_account_rowAnticipo(entry, customer, accounts, tc, dc='c'):
	from erpnext.accounts.party import get_party_account, get_party_account_currency

	ret = {'party_type': '', 'party': '', 'reference_type': '', 'reference_name': ''}
	party_args = {'party_type': 'Customer', '': '', 'company' :'IBW-NI'}
	# account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
	# account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
	account = '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI'
	#  2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI

	prefix = 'credit' if dc == 'c' else 'debit'
	field = '{0}_in_account_currency'.format(prefix)
	ret.update({'account': account, 'account_currency': "NIO"})
	if entry.link_doctype == "Anticipo":
		# accounts == 1
		# ret[field] = frappe.db.get_value(entry.link_doctype, entry.link_name, 'outstanding_amount')
		ret[field] = entry.MontoFac
		# # if account_currency == 'USD':
		# # 	er = frappe.db.get_value(entry.link_doctype, entry.link_name, 'conversion_rate')
		# # else:
		# # 	er = 1.0
		# ret[prefix] = flt(compute_nio(ret[field], tc),2)
		ret[prefix] = flt(compute_nio(ret[field], 1),2)
        # #frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
		# #ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
		ret['exchange_rate'] = flt(1,3)
	accounts.append(ret)

def validate_party_entriesAnticipo(entries, accounts, messages, tc, dc='c', customer=None):
	customer_founds = set()
	if customer:
		customer_founds.add(customer)
	for entry in entries:
		# if not frappe.db.exists(entry['link_doctype'], entry['link_name']):
		# 	messages.append("The {0} {1} doesn't exists".format(entry["link_doctype"], entry["link_name"]))
		# elif entry['link_doctype'] == 'Sales Invoice':
		if entry['link_doctype'] == 'Anticipo':
			# invoice_customer = frappe.db.get_value(entry["link_doctype"], entry["link_name"], "customer")
			# if not customer_founds:
			# 	customer_founds.add(invoice_customer)
			# elif entry['link_doctype'] == 'Journal Entry':
			# 	customers_set, message = get_customer_from_journal_entry(entry['link_name'])
			# 	if message:
			# 		messages.append(message['message'])
			# 	elif len(customers_set) > 1:
			# 		messages.append('The {0} {1} belongs to {2} customers, you should pass regnumber!'.format(
			# 			entry['link_doctype'],
			# 			entry['link_name'],
			# 			len(customers_set)))
			# 	else:
			# 		customer_founds.add(customers_set[0])
			# get_party_account_row(entry, customer or list(customer_founds)[-1], accounts, tc, dc)
			get_party_account_rowAnticipo(entry, customer, accounts, tc, dc)
		if len(customer_founds) > 1:
			messages.append('Mismatch in deudas values, one payment cannot pay invoice(s) for {0} diferent customers ({1})'.format(
				len(customer_founds), ', '.join(customer_founds)))

@frappe.whitelist()
def aplicar_Anticipos(deudas=None,pagos=None,cuentaBanco=None,regnumber=None, tc=None,fecha=None,observacion = None,dc='c',_ui_=False):
	from erpnext.accounts.party import get_party_account, get_party_account_currency						


	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)

	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)

	# if isinstance(regnumber, six.string_types):
	# 	regnumber = json.loads(regnumber, object_pairs_hook=frappe._dict)

	# if isinstance(cuentaBanco, six.string_types):
	# 	cuentaBanco = json.loads(cuentaBanco, object_pairs_hook=frappe._dict)

	# if isinstance(fecha, six.string_types):
	# 	fecha = json.loads(fecha, object_pairs_hook=frappe._dict)

	# if isinstance(tc, six.string_types):
	# 	tc = json.loads(tc, object_pairs_hook=frappe._dict)

	# return deudas,pagos,regnumber

	cuentaBanco = '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI'
	# return fecha
	# entry = deudas
	customer = regnumber
	accounts = []

	# for divisa in pagos:
	# 	divi = divisa.moneda
	
	MontoTotal = 0.0
	# return deudas.link_doctype
	for deuda in deudas:
		ret = {'party_type': 'Customer', 'party': customer, 'reference_type': deuda.link_doctype, 'reference_name': deuda.link_name}
		party_args = {'party_type': 'Customer', 'party': customer, 'company' :'IBW-NI'}
		
		# if divi == 'NIO':
		# 	account, account_currency = get_party_account(**party_args), 'NIO'
		# else:
		# 	account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
		
		account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
		
		prefix = 'credit' if dc == 'c' else 'debit'
		field = '{0}_in_account_currency'.format(prefix)
		ret.update({'account': account, 'account_currency': account_currency})
		if deuda.link_doctype == "Sales Invoice":
			# Asignarle el monto que digito en el Deposito
			ret[field] = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'outstanding_amount')
			for monto in pagos:
				if monto.Factura == deuda.link_name:
					# ret[field] = monto.monto
					MontoTotal += monto.monto

			if account_currency == 'USD':
				er = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'conversion_rate')
			else:
				er = 1.0
				# Hice pase tasa tc
			ret[prefix] = flt(compute_nio(ret[field], er),2)
			#frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
			#ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
			ret['exchange_rate'] = er
		accounts.append(ret)

	# return MontoTotal
	# return accounts
	# mode = 'Depositos'
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in pagos:
		currency = currency_map.get((entry.moneda or '').lower())
		if not currency:
			messages.append('The currency {0} is not recognized as an valid currency!'.format(entry.moneda))
		else:
			# if not frappe.db.exists('Mode of Payment Account', {'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user}):
			# 	messages.append("The active user don't have an properly configured account for mode of payment {0}".format(entry.tipo_de_pago))
			# else:
				# default_account = frappe.db.get_value('Mode of Payment Account',
				# 	fieldname='default_account',
				# 	filters={'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user})

				prefix = 'debit'
				field = '{0}_in_account_currency'.format(prefix)
				# Reversion de modo de pago para el usuario
				row = {'account': cuentaBanco, 'account_currency': currency, 'mode_of_payment':'Deposito'}
				# row[field] = flt(entry.monto, 2)
				row[field] = flt(MontoTotal,2) #MontoTotal Cambiarle la variable

				if currency == 'NIO':
					er = 1.0
				else:
					# tc = tc.replace('\"','')
					er = tc
				# row[prefix] = compute_nio(row[field], er)
				# er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)
				break

	# # Variable para verificar si viene un pago en Cordobas
	# hayNIO = "USD"

	# #Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	# facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	# for acc in facs:
	# 	acc['tipo_de_cuenta']="Pagado"

	# facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	# for acc in facs:
	# 	acc['tipo_de_cuenta']="Recibido"

	# 	if acc['account_currency']=="NIO":
	# 		hayNIO = acc['account_currency']


	# Importante
	# #sum_debits es el pago que hara el cliente.
	# sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	# #sum_credits es el monto total de las facturas pendientes.
	# sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']

	# return accounts,hayNIO
	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return tc
	# return accounts

	# return accounts
	# if flt(sum_debits,2) < flt(sum_credits,2):
	facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
	if hayNIO == 'USD':
		for acc in facs:
			for MontFac in pagos:
				if MontFac.Factura == acc['reference_name']:
					acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
					acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
					acc['credit'] = flt(flt(MontFac.monto) * flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"),4))
	# 				acc['account_currency_pago'] = 'USD'
	# if hayNIO == 'NIO':
	# 	for acc in facs:
	# 		for MontFac in pagos:
	# 			if MontFac.Factura == acc['reference_name']:
	# 				acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
	# 				acc['exchange_rate'] = 1.00
	# 				acc['credit'] = flt(flt(MontFac.monto) * 1)
	# 				acc['account_currency_pago'] = None

	# #sum_debits es el pago que hara el cliente.
	# sum_debits = sum([d.get('debit_in_account_currency', 0.00) for d in accounts])
	# #sum_credits es el monto total de las facturas pendientes.
	# sum_credits = sum([d.get('credit_in_account_currency', 0.00) for d in accounts])

	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.00) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.00) for d in accounts])

	# return accounts
	diff_amount = None
	tdoc = None

	diff_amount = Cal_total_debit_credit(sum_debits,sum_credits)


	tdoc = None

	# try:
	# 	tdoc = frappe.new_doc('Journal Entry').update({
	# 		'voucher_type': 'Journal Entry',
	# 		'posting_date': fecha,
	# 		'multi_currency': 1,
	# 		'accounts': accounts,
	# 		'ui': _ui_
	# 	})

	# 	tdoc.run_method('validate')
	# except Exception:
	# 	frappe.local.message_log = []
	# 	if tdoc.difference:
	# 		diff_amount = tdoc.difference

	# return tdoc

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
	
	# return {'accounts':accounts}
	if _ui_:
		newJe = frappe.new_doc('Journal Entry')
		newJe.update({
			'posting_date': today(),
			'accounts':accounts,
			'multi_currency': True,
			# frappe.get_value('Journal Entry',{"numero_de_recibo":AprobadoExterno,'docstatus':1},"name")
			'codigoanticipo' : frappe.get_value('Anticipos',{"Cliente":regnumber,'docstatus':0},"name"),
			'tipo_de_pago' : "Aplicar Anticipo",
			# 'aplico_deposito_banco':1,
			'user_remark': observacion,
			'regnumber': regnumber,
			# 'numero_de_recibo': numero_de_recibo,
			'numero_de_recibo': frappe.get_value('Anticipos',{"Cliente":regnumber,'docstatus':0},"nombre_del_documento"),
			'no_registrar_cierre': 1,
			'ui':_ui_
		})

		newJe.save()
		newJe.flags.ignore_submit_comment = True
		newJe.submit()
		frappe.db.commit()
		return newJe.name

	else:
		return {'accounts':accounts}

def validate_payment_entriesAnticipos(entries, accounts, messages, tc, dc='d'):
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in entries:
		# currency = currency_map.get((entry.moneda or '').lower())
		# if not currency:
		# 	messages.append('The currency {0} is not recognized as an valid currency!'.format(entry.moneda))
		# else:
			# if not frappe.db.exists('Mode of Payment Account', {'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user}):
			# 	messages.append("The active user don't have an properly configured account for mode of payment {0}".format(entry.tipo_de_pago))
			# else:
				# default_account = frappe.db.get_value('Mode of Payment Account',
				# 	fieldname='default_account',
				# 	filters={'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': 'NIO', 'usuario': frappe.session.user})

				prefix = 'debit' if dc == 'd' else 'credit'
				field = '{0}_in_account_currency'.format(prefix)

				row = {'account': '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI', 'account_currency': 'NIO', 'mode_of_payment':''}
				row[field] = flt(entry.monto, 2)

				# if currency == 'NIO':
				# 	er = 1.0
				# else:
				# 	er = tc
				# row[prefix] = compute_nio(row[field], er)
				er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)
#endregion

#region Depositos en Garantia
#Depositos
@frappe.whitelist()
def crear_deposito(regnumber=None, fecha=None, tc=None,deudas=None, creditos=None, pagos=None, cambios=None, aplicable=None, metadata=None, _ui_=False):
	local_user = frappe.session.user

	if isinstance(metadata, six.string_types):
		# lo convierte en un diccionario
		metadata = json.loads(metadata)

	regnumber = regnumber.replace('\"','')
	# Asiganar a la metadata de Interfaz
	if regnumber:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# return customer
	# Dealer
	if metadata and 'colector' and 'IDdealer' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Colector
	elif metadata and 'colector' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})

		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Caja
	else:
		Tercero = frappe.db.get_value('User',{'email':local_user})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			# return "OK"
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'User',
				'tercero': Tercero
			}).insert()

	if not fecha:
		fecha = today()
	else:
		fecha = fecha.replace('\"','')

	# Tasa de cambio paralela
	if not tc:
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)

	messages = []
	accounts = []
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)
	if isinstance(creditos, six.string_types):
		creditos = json.loads(creditos, object_pairs_hook=frappe._dict)
	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	if isinstance(cambios, six.string_types):
		cambios = json.loads(cambios, object_pairs_hook=frappe._dict)
	if isinstance(aplicable, six.string_types):
		aplicable = json.loads(aplicable, object_pairs_hook=frappe._dict)

	if deudas:
		messages += validate_list_of_dicts(deudas, 'deudas', ('link_doctype', 'link_name',"MontoDeposito"))
	if creditos:
		messages += validate_list_of_dicts(creditos, 'creditos', ('link_doctype', 'link_name'))
	if pagos:
		messages += validate_list_of_dicts(pagos, 'pagos', ('tipo_de_pago', 'moneda', 'monto'), ('referencia',))
	if cambios:
		messages += validate_list_of_dicts(cambios, 'cambios', ('moneda', 'monto'))

	if not regnumber and not deudas and not (creditos or pagos):
		return {
			'status': 'error',
			'message': 'You should provide at least the regnumber or deudas and/or creditos or pagos'
		}
	elif not regnumber:
		if not creditos and not pagos:
			return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}

	if not regnumber:
		return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	else:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})
	# return messages
	# Falta depurar
	if deudas:
		# validate_party_entries(deudas, accounts, messages, tc, 'c', customer=customer)
		validate_party_entriesDeposito(deudas, accounts, messages, tc, 'c', customer=customer)
	if creditos:
		validate_party_entries(creditos, accounts, messages, tc, 'd', customer=customer)
	if pagos:
		validate_payment_entries(pagos, accounts, messages, tc, 'd')
		# validate_payment_Deposito(pagos, accounts, messages, tc, 'd')
	if cambios:
		validate_payment_entries( list(map(lambda d: d.update({'tipo_de_pago': 'Efectivo'}), cambios)), accounts, messages, tc, 'c')

	# return accounts
	# Importante
	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.0) for d in accounts])
	# return accounts,sum_debits,sum_credits,messages
	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	# facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))
	facs = list(filter(lambda acc: acc.get("account") == "2.01.001.002.001-Depósitos de Clientes - NI", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	# facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))
	facs = list(filter(lambda acc: acc.get("account") != "2.01.001.002.001-Depósitos de Clientes - NI", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']


	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return accounts
	# condicion de pagos parciales
	if sum_debits < sum_credits:
		# si hay Pago en cordobas
		if hayNIO == "NIO":
			# Pago parcial para Cordobas
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['credit_in_account_currency'] = flt(flt(acc.get('credit', 0.0),2) / flt(acc.get('exchange_rate'), 4), 4)
				acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
				acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
		else:
			# Pago parcial para dolares
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				if acc['account_currency'] == "NIO":
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(acc.get('exchange_rate', 1.0), 4)
				else:
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(tc, 4)
					acc['exchange_rate'] = flt(tc,4)
					if accounts[1]['account_currency'] == "USD":
						acc['account_currency_pago'] = accounts[1]['account_currency']
					else:
						acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
	else:
	# # No se efectua la conversacion del monto con la tasa de cambio
	# # Pagos con forme de la factura

		# return accounts

		if hayNIO == "NIO" and sum_credits == sum_debits:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			# return facs
			for acc in facs:
				ac = accounts[0]["credit_in_account_currency"]
				t= flt(ac,2)*flt(tc,4)
				acc['credit'] = abs(t)
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = "USD"
					acc['exchange_rate'] = tc
				# break
		else:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			for acc in facs:
				# Validacion de que punto tomar
				acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					if hayNIO=="USD":
						acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = None
				# break

	# return accounts

	diff = None
	diff_amount = None
	hayNIOExc="USD"
	# #import pdb; pdb.set_trace()
	# # Guarda  un nuevo documento
	# return accounts
	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

		hayNIOExc="USD"

		for a in tdoc.get("accounts"):
			if a.account_currency == "NIO":
				hayNIOExc = a.account_currency
				break

	# return tdoc.get("accounts")
	# return diff_amount

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# reemplaza el 5 > abs(flt(frappe.db.get_value('Accounts Settings', 'Accounts Settings', 'miniminal_credit_amount')))
	# 	if diff_amount > 0 and flt(diff_amount, 2) / flt(tc) > 5:
	# # 		#  Facturación Cobrada por Anticipado - IBWNI
	# 		diff = list(filter(lambda e: e['account'] == u'2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI', accounts))
	# 		if not diff:
	# # 			#  Facturación Cobrada por Anticipado - IBWNI
	# 			account = frappe.db.get_value('Account', filters={'name': ['like', '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI']})
	# 			if not regnumber:
	# 				account = account.replace(' - ', ' ZZ - ')
	# 			diff = {
	# 				'account': account,
	# 				'account_currency': 'USD',
	# 				'account_type': 'Payable',
	# 				'credit_in_account_currency': 0.0,
	# 				'credit': 0.0,
	# 				'debit_in_account_currency': 0.0,
	# 				'debit': 0.0,
	# 				'exchange_rate': 0.0,
	# 				'party_type': 'Customer',
	# 				'party': get_cliente_id(regnumber),
	# 				'is_advance': 'Yes'
	# 			}
	# 			accounts.append(diff)
	# 		else:
	# 			diff = diff[0]

	# 		diff['credit'] = flt(abs(diff_amount), 2)
	# 		diff['credit_in_account_currency'] = compute_usd(abs(diff_amount), tc)
	# 		diff['exchange_rate'] = compute_tc(diff['credit_in_account_currency'], diff['credit'])
	# 	else:
		# Generar utilidades
		if diff_amount > 0:
			if hayNIOExc == "NIO":
				# Utilidades Cambiarias - IBWNI
				diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

				if not diff:
				#  Utilidades Cambiarias - IBWNI
					diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
					accounts.append(diff)
				else:
					diff = diff[0]

				diff[p] += abs(diff_amount)
				diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

				# return accounts
				if diff and diff['debit'] and diff['credit']:
					if diff['debit'] > diff['credit']:
						diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
						diff['debit'] -= diff['credit']
						diff['credit_in_account_currency'] = diff['credit'] = 0.0
					else:
						diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
						diff['credit'] -= diff['debit']
						diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			if hayNIOExc == "NIO":
					# Utilidades Cambiarias - IBWNI
					diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

					if not diff:
					##  Utilidades Cambiarias - IBWNI
						diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
						accounts.append(diff)
					else:
						diff = diff[0]

					diff[p] += abs(diff_amount)
					diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

					# return accounts
					if diff and diff['debit'] and diff['credit']:
						if diff['debit'] > diff['credit']:
							diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
							diff['debit'] -= diff['credit']
							diff['credit_in_account_currency'] = diff['credit'] = 0.0
						else:
							diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
							diff['credit'] -= diff['debit']
							diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	if _ui_:
		return {
			'accounts': accounts,
			'messages': messages
		}
	if messages:
		return {
			'status': 'error',
			'error': u'\n'.join(messages)
		}
	else:
		doc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'mode_of_payment': pagos[0]['tipo_de_pago'],
			'user_remark': 'Aplicacion de Pago ' + fecha,
			'ui': _ui_
		})

		if not regnumber:
			doc.user_remark = 'Pago ZZ'

		if metadata:
			if 'colector' in metadata:
				#  Collector toma una cuenta
				metadata['collector'] = frappe.db.get_value('Colectores', filters={'colectorid': metadata.pop('colector')})
				# return metadata
			if 'dealer' in metadata:
				metadata['dealer'] = frappe.db.get_value('Colectores', filters={'iddealer':metadata.pop('dealer')})
			if 'recibo' in metadata:
				metadata['ensure_name'] = metadata.pop('recibo')
				# return metadata
				doc.update(metadata)

		try:
			doc.save()
			if 'dealer' in metadata and 'collector' in metadata:
				id_Name_Dealer = metadata['dealer']
				estado = False
			elif 'collector' in metadata:
				id_Name_Dealer = metadata['collector']
				estado = False
			else:
				id_Name_Dealer = None
				estado = True

			res = registrarPagoEnElCierre(doc,id_Name_Dealer, estado)

			if isinstance(res, str):
				frappe.db.rollback()
				return res

			doc.flags.ignore_submit_comment = True
			doc.submit()
			frappe.db.commit()
			if not regnumber:
				DocTags(doc.doctype).add(doc.name, 'ZZ')
				frappe.db.commit()
		except Exception as e:
			if doc.name and doc.docstatus:
				if not regnumber:
					DocTags(doc.doctype).add(doc.name, 'ZZ')
					frappe.db.commit()
				return doc.name.split("-")[1]
			return {
				'status': 'error',
				'error': e,
				'doc': doc.as_json()
			}

		frappe.db.commit()
		frappe.set_user(local_user)

		return doc.name.split("-")[1]

def get_party_account_rowDeposito(entry, customer, accounts, tc, dc='c'):
	from erpnext.accounts.party import get_party_account, get_party_account_currency

	ret = {'party_type': '', 'party': '', 'reference_type': 'Deposito en Garantia', 'reference_name': ''}
	party_args = {'party_type': 'Customer', '': '', 'company' :'IBW-NI'}
	# account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
	# account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
	account = '2.01.001.002.001-Depósitos de Clientes - NI'
	#  2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI

	prefix = 'credit' if dc == 'c' else 'debit'
	field = '{0}_in_account_currency'.format(prefix)
	ret.update({'account': account, 'account_currency': "NIO"})
	if entry.link_doctype == "Deposito":
		# accounts == 1
		# ret[field] = frappe.db.get_value(entry.link_doctype, entry.link_name, 'outstanding_amount')
		ret[field] = entry.MontoDeposito
		# # if account_currency == 'USD':
		# # 	er = frappe.db.get_value(entry.link_doctype, entry.link_name, 'conversion_rate')
		# # else:
		# # 	er = 1.0
		# ret[prefix] = flt(compute_nio(ret[field], tc),2)
		ret[prefix] = flt(compute_nio(ret[field], 1),2)
        # #frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
		# #ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
		ret['exchange_rate'] = flt(1,3)
	accounts.append(ret)

def validate_party_entriesDeposito(entries, accounts, messages, tc, dc='c', customer=None):
	customer_founds = set()
	if customer:
		customer_founds.add(customer)
	for entry in entries:
		# if not frappe.db.exists(entry['link_doctype'], entry['link_name']):
		# 	messages.append("The {0} {1} doesn't exists".format(entry["link_doctype"], entry["link_name"]))
		# elif entry['link_doctype'] == 'Sales Invoice':
		if entry['link_doctype'] == 'Deposito':
			# invoice_customer = frappe.db.get_value(entry["link_doctype"], entry["link_name"], "customer")
			# if not customer_founds:
			# 	customer_founds.add(invoice_customer)
			# elif entry['link_doctype'] == 'Journal Entry':
			# 	customers_set, message = get_customer_from_journal_entry(entry['link_name'])
			# 	if message:
			# 		messages.append(message['message'])
			# 	elif len(customers_set) > 1:
			# 		messages.append('The {0} {1} belongs to {2} customers, you should pass regnumber!'.format(
			# 			entry['link_doctype'],
			# 			entry['link_name'],
			# 			len(customers_set)))
			# 	else:
			# 		customer_founds.add(customers_set[0])
			# get_party_account_row(entry, customer or list(customer_founds)[-1], accounts, tc, dc)
			get_party_account_rowDeposito(entry, customer, accounts, tc, dc)
		if len(customer_founds) > 1:
			messages.append('Mismatch in deudas values, one payment cannot pay invoice(s) for {0} diferent customers ({1})'.format(
				len(customer_founds), ', '.join(customer_founds)))

@frappe.whitelist()
def aplicar_DepositosDeGarantia(regnumber=None, fecha=None, tc=None,deudas=None, creditos=None, pagos=None, cambios=None, aplicable=None, metadata=None, _ui_=False):
	local_user = frappe.session.user

	if isinstance(metadata, six.string_types):
		# lo convierte en un diccionario
		metadata = json.loads(metadata)

	# Asiganar a la metadata de Interfaz
	if regnumber:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})


	# Dealer
	if metadata and 'colector' and 'IDdealer' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Colector
	elif metadata and 'colector' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})

		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Caja
	else:
		Tercero = frappe.db.get_value('User',{'email':local_user})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			# return "OK"
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'User',
				'tercero': Tercero
			}).insert()

	if not fecha:
		fecha = today()
	else:
		fecha = fecha.replace('\"','')

	# Tasa de cambio paralela
	if not tc:
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)

	messages = []
	accounts = []
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)
	if isinstance(creditos, six.string_types):
		creditos = json.loads(creditos, object_pairs_hook=frappe._dict)
	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	if isinstance(cambios, six.string_types):
		cambios = json.loads(cambios, object_pairs_hook=frappe._dict)
	if isinstance(aplicable, six.string_types):
		aplicable = json.loads(aplicable, object_pairs_hook=frappe._dict)

	if deudas:
		messages += validate_list_of_dicts(deudas, 'deudas', ('link_doctype', 'link_name'))
	if creditos:
		messages += validate_list_of_dicts(creditos, 'creditos', ('link_doctype', 'link_name'))
	if pagos:
		messages += validate_list_of_dicts(pagos, 'pagos', ('tipo_de_pago', 'moneda', 'monto'), ('referencia',))
	if cambios:
		messages += validate_list_of_dicts(cambios, 'cambios', ('moneda', 'monto'))

	if not regnumber and not deudas and not (creditos or pagos):
		return {
			'status': 'error',
			'message': 'You should provide at least the regnumber or deudas and/or creditos or pagos'
		}
	elif not regnumber:
		if not creditos and not pagos:
			return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}

	if not regnumber:
		return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	else:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# Falta depurar
	if deudas:
		validate_party_entries(deudas, accounts, messages, tc, 'c', customer=customer)
	if creditos:
		validate_party_entries(creditos, accounts, messages, tc, 'd', customer=customer)
	if pagos:
		# validate_payment_entries(pagos, accounts, messages, tc, 'd')
		validate_payment_entriesDepositos(pagos, accounts, messages, tc, 'd')
	if cambios:
		validate_payment_entries( list(map(lambda d: d.update({'tipo_de_pago': 'Efectivo'}), cambios)), accounts, messages, tc, 'c')

	# return accounts,messages
	# Importante
	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']


	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return accounts
	# condicion de pagos parciales
	if sum_debits < sum_credits:
		# si hay Pago en cordobas
		if hayNIO == "NIO":
			# Pago parcial para Cordobas
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['credit_in_account_currency'] = flt(flt(acc.get('credit', 0.0),2) / flt(acc.get('exchange_rate'), 4), 4)
				acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
				acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
		else:
			# Pago parcial para dolares
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				if acc['account_currency'] == "NIO":
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(acc.get('exchange_rate', 1.0), 4)
				else:
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(tc, 4)
					acc['exchange_rate'] = flt(tc,4)
					if accounts[1]['account_currency'] == "USD":
						acc['account_currency_pago'] = accounts[1]['account_currency']
					else:
						acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
	else:
	# # No se efectua la conversacion del monto con la tasa de cambio
	# # Pagos con forme de la factura

		# return accounts

		if hayNIO == "NIO" and sum_credits == sum_debits:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			# return facs
			for acc in facs:
				ac = accounts[0]["credit_in_account_currency"]
				t= flt(ac,2)*flt(tc,4)
				acc['credit'] = abs(t)
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = "USD"
					acc['exchange_rate'] = tc
				# break
		else:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			for acc in facs:
				# Validacion de que punto tomar
				acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					if hayNIO=="USD":
						acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = None
				# break

	# return accounts

	diff = None
	diff_amount = None
	hayNIOExc="USD"
	# #import pdb; pdb.set_trace()
	# # Guarda  un nuevo documento
	# return accounts
	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

		hayNIOExc="USD"

		for a in tdoc.get("accounts"):
			if a.account_currency == "NIO":
				hayNIOExc = a.account_currency
				break

	# return tdoc.get("accounts")
	# return tdoc.difference

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# reemplaza el 5 > abs(flt(frappe.db.get_value('Accounts Settings', 'Accounts Settings', 'miniminal_credit_amount')))
	# 	if diff_amount > 0 and flt(diff_amount, 2) / flt(tc) > 5:
	# # 		#  Facturación Cobrada por Anticipado - IBWNI
	# 		diff = list(filter(lambda e: e['account'] == u'2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI', accounts))
	# 		if not diff:
	# # 			#  Facturación Cobrada por Anticipado - IBWNI
	# 			account = frappe.db.get_value('Account', filters={'name': ['like', '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI']})
	# 			if not regnumber:
	# 				account = account.replace(' - ', ' ZZ - ')
	# 			diff = {
	# 				'account': account,
	# 				'account_currency': 'USD',
	# 				'account_type': 'Payable',
	# 				'credit_in_account_currency': 0.0,
	# 				'credit': 0.0,
	# 				'debit_in_account_currency': 0.0,
	# 				'debit': 0.0,
	# 				'exchange_rate': 0.0,
	# 				'party_type': 'Customer',
	# 				'party': get_cliente_id(regnumber),
	# 				'is_advance': 'Yes'
	# 			}
	# 			accounts.append(diff)
	# 		else:
	# 			diff = diff[0]

	# 		diff['credit'] = flt(abs(diff_amount), 2)
	# 		diff['credit_in_account_currency'] = compute_usd(abs(diff_amount), tc)
	# 		diff['exchange_rate'] = compute_tc(diff['credit_in_account_currency'], diff['credit'])
	# 	else:
		# Generar utilidades
		if diff_amount > 0:
			if hayNIOExc == "NIO":
				# Utilidades Cambiarias - IBWNI
				diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

				if not diff:
				#  Utilidades Cambiarias - IBWNI
					diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
					accounts.append(diff)
				else:
					diff = diff[0]

				diff[p] += abs(diff_amount)
				diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

				# return accounts
				if diff and diff['debit'] and diff['credit']:
					if diff['debit'] > diff['credit']:
						diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
						diff['debit'] -= diff['credit']
						diff['credit_in_account_currency'] = diff['credit'] = 0.0
					else:
						diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
						diff['credit'] -= diff['debit']
						diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			if hayNIOExc == "NIO":
					# Utilidades Cambiarias - IBWNI
					diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

					if not diff:
					##  Utilidades Cambiarias - IBWNI
						diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
						accounts.append(diff)
					else:
						diff = diff[0]

					diff[p] += abs(diff_amount)
					diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

					# return accounts
					if diff and diff['debit'] and diff['credit']:
						if diff['debit'] > diff['credit']:
							diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
							diff['debit'] -= diff['credit']
							diff['credit_in_account_currency'] = diff['credit'] = 0.0
						else:
							diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
							diff['credit'] -= diff['debit']
							diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	if _ui_:
		return {
			'accounts': accounts,
			'messages': messages
		}
	if messages:
		return {
			'status': 'error',
			'error': u'\n'.join(messages)
		}
	else:
		doc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'mode_of_payment': pagos[0]['tipo_de_pago'],
			'user_remark': 'Aplicacion de Pago ' + fecha,
			'ui': _ui_
		})

		if not regnumber:
			doc.user_remark = 'Pago ZZ'

		if metadata:
			if 'colector' in metadata:
				#  Collector toma una cuenta
				metadata['collector'] = frappe.db.get_value('Colectores', filters={'colectorid': metadata.pop('colector')})
				# return metadata
			if 'dealer' in metadata:
				metadata['dealer'] = frappe.db.get_value('Colectores', filters={'iddealer':metadata.pop('dealer')})
			if 'recibo' in metadata:
				metadata['ensure_name'] = metadata.pop('recibo')
				# return metadata
				doc.update(metadata)

		try:
			doc.save()
			if 'dealer' in metadata and 'collector' in metadata:
				id_Name_Dealer = metadata['dealer']
				estado = False
			elif 'collector' in metadata:
				id_Name_Dealer = metadata['collector']
				estado = False
			else:
				id_Name_Dealer = None
				estado = True

			res = registrarPagoEnElCierre(doc,id_Name_Dealer, estado)

			if isinstance(res, str):
				frappe.db.rollback()
				return res

			doc.flags.ignore_submit_comment = True
			doc.submit()
			frappe.db.commit()
			if not regnumber:
				DocTags(doc.doctype).add(doc.name, 'ZZ')
				frappe.db.commit()
		except Exception as e:
			if doc.name and doc.docstatus:
				if not regnumber:
					DocTags(doc.doctype).add(doc.name, 'ZZ')
					frappe.db.commit()
				return doc.name.split("-")[1]
			return {
				'status': 'error',
				'error': e,
				'doc': doc.as_json()
			}

		frappe.db.commit()
		frappe.set_user(local_user)

		return doc.name.split("-")[1]

def validate_payment_entriesDepositos(entries, accounts, messages, tc, dc='d'):
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in entries:
		# currency = currency_map.get((entry.moneda or '').lower())
		# if not currency:
		# 	messages.append('The currency {0} is not recognized as an valid currency!'.format(entry.moneda))
		# else:
			# if not frappe.db.exists('Mode of Payment Account', {'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user}):
			# 	messages.append("The active user don't have an properly configured account for mode of payment {0}".format(entry.tipo_de_pago))
			# else:
				# default_account = frappe.db.get_value('Mode of Payment Account',
				# 	fieldname='default_account',
				# 	filters={'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': 'NIO', 'usuario': frappe.session.user})

				prefix = 'debit' if dc == 'd' else 'credit'
				field = '{0}_in_account_currency'.format(prefix)

				row = {'account': '2.01.001.002.001-Depósitos de Clientes - NI', 'account_currency': 'NIO', 'mode_of_payment':''}
				row[field] = flt(entry.monto, 2)

				# if currency == 'NIO':
				# 	er = 1.0
				# else:
				# 	er = tc
				# row[prefix] = compute_nio(row[field], er)
				er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)
#endregion

#region Depositos de BAnco --PAgos sin Identificar
# Depositos de BAnco
@frappe.whitelist()
def Aplicar_Deposito_Banco(deudas=None,pagos=None,cuentaBanco=None,regnumber=None, tc=None,fecha=None,ID_pago_ZZ = None,observacion = None,numero_de_recibo = None,posting_date = None,dc='c',_ui_=True):
	from erpnext.accounts.party import get_party_account, get_party_account_currency						

	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)

	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)

	# if isinstance(regnumber, six.string_types):
	# 	regnumber = json.loads(regnumber, object_pairs_hook=frappe._dict)

	# if isinstance(cuentaBanco, six.string_types):
	# 	cuentaBanco = json.loads(cuentaBanco, object_pairs_hook=frappe._dict)

	# if isinstance(fecha, six.string_types):
	# 	fecha = json.loads(fecha, object_pairs_hook=frappe._dict)

	# if isinstance(tc, six.string_types):
	# 	tc = json.loads(tc, object_pairs_hook=frappe._dict)

	# return deudas,pagos,regnumber


	# return fecha
	# entry = deudas
	customer = regnumber
	accounts = []

	for divisa in pagos:
		divi = divisa.moneda
	
	MontoTotal = 0.0
	# return deudas.link_doctype
	for deuda in deudas:
		ret = {'party_type': 'Customer', 'party': customer, 'reference_type': deuda.link_doctype, 'reference_name': deuda.link_name}
		party_args = {'party_type': 'Customer', 'party': customer, 'company' :'IBW-NI'}
		
		# if divi == 'NIO':
		# 	account, account_currency = get_party_account(**party_args), 'NIO'
		# else:
		# 	account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
		
		account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
		
		prefix = 'credit' if dc == 'c' else 'debit'
		field = '{0}_in_account_currency'.format(prefix)
		ret.update({'account': account, 'account_currency': account_currency})
		if deuda.link_doctype == "Sales Invoice":
			# Asignarle el monto que digito en el Deposito
			ret[field] = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'outstanding_amount')
			for monto in pagos:
				if monto.Factura == deuda.link_name:
					# ret[field] = monto.monto
					MontoTotal += monto.monto

			if account_currency == 'USD':
				er = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'conversion_rate')
			else:
				er = 1.0
				# Hice pase tasa tc
			ret[prefix] = flt(compute_nio(ret[field], er),2)
			#frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
			#ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
			ret['exchange_rate'] = er
		accounts.append(ret)

	# return MontoTotal
	# return accounts
	# mode = 'Depositos'
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in pagos:
		currency = currency_map.get((entry.moneda or '').lower())
		if not currency:
			messages.append('The currency {0} is not recognized as an valid currency!'.format(entry.moneda))
		else:
			# if not frappe.db.exists('Mode of Payment Account', {'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user}):
			# 	messages.append("The active user don't have an properly configured account for mode of payment {0}".format(entry.tipo_de_pago))
			# else:
				# default_account = frappe.db.get_value('Mode of Payment Account',
				# 	fieldname='default_account',
				# 	filters={'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user})

				prefix = 'debit'
				field = '{0}_in_account_currency'.format(prefix)
				# Reversion de modo de pago para el usuario
				row = {'account': cuentaBanco, 'account_currency': currency, 'mode_of_payment':'Deposito'}
				# row[field] = flt(entry.monto, 2)
				row[field] = flt(MontoTotal,2) #MontoTotal Cambiarle la variable

				if currency == 'NIO':
					er = 1.0
				else:
					# tc = tc.replace('\"','')
					er = tc
				# row[prefix] = compute_nio(row[field], er)
				# er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)
				break

	# # Variable para verificar si viene un pago en Cordobas
	# hayNIO = "USD"

	# #Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	# facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	# for acc in facs:
	# 	acc['tipo_de_cuenta']="Pagado"

	# facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	# for acc in facs:
	# 	acc['tipo_de_cuenta']="Recibido"

	# 	if acc['account_currency']=="NIO":
	# 		hayNIO = acc['account_currency']


	# Importante
	# #sum_debits es el pago que hara el cliente.
	# sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	# #sum_credits es el monto total de las facturas pendientes.
	# sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']

	# return accounts,hayNIO
	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return tc
	# return accounts

	# return accounts
	# if flt(sum_debits,2) < flt(sum_credits,2):
	facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
	if hayNIO == 'USD':
		for acc in facs:
			for MontFac in pagos:
				if MontFac.Factura == acc['reference_name']:
					acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
					acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
					acc['credit'] = flt(flt(MontFac.monto) * flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"),4))
	# 				acc['account_currency_pago'] = 'USD'
	# if hayNIO == 'NIO':
	# 	for acc in facs:
	# 		for MontFac in pagos:
	# 			if MontFac.Factura == acc['reference_name']:
	# 				acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
	# 				acc['exchange_rate'] = 1.00
	# 				acc['credit'] = flt(flt(MontFac.monto) * 1)
	# 				acc['account_currency_pago'] = None

	# #sum_debits es el pago que hara el cliente.
	# sum_debits = sum([d.get('debit_in_account_currency', 0.00) for d in accounts])
	# #sum_credits es el monto total de las facturas pendientes.
	# sum_credits = sum([d.get('credit_in_account_currency', 0.00) for d in accounts])

	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.00) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.00) for d in accounts])

	# return accounts
	diff_amount = None
	tdoc = None

	diff_amount = Cal_total_debit_credit(sum_debits,sum_credits)

	# return diff_amount,sum_debits,sum_credits,accounts

	# # condicion de pagos parciales
	# if flt(sum_debits,2) < flt(sum_credits,2):
	# 	# si hay Pago en cordobas
	# 	if hayNIO == "NIO":
	# 		# Pago parcial para Cordobas
	# 		facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

	# 		for acc in facs:
	# 			acc['credit'] = abs(flt(sum_debits, 2))
	# 			acc['credit_in_account_currency'] = flt(flt(acc.get('credit', 0.0),2) / flt(acc.get('exchange_rate'), 4), 4)
	# 			acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
	# 			acc['account_currency_pago'] = None
	# 			# break
	# 		sum_credits = sum_debits
	# 	else:
	# 		# Pago parcial para dolares
	# 		facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

	# 		for acc in facs:
	# 			acc['credit'] = abs(flt(sum_debits, 2))
	# 			if acc['account_currency'] == "NIO":
	# 				acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(acc.get('exchange_rate', 1.0), 4)
	# 			else:
	# 				# return accounts
	# 				acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(tc, 4)
	# 				# acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2)
	# 				acc['exchange_rate'] = flt(tc,4)
	# 				if accounts[1]['account_currency'] == "USD":
	# 					acc['account_currency_pago'] = accounts[1]['account_currency']
	# 				else:
	# 					acc['account_currency_pago'] = None
	# 			# break
	# 		sum_credits = sum_debits
	# else:
	# # # No se efectua la conversacion del monto con la tasa de cambio
	# # # Pagos con forme de la factura

	# 	# return accounts

	# 	if hayNIO == "NIO" and flt(sum_debits,2) == flt(sum_credits,2):
	# 		facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
	# 		# return facs
	# 		for acc in facs:
	# 			ac = accounts[0]["credit_in_account_currency"]
	# 			t= flt(ac,2)*flt(tc,4)
	# 			acc['credit'] = abs(t)
	# 			acc['account_currency_pago'] = accounts[1]['account_currency']
	# 			if  accounts[1]['account_currency'] == "USD":
	# 				# Tasa de cambio una decima menor
	# 				acc['exchange_rate'] = flt(tc,4)
	# 			else:
	# 				acc['account_currency_pago'] = "USD"
	# 				acc['exchange_rate'] = tc
	# 			# break
	# 	else:
	# 		facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
	# 		for acc in facs:
	# 			# Validacion de que punto tomar
	# 			# acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
	# 			# El monto en dolares en cuenta de Factura
	# 			acc['credit_in_account_currency'] = acc['credit_in_account_currency']
	# 			acc['credit'] = abs(flt(sum_debits, 2))
	# 			acc['account_currency_pago'] = accounts[1]['account_currency']

	# return accounts

	# diff_amount = None
	tdoc = None

	# try:
	# 	tdoc = frappe.new_doc('Journal Entry').update({
	# 		'voucher_type': 'Journal Entry',
	# 		'posting_date': fecha,
	# 		'multi_currency': 1,
	# 		'accounts': accounts,
	# 		'ui': _ui_
	# 	})

	# 	tdoc.run_method('validate')
	# except Exception:
	# 	frappe.local.message_log = []
	# 	if tdoc.difference:
	# 		diff_amount = tdoc.difference

	# return tdoc

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
	
	# return accounts
	newJe = frappe.new_doc('Journal Entry')
	newJe.update({
		'posting_date': today(),
		'posting_time': today(),
		'accounts':accounts,
		'multi_currency': True,
		'codigo_deposito_zzz' : ID_pago_ZZ,
		'tipo_de_pago' : "DepositoBanco",
		'aplico_deposito_banco':1,
		'user_remark': observacion,
		'regnumber': regnumber,
		'numero_de_recibo': numero_de_recibo,
		'posting_date': posting_date,
		'no_registrar_cierre':1
	})
	 

	# # newJe.append("accounts", accounts)

	# # return {'docs': newJe.as_dict()}
	return {'docs': newJe.as_dict()}
	# return accounts
#endregion

#region notas de Credito
# Aplicar notas de Credito
@frappe.whitelist()
def Aplicar_Nota_Credito(deudas=None,pagos=None,cuentaBanco=None,regnumber=None, tc=None,fecha=None,codigo_nota_credito = None,numero_de_Recibido = None,dc='c',_ui_=True):
	from erpnext.accounts.party import get_party_account, get_party_account_currency
	# local_user = frappe.session.user
	# name = frappe.session.user
	
	# return 'USer'
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)

	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)

	# if isinstance(regnumber, six.string_types):
	# 	regnumber = json.loads(regnumber, object_pairs_hook=frappe._dict)

	# if isinstance(cuentaBanco, six.string_types):
	# 	cuentaBanco = json.loads(cuentaBanco, object_pairs_hook=frappe._dict)

	
	# if isinstance(fecha, six.string_types):
	# 	fecha = json.loads(fecha, object_pairs_hook=frappe._dict)

	# if isinstance(tc, six.string_types):
	# 	tc = json.loads(tc, object_pairs_hook=frappe._dict)

	# return deudas,pagos,regnumber

	# default_account = frappe.db.exists("Mode of Payment Account", {'default_account': cuentaBanco})		

	# return default_account,cuentaBanco
	# entry = deudas
	customer = regnumber
	accounts = []
	tcF = []
	MontoTotal = 0.0
	# return deudas.link_doctype
	for deuda in deudas:
		ret = {'party_type': 'Customer', 'party': customer, 'reference_type': deuda.link_doctype, 'reference_name': deuda.link_name}
		party_args = {'party_type': 'Customer', 'party': customer, 'company' :'IBW-NI'}
		account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
		prefix = 'credit' if dc == 'c' else 'debit'
		field = '{0}_in_account_currency'.format(prefix)
		ret.update({'account': account, 'account_currency': account_currency})
		if deuda.link_doctype == "Sales Invoice":
			# Monto real de su factura
			ret[field] = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'outstanding_amount')
			# # Asignarle el monto que digito en el Deposito
			for monto in pagos:
				if monto.Factura == deuda.link_name:
					# ret[field] = monto.monto
					MontoTotal += monto.monto
					
			if account_currency == 'USD':
				er = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'conversion_rate')
				tcFa = {'reference_name': deuda.link_name, 'tc':er}
			else:
				er = 1.0
				tcFa = {'reference_name': deuda.link_name, 'tc':er}
				# Hice pase tasa tc
			ret[prefix] = flt(compute_nio(ret[field], er),2)
			#frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
			#ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
			ret['exchange_rate'] = er
		accounts.append(ret)
		tcF.append(tcFa)

	
	# return MontoTotal
	# return tcF
	# mode = 'Depositos'
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in pagos:
		currency = currency_map.get((entry.moneda or '').lower())
		if not currency:
			return 'The currency {0} is not recognized as an valid currency!'.format(entry.moneda)
		else:
			# # Validar si la cuenta que viene, esta en la lista de pago
			## Configuracion de cuenta de en Cordobas
				default_account = None
				if cuentaBanco == '1.01.001.001.001.003-Caja General - Cuenta Puente - NI':
					currency = 'NIO'

					default_account = frappe.db.get_value('Mode of Payment Account',
					fieldname='default_account',
					filters={'parent': 'Nota de Credito', 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user,'default_account': cuentaBanco})
				else:
					default_account = frappe.db.get_value('Mode of Payment Account',
						fieldname='default_account',
						filters={'parent': 'Nota de Credito', 'moneda_de_la_cuenta': 'USD', 'usuario': frappe.session.user,'default_account': cuentaBanco})
					# filters={'parent': 'Nota de Credito', 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user,'default_account': cuentaBanco})

				# default_account = frappe.db.exists("Mode of Payment Account", {'moneda_de_la_cuenta': currency,'usuario': frappe.session.user,'default_account': cuentaBanco})
				if not default_account:
					return 'Error, usuario no tiene un modo de pago de nota de credito'

				prefix = 'debit'
				field = '{0}_in_account_currency'.format(prefix)

				row = {'account': default_account, 'account_currency': currency, 'mode_of_payment':'Nota de Credito'}
				#Convertir los dolares en cordobas
				if currency == 'NIO' and cuentaBanco == '1.01.001.001.001.003-Caja General - Cuenta Puente - NI':
					row[field] = flt(flt(MontoTotal) * flt(tc),2) #MontoTotal Cambiarle la variable
					er = 1.0
				elif currency == 'NIO' and cuentaBanco != '1.01.001.001.001.003-Caja General - Cuenta Puente - NI':
					row[field] = flt(flt(MontoTotal) / flt(tc),4) #MontoTotal Cambiarle la variable
					# er = tc
					er = frappe.db.get_value('Sales Invoice', entry.Factura, 'conversion_rate')
					row['account_currency'] = 'USD'
				else:
					row[field] = flt(MontoTotal,2) #MontoTotal Cambiarle la variable
					# er = tc
					er = frappe.db.get_value('Sales Invoice', entry.Factura, 'conversion_rate')

				if not er:
					return 'Error TC'

				# if currency == 'NIO':
				# 	er = 1.0
				# else:
				# 	# tc = tc.replace('\"','')
				# 	er = tc
					# A la misma tasa de la factura
					# er = accounts[0]['exchange_rate']
					# # Recorrer la mismta facuta con su tc
					# for tcc in tcF:
					# 	if entry.Factura == tcc['reference_name']:
					# 	# if entry.Factura in tcF:
					# 		er = tcc['tc']
					# 		tcc.pop('reference_name')
					# 		tcc.pop('tc')
				# row[prefix] = compute_nio(row[field], er)
				# er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)
				break

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']

	# return accounts

	# #sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit_in_account_currency', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit_in_account_currency', 0.0) for d in accounts])

	if flt(sum_debits,2) < flt(sum_credits,2):
		facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))  
		
		for acc in facs:
			for MontFac in pagos:
				if MontFac.Factura == acc['reference_name']:
					# if account == 'DEUDORES VARIOS - NI' and MontFac.moneda == 'USD':
					if acc['account'] == 'DEUDORES VARIOS - NI' and MontFac.moneda == 'USD':	
						acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2) * flt(tc,4))
						acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
						acc['credit'] = abs(flt(MontFac.monto, 2) * flt(tc,4))
						acc['account_currency_pago'] = 'NIO'
					if account == 'DEUDORES VARIOS - NI' and MontFac.moneda == 'NIO':
						acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
						acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
						acc['credit'] = abs(flt(MontFac.monto, 2))
						acc['account_currency_pago'] = 'NIO'
					if account == 'Cuentas por Cobrar Moneda Extranjera - IBWNI - NI' and MontFac.moneda == 'NIO':
						acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2)/frappe.db.get_value('Sales Invoice', entry.Factura, 'conversion_rate'))
						acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
						acc['credit'] = flt(MontFac.monto)
						acc['account_currency_pago'] = 'USD'
					else:
						acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
						acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
						acc['credit'] = flt(flt(MontFac.monto) * flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"),4))
						acc['account_currency_pago'] = 'USD'
						
				# if MontFac.Factura == acc['reference_name']:
				# 	acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
				# 	acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
				# 	acc['credit'] = flt(flt(MontFac.monto) * flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"),4))
				# 	acc['account_currency_pago'] = 'USD'

	# return accounts

	diff_amount = None
	tdoc = None
	
	#sum_debits es el pago que hara el cliente.
	debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	credits = sum([d.get('credit', 0.0) for d in accounts])

	diff_amount = Cal_total_debit_credit(debits,credits)

	# try:
	# 	tdoc = frappe.new_doc('Journal Entry').update({
	# 		'voucher_type': 'Journal Entry',
	# 		'posting_date': fecha,
	# 		'multi_currency': 1,
	# 		'accounts': accounts,
	# 		'ui': _ui_
	# 	})

	# 	tdoc.run_method('validate')
	# except Exception:
	# 	frappe.local.message_log = []
	# 	if tdoc.difference:
	# 		diff_amount = tdoc.difference

	# return tdoc

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	newJe = frappe.new_doc('Journal Entry')
	newJe.update({
		'posting_date': today(),
		'posting_time': today(),
		'accounts':accounts,
		'multi_currency': True,
		'codigo_nota_credito' : codigo_nota_credito,
		'numero_de_recibo':numero_de_Recibido,
		'aplico_nota_credito':1,
		'regnumber':customer,
		'voucher_type': 'Credit Note',
		'no_registrar_cierre': 1
		# 'tipo_de_pago' : "DepositoBanco",
		# 'aplico_deposito_banco':1
		# 'observacion': 'Se revertio el pag'
	})
	# # newJe.append("accounts", accounts)

	# # return {'docs': newJe.as_dict()}
	return {'docs': newJe.as_dict()}
	# return accounts
#endregion


#Pase para calcular Perdidas o Utilidades
def Cal_total_debit_credit(total_debit,total_credit):
	difference = 0
		# for d in self.get("accounts"):
		# 	if d.debit and d.credit:
		# 		frappe.msgprint(_("You cannot credit and debit same account at the same time"))
		# 	# Cambio a 4 decimales
		# 	# self.total_debit = flt(self.total_debit) + flt(d.debit, d.precision("debit"))
		# 	self.total_debit = flt(self.total_debit) + flt(d.debit, 2)
		# 	# Cambio a 4 decimales
		# 	# self.total_credit = flt(self.total_credit) + flt(d.credit, d.precision("credit"))
		# 	self.total_credit = flt(self.total_credit) + flt(d.credit, 2)

		# Cambio a 4 decimales
		# self.difference = flt(self.total_debit, self.precision("total_debit")) - flt(
		# 	self.total_credit, self.precision("total_credit")
		# )
	difference = flt(total_debit, 2) - flt(total_credit, 2)
	return difference

#region Pagos Batch
# Registrar pagos de Batch
@frappe.whitelist()
def agregar_pago_batch(deudas=None,pagos=None,Recibo=None,NumCheque=None,ChequeChek=None,Colector=None,NameBatch=None,regnumber=None,factura=None,tc=None,fecha=None,montoNIO=None,montoUSD = None,dc='c',_ui_=True,Num_cheque = None,Fecha_Cheque = None,nombre_banco=None):
	from erpnext.accounts.party import get_party_account, get_party_account_currency
	
	batch =  frappe.get_doc('Pago Batch',NameBatch)
	
	detalles = {
		'fecha':fecha,
		'regnumber':regnumber,
		'no_recibo':Recibo,
		'monto_cordoba':montoNIO,
		'monto_dolar':montoUSD,
		'cheque':ChequeChek,
		'no_cheque':NumCheque,
		'colector':Colector,
		'factura':factura,
		'numero_de_cheque':Num_cheque,
		'fecha_de_referencia':Fecha_Cheque,
		'nombre_del_banco':nombre_banco
	}
	
	batch.append("pagos_detalle", detalles)
	batch.flags.ignore_permissions = True
	batch.save()
	frappe.db.commit()
	return 'Ok'


@frappe.whitelist()
def aplicar_batch(id_batch):
	batch = frappe.get_doc('Pago Batch', id_batch)

	deudas=[] 
	pagos=[]
	metadata=dict()

	# for a in range(0,len(batch.pagos_detalle)):
	# for a in batch.get('pagos_detalle'):
	# 	deudas.append(dict(link_doctype = "Sales Invoice", link_name = batch.pagos_detalle[a].factura))

	# 	if batch.pagos_detalle[a].monto_cordoba:
	# 		pagos.append(dict(colector = batch.pagos_detalle[a].colector, moneda = 'NIO', monto = batch.pagos_detalle[a].monto_cordoba, tipo_de_pago = 'Cheque' if batch.pagos_detalle[a].cheque else 'Efectivo'))

	# 	if batch.pagos_detalle[a].monto_dolar:
	# 		pagos.append(dict(colector = batch.pagos_detalle[a].colector, moneda = 'USD', monto = batch.pagos_detalle[a].monto_dolar, tipo_de_pago = 'Cheque' if batch.pagos_detalle[a].cheque else 'Efectivo'))
		
	# 	metadata = dict(colector =  batch.pagos_detalle[a].colector, recibo =  batch.pagos_detalle[a].no_recibo)
		
	# 	res = aplicar_pago_batch(batch.pagos_detalle[a].regnumber, batch.pagos_detalle[a].fecha, batch.tasa_de_cambio,deudas, None,pagos, None, None, metadata, False,id_batch,batch.pagos_detalle[a].numero_de_cheque,batch.pagos_detalle[a].fecha_de_referencia,batch.pagos_detalle[a].nombre_del_banco,batch.pagos_detalle[a].centeno)
		
	# 	batchDetail = batch.get("pagos_detalle", {"name": batch.pagos_detalle[a].name})

	# 	batchDetail[0].journal_entry =  res
	# 	batchDetail[0].estado =  'Validado'

	# 	deudas.clear()
	# 	pagos.clear()

	if batch.aplicado==0:
		for a in batch.get('pagos_detalle'):
			if a.journal_entry == None:
				deudas.append(dict(link_doctype = "Sales Invoice", link_name = a.factura))

				if a.monto_cordoba:
					pagos.append(dict(colector = a.colector, moneda = 'NIO', monto = a.monto_cordoba, tipo_de_pago = 'Cheque' if a.cheque else 'Efectivo'))

				if a.monto_dolar:
					pagos.append(dict(colector = a.colector, moneda = 'USD', monto = a.monto_dolar, tipo_de_pago = 'Cheque' if a.cheque else 'Efectivo'))
				
				metadata = dict(colector =  a.colector, recibo = a.no_recibo)
				
				res = aplicar_pago_batch(a.regnumber, a.fecha, batch.tasa_de_cambio,deudas, None, pagos, None, None, metadata, False, id_batch, a.numero_de_cheque, a.fecha_de_referencia, a.nombre_del_banco, a.centeno)
				
				batchDetail = batch.get("pagos_detalle", {"name": a.name})

				batchDetail[0].journal_entry =  res
				batchDetail[0].estado =  'Validado'

				deudas.clear()
				pagos.clear()
			
		batch.aplicado = 1
		batch.save(ignore_permissions=True)
		batch.flags.ignore_submit_comment = True
		batch.submit()
		frappe.db.commit()
		return 'Ok'
	else:
		return 'ERROR'

def validate_payment_entries_batch(entries, accounts, messages, tc, dc='d'):
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}
    
	for entry in entries:
		currency = currency_map.get((entry['moneda'] or '').lower())
		if not currency:
			messages.append('The currency {0} is not recognized as an valid currency!'.format(entry['moneda']))
		else:
			if not frappe.db.exists('Account_Colector', {'parent': entry['colector'], 'tipo_de_cuenta': currency}):
				messages.append("El colector no tiene una cuenta configurada {0}".format(entry['colector']))
			else:
				default_account = frappe.db.get_value('Account_Colector',
					fieldname='cuentas',
					filters={'parent': entry['colector'], 'tipo_de_cuenta': currency})

				prefix = 'debit' if dc == 'd' else 'credit'
				field = '{0}_in_account_currency'.format(prefix)

				row = {'account': default_account, 'account_currency': currency, 'mode_of_payment':entry['tipo_de_pago']}
				row[field] = flt(entry['monto'], 2)

				if currency == 'NIO':
					er = 1.0
				else:
					# tc = tc.replace('\"','')
					er = tc
				# row[prefix] = compute_nio(row[field], er)
				# er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)


@frappe.whitelist()
def aplicar_pago_batch(regnumber=None, fecha=None, tc=None,deudas=None, creditos=None, pagos=None, cambios=None, aplicable=None, metadata=None, _ui_=False,IdBatch = None,numero_de_cheque = None,fecha_de_referencia = None,nombre_del_banco = None,centeno = None):
	local_user = frappe.session.user
	
	if isinstance(metadata, six.string_types):
		# lo convierte en un diccionario
		metadata = json.loads(metadata)
	# return regnumber
	# Asiganar a la metadata de Interfaz
	if regnumber:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})
	
	# tc = tc.replace('\"','')
	# print(type(deudas))
	
	# Dealer
	if metadata and 'colector' and 'IDdealer' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
		# return Tercero
		# if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
		# 	# return 'No existe cierre'
		# 	frappe.new_doc('Daily Closing Voucher').update({
		# 		'posting_date': today(),
		# 		'company': 'IBW-NI',
		# 		'remarks': 'Cierre de Caja {}'.format(Tercero),
		# 		'tipo': 'Colectores',
		# 		'tercero': Tercero
		# 	}).insert()
	# Colector
		# return 'Hay uno abierto'
	elif metadata and 'colector' in metadata:
		# Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})
		# Por el momento dejo pasar pagos, pero esta en la condicion Tercero
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})

		# if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
		# 	frappe.new_doc('Daily Closing Voucher').update({
		# 		'posting_date': today(),
		# 		'company': 'IBW-NI',
		# 		'remarks': 'Cierre de Caja {}'.format(Tercero),
		# 		'tipo': 'Colectores',
		# 		'tercero': Tercero
		# 	}).insert()
	# Caja
	# else:
	# 	Tercero = frappe.db.get_value('User',{'email':local_user})
	# 	# return Tercero
	# 	if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
	# 		# return "OK"
	# 		frappe.new_doc('Daily Closing Voucher').update({
	# 			'posting_date': today(),
	# 			'company': 'IBW-NI',
	# 			'remarks': 'Cierre de Caja {}'.format(Tercero),
	# 			'tipo': 'User',
	# 			'tercero': Tercero
	# 		}).insert()
	
	if not fecha:
		fecha = today()
	# else:
	# 	fecha = fecha.replace('\"','')

	# Tasa de cambio paralela
	if not tc:
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)
	
	messages = []
	accounts = []
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)
	if isinstance(creditos, six.string_types):
		creditos = json.loads(creditos, object_pairs_hook=frappe._dict)
	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	if isinstance(cambios, six.string_types):
		cambios = json.loads(cambios, object_pairs_hook=frappe._dict)
	if isinstance(aplicable, six.string_types):
		aplicable = json.loads(aplicable, object_pairs_hook=frappe._dict)
	
	if deudas:
		messages += validate_list_of_dicts(deudas, 'deudas', ('link_doctype', 'link_name'))
	if creditos:
		messages += validate_list_of_dicts(creditos, 'creditos', ('link_doctype', 'link_name'))
	if pagos:
		messages += validate_list_of_dicts(pagos, 'pagos', ('tipo_de_pago', 'moneda', 'monto'), ('referencia',))
	if cambios:
		messages += validate_list_of_dicts(cambios, 'cambios', ('moneda', 'monto'))
	
	if not regnumber and not deudas and not (creditos or pagos):
		return {
			'status': 'error',
			'message': 'You should provide at least the regnumber or deudas and/or creditos or pagos'
		}
	elif not regnumber:
		if not creditos and not pagos:
			return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	
	if not regnumber:
		return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	else:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})
	
	
	# Falta depurar
	# list(deudas)
	# return deudas
	# return type(deudas)
	
	if deudas:
		validate_party_entries_batch(deudas, accounts, messages, tc, 'c', customer=customer)
	# if creditos:
	# 	validate_party_entries_batch(creditos, accounts, messages, tc, 'd', customer=customer)
	
	if pagos:
		validate_payment_entries_batch(pagos, accounts, messages, tc, 'd')
	# if cambios:
	# 	validate_payment_entries( list(map(lambda d: d.update({'tipo_de_pago': 'Efectivo'}), cambios)), accounts, messages, tc, 'c')
	

	sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']


	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return tc

	# condicion de pagos parciales
	if flt(sum_debits,2) < flt(sum_credits,2):
		# si hay Pago en cordobas
		if hayNIO == "NIO":
			# Pago parcial para Cordobas
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['credit_in_account_currency'] = flt(flt(acc.get('credit', 0.0),2) / flt(acc.get('exchange_rate'), 4), 4)
				acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
				acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
		else:
			# Pago parcial para dolares
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				if acc['account_currency'] == "NIO":
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(acc.get('exchange_rate', 1.0), 4)
				else:
					# return accounts
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(tc, 4)
					# acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2)
					acc['exchange_rate'] = flt(tc,4)
					if accounts[1]['account_currency'] == "USD":
						acc['account_currency_pago'] = accounts[1]['account_currency']
					else:
						acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
	else:
	# # No se efectua la conversacion del monto con la tasa de cambio
	# # Pagos con forme de la factura

		# return accounts

		if hayNIO == "NIO" and sum_credits == sum_debits:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			# return facs
			for acc in facs:
				ac = accounts[0]["credit_in_account_currency"]
				t= flt(ac,2)*flt(tc,4)
				acc['credit'] = abs(t)
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					# Tasa de cambio una decima menor
					acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = "USD"
					acc['exchange_rate'] = tc
				# break
		else:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			for acc in facs:
				# Validacion de que punto tomar
				# acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
				# El monto en dolares en cuenta de Factura
				acc['credit_in_account_currency'] = acc['credit_in_account_currency']
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['account_currency_pago'] = accounts[1]['account_currency']
				# if  accounts[1]['account_currency'] == "USD":
				# 	if hayNIO=="USD":
				# 		acc['exchange_rate'] = flt(tc,4)
				# else:
				# 	acc['account_currency_pago'] = None
				# break

	# return accounts

	diff = None
	diff_amount = None
	# hayNIOExc="USD"
	# #import pdb; pdb.set_trace()
	# # Guarda  un nuevo documento
	# return accounts
	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

		# hayNIOExc="USD"

		# for a in tdoc.get("accounts"):
		# 	if a.account_currency == "NIO":
		# 		hayNIOExc = a.account_currency
		# 		break

	# return tdoc.get("accounts")
	# return diff_amount

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# reemplaza el 5 > abs(flt(frappe.db.get_value('Accounts Settings', 'Accounts Settings', 'miniminal_credit_amount')))
	# 	if diff_amount > 0 and flt(diff_amount, 2) / flt(tc) > 5:
	# # 		#  Facturación Cobrada por Anticipado - IBWNI
	# 		diff = list(filter(lambda e: e['account'] == u'2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI', accounts))
	# 		if not diff:
	# # 			#  Facturación Cobrada por Anticipado - IBWNI
	# 			account = frappe.db.get_value('Account', filters={'name': ['like', '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI']})
	# 			if not regnumber:
	# 				account = account.replace(' - ', ' ZZ - ')
	# 			diff = {
	# 				'account': account,
	# 				'account_currency': 'USD',
	# 				'account_type': 'Payable',
	# 				'credit_in_account_currency': 0.0,
	# 				'credit': 0.0,
	# 				'debit_in_account_currency': 0.0,
	# 				'debit': 0.0,
	# 				'exchange_rate': 0.0,
	# 				'party_type': 'Customer',
	# 				'party': get_cliente_id(regnumber),
	# 				'is_advance': 'Yes'
	# 			}
	# 			accounts.append(diff)
	# 		else:
	# 			diff = diff[0]

	# 		diff['credit'] = flt(abs(diff_amount), 2)
	# 		diff['credit_in_account_currency'] = compute_usd(abs(diff_amount), tc)
	# 		diff['exchange_rate'] = compute_tc(diff['credit_in_account_currency'], diff['credit'])
	# 	else:
		# Generar utilidades
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	# if _ui_:
	# 	return {
	# 		'accounts': accounts,
	# 		'messages': messages
	# 	}
	# if messages:
	# 	return {
	# 		'status': 'error',
	# 		'error': u'\n'.join(messages)
	# 	}
	# else:
	
	doc = frappe.new_doc('Journal Entry').update({
		'voucher_type': 'Journal Entry',
		'posting_date': fecha,
		'multi_currency': 1,
		'accounts': accounts,
		'regnumber': customer,
		'mode_of_payment': pagos[0]['tipo_de_pago'],
		'no_registrar_cierre':1,
		'cheque_no':numero_de_cheque,
		'cheque_date':fecha_de_referencia,
		'nombre_cheque_banco':nombre_del_banco,
		'centeno':centeno,
		# 'user_remark': 'Recibo de pago' + fecha,
		# 'pago_batch':IdBatch,
		'ui': _ui_
	})

	if not regnumber:
		doc.user_remark = 'Pago ZZ'

	if metadata:
		if 'colector' in metadata:
			#  Collector toma una cuenta
			# metadata['collector'] = frappe.db.get_value('Colectores', filters={'colectorid': metadata.pop('colector')})
			subject = frappe.db.get_value('Task', 'TASK00002', 'subject')
			name,TipoColector = frappe.db.get_value('Colectores', metadata.pop('colector'),['name', 'collector_type'])
			
			if TipoColector == 'Dealer':
				metadata['dealer'] = name
			if TipoColector == 'Colector':
				metadata['collector'] = name
			# return metadata
		# if 'IDdealer' in metadata:
		# 	metadata['dealer'] = frappe.db.get_value('Colectores', filters={'iddealer':metadata.pop('IDdealer')})
		if 'recibo' in metadata:
			# metadata['user_remark'] = str('Numero de recibo: ' +  metadata.pop('recibo'))
			metadata['numero_de_recibo'] = str(metadata.pop('recibo'))
			# return metadata
			
		doc.update(metadata)
	# return metadata
	# return doc
	try:
		doc.save()
		# if 'dealer' in metadata and 'collector' in metadata:
		# 	id_Name_Dealer = metadata['dealer']
		# 	estado = False
		# elif 'collector' in metadata:
		# 	id_Name_Dealer = metadata['collector']
		# 	estado = False
		# else:
		# 	id_Name_Dealer = None
		# 	estado = True

		# res = registrarPagoEnElCierre(doc,id_Name_Dealer, estado)

		# if isinstance(res, str):
		# 	frappe.db.rollback()
		# 	return res

		# doc.flags.ignore_submit_comment = True

		# if _ui_:
		# 	doc.submit()

		doc.flags.ignore_submit_comment = True
		doc.submit()
		frappe.db.commit()
		if not regnumber:
			DocTags(doc.doctype).add(doc.name, 'ZZ')
			frappe.db.commit()
	except Exception as e:
		if doc.name and doc.docstatus:
			if not regnumber:
				DocTags(doc.doctype).add(doc.name, 'ZZ')
				frappe.db.commit()
			return doc.name.split("-")[1]
		return {
			'status': 'error',
			'error': e,
			'doc': doc.as_json()
		}

	frappe.db.commit()
	# frappe.set_user(local_user)

	# return doc.name.split("-")[1]
	return doc.name

def validate_party_entries_batch(entries, accounts, messages, tc, dc='c', customer=None):
	# return type(entries)
	
	customer_founds = set()
	if customer:
		customer_founds.add(customer)
	for entry in entries:
		if not frappe.db.exists(entry['link_doctype'], entry['link_name']):
			messages.append("The {0} {1} doesn't exists".format(entry["link_doctype"], entry["link_name"]))
		elif entry['link_doctype'] == 'Sales Invoice':
			invoice_customer = frappe.db.get_value(entry["link_doctype"], entry["link_name"], "customer")
			if not customer_founds:
				customer_founds.add(invoice_customer)
			elif entry['link_doctype'] == 'Journal Entry':
				customers_set, message = get_customer_from_journal_entry(entry['link_name'])
				if message:
					messages.append(message['message'])
				elif len(customers_set) > 1:
					messages.append('The {0} {1} belongs to {2} customers, you should pass regnumber!'.format(
						entry['link_doctype'],
						entry['link_name'],
						len(customers_set)))
				else:
					customer_founds.add(customers_set[0])
			
			get_party_account_row_batch(entry, customer or list(customer_founds)[-1], accounts, tc, dc)
		if len(customer_founds) > 1:
			messages.append('Mismatch in deudas values, one payment cannot pay invoice(s) for {0} diferent customers ({1})'.format(
				len(customer_founds), ', '.join(customer_founds)))

def get_party_account_row_batch(entry, customer, accounts, tc, dc='c'):
	from erpnext.accounts.party import get_party_account, get_party_account_currency

	ret = {'party_type': 'Customer', 'party': customer, 'reference_type': entry['link_doctype'], 'reference_name': entry["link_name"]}
	party_args = {'party_type': 'Customer', 'party': customer, 'company' :'IBW-NI'}
	account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
	prefix = 'credit' if dc == 'c' else 'debit'
	field = '{0}_in_account_currency'.format(prefix)
	ret.update({'account': account, 'account_currency': account_currency})
	if entry['link_doctype'] == "Sales Invoice":
		
		ret[field] = frappe.db.get_value(entry['link_doctype'], entry["link_name"], 'outstanding_amount')
		if account_currency == 'USD':
			er = frappe.db.get_value(entry['link_doctype'], entry["link_name"], 'conversion_rate')
		else:
			er = 1.0
			# Hice pase tasa tc
		ret[prefix] = compute_nio(ret[field], er)
        #frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
		#ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
		ret['exchange_rate'] = er
	accounts.append(ret)
	# print(ret[field])
	#diff_amount = flt(compute_nio(ret[field], tc) - ret[prefix], 2)
	#frappe.msgprint('<pre>{}</pre>'.format(diff_amount))

	diff_amount = flt(ret[field] - (ret[prefix] / er), 2)
	#frappe.msgprint('<pre>{}</pre>'.format(diff_amount))
	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# 6.22.010-Utilidades Cambiarias - NI
		# Filtra la variable Acccounts donde el tipo de cuetenta sea  Utilidades Cambiarias - IBWNI
		diff = list(filter(lambda e: e['account'] == 'Utilidades Cambiarias - IBWNI', accounts))
		if not diff:
			diff = {'account': 'Utilidades Cambiarias - IBWNI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0}
			accounts.append(diff)
		else:
			diff = diff[0]
		# ABS Funcion que transforma los numeros a positivos
		diff[p] += abs(diff_amount)
		diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)
#endregion

#Version de pruebas
@frappe.whitelist()
def documento(name):	
	from frappe.utils import money_in_words,fmt_money	
	doc = frappe.get_doc('Journal Entry',name)
	# locale.setlocale(locale.LC_ALL, ("es_ES", "UTF-8"))

	M = []
	Concepto = []
	Fac = []
	FechFac = []
	arr = doc.accounts
	# return arr
	# if len(arr) 
	# return arr
	facs = list(filter(lambda acc: acc.get("tipo_de_cuenta") == "Recibido", arr))
	Acc = list(filter(lambda acc: acc.get("tipo_de_cuenta") == "Pagado", arr))
	sum = 0

	# fecha_str = "2014-03-12"
	# date_object = datetime.strptime(fecha_str, '%B')
	# mydate = datetime.now() 
	# d = mydate.strftime("%B")
	
	# if d == 'April':
	# 	d = 'Abril'
	
	# return date_object
	# today = datetime.now().strftime('%Y-%m-%d')
	# for fac in Acc:
	# 	Fecha_Fact =  frappe.db.get_value(fac.reference_type,fac.reference_name, 'posting_date')
	# 	f = str(Fecha_Fact)
	# 	# Fecha = Fecha_Fact.strptime("%B")
	# 	d= datetime.strptime(f,'%Y-%m-%d').date()
	# 	# de = d.strptime("%m")
		
	# 	mes = ''

	# 	if d.strftime('%B') == 'January':
	# 		mes = 'Enero'
	# 	if d.strftime('%B') == 'February':
	# 		mes = 'Febrero'
	# 	if d.strftime('%B') == 'March':
	# 		mes = 'Marzo'
	# 	if d.strftime('%B') == 'April':
	# 		mes = 'Abril'
	# 	if d.strftime('%B') == 'May':
	# 		mes = 'Mayo'
	# 	if d.strftime('%B') == 'June':
	# 		mes = 'Junio'
	# 	if d.strftime('%B') == 'July':
	# 		mes = 'Julio'
	# 	if d.strftime('%B') == 'August':
	# 		mes = 'Agosto'
	# 	if d.strftime('%B') == 'September':
	# 		mes = 'Septiembre'
	# 	if d.strftime('%B') == 'Octuber':
	# 		mes = 'Octubre'
	# 	if d.strftime('%B') == 'November':
	# 		mes = 'Noviembre'
	# 	if d.strftime('%B') == 'December':
	# 		mes = 'Diciembre'


	# 	Fac.append(
	# 		_("{0}-{1}-{2}").format(fac.reference_name,mes,d.strftime('%Y')
	# 		)
	# 	)

		# mes = ''
		# Fac.append(fac.reference_name)

	# return Fac
	# for a in facs:
	# 	if len(facs) == 1:
	# 		#Pagos completos
	# 		if account_currency == 'NIO':
	# 			sum = a.debit_in_account_currency
			
	# 		if account_currency == 'USD':
	# 			sum = a.debit_in_account_currency
	# 	else:
	# 		sum = 
	# return len(facs)
	currency1 = ''
	 # Monto a Pagar
	for a in arr:
		# Pagos Completos
		if len(facs) == 1:
			if a.tipo_de_cuenta == "Recibido":
				if a.account_currency == "NIO":
					sum = a.debit_in_account_currency
					total_amount_in_words = money_in_words(sum, 'NIO')
					currency1 = 'NIO'
					# M.append(
					# 	_("{0} - {1}").format(
					# 		fmt_money(flt(sum), currency='NIO'), total_amount_in_words
					# 	)
					# )
				
				if a.account_currency == "USD":
					sum = a.debit_in_account_currency
					total_amount_in_words = money_in_words(sum, 'USD')
					currency1 = 'USD'
					# M.append(
					# 	_("{0} - {1}").format(
					# 		fmt_money(flt(sum), currency='USD'), total_amount_in_words
					# 	)
					# )
		else:
			# Pagos Mixtos
			if a.tipo_de_cuenta == "Pagado":
				# if a.account_currency == "NIO":
				sum = a.credit_in_account_currency + sum
				total_amount_in_words = money_in_words(sum, a.account_currency)
				currency1 = 'USD'
				
	M.append(
			_("{0} - {1}").format(
				fmt_money(flt(sum), currency=currency1), total_amount_in_words
			)
			)

	 # Concepto en el recibo
	for a in arr:
		# Pagos Completos
		# if len(facs) == 1:
		if a.tipo_de_cuenta == "Recibido":
			if a.account_currency == "NIO":
				sum = a.debit_in_account_currency
				# total_amount_in_words = money_in_words(sum, 'NIO')
				Concepto.append(
					_("{0}").format(
						fmt_money(flt(sum), currency='NIO')
					)
				)
			
			if a.account_currency == "USD":
				sum = a.debit_in_account_currency
				# total_amount_in_words = money_in_words(sum, 'USD')
				Concepto.append(
					_("{0}").format(
						fmt_money(flt(sum), currency='USD')
					)
				)

	for fac in Acc:
		Fac.append(fac.reference_name)

	
	Mont = str(M)
	Con = str(Concepto).replace("[", " ").replace("]", " ").replace("'", " ")

	return Mont.replace("[", " ").replace("]", " ").replace("'", " ")
	# return Con + ' Aplicado FACT# '+ str(Fac).replace("[", " ").replace("]", " ").replace("'", " ")


#region Arreglo de Pago
@frappe.whitelist()
def Consultar_Arreglo_de_Pago(name):
	CuotasList = []
	# from frappe.utils import money_in_words,fmt_money	
	# doc = frappe.get_doc('Journal Entry',name)
	# doc = frappe.get_doc('Arreglo de Pago',name)
	# locale.setlocale(locale.LC_ALL, ("es_ES", "UTF-8"))

	arreglo = frappe.db.get_value('Arreglo de Pago',
					fieldname='name',
					filters={'regnumber': name, 'docstatus': 0})
	if arreglo:
		# tc = frappe.db.get_value('Currency Exchange',{'date':today()}, 'paralela')
		doc = frappe.get_doc('Arreglo de Pago',arreglo)
		# return doc.get('cuotas')
		for cuotas in doc.get('cuotas'):
			#Validacion de solos pagos pendientes
			if not cuotas.aplicado:
				Cuotas = {
				'doctype': 'Sales Invoice',
				'Fecha':cuotas.fecha_de_pago,
				#Se hizo modificacion
				'Abono':cuotas.cod_abono,
				'Monto':cuotas.monto_abono,
				# 'MontoNIO':flt(cuotas.monto_abono * flt(tc,4),2)
				}
				CuotasList.append(Cuotas)
		# CuotasList.append({'CodigoArreglo':doc.name})
		# return {'cuotas':CuotasList}
		return {'cuotas':CuotasList,
	  			'codigoarreglo':doc.name,
				'tc':frappe.db.get_value("Currency Exchange", {"date": today()},"paralela"),
				'lafise':frappe.db.get_value("Currency Exchange", {"date": today()},"lafise"),
				'cliente': frappe.db.get_value("Customer", {"name": name},"customer_name")
			}
		# return CuotasList
	else: 
		return 'Error, no se encuentra un arreglo de pago del cliente'


# Pagos de Arreglo de pagos
@frappe.whitelist()
def Aplicar_Arreglo_de_Pago(deudas=None,pagos=None,regnumber=None,tc=None,fecha=None,_ui_=True,dc='c',CodigoArreglo = None):
	from erpnext.accounts.party import get_party_account, get_party_account_currency
	local_user = frappe.session.user

	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)

	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)

	#	IMPORTANTE SOLO JASON RECORRE 
	# if isinstance(CodigoArreglo, six.string_types):
	# 	CodigoArreglo = json.loads(CodigoArreglo, object_pairs_hook=frappe._dict)
	
	# if isinstance(regnumber, six.string_types):
	# 	regnumber = json.loads(regnumber, object_pairs_hook=frappe._dict)
	# if isinstance(regnumber, six.string_types):
	# 	regnumber = json.loads(regnumber, object_pairs_hook=frappe._dict)

	# if isinstance(cuentaBanco, six.string_types):
	# 	cuentaBanco = json.loads(cuentaBanco, object_pairs_hook=frappe._dict)

	# if isinstance(fecha, six.string_types):
	# 	fecha = json.loads(fecha, object_pairs_hook=frappe._dict)

	# if isinstance(tc, six.string_types):
	# 	tc = json.loads(tc, object_pairs_hook=frappe._dict)

	# CREACION DEL CIERRE
	Tercero = frappe.db.get_value('User',{'email':local_user})
	# return Tercero
	if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
		# return "OK"
		frappe.new_doc('Daily Closing Voucher').update({
			'posting_date': today(),
			'company': 'IBW-NI',
			'remarks': 'Cierre de Caja {}'.format(Tercero),
			'tipo': 'User',
			'tercero': Tercero
		}).insert()

	# return deudas,pagos,regnumber
	ArreglodePago =  frappe.get_doc('Arreglo de Pago',CodigoArreglo)

	PagoFac = []
	for deuda in deudas:
		for Arreglo in ArreglodePago.get('detalle'):
			if Arreglo.abono == deuda.link_name:
				detelle = {
				'link_doctype': 'Sales Invoice',
				'link_name':Arreglo.factura,
				'monto':Arreglo.monto
				}
				PagoFac.append(detelle)
	# return ArreglodePago
	# return fecha
	# entry = deudas

	# return PagoFac
	customer = regnumber
	# return customer
	accounts = []
	messages = []
	if isinstance(PagoFac, six.string_types):
		PagoFac = json.loads(PagoFac, object_pairs_hook=frappe._dict)
	
	# return PagoFac
	# return deudas,pagos
	# return deudas.link_doctype
	for deuda in PagoFac:
		ret = {'party_type': 'Customer', 'party': customer, 'reference_type': deuda['link_doctype'], 'reference_name': deuda['link_name']}
		party_args = {'party_type': 'Customer', 'party': customer, 'company' :'IBW-NI'}
		account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)
		prefix = 'credit' if dc == 'c' else 'debit'
		field = '{0}_in_account_currency'.format(prefix)
		ret.update({'account': account, 'account_currency': account_currency})
		if deuda['link_doctype'] == "Sales Invoice":
			# Asignarle el monto que digito en el Deposito
			# ret[field] = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'outstanding_amount')
			# for monto in pagos:
			# 	if monto.Factura == deuda['link_name']:
			# 		ret[field] = monto.monto
			ret[field] = deuda['monto']

			if account_currency == 'USD':
				er = frappe.db.get_value(deuda['link_doctype'], deuda['link_name'], 'conversion_rate')
			else:
				er = 1.0
				# Hice pase tasa tc
			ret[prefix] = flt(compute_nio(ret[field], er),2)
			#frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
			#ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
			ret['exchange_rate'] = er
		accounts.append(ret)

	# return accounts
	# mode = 'Depositos'
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in pagos:
		currency = currency_map.get((entry.moneda or '').lower())
		if not currency:
			return 'The currency {0} is not recognized as an valid currency!'.format(entry.moneda)
		else:
			if not frappe.db.exists('Mode of Payment Account', {'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user}):
				messages.append("The active user don't have an properly configured account for mode of payment {0}".format(entry.tipo_de_pago))
			else:
				default_account = frappe.db.get_value('Mode of Payment Account',
					fieldname='default_account',
					filters={'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user})

				prefix = 'debit'
				field = '{0}_in_account_currency'.format(prefix)

				row = {'account': default_account, 'account_currency': currency, 'mode_of_payment':entry.tipo_de_pago}
				row[field] = flt(entry.monto, 2)

				if currency == 'NIO':
					er = 1.0
				else:
					tc = tc.replace('\"','')
					er = tc
				# row[prefix] = compute_nio(row[field], er)
				# er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)

	# return accounts
	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']

	# return accounts

	diff_amount = None
	tdoc = None

	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

	# return tdoc

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0

	return {'accounts': accounts,'messages': messages}
#endregion"

# region Validacion de Facturas antes de aplicar en Batch
# Validacion de Facturas antes de aplicar en Batch
@frappe.whitelist()
def Validar_FActuras_Batch(idbatch):
# bat = frappe.get_value('Pago Batch',idbatch,)
	# description = frappe.db.get_value('Pago Batch',idbatch,'pagos_detalle')
	doc = frappe.get_doc('Pago Batch',idbatch)
	# values = {'name':idbatch}
	# data = frappe.db.sql("""select name,docstatus,status from `tabSales Invoice` where name = %(name)s """, {'name': idbatch}, as_dict=0)

	message = []
	for ba in doc.get('pagos_detalle'):
		# values = {'name': ba.factura}
		if ba.journal_entry == None:

			data = frappe.db.sql("""select name,docstatus,status,customer,currency,conversion_rate,outstanding_amount from `tabSales Invoice` where name = %(name)s """, {'name': ba.factura}, as_dict=0)

			if data:
					# Valida si la factua le pertenece al cliente
					if data[0][3] == ba.regnumber:
						# factAnteriorPendiente = frappe.db.sql("""select name from `tabSales Invoice` where customer = %(name)s  and docstatus = 1 order  by posting_date asc limit 1; """, {'name': data[0][3]}, as_dict=0)
						factAnteriorPendiente = frappe.db.sql("""select name, (TO_DAYS(CURRENT_TIMESTAMP()) - TO_DAYS(`posting_date`)) as dias from `tabSales Invoice` where customer = %(name)s  and docstatus = 1 and outstanding_amount > 1 and (TO_DAYS(CURRENT_TIMESTAMP()) - TO_DAYS(`posting_date`))>30 order by posting_date asc limit 1; """, {'name': data[0][3]}, as_dict=0)
						
						# if str(factAnteriorPendiente[0][0]) != str(ba.factura):
						if factAnteriorPendiente:
							if factAnteriorPendiente[0][0] != ba.factura:
								message.append(_("Tiene facturas anteriores del cliente: {0} de la factura: {1}").format(ba.regnumber,factAnteriorPendiente[0][0]))
						
						# docstatus, ver en los casos que esten en 0 Borrador
						if data[0][1] == 1:
							#status
							if data[0][2] != 'Paid':
								# Se valida el monto a pagar
								# Moneda
								if data[0][4] == 'USD':
									montoF = round(data[0][5] * data[0][6],2)

								else:
									montoF = round(data[0][6],2)

								tc = frappe.db.get_value('Currency Exchange',{'date': today()},'paralela')
								
								if flt(ba.monto_cordoba,2) == 0 and flt(ba.monto_dolar,2) == 0:
									message.append(_("Monto a pagar a la Factura: {0} es igual 0, debe de digitar un monto $ o C$").format(ba.factura))
								else:				
									sumaBat = round(ba.monto_cordoba + (ba.monto_dolar * round(tc,4)),2)

									if sumaBat > montoF:									
										mont = round(sumaBat - montoF,2)
										if mont > round(tc * 2,2):
											message.append(_("Monto a pagar es mayor a la Factura: {0} monto:{1}, monto ingresado: {2}").format(ba.factura,montoF,sumaBat,))

								# message.append(_("Exito a la factura: {0}").format(ba.factura))
								pass
							else:
								message.append(_("Factura Pagada: {0}").format(ba.factura))
						else:
							message.append(_("Factura Cancelada: {0}").format(ba.factura))
							
					else:
						message.append(_("Factura no coincide con el cliente: {0}").format(ba.factura))
			else:
				message.append(_("Factura no encontrado: {0}").format(ba.factura))
	
	if not message:
		message.append("Exito")

	return {'messages':message}
#endregion"

# Validacion de aplicacion de nota de credito a facturas.
@frappe.whitelist()
def Validar_Aplicacion_de_Anticipos(customer):
	consulta = consulta_deuda(name=customer, factura=None, fecha=None, tc=None)
	# return consulta['deudas'][0]['name']
	# return consulta['deudas']

	message = []

	for i in consulta['deudas']:
		# message.append(i['name'])
		name  = frappe.db.get_value("Nota de Credito Detalle",
						fieldname='name',
						filters={'factura': i['name'], 'docstatus': 1})
		# if name:
		# 	frappe.db.get_value("Nota de Credito",
		# 				fieldname='parent',
		# 				filters={'factura': i['name'], 'docstatus': 1,'workflow_state':'Aplicado'})
		if name:
			fact,moneda,mont,date  = frappe.db.get_value("Nota de Credito Detalle",name,['factura','currency','monto','fecha'])
				
			message.append('Ya tiene aplicado una nota de credito a las siguientes Facturas: {0} Moneda:{1} Monto: {2} Fecha:{3}'.format(fact,moneda,mont,date))
			# break
	return message

#region render_row dealer
def render_row_Dealer(row, tc):
	ret = {'doctype': row['voucher_type'], 'name': row['voucher_no'], 'comentarios': row['remarks'], 'fecha': row['posting_date']}
	deuda = get_deuda(row['voucher_type'], row['voucher_no'])
	# actual = get_actual(deuda, tc)
	ret['deuda'] = deuda
	# ret['actual'] = actual
	return ret
#endregion

#region ConsultaDeFacturas
@frappe.whitelist(allow_guest=True)
def ConsultaDeFacturas(CodigoCliente=None,cor = None):
	if CodigoCliente.strip():

		CodigoCliente = frappe.db.get_value("Customer", {"name": ["like", "%{0}".format(CodigoCliente.strip())]})

		if not CodigoCliente:
			return {
				'response': 'OK',
					'data': [
					]
			}

		fecha = today()
		
		account_data = run('Cuentas por Cobrar del Cliente', {
		'report_date': add_months(fecha, 1),
		'customer': CodigoCliente,
		'ageing_based_on': 'Posting Date',
		'company': 'IBW-NI',
		'range1': 30,
		'range2': 60,
		'range3': 90
		})

		deudas = []
		tc = get_exchange_rate('USD', 'NIO', today(), throw=True)
		saldo = {'usd': 0.0, 'tc': tc}

		l=len(account_data['result'])-1

	for r in range(0,l):
		# return row
		# # return row['voucher_no']
		# if flt(account_data['result'][r]["total_outstanding_amount"], 2) < 0:
		# 	creditos.append(render_row(account_data['result'][r], tc))

		if flt(account_data['result'][r]["total_outstanding_amount"], 2) > 1:
			if flt(account_data['result'][r]["outstanding_amount"], 2) > 1:
				# if factura and account_data["result"][con]["voucher_no"] == factura:
				# if factura and flt(account_data['result'][r]["voucher_no"]) == factura:
				# 	continue
				# return row,tc
				deuda = render_row_Dealer(account_data['result'][r], tc)
				# saldo['usd'] += deuda['actual']['usd']
				deudas.append(deuda)

	# return deudas[0]["name"]

	if deudas:
		FactCordobas = frappe.db.get_value('Sales Invoice', {'name': deudas[0]["name"]}, 'debit_to')
		# return FactCordobas
		if FactCordobas == "DEUDORES VARIOS - NI":
				dF=len(deudas)
				for r in range(0,dF):
					deudas[r]["deuda"]['usd'] = 0

	str(cor)
	if cor == '0':
		return {
			'response': 'OK',
			'data': [
				{
				'Serie': row['name'].split('-')[0],
				'Factura': row['name'].split('-')[1],
				'Notes': _("FACTURA: {0} -MES: {1}").format(row['name'].split('-')[1],frappe.db.get_value('Sales Invoice', row['name'], 'posting_date')),
				# 'total': round(row['invoice_amount'], 2),
				# 'Saldo': round(row['outstanding_amount'], 2),
				# 'total': row['deuda']['usd'],
				'total': frappe.db.get_value('Sales Invoice', row['name'], 'outstanding_amount'),
				'Saldo':frappe.db.get_value('Sales Invoice', row['name'], 'outstanding_amount'),
				'BillDate': row['fecha'],
				'totalCordobas': round(row['deuda']['nio'],2),
				'SaldoCordobas': round(row['deuda']['nio'],2)
				} for row in deudas 
			]
		}
	else:
		return {
			'response': 'OK',
			'data': [
				{
				'Serie': row['name'].split('-')[0],
				'Factura': row['name'].split('-')[1],
				'Notes': _("FACTURA: {0} -MES: {1}").format(row['name'].split('-')[1],frappe.db.get_value('Sales Invoice', row['name'], 'posting_date')),
				# 'total': row['deuda']['usd'],
				'total':frappe.db.get_value('Sales Invoice', row['name'], 'outstanding_amount'),
				'Saldo':frappe.db.get_value('Sales Invoice', row['name'], 'outstanding_amount'),
				'BillDate': row['fecha'],
				'totalCordobas': round(row['deuda']['nio'],2),
				'SaldoCordobas': round(row['deuda']['nio'],2)
				# 'tc': row['deuda']['tc']
				} for row in deudas 
			]
		}
#endregion

#region buscarCliente
@frappe.whitelist(allow_guest=True)
def buscarCliente(CodigoCliente = None,NombreCompletoCliente = None,NoIdentificacion = None,Factura = None):
	# name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'name': ['like', '%'+CodigoCliente]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])
	
	CodigoCliente = frappe.db.get_value("Customer", {"name": ["like", "%{0}".format(CodigoCliente.strip())]})

	if not CodigoCliente:
		return {
			'response': 'OK',
				'data': [
				]
		}


	if CodigoCliente:
		name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'name': ['like', '%'+CodigoCliente]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])

	if CodigoCliente and NombreCompletoCliente and NoIdentificacion:
		name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'name': ['like', '%'+CodigoCliente],'company_name': ['like', '%'+NombreCompletoCliente],'cedula': ['like', '%'+NoIdentificacion]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])

	if CodigoCliente and NombreCompletoCliente and NoIdentificacion:
		name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'name': ['like', '%'+CodigoCliente],'company_name': ['like', '%'+NombreCompletoCliente],'cedula': ['like', '%'+NoIdentificacion]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])
	
	if CodigoCliente and NoIdentificacion:
		name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'name': ['like', '%'+CodigoCliente],'cedula': ['like', '%'+NoIdentificacion]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])


	elif CodigoCliente and not NombreCompletoCliente and not NoIdentificacion and not Factura:
		# name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'name': ['like', '%'+CodigoCliente]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])
		CodigoCliente = "%"+ CodigoCliente + "%"
		data = frappe.db.sql("""
			select name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc from `tabCustomer` where name LIKE %(name)s limit 1
		""", {'name': CodigoCliente}, as_dict= 1)
		name = data[0]['name']
		first_name = data[0]['first_name']
		last_name = data[0]['last_name']
		company_name = data[0]['company_name']
		customer_group = data[0]['customer_group']
		address_line1 = data[0]['address_line1']
		municipio = data[0]['municipio']
		phone = data[0]['name']
		phone = data[0]['name']
		email_id = data[0]['email_id']
		cedula = data[0]['cedula']
		ruc = data[0]['ruc']

	elif NombreCompletoCliente:
		# name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'customer_name': ['like', '%'+NombreCompletoCliente]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])
		NombreCompletoCliente = "%"+ NombreCompletoCliente + "%"
		data = frappe.db.sql("""
			select name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc from `tabCustomer` where customer_name LIKE %(customer_name)s limit 1
		""", {'customer_name': NombreCompletoCliente}, as_dict= 1)
		name = data[0]['name']
		first_name = data[0]['first_name']
		last_name = data[0]['last_name']
		company_name = data[0]['company_name']
		customer_group = data[0]['customer_group']
		address_line1 = data[0]['address_line1']
		municipio = data[0]['municipio']
		phone = data[0]['name']
		phone = data[0]['name']
		email_id = data[0]['email_id']
		cedula = data[0]['cedula']
		ruc = data[0]['ruc']

	elif NoIdentificacion:
		name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'cedula': ['like', '%'+NoIdentificacion]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])

	elif Factura:
		cus = frappe.db.get_value("Sales Invoice", {'name': ['like', '%'+Factura]}, ["customer"])
		if cus:
			name, first_name,last_name,company_name,customer_group,address_line1,municipio,email_id,cedula,ruc = frappe.db.get_value("Customer", {'name': ['like', '%'+cus]}, ["name", "first_name","last_name","company_name","customer_group","address_line1","municipio","email_id","cedula","ruc"])

		
	# name = frappe.db.get_value("Customer", {'name': ['like', '%'+CodigoCliente],'cedula':['like', '%'+NoIdentificacion],'customer_name':['like', '%'+NombreCompletoCliente]}, ["name"])
	# res = frappe.get_doc("Customer", {'name': ['like', '%'+CodigoCliente]})
	
	# return cus
	fecha = today()
	account_data = run('Cuentas por Cobrar del Cliente', {
	'report_date': add_months(fecha, 1),
	# 'customer': CodigoCliente if CodigoCliente else name,
	'customer': name,
	'ageing_based_on': 'Posting Date',
	'company': 'IBW-NI',
	'range1': 30,
	'range2': 60,
	'range3': 90
	})

	deudas = []
	tc = get_exchange_rate('USD', 'NIO', today(), throw=True)
	saldo = {'usd': 0.0, 'tc': tc}

	l=len(account_data['result'])-1

	for r in range(0,l):
		if flt(account_data['result'][r]["total_outstanding_amount"], 2) > 1:
			if flt(account_data['result'][r]["outstanding_amount"], 2) > 1:
				deuda = render_row_Dealer(account_data['result'][r], tc)
				deudas.append(deuda)

	if deudas:
		FactCordobas = frappe.db.get_value('Sales Invoice', {'name': deudas[0]["name"]}, 'debit_to')
		if FactCordobas == "DEUDORES VARIOS - NI":
				dF=len(deudas)
				for r in range(0,dF):
					deudas[r]["deuda"]['usd'] = 0



	values = {'link_name': name}
	cell = frappe.db.sql("""
			SELECT GROUP_CONCAT(phone SEPARATOR ' - ') AS telefonos
			FROM `tabContact Phone` where parent in (select link_title from `tabDynamic Link` where 
			link_name = %(link_name)s and parenttype = 'Contact') 
		""", values=values, as_dict=0)
	# return cell[0]

	phone = str(cell[0]).replace("'", " ").replace("(", " ").replace(")", " ").replace(",", " ").replace(" ", "")

	saldo = 0
	for row in deudas:
		saldof=frappe.db.get_value('Sales Invoice', row['name'], 'outstanding_amount')
		saldo = saldo + saldof
	
	if deudas:
		return {
			'response': 'OK',
			'data': [
				{
				'CustomerID': name.split('-')[1],
				'RegNumber': name.split('-')[1],
				'FirstName':first_name,
				'LastName': last_name,
				'Company': company_name,
				'Tipo_Cliente':customer_group,
				'Saldo':saldo,
				'Address':address_line1,
				'City':municipio,
				'HomePhone': phone,
				'MobilePhone': phone,
				'BusinessPhone': '',
				'Email': email_id,
				'Cedula': cedula,
				'RUC': ruc
				}
			]
		}
	else:
		return {
			'response': 'OK',
			'data': [
				{
				'CustomerID': name.split('-')[1],
				'RegNumber': name.split('-')[1],
				'FirstName':first_name,
				'LastName': last_name,
				'Company': company_name,
				'Tipo_Cliente':customer_group,
				'Sald o':0.00,
				'Address':address_line1,
				'City':municipio,
				'HomePhone': phone,
				'MobilePhone': phone,
				'BusinessPhone': '',
				'Email': email_id,
				'Cedula': cedula,
				'RUC': ruc
				} 
			]
		}
#endregion

#region Cancelar_Pagos Batch
@frappe.whitelist()
def Cancelar_Pagos_batch(name):
	batch = frappe.get_doc('Pago Batch',name)
	message = []
	try:
		for bat in batch.get('pagos_detalle'):
			if bat.journal_entry:
				je = frappe.get_doc('Journal Entry',bat.journal_entry)
				je.flags.ignore_submit_comment = True
				je.cancel()
				frappe.db.commit()
		
		# frappe.msgprint(frappe._('Exito'))
		message.append(_("Exito"))
		
		return {'messages':message}

	except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))	
#endregion

#region POGOS DE DEALER
@frappe.whitelist()
def aplicar_pago_dealer(regnumber=None, fecha=None, tc=None,deudas=None, creditos=None, pagos=None, cambios=None, aplicable=None, metadata=None, _ui_=False):
	local_user = frappe.session.user
	# return type(deudas),type(pagos)
	
	customer = ''

	if isinstance(metadata, six.string_types):
		# lo convierte en un diccionario
		metadata = json.loads(metadata)

	# return metadata
	# Asiganar a la metadata de Interfaz
	if regnumber:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	if not customer:
		return {
			'response': 'Error 2',
			'variables': 'regnumber',
			'message': 'No se encuentra el cliente ID'
		}
	
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)

	if deudas:
		fact = frappe.db.exists("Sales Invoice", {"name": str(deudas[0]['link_name'])})
	
	# return fact
	if not fact:
		return {
			'response': 'Error 12',
			'variables': 'Sales Invoice',
			'message': 'No se encuentra la factura ID'
		}

	# tc = tc.replace('\"','')

	# return customer
	# Dealer
	if metadata and 'colector' and 'IDdealer' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			# return 'No existe cierre'
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Colector
		# return Tercero
	elif metadata and 'colector' in metadata:
		# Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})
		# Por el momento dejo pasar pagos, pero esta en la condicion Tercero
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})

		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
			
	
	
		
	# Caja
	# else:
	# 	rol = consultar_rol()
	# 	# return rol
	# 	if rol and not 'Administrador Caja' in rol:
	# 		# Tercero = frappe.db.get_value('User',{'email':local_user})
	# 		# return 
	# 		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
	# 		return Tercero
	# 		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
	# 			# return "OK"
				
	# 			frappe.new_doc('Daily Closing Voucher').update({
	# 				'posting_date': today(),
	# 				'company': 'IBW-NI',
	# 				'remarks': 'Cierre de Caja {}'.format(Tercero),
	# 				'tipo': 'User',
	# 				'tercero': Tercero
	# 				# 'tercero': Tercero 
	# 			}).insert()

	if not fecha:
		fecha = today()
	else:
		fecha = fecha.replace('\"','')

	# Tasa de cambio paralela
	if not tc:
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)

	messages = []
	accounts = []
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)
	if isinstance(creditos, six.string_types):
		creditos = json.loads(creditos, object_pairs_hook=frappe._dict)
	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	if isinstance(cambios, six.string_types):
		cambios = json.loads(cambios, object_pairs_hook=frappe._dict)
	if isinstance(aplicable, six.string_types):
		aplicable = json.loads(aplicable, object_pairs_hook=frappe._dict)

	if deudas:
		messages += validate_list_of_dicts(deudas, 'deudas', ('link_doctype', 'link_name'))
	if creditos:
		messages += validate_list_of_dicts(creditos, 'creditos', ('link_doctype', 'link_name'))
	if pagos:
		messages += validate_list_of_dicts(pagos, 'pagos', ('tipo_de_pago', 'moneda', 'monto'), ('referencia',))
	if cambios:
		messages += validate_list_of_dicts(cambios, 'cambios', ('moneda', 'monto'))

	if not regnumber and not deudas and not (creditos or pagos):
		return {
			'status': 'error',
			'message': 'You should provide at least the regnumber or deudas and/or creditos or pagos'
		}
	elif not regnumber:
		if not creditos and not pagos:
			return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}

	if not regnumber:
		return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	else:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# Falta depurar

	if metadata and 'colector' and 'IDdealer' in metadata:
		dealer = frappe.db.get_value('Colectores', filters={'iddealer': metadata['IDdealer']})
		if dealer == 'AirPack':
			for pago in pagos:
				if pago.moneda == 'NIO':
					return 'No tiene una cuenta en cordobas'

	# return accounts
	if deudas:
		validate_party_entries(deudas, accounts, messages, tc, 'c', customer=customer)
	if creditos:
		validate_party_entries(creditos, accounts, messages, tc, 'd', customer=customer)
	if pagos:
		validate_payment_entries(pagos, accounts, messages, tc, 'd')
	if cambios:
		validate_payment_entries( list(map(lambda d: d.update({'tipo_de_pago': 'Efectivo'}), cambios)), accounts, messages, tc, 'c')

	# return accounts
	# return tc
	# Importante
	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']


	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return local_user

	# condicion de pagos parciales
	if flt(sum_debits,2) < flt(sum_credits,2):
		# si hay Pago en cordobas
		if hayNIO == "NIO":
			# Pago parcial para Cordobas
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['credit_in_account_currency'] = flt(flt(acc.get('credit', 0.0),2) / flt(acc.get('exchange_rate'), 4), 4)
				acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
				acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
		else:
			# Pago parcial para dolares
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			for acc in facs:
				acc['credit'] = abs(flt(sum_debits, 2))
				if acc['account_currency'] == "NIO":
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(acc.get('exchange_rate', 1.0), 4)
				else:
					# return accounts
					acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2) / flt(tc, 4)
					# acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2)
					acc['exchange_rate'] = flt(tc,4)
					if accounts[1]['account_currency'] == "USD":
						acc['account_currency_pago'] = accounts[1]['account_currency']
					else:
						acc['account_currency_pago'] = None
				# break
			sum_credits = sum_debits
	else:
	# # No se efectua la conversacion del monto con la tasa de cambio
	# # Pagos con forme de la factura

		# return accounts

		if hayNIO == "NIO" and flt(sum_debits,2) == flt(sum_credits,2):
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			# return facs
			for acc in facs:
				ac = accounts[0]["credit_in_account_currency"]
				t= flt(ac,2)*flt(tc,4)
				acc['credit'] = abs(t)
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					# Tasa de cambio una decima menor
					acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = "USD"
					acc['exchange_rate'] = tc
				# break
		else:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			for acc in facs:
				# Validacion de que punto tomar
				# acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
				# El monto en dolares en cuenta de Factura
				acc['credit_in_account_currency'] = acc['credit_in_account_currency']
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['account_currency_pago'] = accounts[1]['account_currency']
				# if  accounts[1]['account_currency'] == "USD":
				# 	if hayNIO=="USD":
				# 		acc['exchange_rate'] = flt(tc,4)
				# else:
				# 	acc['account_currency_pago'] = None
				# break

	# return accounts
	# return metadata['recibo']
	diff = None
	diff_amount = None
	# hayNIOExc="USD"
	# #import pdb; pdb.set_trace()
	# # Guarda  un nuevo documento
	# return accounts
	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

		# hayNIOExc="USD"

		# for a in tdoc.get("accounts"):
		# 	if a.account_currency == "NIO":
		# 		hayNIOExc = a.account_currency
		# 		break

	# return tdoc.get("accounts")
	# return diff_amount

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'

		# Generar utilidades
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	if _ui_:
		return {
			'accounts': accounts,
			'messages': messages
		}
	if messages:
		return {
			'status': 'error',
			'error': u'\n'.join(messages)
		}
	else:
		doc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'mode_of_payment': pagos[0]['tipo_de_pago'],
			'regnumber': customer,
			# 'numero_de_recibo': metadata['recibo'],
			# 'user_remark': 'Recibo de pago' + fecha,
			'ui': _ui_
		})

		if not regnumber:
			doc.user_remark = 'Pago ZZ'

		if metadata:
			if 'IDdealer' in metadata:
				#  Collector toma una cuenta
				metadata['dealer'] = frappe.db.get_value('Colectores', filters={'colectorid': metadata.pop('colector')})
				# return metadata
			else:
				if 'colector' in metadata:
					metadata['collector'] = frappe.db.get_value('Colectores', filters={'iddealer':metadata.pop('IDdealer')})
			
			# if 'recibo' in metadata:
			# 	# metadata['user_remark'] = metadata.pop('recibo')
			# 	metadata['numero_de_recibo'] = metadata.pop('recibo')
			# 	# return metadata
			# 	doc.update(metadata)
			
			if 'AprobadoExterno' in metadata:
				# metadata['user_remark'] = metadata.pop('recibo')
				# metadata['numero_de_recibo'] = metadata.pop('recibo')
				metadata['numero_de_recibo'] = metadata.pop('AprobadoExterno')
				# return metadata
				doc.update(metadata)
		# return metadata
		try:
			doc.save()
			if 'dealer' in metadata and 'collector' in metadata:
				id_Name_Dealer = metadata['dealer']
				estado = False
			elif 'collector' in metadata:
				id_Name_Dealer = metadata['collector']
				estado = False
			else:
				id_Name_Dealer = None
				estado = True

			res = registrarPagoEnElCierre(doc,id_Name_Dealer, estado)

			if isinstance(res, str):
				frappe.db.rollback()
				return res

			doc.flags.ignore_submit_comment = True
			doc.submit()
			frappe.db.commit()
			if not regnumber:
				DocTags(doc.doctype).add(doc.name, 'ZZ')
				frappe.db.commit()
		except Exception as e:
			if doc.name and doc.docstatus:
				if not regnumber:
					DocTags(doc.doctype).add(doc.name, 'ZZ')
					frappe.db.commit()
				return doc.name.split("-")[1]
			return {
				'status': 'error',
				'error': e,
				'doc': doc.as_json()
			}

		frappe.db.commit()
		frappe.set_user(local_user)

		return doc.name.split("-")[1]
# endregion

#reggion Cancelar pagos Batch
@frappe.whitelist()
def Credenciales_dealer(iddealer):
	correo,contra = frappe.db.get_value("Colectores", {'iddealer': ['like', '%'+iddealer]},["email","pass"])
	
	if not correo:
		return 'Error, usuario no encontrado'
	
	return {'Usuario':correo,'Contra':contra}

#reggion Buscar Dealer para Cancelacion de Pago
@frappe.whitelist()
def Credenciales_dealerReversion(name):
	dealer = frappe.db.get_value("Journal Entry", {'name': ['like', '%'+name]},["owner"])
	
	if dealer:
		correo,contra = frappe.db.get_value("Colectores", {'email': ['like', '%'+dealer]},["email","pass"])
		return {'Usuario':correo,'Contra':contra}
	else:
		return 'Error, usuario no encontrado'

#reggion Buscar Dealer para Cierre de Caja
@frappe.whitelist()
def Credenciales_dealerCierreTransacion(idDealer):
	dealer = frappe.db.get_value("Colectores", {'iddealer': ['like', '%'+idDealer]},["name"])
	
	# return dealer
	if dealer:
		correo,contra = frappe.db.get_value("Colectores", {'name': ['like', '%'+dealer]},["email","pass"])
		return {'Usuario':correo,'Contra':contra}
	else:
		return 'Error, usuario no encontrado'

# verificarCliente
@frappe.whitelist()
def verificarCliente(CodigoCliente,numero):
	if not CodigoCliente:
		return 'No existe'

	# customer =  frappe.get_doc('Customer',CodigoCliente)
	regnumber = frappe.db.get_value('Customer', {'name': ['like', '%'+CodigoCliente],'mobile_no':['like','%'+numero]}, 'name')

	values = {'link_name': CodigoCliente}
	cell = frappe.db.sql("""
			SELECT GROUP_CONCAT(phone SEPARATOR ' - ') AS telefonos
			FROM `tabContact Phone` where parent in (select link_title from `tabDynamic Link` where 
			link_name = %(link_name)s and parenttype = 'Contact') 
		""", values=values, as_dict=0)
	# return cell[0]

	phone = str(cell[0]).replace("'", " ").replace("(", " ").replace(")", " ").replace(",", " ").replace(" ", "")

	if regnumber:
		return "Cliente Existente"

	elif phone:
		return "Cliente Existente"
	
	else:
		return "No existe"


@frappe.whitelist(allow_guest=True)
def validarAprobadoIBW(validarAprobadoIBW = None):
	valor = frappe.get_value('Journal Entry',{'name': ['like', 'JV-{}%'.format(validarAprobadoIBW)],'docstatus':1},"name")
	if not valor:
		return False
	else: 
		return True

@frappe.whitelist(allow_guest=True)
def validarAprobadoExterno(AprobadoExterno = None):
	valor = frappe.get_value('Journal Entry',{"numero_de_recibo":AprobadoExterno,'docstatus':1},"name")
	if not valor:
		return False
	else: 
		return True

@frappe.whitelist(allow_guest=True)
def getAprobadoIBW(AprobadoExterno = None):
	valor = frappe.get_value('Journal Entry',{"numero_de_recibo":AprobadoExterno,'docstatus':1},"name")
	return valor.replace('JV-',"")

@frappe.whitelist()
def Agregar_batch_Anticipos(name):
	# return 'ok'
	doc = frappe.get_doc('Pago Batch',name)

	data = frappe.db.sql("""select cliente,monto,nombre_del_documento as Numero_recibo,tasa_de_cambio,currency,meses_anticipo from `tabAnticipos` where docstatus = 0 and meses_anticipo > 0 and monto > 0 and aplicado = 0 limit 10000;""", as_dict=1)
	
	message = []
	# return data
	if data:
		for d in data:
			# La ultima factura tomo 
			factValidar = frappe.db.sql("""select name,currency,conversion_rate,outstanding_amount from `tabSales Invoice` where customer = %(name)s and docstatus = 1 and outstanding_amount > 1 order by posting_date asc limit 1;""", {'name': d['cliente']}, as_dict=1)
			# return factValidar[0]['name']
			# return factValidar
			
			if int(d['meses_anticipo']) == 1:
				# return 'Ok'
				if factValidar:

					if factValidar[0]['currency'] == 'USD':
						monto = factValidar[0]['conversion_rate'] * factValidar[0]['outstanding_amount']

					else:
						monto = factValidar[0]['outstanding_amount']

					# return monto

					if d['monto'] <= monto:
						pagos_detalle = {
							"monto_cordoba": d['monto'],
							# "monto_dolar": d['monto'],
							"factura": factValidar[0]['name'],
							"no_recibo":d['Numero_recibo'],
							"fecha":today(),
							"regnumber":d['cliente']
							}
					else:
						pagos_detalle = {
							"monto_cordoba": monto,
							# "monto_dolar": d['monto'],
							"factura": factValidar[0]['name'],
							"no_recibo":d['Numero_recibo'],
							"fecha":today(),
							"regnumber":d['cliente']
							}
					
					doc.append("pagos_detalle", pagos_detalle)
				else:
					message.append(_("No tiene factura generada del cliente: {0}").format(d['cliente']))
			
			else:

				if factValidar:

					if factValidar[0]['currency'] == 'USD':
						monto = factValidar[0]['conversion_rate'] * factValidar[0]['outstanding_amount']

					else:
						monto = factValidar[0]['outstanding_amount']

					# return monto

					if d['monto'] <= monto:
						pagos_detalle = {
							"monto_cordoba": d['monto'],
							# "monto_dolar": d['monto'],
							"factura": factValidar[0]['name'],
							"no_recibo":d['Numero_recibo'],
							"fecha":today(),
							"regnumber":d['cliente']
							}
					else:
						pagos_detalle = {
							"monto_cordoba": monto,
							# "monto_dolar": d['monto'],
							"factura": factValidar[0]['name'],
							"no_recibo":d['Numero_recibo'],
							"fecha":today(),
							"regnumber":d['cliente']
							}
					
					doc.append("pagos_detalle", pagos_detalle)
				else:
					message.append(_("No tiene factura generada del cliente: {0}").format(d['cliente']))

		# Agregar los anticipos
		doc.flags.ignore_permissions = True
		doc.save()

		# avisarle que el usuario no tiene factura generada
		if message:
			return {'messages':message}
		
		
		message.append("Exito")
	else:
		message.append("No hay registros de Anticipos")

	return {'messages':message}

	# return data

@frappe.whitelist()
def aplicar_pago_Centeno_Parcial(regnumber=None, fecha=None, tc=None,deudas=None, creditos=None, pagos=None, cambios=None, aplicable=None, metadata=None, _ui_=False):
	local_user = frappe.session.user
	# return type(deudas),type(pagos)

	if isinstance(metadata, six.string_types):
		# lo convierte en un diccionario
		metadata = json.loads(metadata)

	# Asiganar a la metadata de Interfaz
	if regnumber:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# tc = tc.replace('\"','')

	# return customer
	# Dealer

	if metadata and 'colector' and 'IDdealer' in metadata:
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector'],'iddealer':metadata['IDdealer']})
		# return Tercero
		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			# return 'No existe cierre'
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Colector
		# return 'Hay uno abierto'
	elif metadata and 'colector' in metadata:
		# Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})
		# Por el momento dejo pasar pagos, pero esta en la condicion Tercero
		Tercero = frappe.db.get_value('Colectores',{'colectorid': metadata['colector']})

		if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
			frappe.new_doc('Daily Closing Voucher').update({
				'posting_date': today(),
				'company': 'IBW-NI',
				'remarks': 'Cierre de Caja {}'.format(Tercero),
				'tipo': 'Colectores',
				'tercero': Tercero
			}).insert()
	# Caja
	else:
		rol = consultar_rol()
		# return rol
		if rol and not 'Administrador Caja' in rol:
			Tercero = frappe.db.get_value('User',{'email':local_user})
			# return Tercero
			if not frappe.db.exists('Daily Closing Voucher', {'tercero': Tercero, 'docstatus': 0}):
				# return "OK"
				frappe.new_doc('Daily Closing Voucher').update({
					'posting_date': today(),
					'company': 'IBW-NI',
					'remarks': 'Cierre de Caja {}'.format(Tercero),
					'tipo': 'User',
					'tercero': Tercero
				}).insert()

	if not fecha:
		fecha = today()
	else:
		fecha = fecha.replace('\"','')

	# Tasa de cambio paralela
	if not tc:
		tc = get_exchange_rate('USD', 'NIO', fecha, throw=True)

	messages = []
	accounts = []
	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)
	if isinstance(creditos, six.string_types):
		creditos = json.loads(creditos, object_pairs_hook=frappe._dict)
	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	if isinstance(cambios, six.string_types):
		cambios = json.loads(cambios, object_pairs_hook=frappe._dict)
	if isinstance(aplicable, six.string_types):
		aplicable = json.loads(aplicable, object_pairs_hook=frappe._dict)

	if deudas:
		messages += validate_list_of_dicts(deudas, 'deudas', ('link_doctype', 'link_name'))
	if creditos:
		messages += validate_list_of_dicts(creditos, 'creditos', ('link_doctype', 'link_name'))
	if pagos:
		messages += validate_list_of_dicts(pagos, 'pagos', ('tipo_de_pago', 'moneda', 'monto'), ('referencia',))
	if cambios:
		messages += validate_list_of_dicts(cambios, 'cambios', ('moneda', 'monto'))

	if not regnumber and not deudas and not (creditos or pagos):
		return {
			'status': 'error',
			'message': 'You should provide at least the regnumber or deudas and/or creditos or pagos'
		}
	elif not regnumber:
		if not creditos and not pagos:
			return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}

	if not regnumber:
		return {
				'status': 'error',
				'message': 'You should provide at least the creditos or pagos values'
			}
	else:
		customer = frappe.db.exists("Customer", {"name": ["like", "%{}".format(regnumber)]})

	# Falta depurar

	if deudas:
		validate_party_entries(deudas, accounts, messages, tc, 'c', customer=customer)
	if creditos:
		validate_party_entries(creditos, accounts, messages, tc, 'd', customer=customer)
	if pagos:
		validate_payment_entries(pagos, accounts, messages, tc, 'd')
	if cambios:
		validate_payment_entries( list(map(lambda d: d.update({'tipo_de_pago': 'Efectivo'}), cambios)), accounts, messages, tc, 'c')

	# return accounts
	# return tc
	# Importante
	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']


	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return accounts

	# condicion de pagos parciales
	if flt(sum_debits,2) < flt(sum_credits,2):
		fecha_Fact = []
		# si hay Pago en cordobas
		if hayNIO == "NIO":
			# return "Entra Aqui"
			# Pago parcial para Cordobas
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			sum_debits_nio = sum([d.get('debit_in_account_currency', 0.0) for d in accounts])

			# return facs
			for fec in facs:
				# fecha_Fact.append(_("Factura Pagada: {0}").format(frappe.get_value('Sales Invoice',fec['reference_name'],'posting_date')))
				fecha =  frappe.get_value('Sales Invoice',fec['reference_name'],'posting_date')
				fecha_Fact.append(_("{0}").format(fec['reference_name']))

			# message.append(_("Factura Pagada: {0}").format(ba.factura))
			# return "(" + str(fecha_Fact).replace("[","").replace("]","") + ")"
			values = {'company':fecha_Fact}
			# reti
			# return values
			ordenFacturas = frappe.db.sql("""
				select name,posting_date from `tabSales Invoice` where name in %(company)s order by posting_date asc;
			""", values=values, as_dict=1)

			# return len(accounts)-1

			# debits = flt(sum_debits_nio/len(facs))
			# VERIFICAR PAGOS FALTA CONDICION
			saldo = sum_debits_nio
			# return saldo,ordenFacturas
			# return accounts[0]['credit']
			for fa in ordenFacturas:
				for acc in facs:
					if fa.name == acc['reference_name']:
						# if i == int(len(ordenFacturas)-1):

						saldo = round(saldo - acc['credit'],2)

						if saldo > 0:
							# saldo = flt(saldo)
							# acc['credit'] = abs(flt(saldo, 2))
							# acc['credit_in_account_currency'] = flt(flt(saldo,2) / flt(acc.get('exchange_rate'), 4), 4)
							acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
							acc['account_currency_pago'] = None

						else:
							saldo = flt(saldo + acc['credit'])
							acc['credit'] = abs(flt(saldo, 2))
							acc['credit_in_account_currency'] = round(flt(saldo,2) / flt(acc.get('exchange_rate'), 4), 4)
							acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
							acc['account_currency_pago'] = None

		else:
			# Pago parcial para dolares
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))

			sum_debits_usd = sum([d.get('debit_in_account_currency', 0.0) for d in accounts])
			# sum_debits_nio = sum([d.get('debit', 0.0) for d in accounts])

			for fec in facs:
				fecha =  frappe.get_value('Sales Invoice',fec['reference_name'],'posting_date')
				fecha_Fact.append(_("{0}").format(fec['reference_name']))

			values = {'facturas':fecha_Fact}
			# reti
			# return values
			ordenFacturas = frappe.db.sql("""
				select name,posting_date from `tabSales Invoice` where name in %(facturas)s order by posting_date asc;
			""", values=values, as_dict=1)

			saldo = sum_debits_usd
			# return accounts
			for fa in ordenFacturas:
				for acc in facs:
					if fa.name == acc['reference_name']:
						# if i == int(len(ordenFacturas)-1):
						saldo = round(saldo - acc['credit_in_account_currency'],2)

						if saldo > 0:
							saldo = flt(saldo)
							# acc['credit'] = abs(flt(saldo, 2))
							# acc['credit_in_account_currency'] = flt(flt(saldo,2) / flt(acc.get('exchange_rate'), 4), 4)
							# acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
							# acc['account_currency_pago'] = None

							acc['credit'] = round(acc['credit_in_account_currency'] * flt(tc, 4),2)
							# acc['credit_in_account_currency'] = flt(acc.get('credit', 0.0), 2)
							acc['exchange_rate'] = flt(tc,4)
							if accounts[1]['account_currency'] == "USD":
								acc['account_currency_pago'] = accounts[1]['account_currency']
							else:
								acc['account_currency_pago'] = None

						else:
							saldo = flt(saldo + acc['credit_in_account_currency'])
							acc['credit_in_account_currency'] = saldo
							acc['credit'] = round(flt(saldo * flt(tc,4) ,2),2)
							acc['exchange_rate'] = flt(tc,4)
							if accounts[1]['account_currency'] == "USD":
								acc['account_currency_pago'] = accounts[1]['account_currency']
							else:
								acc['account_currency_pago'] = None

	else:
	# # No se efectua la conversacion del monto con la tasa de cambio
	# # Pagos con forme de la factura

		# return accounts

		if hayNIO == "NIO" and flt(sum_debits,2) == flt(sum_credits,2):
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			# return facs
			for acc in facs:
				ac = accounts[0]["credit_in_account_currency"]
				t= flt(ac,2)*flt(tc,4)
				acc['credit'] = abs(t)
				acc['account_currency_pago'] = accounts[1]['account_currency']
				if  accounts[1]['account_currency'] == "USD":
					# Tasa de cambio una decima menor
					acc['exchange_rate'] = flt(tc,4)
				else:
					acc['account_currency_pago'] = "USD"
					acc['exchange_rate'] = tc
				# break
		else:
			facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
			for acc in facs:
				# Validacion de que punto tomar
				# acc['credit_in_account_currency'] = truncate(acc['credit_in_account_currency'],2)
				# El monto en dolares en cuenta de Factura
				acc['credit_in_account_currency'] = acc['credit_in_account_currency']
				acc['credit'] = abs(flt(sum_debits, 2))
				acc['account_currency_pago'] = accounts[1]['account_currency']
				# if  accounts[1]['account_currency'] == "USD":
				# 	if hayNIO=="USD":
				# 		acc['exchange_rate'] = flt(tc,4)
				# else:
				# 	acc['account_currency_pago'] = None
				# break
	#Ver cuentas
	# return accounts

	diff = None
	diff_amount = None
	# hayNIOExc="USD"
	# #import pdb; pdb.set_trace()
	# # Guarda  un nuevo documento
	# return accounts
	try:
		tdoc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'ui': _ui_
		})

		tdoc.run_method('validate')
	except Exception:
		frappe.local.message_log = []
		if tdoc.difference:
			diff_amount = tdoc.difference

		# hayNIOExc="USD"

		# for a in tdoc.get("accounts"):
		# 	if a.account_currency == "NIO":
		# 		hayNIOExc = a.account_currency
		# 		break

	# return tdoc.get("accounts")
	# return diff_amount

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		# reemplaza el 5 > abs(flt(frappe.db.get_value('Accounts Settings', 'Accounts Settings', 'miniminal_credit_amount')))
	# 	if diff_amount > 0 and flt(diff_amount, 2) / flt(tc) > 5:
	# # 		#  Facturación Cobrada por Anticipado - IBWNI
	# 		diff = list(filter(lambda e: e['account'] == u'2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI', accounts))
	# 		if not diff:
	# # 			#  Facturación Cobrada por Anticipado - IBWNI
	# 			account = frappe.db.get_value('Account', filters={'name': ['like', '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI']})
	# 			if not regnumber:
	# 				account = account.replace(' - ', ' ZZ - ')
	# 			diff = {
	# 				'account': account,
	# 				'account_currency': 'USD',
	# 				'account_type': 'Payable',
	# 				'credit_in_account_currency': 0.0,
	# 				'credit': 0.0,
	# 				'debit_in_account_currency': 0.0,
	# 				'debit': 0.0,
	# 				'exchange_rate': 0.0,
	# 				'party_type': 'Customer',
	# 				'party': get_cliente_id(regnumber),
	# 				'is_advance': 'Yes'
	# 			}
	# 			accounts.append(diff)
	# 		else:
	# 			diff = diff[0]

	# 		diff['credit'] = flt(abs(diff_amount), 2)
	# 		diff['credit_in_account_currency'] = compute_usd(abs(diff_amount), tc)
	# 		diff['exchange_rate'] = compute_tc(diff['credit_in_account_currency'], diff['credit'])
	# 	else:
		# Generar utilidades
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0

	# return accounts
	if _ui_:
		return {
			'accounts': accounts,
			'messages': messages
		}
	if messages:
		return {
			'status': 'error',
			'error': u'\n'.join(messages)
		}
	else:
		doc = frappe.new_doc('Journal Entry').update({
			'voucher_type': 'Journal Entry',
			'posting_date': fecha,
			'multi_currency': 1,
			'accounts': accounts,
			'mode_of_payment': pagos[0]['tipo_de_pago'],
			# 'user_remark': 'Recibo de pago' + fecha,
			'ui': _ui_
		})

		if not regnumber:
			doc.user_remark = 'Pago ZZ'

		if metadata:
			if 'colector' in metadata:
				#  Collector toma una cuenta
				metadata['collector'] = frappe.db.get_value('Colectores', filters={'colectorid': metadata.pop('colector')})
				# return metadata
			if 'IDdealer' in metadata:
				metadata['dealer'] = frappe.db.get_value('Colectores', filters={'iddealer':metadata.pop('IDdealer')})
			if 'recibo' in metadata:
				metadata['user_remark'] = metadata.pop('recibo')
				# return metadata
				doc.update(metadata)
		# return metadata
		try:
			doc.save()
			if 'dealer' in metadata and 'collector' in metadata:
				id_Name_Dealer = metadata['dealer']
				estado = False
			elif 'collector' in metadata:
				id_Name_Dealer = metadata['collector']
				estado = False
			else:
				id_Name_Dealer = None
				estado = True

			res = registrarPagoEnElCierre(doc,id_Name_Dealer, estado)

			if isinstance(res, str):
				frappe.db.rollback()
				return res

			doc.flags.ignore_submit_comment = True
			doc.submit()
			frappe.db.commit()
			if not regnumber:
				DocTags(doc.doctype).add(doc.name, 'ZZ')
				frappe.db.commit()
		except Exception as e:
			if doc.name and doc.docstatus:
				if not regnumber:
					DocTags(doc.doctype).add(doc.name, 'ZZ')
					frappe.db.commit()
				return doc.name.split("-")[1]
			return {
				'status': 'error',
				'error': e,
				'doc': doc.as_json()
			}

		frappe.db.commit()
		frappe.set_user(local_user)

		return doc.name.split("-")[1]

@frappe.whitelist()
def aplicar_AnticiposBatch(deudas=None,pagos=None,cuentaBanco=None,regnumber=None, tc=None,fecha=None,observacion = None,dc='c',_ui_=False):
	from erpnext.accounts.party import get_party_account, get_party_account_currency


	if isinstance(deudas, six.string_types):
		deudas = json.loads(deudas, object_pairs_hook=frappe._dict)

	if isinstance(pagos, six.string_types):
		pagos = json.loads(pagos, object_pairs_hook=frappe._dict)
	
	# if isinstance(regnumber, six.string_types):
	# 	regnumber = json.loads(regnumber, object_pairs_hook=frappe._dict)

	# if isinstance(cuentaBanco, six.string_types):
	# 	cuentaBanco = json.loads(cuentaBanco, object_pairs_hook=frappe._dict)

	# if isinstance(fecha, six.string_types):
	# 	fecha = json.loads(fecha, object_pairs_hook=frappe._dict)

	# if isinstance(tc, six.string_types):
	# 	tc = json.loads(tc, object_pairs_hook=frappe._dict)

	# return deudas,pagos,regnumber

	cuentaBanco = '2.02.003.001.002-POSTPAGO, FACTURACION COBRADA POR ANTICIPADO - NI'
	# return fecha
	# entry = deudas
	customer = regnumber
	accounts = []

	# for divisa in pagos:
	# 	divi = divisa.moneda
	
	MontoTotal = 0.0
	# return deudas.link_doctype
	for deuda in deudas:
		# ret = {'party_type': 'Customer', 'party': customer, 'reference_type': deuda.link_doctype, 'reference_name': deuda.link_name}
		ret = {'party_type': 'Customer', 'party': customer, 'reference_type': deuda['link_doctype'], 'reference_name':deuda['link_name']}
		party_args = {'party_type': 'Customer', 'party': customer, 'company' :'IBW-NI'}

		# if divi == 'NIO':
		# 	account, account_currency = get_party_account(**party_args), 'NIO'
		# else:
		# 	account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)

		account, account_currency = get_party_account(**party_args), get_party_account_currency(**party_args)

		prefix = 'credit' if dc == 'c' else 'debit'
		field = '{0}_in_account_currency'.format(prefix)
		ret.update({'account': account, 'account_currency': account_currency})
		# if deuda.link_doctype == "Sales Invoice":
		if deuda['link_doctype'] == "Sales Invoice":
			# Asignarle el monto que digito en el Deposito
			# ret[field] = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'outstanding_amount')
			ret[field] = frappe.db.get_value(deuda['link_doctype'], deuda['link_name'], 'outstanding_amount')
			for monto in pagos:
				# if monto.Factura == deuda.link_name:
				if monto['Factura'] == deuda['link_name']:
					# ret[field] = monto.monto
					# MontoTotal += monto.monto
					MontoTotal += monto['monto']

			if account_currency == 'USD':
				# er = frappe.db.get_value(deuda.link_doctype, deuda.link_name, 'conversion_rate')
				er = frappe.db.get_value(deuda['link_doctype'], deuda['link_name'], 'conversion_rate')
			else:
				er = 1.0
				# Hice pase tasa tc
			ret[prefix] = flt(compute_nio(ret[field], er),2)
			#frappe.msgprint('<pre>' + frappe.as_json(ret) + '</pre>')
			#ret['exchange_rate'] = compute_tc(ret[field], ret[prefix])
			ret['exchange_rate'] = er
		accounts.append(ret)

	# return MontoTotal
	# return accounts
	# mode = 'Depositos'
	currency_map = {
		'nio': 'NIO',
		'c$': 'NIO',
		'usd': 'USD',
		'$': 'USD'
	}

	for entry in pagos:
		# currency = currency_map.get((entry.moneda or '').lower())
		currency = currency_map.get((entry['moneda'] or '').lower())
		if not currency:
			# messages.append('The currency {0} is not recognized as an valid currency!'.format(entry.moneda))
			messages.append('The currency {0} is not recognized as an valid currency!'.format(entry['moneda']))
		else:
			# if not frappe.db.exists('Mode of Payment Account', {'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user}):
			# 	messages.append("The active user don't have an properly configured account for mode of payment {0}".format(entry.tipo_de_pago))
			# else:
				# default_account = frappe.db.get_value('Mode of Payment Account',
				# 	fieldname='default_account',
				# 	filters={'parent': entry.tipo_de_pago, 'moneda_de_la_cuenta': currency, 'usuario': frappe.session.user})

				prefix = 'debit'
				field = '{0}_in_account_currency'.format(prefix)
				# Reversion de modo de pago para el usuario
				row = {'account': cuentaBanco, 'account_currency': currency, 'mode_of_payment':'Deposito'}
				# row[field] = flt(entry.monto, 2)
				row[field] = flt(MontoTotal,2) #MontoTotal Cambiarle la variable

				if currency == 'NIO':
					er = 1.0
				else:
					# tc = tc.replace('\"','')
					er = tc
				# row[prefix] = compute_nio(row[field], er)
				# er = 1.0
				row[prefix] = compute_nio(row[field], er)
				row['exchange_rate'] = flt(compute_tc(row[field], row[prefix]),4)
				accounts.append(row)
				break

	# # Variable para verificar si viene un pago en Cordobas
	# hayNIO = "USD"

	# #Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	# facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	# for acc in facs:
	# 	acc['tipo_de_cuenta']="Pagado"

	# facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	# for acc in facs:
	# 	acc['tipo_de_cuenta']="Recibido"

	# 	if acc['account_currency']=="NIO":
	# 		hayNIO = acc['account_currency']


	# Importante
	# #sum_debits es el pago que hara el cliente.
	# sum_debits = sum([d.get('debit', 0.0) for d in accounts])
	# #sum_credits es el monto total de las facturas pendientes.
	# sum_credits = sum([d.get('credit', 0.0) for d in accounts])

	# Variable para verificar si viene un pago en Cordobas
	hayNIO = "USD"

	#Pase para poner el tipo de cuenta e identificar lo que aumenta o disminuye en los cierres
	facs = list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Pagado"

	facs = list(filter(lambda acc: acc.get("reference_type") != "Sales Invoice", accounts))

	for acc in facs:
		acc['tipo_de_cuenta']="Recibido"

		if acc['account_currency']=="NIO":
			hayNIO = acc['account_currency']

	# return accounts,hayNIO
	# return hayNIO
	# for a in range(1,len(accounts)):
	# 	if accounts[a]['account_currency'] == "NIO":
	# 		hayNIO = accounts[a]['account_currency']
	# 		break

	# return sum_debits, sum_credits
	# return tc
	# return accounts

	# return accounts
	# if flt(sum_debits,2) < flt(sum_credits,2):
	facs = list(reversed(list(filter(lambda acc: acc.get("reference_type") == "Sales Invoice", accounts))))
	if hayNIO == 'USD':
		for acc in facs:
			for MontFac in pagos:
				if MontFac.Factura == acc['reference_name']:
					acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
					acc['exchange_rate'] = flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"), 4)
					acc['credit'] = flt(flt(MontFac.monto) * flt(frappe.get_value("Sales Invoice",acc.get('reference_name'),"conversion_rate"),4))
	# 				acc['account_currency_pago'] = 'USD'
	# if hayNIO == 'NIO':
	# 	for acc in facs:
	# 		for MontFac in pagos:
	# 			if MontFac.Factura == acc['reference_name']:
	# 				acc['credit_in_account_currency'] = abs(flt(MontFac.monto, 2))
	# 				acc['exchange_rate'] = 1.00
	# 				acc['credit'] = flt(flt(MontFac.monto) * 1)
	# 				acc['account_currency_pago'] = None

	# #sum_debits es el pago que hara el cliente.
	# sum_debits = sum([d.get('debit_in_account_currency', 0.00) for d in accounts])
	# #sum_credits es el monto total de las facturas pendientes.
	# sum_credits = sum([d.get('credit_in_account_currency', 0.00) for d in accounts])

	#sum_debits es el pago que hara el cliente.
	sum_debits = sum([d.get('debit', 0.00) for d in accounts])
	#sum_credits es el monto total de las facturas pendientes.
	sum_credits = sum([d.get('credit', 0.00) for d in accounts])

	# return accounts
	diff_amount = None
	tdoc = None

	diff_amount = Cal_total_debit_credit(sum_debits,sum_credits)


	tdoc = None

	# try:
	# 	tdoc = frappe.new_doc('Journal Entry').update({
	# 		'voucher_type': 'Journal Entry',
	# 		'posting_date': fecha,
	# 		'multi_currency': 1,
	# 		'accounts': accounts,
	# 		'ui': _ui_
	# 	})

	# 	tdoc.run_method('validate')
	# except Exception:
	# 	frappe.local.message_log = []
	# 	if tdoc.difference:
	# 		diff_amount = tdoc.difference

	# return tdoc

	if diff_amount:
		p = 'debit' if diff_amount < 0 else 'credit'
		if diff_amount > 0:
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.010-Utilidades Cambiarias - NI', accounts))

			if not diff:
			#  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.010-Utilidades Cambiarias - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
		# Generar Perdidas
		else:
			# Generar Perdida Cambiaria
			# if hayNIOExc == "NIO":
			# Utilidades Cambiarias - IBWNI
			diff = list(filter(lambda e: e['account'] == '6.22.002-Pérdida Cambiaria - NI', accounts))

			if not diff:
			##  Utilidades Cambiarias - IBWNI
				diff = {'account': '6.22.002-Pérdida Cambiaria - NI', 'account_currency': 'NIO', 'conversion_rate': 1, 'debit': 0.0, 'credit': 0.0, 'debit_in_account_currency': 0.0, 'credit_in_account_currency': 0.0, "tipo_de_cuenta":"Diferencial Cambiario"}
				accounts.append(diff)
			else:
				diff = diff[0]

			diff[p] += abs(diff_amount)
			diff['{0}_in_account_currency'.format(p)] += abs(diff_amount)

			# return accounts
			if diff and diff['debit'] and diff['credit']:
				if diff['debit'] > diff['credit']:
					diff['debit_in_account_currency'] -= diff['credit_in_account_currency']
					diff['debit'] -= diff['credit']
					diff['credit_in_account_currency'] = diff['credit'] = 0.0
				else:
					diff['credit_in_account_currency'] -= diff['debit_in_account_currency']
					diff['credit'] -= diff['debit']
					diff['debit_in_account_currency'] = diff['debit'] = 0.0
	
	# return {'accounts':accounts}
	
	if _ui_:
		newJe = frappe.new_doc('Journal Entry')
		newJe.update({
			'posting_date': today(),
			'accounts':accounts,
			'multi_currency': True,
			# frappe.get_value('Journal Entry',{"numero_de_recibo":AprobadoExterno,'docstatus':1},"name")
			'codigoanticipo' : frappe.get_value('Anticipos',{"Cliente":regnumber,'docstatus':0},"name"),
			'tipo_de_pago' : "Aplicar Anticipo",
			# 'aplico_deposito_banco':1,
			'user_remark': observacion,
			'regnumber': regnumber,
			# 'numero_de_recibo': numero_de_recibo,
			'numero_de_recibo': frappe.get_value('Anticipos',{"Cliente":regnumber,'docstatus':0},"nombre_del_documento"),
			'no_registrar_cierre': 1,
			'ui':_ui_
		})

		newJe.save()
		newJe.flags.ignore_submit_comment = True
		newJe.submit()
		frappe.db.commit()
		return newJe.name

	else:
		return {'accounts':accounts}

@frappe.whitelist()
def formato_BAC():
	import zipfile
	import os

	rep = frappe.db.sql(
			"""call Formato_BAC;""",as_dict=True,)

	fecha = today()
	f = open( './ibwni-crm.ibw.com/public/files/Cargos_BAC/Cargos_bac_'+fecha+".csv","w")

	for r in range(len(rep)):
		if r == len(rep)-1:
			f.write(f"{int(rep[r]['n'])},{rep[r]['RegNumber']},{rep[r]['IBWInvoice']},{rep[r]['total']},{rep[r]['fecha_vence']},{rep[r]['Nombre']},{rep[r]['cedula']},{rep[r]['BillDate']},{rep[r]['Notes']}")
			break

		f.write(f"{int(rep[r]['n'])},{rep[r]['RegNumber']},{rep[r]['IBWInvoice']},{rep[r]['total']},{rep[r]['fecha_vence']},{rep[r]['Nombre']},{rep[r]['cedula']},{rep[r]['BillDate']},{rep[r]['Notes']}\n")
	
	f.close()   
	
	ruta_archivo_zip = "./ibwni-crm.ibw.com/public/files/Cargos_BAC/Cargos_bac_"+fecha+".zip" 

	archivos_a_comprimir = ["./ibwni-crm.ibw.com/public/files/Cargos_BAC/Cargos_bac_"+fecha+".csv"]

	with zipfile.ZipFile(ruta_archivo_zip, 'w',zipfile.ZIP_DEFLATED) as mi_zip:
		# Agrega los archivos a comprimir al archivo ZIP
		for archivo in archivos_a_comprimir:
			mi_zip.write(archivo, arcname=archivo.split("/")[-1])

	message = []
	try:
		os.remove("./ibwni-crm.ibw.com/public/files/Cargos_BAC/Cargos_bac_"+fecha+".csv")
		message.append(_("El archivo {0} ha sido eliminado con éxito.").format("Cargos_bac_"+fecha+".csv"))
	except OSError as e:
		message.append(_("No se pudo eliminar el archivo {0}").format("Cargos_bac_"+fecha+".csv"))

	send_mail("supervisoresauttelnic@baccredomatic.ni", "Carga de Facturas " + fecha, "Este es el archivo para carga de facturas correspondiente al dia " + fecha, "./ibwni-crm.ibw.com/public/files/Cargos_BAC/Cargos_bac_" + fecha + ".zip", "Cargos_bac_" + fecha + ".zip")

	return 'OK'

def send_mail(receiver_email, subject, body, filename, file):
	try:
		port = 465 
		smtp_server = "cobranza.ibw.com.ni"
		login = "relay@cobranza.ibw.com.ni"
		password = "r1rJzG9wxc:UTq7mgiFAu"

		sender_email = "cobranza@ibw.com.ni"

		message = MIMEMultipart()
		message["From"] = sender_email
		message["To"] = receiver_email
		message["CC"] = "it@ibw.com.ni"
		message["Subject"] = subject

		# Agrega el cuerpo al correo
		message.attach(MIMEText(body, "plain"))

		# We assume that the file is in the directory where you run your Python script from
		with open(filename, "rb") as attachment:
			# The content type "application/octet-stream" means that a MIME attachment is a binary file
			part = MIMEBase("application", "octet-stream")
			part.set_payload(attachment.read())

		# Encode to base64
		encoders.encode_base64(part)

		# Add header 
		part.add_header(
			"Content-Disposition",
			f"attachment; filename= {file}",
		)

		# Add attachment to your message and convert it to string
		message.attach(part)
		text = message.as_string()

		# send your email
		with smtplib.SMTP_SSL(smtp_server, port) as server:
			server.login(login, password)
			server.sendmail(
				sender_email, receiver_email, text
			)
	except Exception as e:
		print(str(e))