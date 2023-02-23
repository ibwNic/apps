# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
import random
import string
from frappe.utils import now, today
import frappe
from frappe import _
from frappe.model.document import Document
import datetime
from frappe.utils import flt, get_fullname, format_time, formatdate, getdate, nowdate,nowtime, date_diff, time_diff_in_seconds
from frappe.utils.data import (
	add_days,
	add_months,
	add_years,
	add_to_date,
	cint,
	cstr,
	date_diff,
	flt,
	get_last_day,
	getdate,
	nowdate,
)

class OrdendeServicioInterno(Document):
	def on_update(self):
		idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
		try:
			idx = int(idx[0][0]) + 1
		except:
			idx = 1
		if self.workflow_state == "Finalizado":
			if self.estado_anterior == 'ATENDIDO':
				date = now()
				frappe.db.sql(""" update `tabOrden de Servicio Interno` set fecha_finalizado = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				bitacora_fin = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden FINALIZADA",
					"fecha_transaccion": date,
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_atendido),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_de_orden",
					"parenttype": "Orden de Servicio Interno",
					"idx":idx
					})
				bitacora_fin.insert(ignore_permissions=True)
			
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'FINALIZADO')
			frappe.db.set_value(self.doctype, self.name, 'docstatus', 1)
	
		if self.workflow_state == "Abierto":
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ABIERTO')	

		if self.workflow_state == "Atendido":
			if not self.solucion:
				frappe.msgprint("Inserte una solución")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
				self.reload()
				return
			if not self.tecnico:
				frappe.msgprint("Agregue un técnico a la orden")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
				self.reload()
				return
			if self.tipo_de_orden == 'INSTALACIÓN DE NODO':
				if not self.nodo:
					frappe.msgprint("Agregue un nodo")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return
			if self.estado_anterior == 'SEGUIMIENTO':			
				date = now()
				frappe.db.sql(""" update `tabOrden de Servicio Interno` set fecha_atendido = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				bitacora_atend = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado SEGUIMIENTO a estado ATENDIDO",
					"fecha_transaccion": date,
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_seguimiento),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_de_orden",
					"parenttype": "Orden de Servicio Interno",
					"idx":idx
					})
				bitacora_atend.insert(ignore_permissions=True)
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ATENDIDO')			

		if self.workflow_state == "Seguimiento":
			if not self.gestion:
				frappe.msgprint("El campo subtipo no puede estar vacío")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
				self.reload()
				return
			if self.estado_anterior == 'ABIERTO':
				if not self.fecha_inicio:
					frappe.msgprint("inserte fecha de inicio")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
					self.reload()
					return
				date = now()
				frappe.db.sql(""" update `tabOrden de Servicio Interno` set fecha_seguimiento = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				
				if time_diff_in_seconds(date, self.fecha_inicio) < 0:
					frappe.msgprint("Error en fecha y hora insertada")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
					self.reload()
					return
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden ABIERTA",
					"fecha_transaccion": self.fecha_inicio,
					"usuario":frappe.session.user,
					"tiempo_transcurrido":0.00,
					"fecha_definida_por_usuario": self.fecha_inicio,
					"parent": self.name,
					"parentfield":"bitacora_de_orden",
					"parenttype": "Orden de Servicio Interno",
					"idx":idx
					})
				bitacora_orden.insert(ignore_permissions=True)
				idx += 1
				bitacora_seg = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado ABIERTO a estado SEGUIMIENTO",
					"fecha_transaccion": date,
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_inicio),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_de_orden",
					"parenttype": "Orden de Servicio Interno",
					"idx":idx
					})
				bitacora_seg.insert(ignore_permissions=True)

			if self.estado_anterior == 'PENDIENTE':
				date = now()
				frappe.db.sql(""" update `tabOrden de Servicio Interno` set fecha_seguimiento = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado PENDIENTE a estado SEGUIMIENTO",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_pendiente),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_de_orden",
					"parenttype": "Orden de Servicio Interno",
					"idx":idx
					})
				bitacora_orden.insert(ignore_permissions=True)	
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'SEGUIMIENTO')	

		if self.workflow_state == "Pending":
			if self.estado_anterior == 'ATENDIDO':
				date = now()
				frappe.db.sql(""" update `tabOrden de Servicio Interno` set fecha_pendiente = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				bitacora_orden = frappe.get_doc({
						"doctype": "Bitacora Orden",
						"detalle":"Orden cambió de estado ATENDIDO a estado PENDIENTE",
						"fecha_transaccion": date,
						"usuario":frappe.session.user,
						"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_atendido),
						"fecha_definida_por_usuario": date,
						"parent": self.name,
						"parentfield":"bitacora_de_orden",
						"parenttype": "Orden de Servicio Interno",
						"idx":idx
						})
				bitacora_orden.insert(ignore_permissions=True)		
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'PENDIENTE')

		total_abierto = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado ABIERTO a estado SEGUIMIENTO' and parent = %(name)s; """, {"name":self.name})[0][0])
		total_seguimiento = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado SEGUIMIENTO a estado ATENDIDO' and parent = %(name)s; """, {"name":self.name})[0][0])
		total_atendido = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle in ('Orden cambió de estado ATENDIDO a estado PENDIENTE','Orden FINALIZADA') and parent = %(name)s; """, {"name":self.name})[0][0])
		total_pendiente = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado PENDIENTE a estado SEGUIMIENTO' and parent = %(name)s; """, {"name":self.name})[0][0])
		frappe.db.sql(""" update `tabOrden de Servicio Interno` set total_abierto = %(total_abierto)s, total_seguimiento = %(total_seguimiento)s, total_atendido = %(total_atendido)s, total_pendiente = %(total_pendiente)s where name = %(name)s""", {"total_abierto":total_abierto, "total_seguimiento":total_seguimiento, "total_atendido":total_atendido, "total_pendiente":total_pendiente,"name":self.name})	
		self.reload()
	#def on_submit(self):
