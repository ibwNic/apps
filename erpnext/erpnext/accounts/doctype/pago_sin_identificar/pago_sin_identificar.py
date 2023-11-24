# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _, msgprint, throw

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
					frappe.throw(
						title='Error',
						msg='Lo sentimos no se encuentra registrado una cuenta de dolares!',
						exc=FileNotFoundError
					)
			self.reload()

		if self.workflow_state == "Por aplicar" and self.docstatus == 0:
			sum = 0
			for monto in self.get("facturaporaplicar"):
				sum = sum + monto.monto
			
			if sum > 0:
				if sum > self.monto:
					# raise Exception("Debe de cerrar caja antes de empezar hacer transacciones")
					frappe.msgprint(_("La suma de los montos no puede ser mayor a lo registrado!"))
					frappe.db.set_value('Pago Sin Identificar', self.name, 'workflow_state', 'Pendiente')
					self.reload()
					return
				
		user = frappe.get_doc("User", frappe.session.user)

		if user:
			for rol in user.get('roles'):
				if rol.role == 'Cobranza':
					if not self.get("facturaporaplicar"):
						frappe.msgprint(_("Debe de registrar al menos una factura!"))
						frappe.db.set_value('Pago Sin Identificar', self.name, 'workflow_state', 'Pendiente')
						self.reload()
						return