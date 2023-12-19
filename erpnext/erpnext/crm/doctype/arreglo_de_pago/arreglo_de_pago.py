# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_days,	add_months
from frappe import _

class ArreglodePago(Document):
	def on_update(self):
		self.valiadcion_monto_Total()
	

	def valiadcion_monto_Total(self):
		ap = frappe.get_doc('Arreglo de Pago', self.name)

		if not self.get("cuotas"):
			# frappe.throw("entra")

			sum = 0
			valoresUpdate = []
			for c in self.get("cuotas"):
				sum = c.monto_abono + sum

				# valoresUpdate.append(_("Abono: {0}").format(c.cod_abono))
				valoresUpdate.append({
					"Abono": c.cod_abono,
					"Monto": c.monto_abono
				})

			# frappe.msgprint(_("Enta"))
			if sum > self.saldo_total:
				# frappe.throw("Los montos de las cuotas, no pueden ser mayor al Saldo Total")
				frappe.throw(_("Los montos de las cuotas, no pueden ser mayor al Saldo Total"))
				# frappe.msgprint("Los montos de las cuotas, no pueden ser mayor al Saldo Total")
				self.reload()
			else:

				for up in self.get("detalle"):
					for c in valoresUpdate:
						if up.abono == c['Abono']:
							if up.monto != c['Monto']:
								frappe.db.sql("update `tabArreglo de Pago Cuota Detalle` set monto = %(monto_abono)s where parent = %(name)s and abono = %(up.abono)s ",{"name":self.name,"monto_abono":c['Monto'],"up.abono":up.abono})
								break

				self.reload()

@frappe.whitelist()
def get_facturas(regnumber):
	facturas = frappe.db.sql(""" select count(name) as cantidad, sum(saldo) as total from montos_por_cobrar_720 where customer = %(regnumber)s and saldo > 0;""",{"regnumber":regnumber})

	return facturas

@frappe.whitelist()
def generar_calendario(name):
	ap = frappe.get_doc('Arreglo de Pago', name)
	fct_pend = frappe.db.sql(""" select name, saldo from montos_por_cobrar_720 where customer = %(regnumber)s and saldo > 0; """,{"regnumber":ap.regnumber})

	saldo_total = ap.saldo_total
	abonos = flt(ap.saldo_total / ap.intervalo, 2)
	
	saldo_abono = 0.00
	saldo_fact = 0.00
	abono_fact = 0.00
	new_fecha = ap.fecha
	i=0

	for a in range(1, ap.intervalo + 1):
		if ap.intervalos_de_pago=="MES":
			new_fecha = add_months(new_fecha, ap.intervalo - 1)
		else:
			new_fecha = add_days(new_fecha, ap.intervalo - 1)

		saldo_abono = abonos

		if(a == 1):
			saldo_fact = fct_pend[i][1]
		else:
			if(saldo_fact == 0):
				i = i + 1
				saldo_fact = fct_pend[i][1]
		
		while saldo_abono > 0:
			abono_fact = 0

			if(saldo_abono > saldo_fact):
				abono_fact = saldo_abono - saldo_fact
			elif(saldo_abono == saldo_fact):
				abono_fact = saldo_fact
			else:
				abono_fact = saldo_abono

			ap.append("detalle", {
				"fecha": new_fecha,
				"factura": fct_pend[i][0],
				"monto": abono_fact,
				"abono": "Abono " + str(a),
				"pago": None
			})

			saldo_abono = saldo_abono - abono_fact

			if(saldo_abono == 0):
				break
		
		ap.append("cuotas", {
			"fecha_de_pago": new_fecha,
		    "cod_abono": "Abono " + str(a),
			"monto_abono": flt(abonos,2),
			"saldo_abono": flt(abonos,2),
			"aplicado": 0})
		
	ap.flags.ignore_permissions = True
	ap.save()

	return ap

@frappe.whitelist()
def update_Vencimiento():
	facturas = frappe.db.sql("""select name,fecha_de_vencimiento from `tabArreglo de Pago` where docstatus = 0""")
	fecha_Actual = today()
	for fac in facturas:
		# return fac[1]
		if str(fecha_Actual) == str(fac[1]):
			# return "Entra"
			frappe.db.set_value('Arreglo de Pago', fac[0], {
					'workflow_state': "Vencido",
					'docstatus':1
			})

	return "OK"