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
from erpnext.crm.doctype.opportunity.opportunity import consultar_rol
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
		if self.averia_masiva and not frappe.db.exists("Issue Detalle",{"issue":self.name}):
			subordenes = frappe.get_doc({
				"doctype": "Issue Detalle",
				"issue" :self.name,
				"tipo_documento":'Orden de Servicio Interno',
				"estado":self.workflow_state,
				"tipo":self.tipo_de_orden,
				"problema":self.descripcion,
				"parent": self.averia_masiva,
				"parentfield":"ordenes",
				"parenttype": "AveriasMasivas",
			})
			subordenes.insert(ignore_permissions=True)
		
		if frappe.db.exists({"doctype": "Issue Detalle", "issue": self.name}):
			frappe.db.sql(""" update `tabIssue Detalle` set estado = %(estado)s, problema = %(descrip)s where issue = %(name)s ;""",{"estado":self.workflow_state,"descrip":self.descripcion,"name":self.name})

		idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
		try:
			idx = int(idx[0][0]) + 1
		except:
			idx = 1
		if self.workflow_state == "Finalizado":		
		

			if self.tecnico and len(self.materiales_detalles) > 0 :		
				pendientes = frappe.db.sql("""  select name,posting_date as Fecha,from_warehouse as Origen,tecnico, (case when per_transferred < 100 then 'Pendiente' else 'Listo' end) 'Transferido',
									(case when docstatus=0 then 'Borrador' when docstatus=1 then 'Validado' when docstatus=2 then 'Cancelado' end )
									Estado  from `vw_Stock_Entry_al_Transito`
									where per_transferred < 100  and docstatus = 1 and tecnico in (select tecnico from `tabOrden de Servicio Interno`where name=%(name)s union all
 									select tecnico from `tabTecnicos Service Order`where parent = %(name)s) """,{"name":self.name})

				series_rep = frappe.db.sql(""" SELECT serial_no, COUNT(*) as cantidad
												FROM  `tabMateriales detalles` 
												WHERE parent = %(name)s and serial_no is not null
												GROUP BY  serial_no
												HAVING COUNT(*) > 1; """,{"name":self.name})
				if series_rep:
					try:
						frappe.msgprint(frappe._('El mac {0} se repite {1} veces en la tabla. Elimine duplicados.').format(series_rep[0][0],series_rep[0][1]))
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						self.reload()
						return 
					except:
						pass
						

				if pendientes:
					for i in pendientes:
						frappe.msgprint(frappe._('El técnico {0} tiene la transferencia {1} pendiente por aceptar.').format(i[3], frappe.utils.get_link_to_form("Stock Entry", i[0])))
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						self.reload()
						return 

				almacenes_de_tecnico = [a[0] for a in frappe.db.sql("select almacen from `tabAlmacenes de Tecnico` where parent in (select tecnico from `tabOrden de Servicio Interno`where name=%(name)s ) or parent in (select tecnico from `tabTecnicos Service Order`where parent=%(name)s)",{"name":self.name})]					
				items_repetidos = frappe.db.sql(""" select bodega, material, count(cantidad) as total from `tabMateriales detalles` where parent = %(name)s group by bodega, material;""",{"name":self.name},as_dict=True)

				for row in self.materiales_detalles:
						
					if frappe.db.get_value("Item",row.material,"has_serial_no") and not row.serial_no:
						frappe.msgprint(f" fila # {row.idx}: {row.material} posee número de serie, favor escribirlo. ")
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						self.reload()
						return 
					cantidad_actual = frappe.db.sql(""" SELECT item_code, warehouse, qty_after_transaction, posting_date FROM `tabStock Ledger Entry` WHERE warehouse = %(wh)s
					 				and item_code = %(ic)s and is_cancelled = 0 ORDER BY posting_date DESC ,posting_time DESC , name DESC limit 1;""",{"wh":row.bodega,"ic":row.material})
					try:
						if cantidad_actual[0][2] < row.cantidad:
							frappe.msgprint(f"No se puede liquidar {row.material}. Cantidad existente en {row.bodega} a la fecha {cantidad_actual[0][3]} es de {cantidad_actual[0][2]} y usted ha colocado {row.cantidad}. Necesita {int(row.cantidad) - int(cantidad_actual[0][2])}. Verifique que no tenga transferencias pendientes de aceptar o solicite una transferencia de material.")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							self.reload()
							return 
						for item in items_repetidos:
							if row.material == item.material and row.bodega == item.bodega:
								if cantidad_actual[0][2] < item.total:
									frappe.msgprint(f"No se puede liquidar {row.material}. Cantidad existente en {row.bodega} a la fecha {cantidad_actual[0][3]} es de {cantidad_actual[0][2]} y usted ha colocado {item.total} en total. Necesita {int(item.total) - int(cantidad_actual[0][2])}. Verifique que no tenga transferencias pendientes de aceptar o solicite una transferencia de material.")
									frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
									frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
									frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
									self.reload()
									return 
					except:
						frappe.msgprint(f"No existe {row.material} en {row.bodega}. Verifique que no tenga transferencias pendientes de aceptar o solicite una transferencia de material.")
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						self.reload()
						return 
				

					if frappe.db.get_value("Serial No",row.serial_no,"customer"):
						frappe.msgprint(f"El equipo {row.serial_no} ya fue liquidado")
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						self.reload()
						return

					if row.serial_no:
						if row.cantidad != 1:
							frappe.msgprint(f"fila #{row.idx} equipo {row.serial_no} en tabla de materiales, el campo cantidad no puede ser diferente de 1.")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							self.reload()
							return 
						warehouse_equipo = frappe.db.get_value("Serial No", row.serial_no,"warehouse")
						if warehouse_equipo not in almacenes_de_tecnico:
							frappe.msgprint(f"{row.serial_no} no pertenece a ninguna bodega de los tecnicos seleccionados")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							self.reload()
							return 

				orden = frappe.db.sql(""" select name from `vw_expediciones_crm` where service_order= %(name)s and purpose<>'Material Receipt'; """, {"name":self.name})

				if orden:
					frappe.msgprint(f"Esta Orden ya fue liquidada. Favor comunicarse con IT")
					frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
					frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
					self.reload()
					return
				else:
					from erpnext.stock.doctype.stock_entry.stock_entry import expedicion_de_materiales
					try:
						expedicion_de_materiales(self.name,self.tecnico)
					except:
						# frappe.msgprint("Error en validar inventario. Las existencias en la bodega del técnico no son suficientes con las detalladas en estab orden")
						frappe.msgprint("Esta Orden no se puede validar, favor pedirle a OYM que valide los materiales")
						frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ATENDIDO')
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')	
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})				
						self.reload()
						return

			if self.tecnico and len(self.materiales_desinstalados) > 0:
				for row in self.materiales_desinstalados:
					if row.serial_no:
						if row.cantidad != 1:
							frappe.msgprint(f"fila #{row.idx} equipo {row.serial_no} en tabla de materiales desinstalados, el campo cantidad no puede ser diferente de 1.")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							self.reload()
							return 
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
			
			if self.averia_masiva:
				averia = frappe.get_doc("AveriasMasivas",self.averia_masiva)
				averia.update(
					{
						'workflow_state':'Finalizado',
					}
					)
				averia.save(ignore_permissions=True)
				frappe.db.commit()
				averia.submit()
	
		if self.workflow_state == "Abierto":
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ABIERTO')	

		if self.workflow_state == "Atendido":
			if not self.solucion:
				frappe.msgprint("Inserte una solución")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
				self.reload()
				return
			else:
				if self.averia_masiva:
					frappe.db.sql("update `tabAveriasMasivas` set solucion = %(sol)s where name = %(averia_m)s;",{"sol":self.solucion,"averia_m":self.averia_masiva})

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

			if len(self.materiales_detalles) > 0:
				
				pendientes = frappe.db.sql("""  select name,posting_date as Fecha,from_warehouse as Origen,tecnico, (case when per_transferred < 100 then 'Pendiente' else 'Listo' end) 'Transferido',
									(case when docstatus=0 then 'Borrador' when docstatus=1 then 'Validado' when docstatus=2 then 'Cancelado' end )
									Estado  from `vw_Stock_Entry_al_Transito`
									where per_transferred < 100  and docstatus = 1 and tecnico in (select tecnico from `tabOrden de Servicio Interno` where name=%(name)s union all
 									select tecnico from `tabTecnicos Service Order`where parent = %(name)s) """,{"name":self.name})


				if pendientes:
					for i in pendientes:
						frappe.msgprint(frappe._('El técnico {0} tiene la transferencia {1} pendiente por aceptar.').format(i[3], frappe.utils.get_link_to_form("Stock Entry", i[0])))
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					frappe.db.sql("""update `tabOrden de Servicio Interno` set workflow_state = 'Seguimiento' where name = %(name)s""",{"name":self.name})
					self.reload()
					return
				
				for row in self.materiales_detalles:
					if frappe.db.get_value("Item",row.material,"has_serial_no") and not row.serial_no:
						frappe.msgprint(f" fila # {row.idx}: {row.material} posee número de serie, favor escribirlo. ")
						frappe.db.sql("""update `tabOrden de Servicio Interno` set workflow_state = 'Seguimiento' where name = %(name)s""",{"name":self.name})
						self.reload()
						return
					if frappe.db.get_value("Serial No",row.serial_no,"customer"):
						frappe.msgprint(f"El equipo {row.serial_no} ya fue liquidado")
						frappe.db.sql("""update `tabOrden de Servicio Interno` set workflow_state = 'Seguimiento' where name = %(name)s""",{"name":self.name})

						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						self.reload()
						return
					cantidad_actual = frappe.db.sql(""" SELECT item_code, warehouse, qty_after_transaction, posting_date FROM `tabStock Ledger Entry` WHERE warehouse = %(wh)s
														and item_code = %(ic)s and is_cancelled = 0 ORDER BY posting_date DESC ,posting_time DESC , name DESC limit 1;""",{"wh":row.bodega,"ic":row.material})
					try:
						if cantidad_actual[0][2] < row.cantidad:
							frappe.msgprint(f"No se puede liquidar {row.material}. Cantidad existente en {row.bodega} a la fecha {cantidad_actual[0][3]} es de {cantidad_actual[0][2]} y usted ha colocado {row.cantidad}. Necesita {int(row.cantidad) - int(cantidad_actual[0][2])}. Verifique que no tenga transferencias pendientes de aceptar o solicite una transferencia de material.")
							frappe.db.sql("""update `tabOrden de Servicio Interno` set workflow_state = 'Seguimiento' where name = %(name)s""",{"name":self.name})

							self.reload()
							return 
					except:
						frappe.msgprint(f"No existe {row.material} en {row.bodega}. Verifique que no tenga transferencias pendientes de aceptar o solicite una transferencia de material.")
						frappe.db.sql("""update `tabOrden de Servicio Interno` set workflow_state = 'Seguimiento' where name = %(name)s""",{"name":self.name})

						self.reload()
						return 
				almacenes_de_tecnico = [a[0] for a in frappe.db.sql("select almacen from `tabAlmacenes de Tecnico` where parent in (select tecnico from `tabOrden de Servicio Interno`where name=%(name)s ) or parent in (select tecnico from `tabTecnicos Service Order`where parent=%(name)s)",{"name":self.name})]	
			
				for equipo in self.materiales_detalles:
					if equipo.serial_no:
						if equipo.cantidad != 1:
							frappe.msgprint(f"fila #{equipo.idx} equipo {equipo.serial_no} en tabla de materiales, el campo cantidad no puede ser diferente de 1.")
							frappe.db.sql("""update `tabOrden de Servicio Interno` set workflow_state = 'Seguimiento' where name = %(name)s""",{"name":self.name})
							self.reload()
							return 
						warehouse_equipo = frappe.db.get_value("Serial No",equipo.serial_no,"warehouse")
						if warehouse_equipo not in almacenes_de_tecnico:
							frappe.msgprint(f"{equipo.serial_no} no pertenece a ninguna bodega de los tecnicos seleccionados")
							frappe.db.sql("""update `tabOrden de Servicio Interno` set workflow_state = 'Seguimiento' where name = %(name)s""",{"name":self.name})
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

@frappe.whitelist()
def filtrar_almacen(name):

	almacen = []

	bodegas= frappe.db.sql("""select almacen from `tabAlmacenes de Tecnico` where parent in (select tecnico from `tabIssue` where name=%(name)s ) or parent in (select tecnico from `tabTecnicos Service Order`where parent=%(name)s);""",{"name":name})
	
	rol = consultar_rol()
		# return rol
	if 'Tecnico' in rol and 'System Manager' not in rol:
		bodegas= frappe.db.sql("""select almacen from `tabAlmacenes de Tecnico` where parent in (select name from `tabTecnico` where usuario_reporte = %(usuario)s);""",{"usuario":frappe.session.user})

	for bodega in bodegas:
		
		almacen.append(bodega[0])
			
	return almacen

@frappe.whitelist()
def filtrar_almacen(name):
	almacen = []
	rol = consultar_rol()
		# return rol
	if 'Tecnico' in rol:
		bodegas= frappe.db.sql("""select almacen from `tabAlmacenes de Tecnico` where parent in (select name from `tabTecnico` where usuario_reporte = %(usuario)s);""",{"usuario":frappe.session.user})

		for bodega in bodegas:
			
			almacen.append(bodega[0])
				
		return almacen	
	else: 
		return [almacen[0] for almacen in  frappe.db.sql("""select almacen from `tabAlmacenes de Tecnico` where parent in (select tecnico from `tabOrden de Servicio Interno` where name=%(name)s ) or parent in (select tecnico from `tabTecnicos Service Order`where parent=%(name)s);""",{"name":name})]