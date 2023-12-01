# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_files_path
from frappe.utils import flt, cint, today
from frappe import _, msgprint, throw
import os
from frappe.model.document import Document

class CargosAutomaticos(Document):
	def on_update(self):
		if self.no_recibo:
			self.agregar_recibo()
	

	def agregar_recibo(self):
		c = 1
		for r in self.get("detalle"):
			r.no_recibo = str(c)+'-'+self.no_recibo
			c = c + 1
			# r.db_update()


@frappe.whitelist()
def Mostrar_cargo_aplicar(name):
	# frappe.msgprint(name)
	doc = frappe.get_doc('Cargos Automaticos',name)
	rep = frappe.db.sql(
			"""call cargos_automaticos;""",as_dict=True,)

	for fac in rep:
		regnumber = frappe.db.get_value('Customer', {'name': ['like', '%'+fac.Regnumber]}, 'name')

		factP = frappe.db.sql(
					"""select name,customer,
				(select estado_cliente from `tabCustomer` where name = customer) as estado_cliente,
				currency,tc_facturas,
				case
				when debit_to = "Cuentas por Cobrar Moneda Extranjera - IBWNI - NI" then round((tc_facturas * outstanding_amount),2)
				else round(outstanding_amount,2)
				end as Monto_Cordobas
				,round(outstanding_amount,2) as outstanding_amount from `tabSales Invoice` where customer  =  %(name)s and docstatus =1 and outstanding_amount > 0.01;"""
				# ,round(outstanding_amount,2) as outstanding_amount from `tabSales Invoice` where customer in  %(name)s;"""
		,{'name': regnumber},as_dict=1)

		suma = 0.00
		detalle = []
		
		for sum in factP:
			suma = suma + sum.Monto_Cordobas

		# return fac.MontoCordoba,suma
			
		# if flt(fac.MontoCordoba,2) == flt(suma,2):
		for f in factP:
			detalle = dict(fecha = today(), regnumber = f.customer,no_recibo = '',monto_cordoba = f.Monto_Cordobas,monto_dolar = 0,cheque = None,no_cheque = None,colector = 'Cargos Automaticos',factura = f.name,numero_de_cheque = None,fecha_de_referencia = None,nombre_del_banco = None)
			# detalle = dict(regnumber = f.customer)

			doc.append("detalle",detalle)
				
	doc.save()
	return 'OK'


@frappe.whitelist()
def Descargar_ArchivoBAC(name):
	# frappe.msgprint(name)
	doc = frappe.get_doc('Cargos Automaticos',name)
	rep = frappe.db.sql(
			"""call cargos_automaticos;""",as_dict=True,)

	fecha = today()
	# return factP
	f = open( './ibwni-crm.ibw.com/public/files/BAC'+fecha+".csv","w")
	# f.write(f"Number;Regnumber;Contador;CreditCardNumber;FechaExpiracion;MontoCordoba;fechaAplicacion;Email;Nombre\n")
	

	# for r in rep:
	for r in range(len(rep)):
		for facAprobado in doc.get("detalle"):
			if facAprobado.regnumber == frappe.db.get_value('Customer', {'name': ['like', '%'+rep[r]['Regnumber']]}, 'name'):
				if r == len(rep)-1:
					f.write(f"'{rep[r]['Number']}','{rep[r]['Regnumber']}','{int(rep[r]['Contador'])}','{rep[r]['CreditCardNumber']}','{rep[r]['FechaExpiracion']}','{rep[r]['MontoCordoba']}','{rep[r]['fechaAplicacion']}','{rep[r]['Email']}','{rep[r]['Nombre']}'")
					break
				f.write(f"'{rep[r]['Number']}','{rep[r]['Regnumber']}','{int(rep[r]['Contador'])}','{rep[r]['CreditCardNumber']}','{rep[r]['FechaExpiracion']}','{rep[r]['MontoCordoba']}','{rep[r]['fechaAplicacion']}','{rep[r]['Email']}','{rep[r]['Nombre']}'\n")
	
	f.close()   
	file_path  = "ibwni-crm.ibw.com/public/files/BAC"+fecha+".csv"
	path = os.path.join(get_files_path(), os.path.basename(file_path))
	with open(path, "rb") as fileobj:
		filedata = fileobj.read()
	frappe.local.response.filename = os.path.basename(file_path)
	frappe.local.response.filecontent = filedata
	frappe.local.response.type = "download"

	return filedata

@frappe.whitelist()
def Redireccionar_pago(name):
	doc = frappe.get_doc('Cargos Automaticos',name)
	docpP = frappe.new_doc('Pago Batch')
	if doc.detalle:
		# docpP = frappe.new_doc('Pago Batch')
		docpP.fecha_de_carga = doc.fecha
		docpP.tipo_pago = 'Pago Batch'
		
		factP = frappe.db.sql(
					"""select regnumber,no_recibo,monto_cordoba,colector,factura from `tabDetalle Cargos` where parent = %(name)s and regnumber not in (select regnumber from `tabDetalle Rechazados` where parent = %(name)s);"""
				# ,round(outstanding_amount,2) as outstanding_amount from `tabSales Invoice` where customer in  %(name)s;"""
		,{'name': name},as_dict=1)

		for c in factP:
				detalle = dict(fecha = doc.fecha, regnumber = c.regnumber,no_recibo = c.no_recibo,monto_cordoba = c.monto_cordoba,monto_dolar = 0,cheque = None,no_cheque = None,colector = c.colector,factura = c.factura,numero_de_cheque = None,fecha_de_referencia = None,nombre_del_banco = None)		
				docpP.append("pagos_detalle",detalle)
				doc.save()
		
		docpP.insert()
		doc.save()
			
	frappe.msgprint(_("Se ha creado el Batch: {0}").format(frappe.utils.get_link_to_form("Pago Batch", docpP.name)))