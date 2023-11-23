# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today
from frappe import _, msgprint, throw
from erpnext.api import aplicar_pago_batch
from erpnext.api import aplicar_AnticiposBatch

class Recaudocolectores(Document):
	def validate(self):
		if self.docstatus == 1:
			self.TrasladarBatch()


	def TrasladarBatch(self):
		# doc = frappe.get_doc('Cargos Automaticos',name)
		if self.get('recaudo'):
			docpP = frappe.new_doc('Pago Batch')
		
			# selfpP = frappe.new_doc('Pago Batch')
			docpP.fecha_de_carga = self.fecha
			docpP.tipo_pago = 'Pago Batch'
			
			for c in self.get('recaudo'):
				detalle = dict(fecha = c.fecha, regnumber = c.regnumber,no_recibo = c.no_recibo,monto_cordoba = c.monto_cordoba,monto_dolar = c.monto_dolar,colector = c.colector,factura = c.factura,cheque = c.cheque,numero_de_cheque = c.numero_de_cheque,fecha_de_referencia = c.fecha_de_referencia,nombre_del_banco = c.nombre_del_banco)
				
				docpP.append("pagos_detalle",detalle)
				# docpP.save()	
				
			
			docpP.insert()
			docpP.save()
		
			frappe.msgprint(_("Se ha creado el Batch: {0}").format(frappe.utils.get_link_to_form("Pago Batch", docpP.name)))

@frappe.whitelist()
def agregar_pago(deudas=None,pagos=None,Recibo=None,NumCheque=None,ChequeChek=None,Colector=None,NameBatch=None,regnumber=None,factura=None,tc=None,fecha=None,montoNIO=None,montoUSD = None,dc='c',_ui_=True,Num_cheque = None,nombre_banco=None,talonario=None,talonarioNum=None):
	# from erpnext.accounts.party import get_party_account, get_party_account_currency

	doc =  frappe.get_doc('Recaudo colectores',NameBatch)

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
		# 'fecha_de_referencia':Fecha_Cheque,
		'nombre_del_banco':nombre_banco
	}
	
	modo_de_pago = {}

	if not doc.modo_de_pagos:
		if ChequeChek  == '1':
			modo_de_pago = {
				'modo_de_pago': 'Cheque',
				'nio':montoNIO,
				'usd':montoUSD
			}
		else:
			modo_de_pago = {
				'modo_de_pago':'Efectivo',
				'nio':montoNIO,
				'usd':montoUSD
			}

	else:
		modo_pagos_Cheque = doc.get("modo_de_pagos",{'modo_de_pago':'Cheque'})
		modo_pagos_Efectivo = doc.get("modo_de_pagos",{'modo_de_pago':'Efectivo'})


		if ChequeChek  == '1':
			if modo_pagos_Cheque:
				modo_pagos_Cheque[0].nio = flt(montoNIO,2) + modo_pagos_Cheque[0].nio
				modo_pagos_Cheque[0].usd = flt(montoUSD,2) + modo_pagos_Cheque[0].usd
			else:
				modo_de_pago = {
						'modo_de_pago':'Cheque',
						'nio':montoNIO,
						'usd':montoUSD
				}
		else:
			if modo_pagos_Efectivo:
				modo_pagos_Efectivo[0].nio = flt(montoNIO,2) + modo_pagos_Efectivo[0].nio
				modo_pagos_Efectivo[0].usd = flt(montoUSD,2) + modo_pagos_Efectivo[0].usd
			else:
				modo_de_pago = {
					'modo_de_pago':'Efectivo',
					'nio':montoNIO,
					'usd':montoUSD
				}

	if modo_de_pago:
		doc.append("modo_de_pagos", modo_de_pago)
	
	doc.append("recaudo", detalles)
	if talonario:
		nuevo = int(talonarioNum) + 1
		frappe.db.set_value('Talonario Colectores', talonario, 'numero_de_recibo_actual', nuevo)
	doc.flags.ignore_permissions = True
	doc.save()
	frappe.db.commit()
	return 'Ok'

@frappe.whitelist()
def consultar_rol():
	""" consultar roles por usuario """
	return [r[0] for r in frappe.db.sql(""" select role from  `tabHas Role` where parent = %(parent)s""", {"parent":frappe.session.user})]

@frappe.whitelist()
def Validar_FActuras_Batch(idbatch):
# bat = frappe.get_value('Pago Batch',idbatch,)
	# description = frappe.db.get_value('Pago Batch',idbatch,'pagos_detalle')
	doc = frappe.get_doc('Recaudo colectores',idbatch)
	# values = {'name':idbatch}
	# data = frappe.db.sql("""select name,docstatus,status from `tabSales Invoice` where name = %(name)s """, {'name': idbatch}, as_dict=0)

	message = []
	for ba in doc.get('recaudo'):
		# values = {'name': ba.factura}
		if ba.journal_entry == None:

			data = frappe.db.sql("""select name,docstatus,status,customer from `tabSales Invoice` where name = %(name)s """, {'name': ba.factura}, as_dict=0)

			if data:
					# Valida si la factua le pertenece al cliente
					if data[0][3] == ba.regnumber:
						# factAnteriorPendiente = frappe.db.sql("""select name from `tabSales Invoice` where customer = %(name)s  and docstatus = 1 order  by posting_date asc limit 1; """, {'name': data[0][3]}, as_dict=0)
						factAnteriorPendiente = frappe.db.sql("""select name, (TO_DAYS(CURRENT_TIMESTAMP()) - TO_DAYS(`posting_date`)) as dias from `tabSales Invoice` where customer = %(name)s  and docstatus = 1 and outstanding_amount > 1 and (TO_DAYS(CURRENT_TIMESTAMP()) - TO_DAYS(`posting_date`))>30 order by posting_date asc limit 1; """, {'name': data[0][3]}, as_dict=0)
						
						if factAnteriorPendiente:
							if factAnteriorPendiente != ba.factura:
								message.append(_("Tiene facturas anteriores del cliente: {0} de la factura: {1}").format(ba.regnumber,factAnteriorPendiente[0][0]))
						
						# docstatus, ver en los casos que esten en 0 Borrador
						if data[0][1] == 1:
							#status
							if data[0][2] != 'Paid':
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

@frappe.whitelist()
def montos_facturas(name):
	montoNIO,montoUSD = 0,0

	# comprobarFact = frappe.get_value('Detalle Recaudo',{'factura':name,'docstatus':0},name)

	comprobarFact = frappe.db.sql(
			"""select factura,parent from `tabDetalle Recaudo` where factura =  %(name)s and docstatus= 0;""",{'name': name})
	
	if comprobarFact:
		frappe.msgprint(_("Tiene en otro Recaudo rigistrado la misma factura en: {0}").format(comprobarFact[0][1]))
		# return 'Tiene en otro Recaudo rigistrado la misma factura'
	else:

		if name:
			doc = frappe.get_doc('Sales Invoice',name)

			MontoP = doc.outstanding_amount
			tc = doc.tc_facturas
			cuenta = doc.debit_to

			if cuenta == 'Cuentas por Cobrar Moneda Extranjera - IBWNI - NI':
				montoNIO = flt(MontoP,2) * flt(tc,4)
				montoUSD = flt(MontoP,2)
			
			if cuenta == 'DEUDORES VARIOS - NI':
				montoNIO = flt(MontoP,2)
				# tcday = frappe.get_value('Currency Exchange',{'date':today()},'paralela')
				montoUSD = flt(MontoP,2) / flt(tc,4)
	
	return montoNIO,montoUSD

@frappe.whitelist()
def eliminar_monto(name):
	nio,usd,nioc,usdc = 0,0,0,0
	doc = frappe.get_doc('Recaudo colectores',name)

	items = doc.get("modo_de_pagos")

	items.clear()

	if doc.get("recaudo"):
		cheque,efectivo = False,False
		for r in doc.get("recaudo"):	
			if r.cheque:
				
				cheque = True
				if r.monto_cordoba:
					nioc = nioc + r.monto_cordoba
				
				if r.monto_dolar:
					usdc = usdc + r.monto_dolar

			else:
				efectivo = True
				if r.monto_cordoba:
					nio = nio + r.monto_cordoba
				
				if r.monto_dolar:
					usd = usd + r.monto_dolar
		
		if cheque:
			modo_de_pago = {
				'modo_de_pago': 'Cheque',
				'nio':nioc,
				'usd':usdc
			}
			doc.append("modo_de_pagos", modo_de_pago)
		
		if efectivo:
			modo_de_pago = {
				'modo_de_pago':'Efectivo',
				'nio':nio,
				'usd':usd
			}
			doc.append("modo_de_pagos", modo_de_pago)
		
		doc.save()
	
	doc.save()
	return doc

@frappe.whitelist()
def numero_notalario():
	local_user = frappe.session.user
	name = frappe.db.get_value('Colectores', filters={'email':local_user})
	colector = frappe.db.get_value('Talonario Colectores', filters={'colector':name})
	Talonario = frappe.get_doc('Talonario Colectores',colector)
	
	return Talonario