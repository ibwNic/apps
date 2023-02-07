# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PagoSinIdentificar(Document):
	def on_update(self):
		if self.docstatus == 0:
			# Bancentro
			# BAC
			# Banpro
			# BDF
			if self.banco == 'Bancentro':
				if self.moneda == 'NIO':
					frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.003-Bancentro Córdobas 100208377 - NI')
				if self.moneda == 'USD':
					frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.002.004-Bancentro Dólares No101209210 - NI')
			
			if self.banco == 'BAC':
				if self.moneda == 'NIO':
					frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.004-BAC Córdobas No.351000488 - NI')
				if self.moneda == 'USD':
					frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.002.003-BAC Dolares No 360871727 - NI')
			
			if self.banco == 'Banpro':
				if self.moneda == 'NIO':
					frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.005-BANPRO CORDOBAS - NI')
				if self.moneda == 'USD':
					frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.002.002-BANPRO DOLARES - NI')

			if self.banco == 'BDF':
				if self.moneda == 'NIO':
					frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.001-BDF Córdobas Nº100010030014661 - NI')
				else: 
					frappe.msgprint('Lo sentimos no se encuentra registrado una cunenta de dolares!')
					frappe.db.rollback()
				# if self.moneda == 'USD':
				# 	frappe.db.set_value('Pago_sin_identificar', self.name, 'cuentas', '1.01.001.002.002.002-BANPRO DOLARES - NI')
			self.reload()
			# return 1
	# 		# # try:
	# 		# 	res = obtenerCierreCaja(True)
	# 		# 	if res == 1:
	# 		# 		raise Exception("Debe de cerrar caja antes de empezar hacer transacciones update")
		
	# def validate(self):
	# 	if self.docstatus == 0:
	# 	# Bancentro
	# 	# BAC
	# 	# Banpro
	# 	# BDF
	# 		if self.banco == 'Bancentro':
	# 			if self.moneda == 'NIO':
	# 				frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.003-Bancentro Córdobas 100208377 - NI')
	# 			if self.moneda == 'USD':
	# 				frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.002.004-Bancentro Dólares No101209210 - NI')
			
	# 		if self.banco == 'BAC':
	# 			if self.moneda == 'NIO':
	# 				frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.004-BAC Córdobas No.351000488 - NI')
	# 			if self.moneda == 'USD':
	# 				frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.002.003-BAC Dolares No 360871727 - NI')
			
	# 		if self.banco == 'Banpro':
	# 			if self.moneda == 'NIO':
	# 				frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.005-BANPRO CORDOBAS - NI')
	# 			if self.moneda == 'USD':
	# 				frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.002.002-BANPRO DOLARES - NI')

	# 		if self.banco == 'BDF':
	# 			if self.moneda == 'NIO':
	# 				frappe.db.set_value('Pago Sin Identificar', self.name, 'cuentas', '1.01.001.002.001.001-BDF Córdobas Nº100010030014661 - NI')
	# 			else: 
	# 				frappe.msgprint('Lo sentimos no se encuentra registrado una cunenta de dolares!')
	# 				frappe.db.rollback()

@frappe.whitelist()
def Aplicar_Deposito(Aplicar_Deposito):
	# je = frappe.get_doc('Journal Entry',AsientoContable)
	# accounts=[]
	# je.
	# for acc in je.accounts:
	accouts = [{
	'account' :	'Cuentas por Cobrar Moneda Extrangera - IBWNI - NI ',
	'party_type':'Customer',
	'party': 'acc.party',
	'account_currency':'acc.account_currency',
	'credit_in_account_currency':'acc.debit_in_account_currency',
	'credit': 'acc.debit',
	'exchange_rate':'acc.exchange_rate',
	'debit_in_account_currency':'acc.credit_in_account_currency',
	'debit':'acc.credit',
	'reference_name':'acc.reference_name',
	'reference_type':'Sales Invoice',
	'tipo_de_cuenta':'acc.tipo_de_cuenta',
	'account_currency_pago':'acc.account_currency_pago',
	'doctype':'acc.doctype',
	'aplicco_reversion': 0
	},
	{
	'account' :	'acc.account2',
	'party_type':'acc.party_type',
	'party': 'acc.party',
	'account_currency':'acc.account_currency',
	'credit_in_account_currency':'acc.debit_in_account_currency',
	'credit': 'acc.debit',
	'exchange_rate':'acc.exchange_rate',
	'debit_in_account_currency':'acc.credit_in_account_currency',
	'debit':'acc.credit',
	'reference_name':'acc.reference_name',
	'reference_type':'acc.reference_type',
	'tipo_de_cuenta':'acc.tipo_de_cuenta',
	'account_currency_pago':'acc.account_currency_pago',
	'doctype':'acc.doctype',
	'aplicco_reversion': 0
	}]

	# accounts.append(accouts)
	# accounts.append(accouts2)

	# l=len(accounts)
	
	# for r in range(0,l):
	# 	if accounts[r]['debit_in_account_currency'] == 0.0:
	# 		accounts[r].pop('debit_in_account_currency')
			
	# 	if accounts[r]['debit'] == 0.0:
	# 		accounts[r].pop('debit')
		
	# 	if accounts[r]['credit_in_account_currency'] == 0.0:
	# 		accounts[r].pop('credit_in_account_currency')
		
	# 	if accounts[r]['credit'] == 0.0:
	# 		accounts[r].pop('credit')

	# 	if accounts[r]['party'] == None:
	# 		accounts[r].pop('party')
			
	# 	if accounts[r]['party_type'] == None:
	# 		accounts[r].pop('party_type')
		
	# 	if accounts[r]['reference_name'] == None:
	# 		accounts[r].pop('reference_name')
		
	# 	if accounts[r]['reference_type'] == None:
	# 		accounts[r].pop('reference_type')
		
	# 	if accounts[r]['account_currency_pago'] == None:
	# 		accounts[r].pop('account_currency_pago')

	# newJe = frappe.new_doc('Journal Entry')
	# newJe.update({
	# 	'posting_date': today(),
	# 	'posting_time': today(),
	# 	'accounts':accounts,
	# 	'multi_currency': True,
	# 	'observacion': 'Se revertio el pago'
	# })

	# newJe.append("accounts", accounts)

	# for m in accounts:
	# 	item1 = newJe.append('accounts', {"item_code": ""})				
	# 	item1.schedule_date = nowdate()
	# 	item1.item_code = m[0]
	# 	item1.qty=int(m[1])*int(cantidad)

	# for item in je.accounts:
	# 		# frappe.msgprint(str(item))
	# 	accounts = {
	# 			"tipo_de_pago": item.mode_of_payment,
	# 			"moneda": item.account_currency,
	# 			"montousd":item.debit_in_account_currency,
	# 			"montonio": item.debit,
	# 		}
	# 	newJe.append("accounts", accounts)

	# return {'docs': newJe.as_dict()}
	return accouts