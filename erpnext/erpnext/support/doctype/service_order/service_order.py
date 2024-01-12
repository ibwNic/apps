# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
#modificado 23/01/23
import frappe
import json
import random
import string
from frappe.utils import now, today,datetime
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.crm.doctype.opportunity.opportunity import consultar_rol
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
from erpnext.aprovisionamiento_api import eliminarAprovisionador, cambiarVelocidadAprovisionador, activarAprovisionador, suspenderAprovisionador
from frappe.custom.doctype.aprovisionamiento_iptv.aprovisionamiento_iptv import Deshabilitar_Cliente,Habilitar_Cliente
import erpnext.crm.doctype.envio_sms


class ServiceOrder(Document):

	def on_update(self):
		idx_b = 0
		if self.plan_de_subscripcion:
			idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":self.plan_de_subscripcion})	
			idx_b = idx_b[0][0]
		if self.workflow_state=="Cancelado":
			if not self.motivo_cancelacion:
				frappe.msgprint(f"Debe Seleccionar un motivo de Cancelacion")
				# frappe.msgprint(self.estado_anterior.capitalize())
				# frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
				if self.estado_anterior.capitalize()=='Pendiente':
					estado="Pending"
				else:
					estado=self.estado_anterior.capitalize()

				frappe.db.sql("update `tabService Order` set docstatus = 0,workflow_state=%(estado)s where name = %(name)s;",{"name":self.name ,"estado":estado})

				# frappe.db.set_value(self.doctype, self.name, 'workflow_state', self.estado_anterior.capitalize()) 
				self.reload()
				return 	



		if self.estado != self.workflow_state:
			frappe.db.sql("""update `tabService Order` set estado = workflow_state where name = %(name)s;""",{"name":self.name})
		if frappe.db.exists({"doctype": "Issue Detalle", "issue": self.name}):
	
			frappe.db.sql(""" update `tabIssue Detalle` set estado = %(estado)s, problema = %(descrip)s where issue = %(name)s ;""",{"estado":self.workflow_state,"descrip":self.descripcion,"name":self.name})
		if self.tipo == 'Issue' and not self.direccion:
			direccion = frappe.db.get_value("Issue",self.tercero,"address_line1")
			frappe.db.set_value("Service Order",self.name,"direccion",direccion)
			self.reload()
		if self.tipo == 'Issue' and not self.descripcion:
			descripcion = frappe.db.get_value("Issue",self.tercero,"descripcion")
			frappe.db.set_value("Service Order",self.name,"descripcion",descripcion)
			self.reload()
		
		
		if self.workflow_state == "Finalizado":
			
			if self.tipo_de_origen == 'Gestion' and frappe.db.get_value("Gestion",self.nombre_de_origen,"workflow_state") == 'Atendido':
				frappe.db.set_value("Gestion",{"name":self.nombre_de_origen},"facturado",1)
			try:
				solucion = self.solucion
			except:
				solucion = None
			if not solucion:
				frappe.msgprint("Inserte una solución")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
				frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
				self.reload()
				return
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			date = ''
			if self.estado_anterior == 'ATENDIDO':
				if self.venta_en_caliente == 0:
					date = now()
					frappe.db.sql(""" update `tabService Order` set fecha_finalizado = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				else:
					if not self.fecha_finalizado:
						frappe.msgprint("inserte fecha de finalización")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						self.reload()
						return
					else:
						date = self.fecha_finalizado
				if time_diff_in_seconds(date,self.fecha_atendido) < 0:
					frappe.msgprint("Error en fecha y hora insertada")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
					self.reload()
					return

			if self.tipo_de_orden not in ('DESINSTALACION','REACTIVACION','SUSPENSION','DESINSTALACION RCPE') and self.tecnico and (len(self.productos) > 0 or len(self.equipo_orden_servicio) > 0):
				almacenes_de_tecnico = [a[0] for a in frappe.db.sql("select almacen from `tabAlmacenes de Tecnico` where parent in (select tecnico from `tabService Order`where name=%(name)s ) or parent in (select tecnico from `tabTecnicos Service Order`where parent=%(name)s)",{"name":self.name})]	
				items_repetidos = frappe.db.sql(""" select bodega, material, count(cantidad) as total from `tabMateriales detalles` where parent = %(name)s group by bodega, material;""",{"name":self.name},as_dict=True)


				if self.tipo_de_orden == "INSTALACION":
					equipos = frappe.db.sql(""" select count(*) from `tabEquipo_Orden_Servicio` where parent = %(parent)s """, {"parent": self.name})
					try:
						equipos = int(equipos[0][0])
					except:
						equipos = 0
					if self.portafolio in ['GPON','GPON-CORPORATIVO','GPON-INT-PYME','GPON-INT-RESIDENCIAL','HFC', 'HFC 3.0', 'IMOVIL', 'INET', 'Wimax','IPTV']:
							
						if equipos < 1 and frappe.db.get_value("Subscription Plan",frappe.db.get_value("Subscription Plan Detail",self.plan_de_subscripcion,"plan"),"item")  not in ('ITV HFC SIN VELOCIDAD','TV HFC SIN VELOCIDAD'):
							frappe.msgprint(f"El portafolio {self.portafolio} debe tener al menos un Equipo")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							self.reload()
							return
					elif self.portafolio in ['LTE', 'LTE Productos']:
						sim = frappe.db.sql(""" select count(*) from `tabSerial No` where item_code = 'SIM Card' and name in (select serial_no from `tabEquipo_Orden_Servicio` where parent = %(parent)s ) """, {"parent": self.name})
						try:
							sim = int(sim[0][0])
						except:
							sim = 0
						if equipos < 2 or sim < 1:
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							self.reload()
							return

				for row in self.productos:	
					if frappe.db.get_value("Item",row.material,"has_serial_no") and not row.serial_no:
						frappe.msgprint(f" fila # {row.idx}: {row.material} posee número de serie, favor escribirlo. ")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						self.reload()
						return
					if frappe.db.get_value("Serial No",row.serial_no,"customer"):
						frappe.msgprint(f"El equipo {row.serial_no} ya fue liquidado")
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
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
							frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
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
						frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						self.reload()
						return

				if self.tipo_de_orden != "TRASLADO":
					for row in self.equipo_orden_servicio:	
						if frappe.db.get_value("Serial No",row.serial_no,"customer"):
							frappe.msgprint(f"El equipo {row.serial_no} ya fue liquidado")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							
							self.reload()
							return	

					for equipo in self.equipo_orden_servicio:
						if equipo.serial_no:
							warehouse_equipo = frappe.db.get_value("Serial No",equipo.serial_no,"warehouse")
							if warehouse_equipo not in almacenes_de_tecnico:
								frappe.msgprint(f"{equipo.serial_no} no pertenece a ninguna bodega de los tecnicos seleccionados")
								frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
								frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
								frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
								frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
								self.reload()
								return 
				for equipo in self.productos:
					if equipo.serial_no:
						if equipo.cantidad != 1:
							frappe.msgprint(f"fila #{equipo.idx} equipo {equipo.serial_no} en tabla de materiales, el campo cantidad no puede ser diferente de 1.")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})			
							self.reload()
							return 
						warehouse_equipo = frappe.db.get_value("Serial No",equipo.serial_no,"warehouse")
						if warehouse_equipo not in almacenes_de_tecnico:
							frappe.msgprint(f"{equipo.serial_no} no pertenece a ninguna bodega de los tecnicos seleccionados")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})			
							self.reload()
							return 

						if len(self.equipo_orden_servicio) > 0:
							for equipo2 in self.equipo_orden_servicio:
								if equipo.serial_no == equipo2.serial_no:
									frappe.msgprint(f"{equipo.serial_no} aparece en la tabla de equipos y productos. Favor dejar el equipo solo en la tabla de equipos.")
									frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
									frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
									frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
									frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})			
									self.reload()
									return

				orden = frappe.db.sql(""" select name from `vw_expediciones_crm` where service_order= %(name)s and purpose<>'Material Receipt'; """, {"name":self.name})

				serie_rep = frappe.db.sql("""  SELECT serial_no, COUNT(serial_no) AS contador FROM `tabMateriales detalles` where parent = %(parent)s GROUP BY serial_no HAVING contador > 1; """,{"parent":self.name})
					
				if serie_rep:	
					frappe.msgprint(f" posee número de serie {serie_rep[0][0]} repetido en tabla de materiales, favor eliminar duplicados. ")
					frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
					frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
					frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})		
					self.reload()
					return

				if orden:
					frappe.msgprint(f"Esta Orden ya fue liquidada. Favor comunicarse con IT")
					frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
					frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
					frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})		
					self.reload()
					return
				else:
					from erpnext.stock.doctype.stock_entry.stock_entry import expedicion_de_materiales
				
					try:
						expedicion_de_materiales(self.name,self.tecnico)

					except:
						# frappe.msgprint("Error en validar inventario. Las existencias en la bodega del técnico no son suficientes con las detalladas en estab orden")
						frappe.msgprint("Error en validar inventario.")
						frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ATENDIDO')
						frappe.db.set_value(self.doctype, self.name, 'finalizado_por', None)
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')	
						frappe.db.sql("update `tabMateriales detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
						frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})										
						self.reload()
						return
			if  'DESINSTALACION' in self.tipo_de_orden  and self.tecnico and (len(self.materiales_usados) > 0 or len(self.equipo_orden_servicio) > 0):
				for equipo in self.materiales_usados:
					if equipo.serial_no:
						if equipo.cantidad !=1:
							frappe.msgprint(f"fila #{equipo.idx} equipo {equipo.serial_no} en tabla de materiales desinstalados, el campo cantidad no puede ser diferente de 1.")
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
							frappe.db.sql("update `tabMateriales Usados Detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
							frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})			
							self.reload()
							return
						if len(self.equipo_orden_servicio) > 0:
							for equipo2 in self.equipo_orden_servicio:
								if equipo.serial_no == equipo2.serial_no:
									frappe.msgprint(f"{equipo.serial_no} aparece en la tabla de equipos y materiales usados. Favor dejar el equipo solo en la tabla de equipos.")
									frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
									frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
									frappe.db.sql("update `tabMateriales Usados Detalles` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})
									frappe.db.sql("update `tabEquipo_Orden_Servicio` set docstatus = 0 where parent = %(parent)s;",{"parent":self.name})			
									self.reload()
									return
			# 	from erpnext.stock.doctype.stock_entry.stock_entry import expedicion_de_materiales
			
			# 	try:
			# 		recepcion_de_materiales(self.name,self.tecnico)
			# 	except:
			# 		frappe.msgprint("Los materiales desinstalados no pudieron ingresar a la bodega del tecnico, favor hacerlo utilizando el método 'Obtener Equipos de Desinstalacion desde Tecnico' en el modulo Entradas de Inventario")
				

			date = now()			
			if not self.venta_en_caliente:
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden FINALIZADA",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_atendido),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_orden",
					"parenttype": "Service Order",
					"idx":idx
					})
				bitacora_orden.insert(ignore_permissions=True)
			else:
				bitacora_abierta = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden ABIERTA",
					"fecha_transaccion": self.fecha_solicitud,
					"usuario":frappe.session.user,
					"tiempo_transcurrido":0.00,
					"fecha_definida_por_usuario": self.fecha_solicitud,
					"parent": self.name,
					"parentfield":"bitacora_orden",
					"parenttype": "Service Order",
					"idx":idx
					})
				bitacora_abierta.insert(ignore_permissions=True)
				idx += 1
				bitacora_seg = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado ABIERTO a estado SEGUIMIENTO",
					"fecha_transaccion": self.fecha_seguimiento,
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(self.fecha_seguimiento,self.fecha_solicitud),
					"fecha_definida_por_usuario": self.fecha_seguimiento,
					"parent": self.name,
					"parentfield":"bitacora_orden",
					"parenttype": "Service Order",
					"idx":idx
					})
				bitacora_seg.insert(ignore_permissions=True)
				idx += 1
				bitacora_atend = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado SEGUIMIENTO a estado ATENDIDO",
					"fecha_transaccion": self.fecha_atendido,
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(self.fecha_atendido,self.fecha_seguimiento),
					"fecha_definida_por_usuario": self.fecha_atendido,
					"parent": self.name,
					"parentfield":"bitacora_orden",
					"parenttype": "Service Order",
					"idx":idx
					})
				bitacora_atend.insert(ignore_permissions=True)
				idx += 1
				bitacora_fin = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden FINALIZADA",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(now(),self.fecha_atendido),
					"fecha_definida_por_usuario": now(),
					"parent": self.name,
					"parentfield":"bitacora_orden",
					"parenttype": "Service Order",
					"idx":idx
					})
				bitacora_fin.insert(ignore_permissions=True)
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'FINALIZADO')
			frappe.db.set_value(self.doctype, self.name, 'finalizado_por', frappe.session.user)
			frappe.db.set_value(self.doctype, self.name, 'docstatus', 1)
				
			if self.tipo_de_orden == "SITE SURVEY" and (self.factible == 'El proyecto es factible' or self.factible == 'El proyecto es factible con tercero') and self.opportunity_prospect:
				od = frappe.get_doc({
					'doctype': "Service Order",
					'tipo_de_orden': "PRESUPUESTO",
					'workflow_state': "Abierto",
					'tipo_de_origen': self.tipo_de_origen,
					'nombre_de_origen': self.nombre_de_origen,
					'descripcion': self.descripcion,
					'tipo': self.tipo,
					'tercero': self.tercero,
					'nombre': self.nombre,
					'direccion_de_instalacion': self.direccion_de_instalacion,
					'venta_en_caliente':self.venta_en_caliente,
					'portafolio': self.portafolio,
					'departamento': self.departamento,
					'municipio': self.municipio,
					'barrio': self.barrio,
					'direccion': self.direccion,
					'currency':'USD',
					'site_order':self.name,
					'item_opportunity':self.item_opportunity,
					'proveedor_section':self.proveedor_section,
					'proveedor': self.proveedor,
					'opportunity_prospect': self.opportunity_prospect,
					'site_order': self.name,
					'latitud': self.latitud,
					'longitud': self.longitud,
					'nodo':self.nodo,
					'proveedor':self.proveedor,
					'tipo_de_servicio': self.tipo_de_servicio,
					'tipo_cliente':self.tipo_cliente,
					'informacion_de_contacto':self.informacion_de_contacto,
					'vendedor':self.vendedor
				})	
				od.insert(ignore_permissions=True)
				frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
				frappe.msgprint('Favor ingresar los archivos adjuntos a la orden de site')
				frappe.db.set_value("Service Order", self.name,"site_order",od.name)	
				item_name = frappe.db.get_value("Item",{"name": self.item_opportunity},"item_name")
				opportunity_prospect = frappe.get_doc("Opportunity Prospect", {"name": self.opportunity_prospect})
				if opportunity_prospect.proveedor_section == 'IBW':
					if opportunity_prospect.compresion != '0:0' and opportunity_prospect.portafolio != "OTC":
						rate = (float(opportunity_prospect.tasa) * float(opportunity_prospect.uom.replace(' Mbps', '')))/float(opportunity_prospect.compresion.replace(':1',''))
					else:
						rate = 0
				else:
					rate = 0

				cambio = frappe.db.get_value("Currency Exchange",{"date":today()},"exchange_rate")

				if opportunity_prospect.portafolio not in ("OTC","EQUIPOS"):
					
					# cambio = frappe.db.get_value("Currency Exchange",{"date":today()},"exchange_rate")			
					oi = frappe.get_doc({
						'doctype': "Opportunity Item",
						'precio_tercero': 0.00,
						'importe_ibw': 0.00,
						'descuento_porcentaje':0,
						'base_rate': rate * cambio,
						'base_amount':rate * opportunity_prospect.qty * cambio,
						'rate': rate,
						'amount': rate * opportunity_prospect.qty,
						'proveedor': self.proveedor_section,
						'nombre_proveedor': self.proveedor,
						'item_code': opportunity_prospect.item_code,
						'item_name': item_name,
						'uom':opportunity_prospect.uom,
						'description': self.descripcion,
						'departamento': opportunity_prospect.departamento,
						'tipo_servicio': opportunity_prospect.tipo_servicio,
						'qty':opportunity_prospect.qty,
						'compresion':opportunity_prospect.compresion,
						'tasa':opportunity_prospect.tasa,
						'direccion':opportunity_prospect.direccion,
						'contacto':opportunity_prospect.contacto,
						'parent': opportunity_prospect.parent,
						'parenttype' : opportunity_prospect.parenttype,
						'site_survey' : self.name,
						'parentfield' : 'items'
					})	
					oi.insert(ignore_permissions=True)

				if opportunity_prospect.portafolio  in ("EQUIPOS"):		
					ootc = frappe.get_doc({
					'doctype': "Opportunity Item OTC",
					'item': self.item_opportunity,
					'qty': 1,
					'proveedor':self.proveedor_section,
					'nombre_proveedor': self.proveedor,
					'base_rate': obtener_tasa_de_valoracion_por_item(self.item_opportunity),
					'base_amount': obtener_tasa_de_valoracion_por_item(self.item_opportunity),
					
					'rate': obtener_tasa_de_valoracion_por_item(self.item_opportunity)/cambio,
					'amount':obtener_tasa_de_valoracion_por_item(self.item_opportunity)/cambio,
					'parent': self.nombre_de_origen,
					'parenttype' : 'Opportunity',
					'parentfield' : 'productos_otc',
					'presupuesto': self.name
					})	
					ootc.insert(ignore_permissions=True)

					otc_usd = frappe.db.get_value("Opportunity",self.nombre_de_origen,"total_otc")
					otc_nio = frappe.db.get_value("Opportunity",self.nombre_de_origen,"base_total_otc")

					frappe.db.set_value("Opportunity",self.nombre_de_origen,"total_otc",float(otc_usd) + float(self.total_bom_usd))
					frappe.db.set_value("Opportunity",self.nombre_de_origen,"base_total_otc",float(otc_nio) + float(self.total_bom_nio))	
				
			if self.tipo_de_orden == "PRESUPUESTO" and self.factible == 'El proyecto es factible':				
				ootc = frappe.get_doc({
					'doctype': "Opportunity Item OTC",
					'item': 'Instalacion y Configuracion',
					'qty': 1,
					'proveedor':self.proveedor_section,
					'nombre_proveedor': self.proveedor,
					'base_rate': self.total_bom_nio,
					'base_amount': self.total_bom_nio,
					'rate': self.total_bom_usd,
					'amount': self.total_bom_usd,
					'parent': self.nombre_de_origen,
					'parenttype' : 'Opportunity',
					'parentfield' : 'productos_otc',
					'presupuesto': self.name
				})	
				ootc.insert(ignore_permissions=True)

				otc_usd = frappe.db.get_value("Opportunity",self.nombre_de_origen,"total_otc")
				otc_nio = frappe.db.get_value("Opportunity",self.nombre_de_origen,"base_total_otc")

				frappe.db.set_value("Opportunity",self.nombre_de_origen,"total_otc",float(otc_usd) + float(self.total_bom_usd))
				frappe.db.set_value("Opportunity",self.nombre_de_origen,"base_total_otc",float(otc_nio) + float(self.total_bom_nio))

			if self.tipo_de_orden in ("SUSPENSION","CORTE") and  self.tipo_de_origen=='Suspensiones':
				if frappe.db.get_value("Customer",self.tercero,"estado_cliente") == 'ACTIVO':
					frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'SUSPENDIDO (Manual)' where name = %(customer)s; """,{"customer":self.tercero})
	
				for equipo in self.so_detalle_clientes_suspendidos:
					if equipo.equipos:
						idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":equipo.equipos})	
						try:
							idx = int(idx[0][0]) + 1
						except:
							idx = 1	
						susp = False
						if 'IMOVIL' in self.portafolio:
							if self.departamento == 'Managua':
								suspenderAprovisionador("suspenderYota",equipo.equipos)
							else:
								suspenderAprovisionador("suspenderNetspan",equipo.equipos)
							susp = True
						if 'HFC' in self.portafolio:
							suspenderAprovisionador("suspenderHfc",equipo.equipos)
							susp = True

						if 'IPTV' in self.portafolio:
							# suspenderAprovisionador("suspenderHfc",equipo.equipos)
							iptv = Deshabilitar_Cliente(equipo.cliente)
							susp = True

						if susp:
							add_to_bitacora = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"tipo_transaccion": 'Service Order',
								"transaccion":"Equipo Suspendido",
								"parent":equipo.equipos,
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": self.name,
								"idx":idx
							})
							add_to_bitacora.insert(ignore_permissions=True)

			if "DESINSTALACION" in self.tipo_de_orden and  self.tipo_de_origen=='Subscription':	
				spd = frappe.get_doc("Subscription Plan Detail", {"name": self.plan_de_subscripcion})
				idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":self.plan_de_subscripcion})	
				idx_b = idx_b[0][0]
				if len(self.equipo_orden_servicio) > 0:
					
					for equipo in self.equipo_orden_servicio:
						idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":equipo.serial_no})	
						try:
							idx = int(idx[0][0]) + 1
						except:
							idx = 1	
						aprov = False
						if 'IMOVIL' in self.portafolio:
							if self.departamento == 'Managua':
								# frappe.msgprint('eliminarAprovisionador ("eliminarYota",equipo.serial_no)')
								eliminarAprovisionador ("eliminarYota",equipo.serial_no)
							else:
								# frappe.msgprint('eliminarAprovisionador ("eliminarNetspan",equipo.serial_no)')
								eliminarAprovisionador ("eliminarNetspan",equipo.serial_no)
							aprov = True
						if 'HFC' in self.portafolio:
							# frappe.msgprint('eliminarAprovisionador ("eliminarHFC",equipo.serial_no)' + ' ' + equipo.serial_no)
							eliminarAprovisionador ("eliminarHFC",equipo.serial_no)
							aprov = True
						if aprov:
							add_to_bitacora = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"tipo_transaccion": 'Service Order',
								"transaccion":"Equipo Desaprovisionado",
								"parent":equipo.serial_no,
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": self.name,
								"idx":idx
							})
							add_to_bitacora.insert(ignore_permissions=True)

				if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion}):
					bitacora_plan = frappe.get_doc({
						'doctype': "Bitacora de Planes",
						'plan': spd.plan,
						'cliente':   self.tercero,
						'estado_plan': "Plan Cerrado",
						'direccion': spd.direccion,
						'currency': spd.currency,
						'costo':spd.cost,
						'intervalo_de_facturacion':spd.billing_interval_count,
						'subscription_plan_detail': self.plan_de_subscripcion

					})
					bitacora_plan.insert(ignore_permissions=True)					
				bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion})		
				bitacora_plan.update(
							{
								"estado_plan": "Plan Cerrado",
							})
				bitacora_plan.save(ignore_permissions=True)
									
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"idx": idx_b,
					"detalle":"Plan desinstalado",
					"fecha": now(),
					"usuario":frappe.session.user,
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"Service Order",
					"tercero":self.name,
					'estado_plan': "Plan Cerrado",
					})
				bitacora_detalle.insert(ignore_permissions=True)
		
			if self.tipo_de_orden == "INSTALACION" and  self.tipo_de_origen=='Subscription' :
				idx_b=int(frappe.db.sql(""" select (case when max(idx)is null then "1" else max(idx)+ 1 end)  from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":self.plan_de_subscripcion})[0][0])	
				susc = frappe.get_doc("Subscription", {"name": self.nombre_de_origen})	
				if int(susc.periodo_de_facturacion)>1:
					p = add_months(self.fecha_atendido, int(susc.periodo_de_facturacion)-1)
				else:
					p=self.fecha_atendido
				p = formatdate(frappe.utils.get_last_day(p), "yyyy-MM-dd")
				hay_planes_activos = False
				for plan in susc.plans:
					if plan.estado_plan == 'Activo':
						hay_planes_activos = True
				if hay_planes_activos and susc.tipo_contrato=='NUEVO':

					frappe.db.sql("update `tabSubscription` set workflow_state = 'Instalado' where name = %(sub)s",{"sub":susc.name})
				else:
					frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Instalado', current_invoice_start = %(fecha_finalizado)s , current_invoice_end = %(current_invoice_end)s where name =%(nombre_de_origen)s;""",{"fecha_finalizado":self.fecha_atendido,"current_invoice_end":p,"nombre_de_origen":susc.name})
				combos = tv = gpon = hfc = tv_gpon = tv_hfc = 0
				hay_combo = False 
				#COMBO = 1 GPON = 1 HFC = 0 TV = 1 TV_G = 1 tv_hfc = 0
				for plan in susc.plans:
					if plan.es_combo==1:
						combos +=1
						hay_combo = True
						if "GPON" in plan.plan:
								gpon += 1
						elif "HFC" in plan.plan:
								hfc += 1			
					if 'TV Combo GPON' in plan.plan or 'TV Combo HFC' in plan.plan:
						tv += 1
						if 'TV Combo GPON' in plan.plan:
							tv_gpon +=1
						elif 'TV Combo HFC' in plan.plan:
							tv_hfc +=1
				if tv == combos and hfc == tv_hfc and gpon == tv_gpon and hay_combo:
					for plan in susc.plans:
						spd = frappe.get_doc("Subscription Plan Detail", {"name": plan.name}) 
						if plan.name == self.plan_de_subscripcion:
							spd.update(
								{
									'estado_plan': 'Activo',
									'longitud':self.longitud,
									'latitud':self.latitud,
									'service_start':date,
									'planid':self.plan_de_subscripcion,
									'nodo':self.nodo
								}
							)
							spd.save(ignore_permissions=True)

							frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan = 'Activo', longitud = %(lon)s, latitud = %(lat)s,
							  service_start = %(date)s, planid = %(planid)s, nodo = %(nodo)s where name = %(planid)s;""",{"lon":self.longitud,"lat":self.latitud,
							  "date":self.fecha_atendido, "planid": self.plan_de_subscripcion, "nodo":self.nodo})

							if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": spd.name}):
								bitacora_plan = frappe.get_doc({
									'doctype': "Bitacora de Planes",
									'plan': spd.plan,
									'cliente':   self.tercero,
									'estado_plan': "Activo",
									'direccion': spd.direccion,
									'currency': spd.currency,
									'costo':spd.cost,
									'intervalo_de_facturacion':spd.billing_interval_count,
									'subscription_plan_detail': spd.name,
									'nodo': spd.nodo
								})
								bitacora_plan.insert(ignore_permissions=True)					
							bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": spd.name})
							bitacora_plan.update(
								{
									"estado_plan": "Activo",
								})
							bitacora_plan.save(ignore_permissions=True)								
							bitacora_detalle = frappe.get_doc({
								"doctype": "Detalle Bitacora Planes",
								"idx": idx_b,
								"detalle":"Plan Activado",
								"fecha": now(),
								"usuario":frappe.session.user,
								"parent": bitacora_plan.name,
								"parentfield":"detalle",
								"parenttype": "Bitacora de Planes",
								"tipo_transaccion":"Service Order",
								"tercero":self.name,
								'estado_plan': "Activo",
								})
							bitacora_detalle.insert(ignore_permissions=True)
						elif "TV" in plan.plan and plan.estado_plan == 'Inactivo' and "IPTV" not in plan.plan:
							if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": spd.name}):
								bitacora_plan = frappe.get_doc({
									'doctype': "Bitacora de Planes",
									'plan': spd.plan,
									'cliente':   self.tercero,
									'estado_plan': "Activo",
									'direccion': spd.direccion,
									'currency': spd.currency,
									'costo':spd.cost,
									'intervalo_de_facturacion':spd.billing_interval_count,
									'subscription_plan_detail': spd.name,
									'nodo': spd.nodo
								})
								bitacora_plan.insert(ignore_permissions=True)					
							bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": spd.name})	
							bitacora_plan.update(
								{
									"estado_plan": "Activo",
								})
							bitacora_plan.save(ignore_permissions=True)								
							bitacora_detalle = frappe.get_doc({
								"doctype": "Detalle Bitacora Planes",
								"idx": idx_b,
								"detalle":"Plan Activado",
								"fecha": now(),
								"usuario":frappe.session.user,
								"parent": bitacora_plan.name,
								"parentfield":"detalle",
								"parenttype": "Bitacora de Planes",
								"tipo_transaccion":"Service Order",
								"tercero":self.name,
								'estado_plan': "Activo",
								})
							bitacora_detalle.insert(ignore_permissions=True)
							frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan = 'Activo', longitud = %(lon)s, latitud = %(lat)s,
							  service_start = %(date)s, planid = %(planid)s, nodo = %(nodo)s where name = %(planid)s;""",{"lon":self.longitud,"lat":self.latitud,
							  "date":self.fecha_atendido, "planid": plan.name, "nodo":self.nodo})
				else:
					spd = frappe.get_doc("Subscription Plan Detail", {"name": self.plan_de_subscripcion})
					spd.update(
						{
							'estado_plan': 'Activo',
							'longitud':self.longitud,
							'latitud':self.latitud,
							'service_start':self.fecha_atendido,
							'planid':self.plan_de_subscripcion,
							'nodo':self.nodo
						}
					)
					spd.save()
					frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan = 'Activo', longitud = %(lon)s, latitud = %(lat)s,
							  service_start = %(date)s, planid = %(planid)s, nodo = %(nodo)s where name = %(planid)s;""",{"lon":self.longitud,"lat":self.latitud,
							  "date":self.fecha_atendido, "planid": self.plan_de_subscripcion, "nodo":self.nodo})
					
					if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": spd.name}):
						bitacora_plan = frappe.get_doc({
							'doctype': "Bitacora de Planes",
							'plan': spd.plan,
							'cliente':   self.tercero,
							'estado_plan': "Activo",
							'direccion': spd.direccion,
							'currency': spd.currency,
							'costo':spd.cost,
							'intervalo_de_facturacion':spd.billing_interval_count,
							'subscription_plan_detail': spd.name

						})
						bitacora_plan.insert(ignore_permissions=True)
				
					bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": spd.name})
					bitacora_plan.update(
								{
									"estado_plan": "Activo",
								})
					bitacora_plan.save(ignore_permissions=True)	
					bitacora_detalle = frappe.get_doc({
						"doctype": "Detalle Bitacora Planes",
						"idx": idx_b,
						"detalle":"Plan Activado",
						"fecha": now(),
						"usuario":frappe.session.user,
						"parent": bitacora_plan.name,
						"parentfield":"detalle",
						"parenttype": "Bitacora de Planes",
						"tipo_transaccion":"Service Order",
						"tercero":self.name,
						'estado_plan': "Activo",
						})
					bitacora_detalle.insert(ignore_permissions=True)
				
				old_plan = frappe.db.get_value("Subscription Plan Detail",self.plan_de_subscripcion,"old_plan")
				old_plan_status = frappe.db.get_value("Subscription Plan Detail",old_plan,"estado_plan")
				if (old_plan and old_plan_status == 'Activo') or frappe.db.get_value("Subscription",self.nombre_de_origen,"subscription_update"):
					su = frappe.db.get_value("Subscription Update Planes",{"plan":old_plan},"parent") or frappe.db.get_value("Subscription",self.nombre_de_origen,"subscription_update")
					su = frappe.get_doc("Subscription Update", su)
					for old_plan in su.actualizar_planes_de_contrato:
						frappe.db.sql("""update `tabSubscription Plan Detail` set estado_plan = 'Plan Cerrado',
						service_end = NOW() where name = %(old_plan)s;""",{"old_plan":old_plan.plan})

				insert_portafolio = frappe.db.sql("""
					select i.item_group from `tabItem` i
					inner join `tabSubscription Plan`sp on i.name=sp.item
					inner join `tabSubscription Plan Detail` spd on sp.name=spd.plan
					inner join `tabSubscription` s on s.name=spd.parent 
					where spd.cost>=0 and spd.estado_plan='Activo' and s.party=%(tercero)s
					order by (case when spd.currency='NIO' then (spd.cost)/( select exchange_rate 
					from `tabCurrency Exchange` where date=curdate()) else  (spd.cost) end) desc limit 1;
					""", {"tercero":self.tercero})
				frappe.db.sql("""update `tabCustomer` set estado_cliente = 'ACTIVO', item_group = %(portafolio)s where name = %(customer)s;""",{"portafolio":insert_portafolio[0][0],"customer":self.tercero})

			if self.tipo_de_orden == "REACTIVACION":
				idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":self.plan_de_subscripcion})	
				idx_b = idx_b[0][0]

				combos = tv = gpon = hfc = tv_gpon = tv_hfc = 0
				hay_combo = False 
				susc = frappe.get_doc("Subscription", {"name": frappe.db.get_value("Subscription Plan Detail",self.plan_de_subscripcion,"parent")})
				for plan in susc.plans:
					if plan.es_combo==1:
						combos +=1
						hay_combo = True
						if "GPON" in plan.plan:
								gpon += 1
						elif "HFC" in plan.plan:
								hfc += 1			
					if 'TV Combo GPON' in plan.plan or 'TV Combo HFC' in plan.plan:
						tv += 1
						if 'TV Combo GPON' in plan.plan:
							tv_gpon +=1
						elif 'TV Combo HFC' in plan.plan:
							tv_hfc +=1
				if tv == combos and hfc == tv_hfc and gpon == tv_gpon and hay_combo:
					for plan in susc.plans:
						spd = frappe.get_doc("Subscription Plan Detail", {"name": plan.name}) 
						spd.update(
							{
								"estado_plan": "Activo",
								"service_reactivation": self.fecha_atendido,
							})
						spd.save(ignore_permissions=True)
						frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan = 'Activo', service_reactivation = %(service_reactivation)s
						where name = %(planid)s""",{"service_reactivation":self.fecha_atendido, "planid": plan.name})
				else:
					spd = frappe.get_doc("Subscription Plan Detail", {"name": self.plan_de_subscripcion})
					spd.update(
						{
							'estado_plan': 'Activo',
							"service_reactivation": self.fecha_atendido
						}
					)
					spd.save(ignore_permissions=True)
					frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan = 'Activo', service_reactivation = %(service_reactivation)s
					where name = %(planid)s""",{"service_reactivation":self.fecha_atendido, "planid": self.plan_de_subscripcion})


				upd_spd = frappe.get_doc("Subscription Plan Detail", {"name": self.plan_de_subscripcion})
				
				posting_date = frappe.db.sql(""" select posting_date from `tabSales Invoice` where customer = %(customer)s order by posting_date desc limit 1;""",{"customer":susc.party})
				try:
					posting_date = frappe.utils.formatdate(posting_date[0][0], "MMMM")
				except:
					posting_date = None
				if posting_date:
					if posting_date == frappe.utils.formatdate(self.fecha_atendido, "MMMM"):
						workflow_state = 'Activo'
					else:
						workflow_state = 'Instalado'
				else:
					workflow_state = 'Instalado'

				if self.tipo_de_origen == "Subscription":
					Mes_Suspend = frappe.utils.formatdate(upd_spd.service_suspend, "MM")
					Ano_Suspend = frappe.utils.formatdate(upd_spd.service_suspend, "YY")
				else:
					Mes_Suspend = frappe.utils.formatdate(upd_spd.service_end, "MM")
					Ano_Suspend = frappe.utils.formatdate(upd_spd.service_end, "YY")
				Mes_react = frappe.utils.formatdate(self.fecha_atendido, "MM")
				Ano_react= frappe.utils.formatdate(self.fecha_atendido, "YY")

				if (Mes_Suspend<Mes_react and Ano_Suspend==Ano_react) or (Mes_Suspend>Mes_react  and Ano_Suspend < Ano_react):
					frappe.db.sql(""" update `tabSubscription` set workflow_state = %(workflow_state)s, current_invoice_start = %(current_invoice_start)s, 
					current_invoice_end = %(current_invoice_end)s where name = %(name)s; """,{"workflow_state":workflow_state, "current_invoice_start":self.fecha_atendido,"current_invoice_end":formatdate(frappe.utils.get_last_day(self.fecha_atendido), "yyyy-MM-dd"),"name":susc.name})
				else:
					frappe.db.sql(""" update `tabSubscription` set workflow_state = %(workflow_state)s where name = %(name)s; """,{"workflow_state":workflow_state,"name":susc.name})
					
				


				if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion}):
					bitacora_plan = frappe.get_doc({
						'doctype': "Bitacora de Planes",
						'plan': upd_spd.plan,
						'cliente':  susc.party,
						'estado_plan': "Activo",
						'direccion': upd_spd.direccion,
						'currency': upd_spd.currency,
						'costo':upd_spd.cost,
						'intervalo_de_facturacion':upd_spd.billing_interval_count,
						'subscription_plan_detail': upd_spd.name

					})
					bitacora_plan.insert(ignore_permissions=True)	
				
				try:
					frappe.db.sql("update `tabBitacora de Planes` set estado_plan = 'Activo' where name = %(plan)s; ",{"plan":self.subscription_plan_detail})
				except:
					pass
				# bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion})			
				# bitacora_plan.update(
				# 			{
				# 				"estado_plan": "Activo",
				# 			})
				# bitacora_plan.save(ignore_permissions=True)
			
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"idx": idx_b,
					"detalle":"Plan Reactivado",
					"fecha": self.fecha_atendido,
					"usuario":frappe.session.user,
					"parent": self.plan_de_subscripcion,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"Service Order",
					"tercero":self.name,
					'estado_plan': "Activo",
					})
				bitacora_detalle.insert(ignore_permissions=True)
				
				for equipo in self.equipo_orden_servicio:
					
					if equipo.serial_no:
						idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":equipo.serial_no})	
						try:
							idx = int(idx[0][0]) + 1
						except:
							idx = 1	
						actv = False
						if 'IMOVIL' in self.portafolio:
							if self.departamento == 'Managua':
								# frappe.msgprint("""cambiarVelocidadAprovisionador("cambiarVelocidadYota",equipo.serial_no,frappe.db.get_value("Aprovisionamiento",{"mac":equipo.serial_no},'provisor_speed_id'))""")
								cambiarVelocidadAprovisionador("cambiarVelocidadYota",equipo.serial_no,frappe.db.get_value("Aprovisionamiento",{"mac":equipo.serial_no},'provisor_speed_id'))
							else:
								# frappe.msgprint('activarAprovisionador("activarNetspan",equipo.serial_no)')
								activarAprovisionador("activarNetspan",equipo.serial_no)
							actv = True
						if 'HFC' in self.portafolio:
							# frappe.msgprint('activarAprovisionador("activarHfc",equipo.serial_no)' + ' ' + equipo.serial_no)
							activarAprovisionador("activarHfc",equipo.serial_no)
							actv = True
						
						if 'IPTV' in self.portafolio:
							# frappe.msgprint('activarAprovisionador("activarHfc",equipo.serial_no)' + ' ' + equipo.serial_no)
							
							customer = frappe.db.sql("""select parent from `tabDispositivos IPTv` where mac = %(parent)s """,{"parent":equipo.serial_no}, as_dict=1)	
							if customer:
								for c in customer:
									Habilitado = Habilitar_Cliente(c.parent)
									if Habilitado:
										actv = True

						if actv:
							add_to_bitacora = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"tipo_transaccion": 'Service Order',
								"transaccion":"Equipo Reactivado",
								"parent":equipo.serial_no,
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": self.name,
								"idx":idx
							})
							add_to_bitacora.insert(ignore_permissions=True)
				insert_portafolio = frappe.db.sql("""
					select i.item_group from `tabItem` i
					inner join `tabSubscription Plan`sp on i.name=sp.item
					inner join `tabSubscription Plan Detail` spd on sp.name=spd.plan
					inner join `tabSubscription` s on s.name=spd.parent 
					where spd.cost>=0 and spd.estado_plan='Activo' and s.party=%(tercero)s
					order by (case when spd.currency='NIO' then (spd.cost)/( select exchange_rate 
					from `tabCurrency Exchange` where date=curdate()) else  (spd.cost) end) desc limit 1;
					""", {"tercero":self.tercero})
				frappe.db.sql("""update `tabCustomer` set estado_cliente = 'ACTIVO', item_group = %(portafolio)s where name = %(customer)s;""",{"portafolio":insert_portafolio[0][0],"customer":self.tercero})

			if self.tipo_de_orden == 'RECONEXION' and 'TV' in self.portafolio:
				idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":self.plan_de_subscripcion})	
				idx_b = idx_b[0][0]
				upd_spd = frappe.get_doc("Subscription Plan Detail", {"name": self.plan_de_subscripcion})
				upd_spd.update(
							{
								"estado_plan": "Activo",
								"service_reactivation": now(),
							})
				upd_spd.save()
				
				frappe.db.sql("update `tabSubscription Plan Detail` set estado_plan = 'Activo', service_reactivation = %(now)s where name = %(spd)s;",{"now":now(),"spd": self.plan_de_subscripcion})
				upd_sus = frappe.get_doc("Subscription", {"name": upd_spd.parent})
				posting_date = frappe.db.sql(""" select posting_date from `tabSales Invoice` where customer = %(customer)s order by posting_date desc limit 1;""",{"customer":upd_sus.party})
				try:
					posting_date = frappe.utils.formatdate(posting_date[0][0], "MMMM")
				except:
					posting_date = None
				if posting_date:
					if posting_date == frappe.utils.formatdate(today(), "MMMM"):
						workflow_state = 'Activo'
					else:
						workflow_state = 'Instalado'
				else:
					workflow_state = 'Instalado'
				upd_sus.update(
							{
								"workflow_state":workflow_state,
								"current_invoice_start":today(),
								"current_invoice_end": formatdate(frappe.utils.get_last_day(today()), "yyyy-MM-dd")
							})
				upd_sus.save()
				frappe.db.sql(""" update `tabSubscription` set workflow_state = %(workflow_state)s, current_invoice_start = %(current_invoice_start)s, 
				current_invoice_end = %(current_invoice_end)s where name = %(name)s; """,{"workflow_state":workflow_state, "current_invoice_start":today(),"current_invoice_end":formatdate(frappe.utils.get_last_day(today()), "yyyy-MM-dd"),"name":upd_sus.name})			
				frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'ACTIVO' where name = %(customer)s; """,{"customer":upd_sus.party})
				
				if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion}):
					bitacora_plan = frappe.get_doc({
						'doctype': "Bitacora de Planes",
						'plan': upd_spd.plan,
						'cliente':   self.tercero,
						'estado_plan': "Activo",
						'direccion': upd_spd.direccion,
						'currency': upd_spd.currency,
						'costo':upd_spd.cost,
						'intervalo_de_facturacion':upd_spd.billing_interval_count,
						'subscription_plan_detail': upd_spd.name,
						'nodo': upd_spd.nodo
					})
					bitacora_plan.insert(ignore_permissions=True)					
				bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail":self.plan_de_subscripcion})
				bitacora_plan.update(
							{
								"estado_plan": "Activo",
							})
				bitacora_plan.save(ignore_permissions=True)								
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"idx": idx_b,
					"detalle":"Plan Activado",
					"fecha": now(),
					"usuario":frappe.session.user,
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"Service Order",
					'estado_plan': "Activo",
					"tercero":self.name
					})
				bitacora_detalle.insert(ignore_permissions=True)
				insert_portafolio = frappe.db.sql("""
					select i.item_group from `tabItem` i
					inner join `tabSubscription Plan`sp on i.name=sp.item
					inner join `tabSubscription Plan Detail` spd on sp.name=spd.plan
					inner join `tabSubscription` s on s.name=spd.parent 
					where spd.cost>0 and spd.estado_plan='Activo' and s.party=%(tercero)s
					order by (case when spd.currency='NIO' then (spd.cost)/( select exchange_rate 
					from `tabCurrency Exchange` where date=curdate()) else  (spd.cost) end) desc limit 1;
					""", {"tercero":self.tercero})
				frappe.db.sql("""update `tabCustomer` set estado_cliente = 'ACTIVO', item_group = %(portafolio)s where name = %(customer)s;""",{"portafolio":insert_portafolio[0][0],"customer":self.tercero})

			if self.portafolio == "DIALUP" and self.tipo_de_orden == 'INSTALACION':
				sub = frappe.get_doc("Subscription",self.nombre_de_origen)
				
				
				for c in self.get("correo"):
					correo = {
					"correo": c.correo
					}
					sub.append("correo", correo)

				sub.flags.ignore_permissions = True
				sub.save()

		if self.workflow_state == "Abierto":
			if self.tipo == 'Customer':
				phones= frappe.db.sql(
				"""select phone from `tabContact Phone` where parent in 
					(select parent from `tabDynamic Link` t1 where t1.link_name like %(customer)s and t1.parenttype = 'Contact');""",
					{"customer": '%' + self.tercero + '%'})				
				telefono = []
				for phone in range(len(phones)): 
						telefono.append(phones[phone][0])

				cadena=""
				for t in telefono:
					if t == telefono[-1]:
						cadena= cadena + t
					else :
						cadena= cadena + t + " / "
				frappe.db.set_value("Service Order",self.name,"telefonos",cadena)

			if not frappe.db.exists("Bitacora Orden",{"detalle":'Orden ABIERTA',"parent":self.name}):
				idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
				try:
					idx = int(idx[0][0]) + 1
				except:
					idx = 1	
				if not self.venta_en_caliente:
					bitacora_orden = frappe.get_doc({
						"doctype": "Bitacora Orden",
						"detalle":"Orden ABIERTA",
						"fecha_transaccion": now(),
						"usuario":frappe.session.user,
						"tiempo_transcurrido":0.00,
						"fecha_definida_por_usuario": self.fecha_solicitud,
						"parent": self.name,
						"parentfield":"bitacora_orden",
						"parenttype": "Service Order",
						"idx":idx
						})
					bitacora_orden.insert(ignore_permissions=True)

			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ABIERTO')
					
		if self.workflow_state == "Atendido":
			try:
				solucion = self.solucion
			except:
				solucion = None

			if self.portafolio == "DIALUP":
				if len(self.get("correo")) == 0:
					frappe.msgprint('Debe de ingresar los correos.')
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', "Abierto")
					frappe.db.set_value(self.doctype, self.name, 'estado', "Abierto")
					frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
					self.reload()
					return

			if self.tipo_de_orden not in ('DESINSTALACION','REACTIVACION','SUSPENSION','DESINSTALACION RCPE') and self.tecnico and (len(self.productos) > 0 or len(self.equipo_orden_servicio) > 0 ) and not self.no_requiere_materiales:
				
				pendientes = frappe.db.sql("""  select name,posting_date as Fecha,from_warehouse as Origen,tecnico, (case when per_transferred < 100 then 'Pendiente' else 'Listo' end) 'Transferido',
									(case when docstatus=0 then 'Borrador' when docstatus=1 then 'Validado' when docstatus=2 then 'Cancelado' end )
									Estado  from `vw_Stock_Entry_al_Transito`
									where per_transferred < 100  and docstatus = 1 and tecnico in (select tecnico from `tabService Order`where name=%(name)s union all
 									select tecnico from `tabTecnicos Service Order`where parent = %(name)s) """,{"name":self.name})


				if pendientes:
					for i in pendientes:
						frappe.msgprint(frappe._('El técnico {0} tiene la transferencia {1} pendiente por aceptar.').format(i[3], frappe.utils.get_link_to_form("Stock Entry", i[0])))
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						self.reload()
						return
				
				serie_rep = frappe.db.sql("""  SELECT serial_no, COUNT(serial_no) AS contador FROM `tabMateriales detalles` where parent = %(parent)s GROUP BY serial_no HAVING contador > 1; """,{"parent":self.name})
					
				if serie_rep:	
					frappe.msgprint(f" posee número de serie {serie_rep[0][0]} repetido en tabla de materiales, favor eliminar duplicados. ")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
					frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
					self.reload()
					return
				items_repetidos = frappe.db.sql(""" select bodega, material, count(cantidad) as total from `tabMateriales detalles` where parent = %(name)s group by bodega, material;""",{"name":self.name},as_dict=True)
				for row in self.productos:	
					if frappe.db.get_value("Item",row.material,"has_serial_no") and not row.serial_no:
						frappe.msgprint(f" fila # {row.idx}: {row.material} posee número de serie, favor escribirlo. ")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						self.reload()
						return
					if frappe.db.get_value("Serial No",row.serial_no,"customer"):
						frappe.msgprint(f"El equipo {row.serial_no} ya fue liquidado")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
						frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
						self.reload()
						return

					cantidad_actual = frappe.db.sql(""" SELECT item_code, warehouse, qty_after_transaction, posting_date FROM `tabStock Ledger Entry` WHERE warehouse = %(wh)s
														and item_code = %(ic)s and is_cancelled = 0 ORDER BY posting_date DESC ,posting_time DESC , name DESC limit 1;""",{"wh":row.bodega,"ic":row.material})
					try:
						if cantidad_actual[0][2] < row.cantidad:
							frappe.msgprint(f"No se puede liquidar {row.material}. Cantidad existente en {row.bodega} a la fecha {cantidad_actual[0][3]} es de {cantidad_actual[0][2]} y usted ha colocado {row.cantidad}. Necesita {int(row.cantidad) - int(cantidad_actual[0][2])}. Verifique que no tenga transferencias pendientes de aceptar o solicite una transferencia de material.")
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
							frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
							frappe.db.set_value(self.doctype, self.name, 'docstatus', 0)
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
				
				almacenes_de_tecnico = [a[0] for a in frappe.db.sql("select almacen from `tabAlmacenes de Tecnico` where parent in (select tecnico from `tabService Order`where name=%(name)s ) or parent in (select tecnico from `tabTecnicos Service Order`where parent=%(name)s)",{"name":self.name})]	

				if self.tipo_de_orden != "TRASLADO":
					for row in self.equipo_orden_servicio:	
						if frappe.db.get_value("Serial No",row.serial_no,"customer"):
							frappe.msgprint(f"El equipo {row.serial_no} ya fue liquidado")
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
							frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
							self.reload()
							return	

					for equipo in self.equipo_orden_servicio:
						if equipo.serial_no:
							warehouse_equipo = frappe.db.get_value("Serial No",equipo.serial_no,"warehouse")
							if warehouse_equipo not in almacenes_de_tecnico:
								frappe.msgprint(f"{equipo.serial_no} no pertenece a ninguna bodega de los tecnicos seleccionados")
								frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
								frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
								self.reload()
								return 
				for equipo in self.productos:
					if equipo.serial_no:
						if equipo.cantidad != 1:
							frappe.msgprint(f"fila #{equipo.idx} equipo {equipo.serial_no} en tabla de materiales, el campo cantidad no puede ser diferente de 1.")
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
							frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
							self.reload()
							return

						warehouse_equipo = frappe.db.get_value("Serial No",equipo.serial_no,"warehouse")
						if warehouse_equipo not in almacenes_de_tecnico:
							frappe.msgprint(f"{equipo.serial_no} no pertenece a ninguna bodega de los tecnicos seleccionados")
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
							frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
							self.reload()
							return 

			if self.tipo_de_orden not in ('DESINSTALACION','REACTIVACION','SUSPENSION','DESINSTALACION RCPE') and len(self.productos) == 0 and not self.no_requiere_materiales:
				frappe.msgprint(f"<b>Favor colocar los materiales en la orden!</b> Si no se ocuparon materiales, habilitar el check <b>No requiere materiales</b> en la solución.")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
				frappe.db.set_value(self.doctype, self.name, 'estado', 'Seguimiento')
				self.reload()
				return
			if self.tipo_de_orden in ('INSTALACION'):
				equipos = frappe.db.sql(""" select count(*) from `tabEquipo_Orden_Servicio` where parent = %(parent)s """, {"parent": self.name})
				try:
					equipos = int(equipos[0][0])
				except:
					equipos = 0
				if self.portafolio in ['GPON','GPON-CORPORATIVO','GPON-INT-PYME','GPON-INT-RESIDENCIAL','HFC', 'HFC 3.0', 'IMOVIL', 'INET', 'Wimax','IPTV']:
						
					if equipos < 1 and frappe.db.get_value("Subscription Plan",frappe.db.get_value("Subscription Plan Detail",self.plan_de_subscripcion,"plan"),"item")  not in ('ITV HFC SIN VELOCIDAD','TV HFC SIN VELOCIDAD'):
						frappe.msgprint(f"El portafolio {self.portafolio} debe tener al menos un Equipo")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						self.reload()
						return
				elif self.portafolio in ['LTE', 'LTE Productos']:
					sim = frappe.db.sql(""" select count(*) from `tabSerial No` where item_code = 'SIM Card' and name in (select serial_no from `tabEquipo_Orden_Servicio` where parent = %(parent)s ) """, {"parent": self.name})
					try:
						sim = int(sim[0][0])
					except:
						sim = 0
					if equipos < 2 or sim < 1:
						frappe.msgprint(f"El portafolio {self.portafolio} debe tener al menos un SIM Card y un segundo Equipo")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						self.reload()
						return
				if self.tipo_de_orden =='INSTALACION':
					almacenes = []
					tecnicos = [t.tecnico for t in self.cuadrilla_tecnica]
					tecnicos.append(self.tecnico)
					if frappe.db.exists("Almacenes de Tecnico",{'parent':['in',tecnicos]},"almacen"):
						for almacen in frappe.db.get_values("Almacenes de Tecnico",{'parent':['in',tecnicos]},"almacen"):
							almacenes.append(almacen[0])
					else:	
						frappe.msgprint("El tecnico no tiene bodegas asignadas")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						frappe.db.set_value(self.doctype, self.name, 'fecha_atendido', None)
						self.reload()
						return
					if len(self.equipo_orden_servicio) > 0:
						for equipo in self.equipo_orden_servicio:
							if frappe.db.get_value("Serial No",equipo.serial_no,"warehouse") not in almacenes:							
								frappe.msgprint("El equipo " + equipo.serial_no + " no pertenece a la bodega del técnico")
								frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
								self.reload()
								return
							if 'IMOVIL' in self.portafolio or 'HFC' in self.portafolio:
								aprov_name = frappe.db.get_value("Aprovisionamiento",{"name":equipo.serial_no},'name')
								if aprov_name:
									frappe.db.sql(""" update `tabAprovisionamiento` set plan = %(plan)s where name = %(name)s""", {"plan":self.plan_de_subscripcion,"name":aprov_name})
								else:
									frappe.msgprint("El Equipo No esta Aprovisionado")
									frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
									self.reload()
									return	
											
			if not solucion:
				frappe.msgprint("Inserte una solución")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
				self.reload()
				return
			
			if self.tipo_de_orden in ('INSTALACION','SITE SURVEY'):
						
				if self.latitud == None or self.longitud == None or len(self.latitud) == 0 or len(self.longitud)==0:
					frappe.msgprint("Inserte latitud y longitud")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return
				if not self.nodo:
					frappe.msgprint("Asigne un nodo")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return	

			if self.tipo_de_orden == 'TRASLADO':
				idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":self.plan_de_subscripcion})	
				idx_b = idx_b[0][0]
				if not self.direccion_de_traslado:
					frappe.msgprint("Ingresar nueva dirección")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return
				if self.latitud_traslado == None or self.longitud_traslado == None or len(self.latitud_traslado) == 0 or len(self.longitud_traslado)==0:
					frappe.msgprint("Inserte latitud y longitud de traslado")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return
				if not self.nuevo_nodo:
					frappe.msgprint("Asigne un nuevo nodo")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return

				spd = frappe.get_doc("Subscription Plan Detail",self.plan_de_subscripcion)
				susc = frappe.get_doc("Subscription",spd.parent)
				if definir_combos(susc):
					for plan in susc.plans:
						if plan.es_combo or "TV Combo" in plan.plan or frappe.db.get_value("Subscription Plan",plan.plan,"descripcion") in ('GponTv22','ITV22') or self.plan_de_subscripcion == plan.name:
							plan.update({
									'direccion':self.direccion_de_traslado,
									'address_line':self.nueva_direccion,
									'latitud':self.latitud_traslado,
									'longitud':self.longitud_traslado,
									'nodo':self.nuevo_nodo
							})
							plan.save(ignore_permissions=True)

							if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": plan.name}):
								bitacora_plan = frappe.get_doc({
									'doctype': "Bitacora de Planes",
									'plan': plan.plan,
									'cliente':   self.tercero,
									'estado_plan': "Activo",
									'direccion': plan.direccion,
									'currency': plan.currency,
									'costo':plan.cost,
									'intervalo_de_facturacion':plan.billing_interval_count,
									'subscription_plan_detail': plan.name,
									'nodo': plan.nodo
								})
								bitacora_plan.insert(ignore_permissions=True)					
							bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail":  plan.name})
							bitacora_plan.update(
										{
											"estado_plan": "Activo",
											'direccion': plan.direccion,
										})
							bitacora_plan.save(ignore_permissions=True)								
							bitacora_detalle = frappe.get_doc({
								"doctype": "Detalle Bitacora Planes",
								"idx": idx_b,
								"detalle":"Plan trasladado a nueva direccion",
								"fecha": now(),
								"usuario":frappe.session.user,
								"parent": bitacora_plan.name,
								"parentfield":"detalle",
								"parenttype": "Bitacora de Planes",
								"tipo_transaccion":"Service Order",
								'estado_plan': "Activo",
								"tercero":self.name
								})
							bitacora_detalle.insert(ignore_permissions=True)
				else:
					spd.update({
								'direccion':self.direccion_de_traslado,
								'address_line':self.nueva_direccion,
								'latitud':self.latitud_traslado,
								'longitud':self.longitud_traslado,
								'nodo':self.nuevo_nodo
							})
					spd.save(ignore_permissions=True)

					if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion}):
						bitacora_plan = frappe.get_doc({
							'doctype': "Bitacora de Planes",
							'plan': spd.plan,
							'cliente':   self.tercero,
							'estado_plan': "Activo",
							'direccion': spd.direccion,
							'currency': spd.currency,
							'costo':spd.cost,
							'intervalo_de_facturacion':spd.billing_interval_count,
							'subscription_plan_detail': spd.name,
							'nodo': spd.nodo
						})
						bitacora_plan.insert(ignore_permissions=True)					
					bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail":  self.plan_de_subscripcion})
					bitacora_plan.update(
								{
									"estado_plan": "Activo",
									'direccion': spd.direccion,
								})
					bitacora_plan.save(ignore_permissions=True)								
					bitacora_detalle = frappe.get_doc({
						"doctype": "Detalle Bitacora Planes",
						"idx": idx_b,
						"detalle":"Plan trasladado a nueva direccion",
						"fecha": now(),
						"usuario":frappe.session.user,
						"parent": bitacora_plan.name,
						"parentfield":"detalle",
						"parenttype": "Bitacora de Planes",
						"tipo_transaccion":"Service Order",
						'estado_plan': "Activo",
						"tercero":self.name
						})
					bitacora_detalle.insert(ignore_permissions=True)


				
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1
			if self.estado_anterior == 'SEGUIMIENTO':			
				if self.venta_en_caliente == 0:
					date = now()
					frappe.db.sql(""" update `tabService Order` set fecha_atendido = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				else:
					if not self.fecha_atendido:
						frappe.msgprint("inserte fecha de atendido")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						self.reload()
						return
					else:
						date = self.fecha_atendido
				if time_diff_in_seconds(date,self.fecha_seguimiento) < 0:
					frappe.msgprint("Error en fecha y hora insertada")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return
				if not self.venta_en_caliente:
					bitacora_orden = frappe.get_doc({
						"doctype": "Bitacora Orden",
						"detalle":"Orden cambió de estado SEGUIMIENTO a estado ATENDIDO",
						"fecha_transaccion": now(),
						"usuario":frappe.session.user,
						"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_seguimiento),
						"fecha_definida_por_usuario": date,
						"parent": self.name,
						"parentfield":"bitacora_orden",
						"parenttype": "Service Order",
						"idx":idx
						})
					bitacora_orden.insert(ignore_permissions=True)
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ATENDIDO')			
		
			
		if self.workflow_state == "Seguimiento":
			if self.tipo_de_orden not in ('SUSPENSION','REACTIVACION','RECONEXION','APROVISIONAMIENTO'):
				try:
					tecnico = self.tecnico
				except:
					tecnico = None			
				if not tecnico or tecnico=="":
					frappe.msgprint("Asigne un técnico para esta orden de servicio")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
					self.reload()
					return
				n = frappe.get_doc("Tecnico", self.tecnico)
				try:
					p = frappe.get_doc("User", n.usuario)
				except:
					p= None
				try:
					envio_sms("505", "Orden asignada: "  + self.name, 1, p.mobile_no)
				except:
					pass	
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})		
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			if self.estado_anterior == 'ABIERTO':
				if self.venta_en_caliente == 0:
					date = now()
					frappe.db.sql(""" update `tabService Order` set fecha_seguimiento = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				else:
					if not self.fecha_seguimiento:
						frappe.msgprint("inserte fecha de seguimiento")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
						self.reload()
						return
					else:
						date = self.fecha_seguimiento	
				if time_diff_in_seconds(date,self.fecha_solicitud) < 0:
					frappe.msgprint("Error en fecha y hora insertada")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
					self.reload()
					return
				if not self.venta_en_caliente:
					bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado ABIERTO a estado SEGUIMIENTO",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_solicitud),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_orden",
					"parenttype": "Service Order",
					"idx":idx
					})
					bitacora_orden.insert(ignore_permissions=True)
				
			if self.estado_anterior == 'PENDIENTE':
				if self.venta_en_caliente == 0:
					date = now()
					frappe.db.sql(""" update `tabService Order` set fecha_seguimiento = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				else:
					if not self.fecha_seguimiento:
						frappe.msgprint("inserte fecha de seguimiento")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Pending')
						self.reload()
						return
					else:
						date = self.fecha_seguimiento
				if time_diff_in_seconds(date,self.fecha_pendiente) < 0:
					frappe.msgprint("Error en fecha de seguimiento debe ser mayor a la fecha de estado Pendiente")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Pending')
					self.reload()
					return	
				if not self.venta_en_caliente:
					bitacora_orden = frappe.get_doc({
						"doctype": "Bitacora Orden",
						"detalle":"Orden cambió de estado PENDIENTE a estado SEGUIMIENTO",
						"fecha_transaccion": now(),
						"usuario":frappe.session.user,
						"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_pendiente),
						"fecha_definida_por_usuario": date,
						"parent": self.name,
						"parentfield":"bitacora_orden",
						"parenttype": "Service Order",
						"idx":idx
						})
					bitacora_orden.insert(ignore_permissions=True)	

			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'SEGUIMIENTO')	
			
		if self.workflow_state == "Pending":
			if not self.razon_pendiente:
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
				frappe.msgprint("Inserte razón de estado pendiente")
				self.reload()
				return
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			if self.estado_anterior == 'ATENDIDO':
				if self.venta_en_caliente == 0:
					date = now()
					frappe.db.sql(""" update `tabService Order` set fecha_pendiente = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				else:
					if not self.fecha_pendiente:
						frappe.msgprint("inserte fecha pendiente")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
						self.reload()
						return
					else:
						date = self.fecha_pendiente
				if time_diff_in_seconds(date,self.fecha_atendido) < 0:
					frappe.msgprint("Error en fecha y hora insertada")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Atendido')
					self.reload()
					return	
				if not self.venta_en_caliente:
					bitacora_orden = frappe.get_doc({
						"doctype": "Bitacora Orden",
						"detalle":"Orden cambió de estado ATENDIDO a estado PENDIENTE",
						"fecha_transaccion": now(),
						"usuario":frappe.session.user,
						"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_atendido),
						"fecha_definida_por_usuario": date,
						"parent": self.name,
						"parentfield":"bitacora_orden",
						"parenttype": "Service Order",
						"idx":idx
						})
					bitacora_orden.insert(ignore_permissions=True)				

			if self.estado_anterior == 'SEGUIMIENTO':
				if self.venta_en_caliente == 0:
					date = now()
					frappe.db.sql(""" update `tabService Order` set fecha_pendiente = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
				else:
					if not self.fecha_pendiente:
						frappe.msgprint("inserte fecha pendiente")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						self.reload()
						return
					else:
						date = self.fecha_pendiente
				if time_diff_in_seconds(date,self.fecha_seguimiento) < 0:
					frappe.msgprint("Error en fecha y hora insertada")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return	
				if not self.venta_en_caliente:
					bitacora_orden = frappe.get_doc({
						"doctype": "Bitacora Orden",
						"detalle":"Orden cambió de estado Seguimiento a estado PENDIENTE",
						"fecha_transaccion": now(),
						"usuario":frappe.session.user,
						"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_seguimiento),
						"fecha_definida_por_usuario": date,
						"parent": self.name,
						"parentfield":"bitacora_orden",
						"parenttype": "Service Order",
						"idx":idx
						})
					bitacora_orden.insert(ignore_permissions=True)	
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'PENDIENTE')
		
		
		total_abierto = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado ABIERTO a estado SEGUIMIENTO' and parent = %(name)s; """, {"name":self.name})[0][0])
		total_seguimiento = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado SEGUIMIENTO a estado ATENDIDO' and parent = %(name)s; """, {"name":self.name})[0][0])
		total_atendido = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle in ('Orden cambió de estado ATENDIDO a estado PENDIENTE','Orden FINALIZADA') and parent = %(name)s; """, {"name":self.name})[0][0])
		total_pendiente = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado PENDIENTE a estado SEGUIMIENTO' and parent = %(name)s; """, {"name":self.name})[0][0])
		frappe.db.sql(""" update `tabService Order` set total_abierto = %(total_abierto)s, total_seguimiento = %(total_seguimiento)s, total_atendido = %(total_atendido)s, total_pendiente = %(total_pendiente)s where name = %(name)s""", {"total_abierto":total_abierto, "total_seguimiento":total_seguimiento, "total_atendido":total_atendido, "total_pendiente":total_pendiente,"name":self.name})			
		self.reload()
			
@frappe.whitelist()
def equipos_de_almacen(portafolio,tecnico):
	portafolio = portafolio.replace(" 3.0","")
	if "GPON" in portafolio:
		portafolio = "GPON"	
	if "IMOVIL" in portafolio:
		portafolio = "Wimax"
	portafolio = "%" + portafolio + "%"
	equipos = frappe.db.sql(""" select name from `tabSerial No` where item_group like %(portafolio)s AND warehouse in 
	(select almacen from `tabAlmacenes de Tecnico` where parent = %(tecnico)s);""",{"portafolio": portafolio, "tecnico":tecnico})
	equipo=''
	lista =[]
	for i in range(len(equipos)):
		equipo = str(equipos[i][0])
		lista.append(equipo)
	return lista

@frappe.whitelist()
def materiales_segun_portafolio(name):
	so = frappe.get_doc("Service Order", name)	
	if not so.productos and so.workflow_state in ["Abierto","Seguimiento"] and so.tipo_de_orden == 'INSTALACION':
		portafolio = ''
		for p in frappe.db.sql(""" select name from `tabKit de Materiales`;"""):
			if p[0] in so.portafolio:
				portafolio = p[0]
				break
			else:
				portafolio = so.portafolio	
		materiales = frappe.db.get_values("Detalle Kit Materiales",{"parent":portafolio},["item","qty","uom"])
		for m in materiales:
			nombre_bodega = ''
			bodegas = frappe.db.sql(""" select almacen from `tabAlmacenes de Tecnico` where parent = %(tecnico)s; """,{"tecnico":so.tecnico})
			for bodega in bodegas:
				if "USADO" not in (bodega[0]).upper():
					nombre_bodega = bodega[0]
			frappe.db.sql(""" insert into `tabMateriales detalles` 
			(name,material,cantidad,uom,parent,parentfield,parenttype,bodega) values 
			(%(name)s, %(material)s,%(cantidad)s,%(uom)s,%(parent)s,'productos','Service Order',%(bodega)s)""",{"name":randStr(chars='abcdefghijklmnopqrstuvwxyz1234567890'), "material": m[0], "cantidad": m[1],"uom":m[2] ,"parent": name, "bodega":nombre_bodega})

	
@frappe.whitelist()
def filtrar_almacen(name):

	almacen = []

	bodegas= frappe.db.sql("""select almacen from `tabAlmacenes de Tecnico` where parent in (select tecnico from `tabService Order` where name=%(name)s ) or parent in (select tecnico from `tabTecnicos Service Order`where parent=%(name)s);""",{"name":name})
	
	rol = consultar_rol()
		# return rol
	if 'Tecnico' in rol and 'System Manager' not in rol:
		bodegas= frappe.db.sql("""select almacen from `tabAlmacenes de Tecnico` where parent in (select name from `tabTecnico` where usuario_reporte = %(usuario)s);""",{"usuario":frappe.session.user})

	for bodega in bodegas:
		
		almacen.append(bodega[0])
			
	return almacen

@frappe.whitelist()
def filtrar_productos_disponibles_N(almacen):
	materiales = []
	item_codes= frappe.db.sql(""" select item_code from `tabItem`; """)

	for item in item_codes:	
			actual_qty = frappe.db.sql(""" select qty_after_transaction from `tabStock Ledger Entry` where item_code = %(item_code)s and 
				warehouse = %(bodega)s and is_cancelled = 0 order by (creation) desc limit 1 """,{"item_code":item[0],"bodega":almacen})
			try:
				actual_qty = actual_qty[0][0]
			except:
				actual_qty = 0
			if actual_qty > 0:
				materiales.append(item[0])
		
	return materiales

@frappe.whitelist()
def filtrar_encuesta(doctype,name):
	if frappe.db.exists("Feedback", {"tercero": name}):
		frappe.msgprint("Ya se ha respondido una encuesta para esta orden")
		return
	return [encuesta[0] for encuesta in frappe.db.get_values("Encuestas",{'modulo':doctype,'habilitado':1},'name')]

@frappe.whitelist()
def obtener_preguntas(encuesta):	
	preguntas = frappe.get_doc("Encuestas",encuesta)
	row = []
	for p in preguntas.preguntas:
		row.append([p.pregunta,p.respuestas])
	return row

@frappe.whitelist()
def guardar_encuesta(**args):
	encuesta = frappe.get_doc("Encuestas",args["id_encuesta"])
	lista_preg = []
	for p in encuesta.preguntas:
		lista_preg.append(p.pregunta)
	respuestas = json.loads(args["respuestas"])
	lista_resp = []
	for r in respuestas.values():
		lista_resp.append(r)
	
	feedback = frappe.new_doc('Feedback')
	feedback.encuesta = args["id_encuesta"]
	feedback.modulo = args["doctype"]
	feedback.tercero = args["name"]
	feedback.nombre = lista_resp.pop()
	for i in range(len(lista_preg)):
		row = {
			"pregunta":lista_preg[i],
			"respuesta":lista_resp[i]
		}
		feedback.append("feedback_preguntas", row)
	feedback.docstatus = 1
	feedback.save(ignore_permissions=True)

	frappe.db.sql("update `tabService Order` set feedback = %(feedback)s where name = %(name)s",{"feedback":feedback.name,"name":args["name"]})
	frappe.msgprint(frappe._('Encuesta {0} ha sido guardada').format(feedback.name))
	
def randStr(chars = string.ascii_uppercase + string.digits, N=4):
	return ''.join(random.choice(chars) for _ in range(N))


@frappe.whitelist()
def filtrar_ordenes_OyM():
	try:
		tecnico = frappe.db.get_value("Tecnico",{"usuario":frappe.session.user},"name")
		return tecnico
	except Exception as e:
		frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))

@frappe.whitelist()
def obtener_tasa_de_valoracion_por_item(item_code):
	
	if not frappe.db.exists("Item",item_code):
		return
	if frappe.db.get_value("Item",item_code,'item_group') in ('Instalacion y Configuracion', 'Consumible'):
		tasa = frappe.db.sql("""select valuation_rate from valoracion_item_erp where item_code = %(item_code)s
				and warehouse = 'Bodega Principal - NI' limit 1;""", {"item_code":item_code})
		if not tasa:
			tasa = frappe.db.sql("""select valuation_rate from valoracion_item_erp where item_code = %(item_code)s
				 limit 1;""", {"item_code":item_code})
		try:
			tasa = tasa[0][0]
		except:
			tasa = 0.00

		if tasa == 0.00:
			tasa = frappe.db.sql(""" select valor from tabItem_Price_ERP where item_code = %(item_code)s;""",{"item_code":item_code})
			try:
				tasa = tasa[0][0]
			except:
				tasa = 0.00
		if tasa == 0.00:
			tasa = frappe.db.sql("""  select valuation_rate from `tabStock Ledger Entry` WHERE item_code  = %(item_code)s 
				and warehouse = 'Bodega Central - NI' order by posting_date desc limit 1;""",{"item_code":item_code})
			try:
				tasa = tasa[0][0]
			except:
				tasa = 0.00
		if tasa ==0.00:
			tasa = frappe.db.sql(""" select (cast( price_list_rate as decimal(9,2) )* 
			(select cast(exchange_rate as decimal(9,2))  from `tabCurrency Exchange` where date = curdate() limit 1)) 
			as cambio from `tabItem Price` where currency='USD' and item_code = %(item_code)s """,{"item_code":item_code})
			try:
				tasa = tasa[0][0]
			except:
				tasa = 0.00		
		if tasa == 0.00:
			tasa = frappe.db.sql(""" select cast( price_list_rate as decimal(9,2)) as cambio 
			from `tabItem Price` where currency='NIO' and item_code = %(item_code)s """,{"item_code":item_code})
			try:
				tasa = float(tasa[0][0])
			except:
				tasa = 0.00
			if tasa == 0.00:
				tasa = frappe.db.get_value("Item",item_code,"standard_rate")

	else:
		tasa = frappe.db.sql("""select valuation_rate from valoracion_item_erp where item_code = %(item_code)s
				and warehouse = 'Bodega Principal - NI' limit 1;""", {"item_code":item_code})
		if not tasa:
			tasa = frappe.db.sql("""select valuation_rate from valoracion_item_erp where item_code = %(item_code)s
				 limit 1;""", {"item_code":item_code})
		try:
			tasa = tasa[0][0]
		except:
			tasa = 0.00

		if tasa == 0.00:
			tasa = frappe.db.sql(""" select valor from tabItem_Price_ERP where item_code = %(item_code)s;""",{"item_code":item_code})
			try:
				tasa = tasa[0][0]
			except:
				tasa = 0.00
		if tasa == 0.00:
			tasa = frappe.db.sql("""  select valuation_rate from `tabStock Ledger Entry` WHERE item_code  = %(item_code)s 
				and warehouse = 'Bodega Central - NI' order by posting_date desc limit 1;""",{"item_code":item_code})
			try:
				tasa = float(tasa[0][0])
			except:
				tasa = 0.00
		if tasa == 0.00:
			tasa = frappe.db.sql(""" select cast( price_list_rate as decimal(9,2)) as cambio 
			from `tabItem Price` where currency='NIO' and item_code = %(item_code)s """,{"item_code":item_code})
			try:
				tasa = float(tasa[0][0])
			except:
				tasa = 0.00
		if tasa == 0.00:
			tasa = frappe.db.get_value("Item",item_code,"standard_rate")
	return tasa
	

@frappe.whitelist()
def crear_sub_orden(tipo_de_orden,name):
	orden_inst = frappe.get_doc("Service Order",name)
	suborden = frappe.new_doc('Service Order')
	suborden.fecha_solicitud = now()
	suborden.nombre = orden_inst.nombre
	suborden.tipo_de_orden = tipo_de_orden
	suborden.tipo = orden_inst.tipo
	suborden.tercero = orden_inst.tercero
	suborden.tipo_de_origen = 'Service Order'
	suborden.nombre_de_origen = orden_inst.name
	suborden.plan_de_subscripcion = orden_inst.plan_de_subscripcion
	suborden.portafolio = orden_inst.portafolio
	suborden.telefonos = orden_inst.telefonos
	suborden.informacion_de_contacto = orden_inst.informacion_de_contacto
	suborden.venta_en_caliente = orden_inst.venta_en_caliente
	suborden.tipo_cliente = orden_inst.tipo_cliente
	suborden.descripcion = orden_inst.descripcion
	suborden.direccion_de_instalacion = orden_inst.direccion_de_instalacion
	suborden.direccion = orden_inst.direccion
	suborden.departamento = orden_inst.departamento
	suborden.municipio = orden_inst.municipio
	suborden.barrio = orden_inst.barrio
	suborden.nodo = orden_inst.nodo
	suborden.latitud = orden_inst.latitud
	suborden.longitud = orden_inst.longitud
	suborden.coordenadas = orden_inst.coordenadas
	suborden.workflow_state = 'Abierto'
	suborden.save()

	subordenes = frappe.get_doc({
		"doctype": "Issue Detalle",
		"issue" :suborden.name,
		"tipo_documento":'Service Order',
		"estado":suborden.workflow_state,
		"tipo":tipo_de_orden,
		"problema":suborden.descripcion,
		"parent": name,
		"parentfield":"subordenes",
		"parenttype": "Service Order",
	})
	subordenes.insert(ignore_permissions=True)
	frappe.msgprint(frappe._('Nueva Orden de {0} con ID {1}').format(suborden.tipo_de_orden,frappe.utils.get_link_to_form("Service Order", suborden.name)))


@frappe.whitelist()
def validar_equipo_almacen(equipo, orden,tecnicos):
	# frappe.msgprint(frappe._('Nueva Orden de {0} ').format(tecnicos))
	tecnicos=str(tecnicos)
	tecnicos = tecnicos.replace('[','(')
	tecnicos = tecnicos.replace(']',')')
	#frappe.msgprint(frappe._('{0} ').format(tecnicos))
	warehouse_equipo = frappe.db.get_value("Serial No",equipo,"warehouse")
	query = f"select almacen from `tabAlmacenes de Tecnico` where parent in {tecnicos}"
	#frappe.msgprint(query)
	almacenes_de_tecnico = [a[0] for a in frappe.db.sql(query)]	
	if warehouse_equipo not in almacenes_de_tecnico:
		return equipo
	else:
		return "pasa"

@frappe.whitelist()
def obtener_item_code(serial_no):
	try:
		return frappe.db.sql("select item_code from `tabSerial No` where name = %(serial_no)s",{"serial_no":serial_no})[0][0]
	except:
		return 


def definir_combos(susc):
	combos = tv = gpon = hfc = tv_gpon = tv_hfc = 0
	hay_combo = False 

	for plan in susc.plans:
		if plan.es_combo==1:
			combos +=1
			hay_combo = True
			if "GPON" in plan.plan:
					gpon += 1
			elif "HFC" in plan.plan:
					hfc += 1			
		if 'TV Combo GPON' in plan.plan or 'TV Combo HFC' in plan.plan:
			tv += 1
			if 'TV Combo GPON' in plan.plan:
				tv_gpon +=1
			elif 'TV Combo HFC' in plan.plan:
				tv_hfc +=1
	if tv == combos and hfc == tv_hfc and gpon == tv_gpon and hay_combo:
		return True
	else:
		return False