# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.api import aplicar_pago_batch
from erpnext.api import aplicar_AnticiposBatch
from frappe.utils import today

class PagoBatch(Document):
	pass

@frappe.whitelist()
def aplicar_pagos(id_batch):
	batch = frappe.get_doc('Pago Batch', id_batch)

	deudas=[] 
	pagos=[]
	metadata=dict()

	limite = len(batch.pagos_detalle) + 1

	frappe.msgprint(str(limite))

	if batch.tipo_pago == 'Pago Anticipos':
		tc = frappe.db.get_value('Currency Exchange',{'date':today()}, 'paralela')
		for a in range(0,len(batch.pagos_detalle)):
			deudas.append(dict(link_doctype = "Sales Invoice", link_name = batch.pagos_detalle[a].factura))
			
			if batch.pagos_detalle[a].monto_cordoba:
				pagos.append(dict(Factura = batch.pagos_detalle[a].factura, moneda = 'NIO', monto = batch.pagos_detalle[a].monto_cordoba))
			
			res = aplicar_AnticiposBatch(deudas,pagos,None, batch.pagos_detalle[a].regnumber,tc,batch.pagos_detalle[a].fecha,None,str('c'),True)
			
			# return res
			batchDetail = batch.get("pagos_detalle", {"name": batch.pagos_detalle[a].name})

			batchDetail[0].journal_entry =  res
			batchDetail[0].estado =  'Validado'

			deudas.clear()
			pagos.clear()
			batch.save(ignore_permissions=True)

	if batch.tipo_pago == 'Pago Batch':
		for a in range(0,len(batch.pagos_detalle)):
			if batch.pagos_detalle[a].journal_entry == None:
				deudas.append(dict(link_doctype = "Sales Invoice", link_name = batch.pagos_detalle[a].factura))

				if batch.pagos_detalle[a].monto_cordoba:
					pagos.append(dict(colector = batch.pagos_detalle[a].colector, moneda = 'NIO', monto = batch.pagos_detalle[a].monto_cordoba, tipo_de_pago = 'Cheque' if batch.pagos_detalle[a].cheque else 'Efectivo'))

				if batch.pagos_detalle[a].monto_dolar:
					pagos.append(dict(colector = batch.pagos_detalle[a].colector, moneda = 'USD', monto = batch.pagos_detalle[a].monto_dolar, tipo_de_pago = 'Cheque' if batch.pagos_detalle[a].cheque else 'Efectivo'))
				
				metadata = dict(colector =  batch.pagos_detalle[a].colector, recibo =  batch.pagos_detalle[a].no_recibo)
				
				res = aplicar_pago_batch(batch.pagos_detalle[a].regnumber, batch.pagos_detalle[a].fecha, batch.tasa_de_cambio,deudas, None,pagos, None, None, metadata, False,id_batch,batch.pagos_detalle[a].numero_de_cheque,batch.pagos_detalle[a].fecha_de_referencia,batch.pagos_detalle[a].nombre_del_banco,batch.pagos_detalle[a].centeno)
				
				batchDetail = batch.get("pagos_detalle", {"name": batch.pagos_detalle[a].name})

				batchDetail[0].journal_entry =  res
				batchDetail[0].estado =  'Validado'

				deudas.clear()
				pagos.clear()
				batch.save(ignore_permissions=True)

				frappe.msgprint(str(a))

			if a == limite:
				frappe.msgprint("Listo")
				break
			
	batch.aplicado = 1
	batch.save(ignore_permissions=True)
	batch.flags.ignore_submit_comment = True
	batch.submit()
	frappe.db.commit()
	return 'Ok'