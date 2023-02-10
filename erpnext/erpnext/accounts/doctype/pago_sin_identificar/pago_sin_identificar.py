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

	# def on_submit(self):
	# 	if (frm.doc.docstatus === 0){
    #     //     frm.add_custom_button('Aplicar Deposito', function(){
    #     //         cur_frm.cscript.AplicarDepostos(frm);
    #     //     });
    #     // }
	