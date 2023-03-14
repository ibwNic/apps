# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
#modificado 23/01/23
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
from erpnext.aprovisionamiento_api import eliminarAprovisionador


class ServiceOrder(Document):

	def on_update(self):
		
		
		if self.workflow_state == "Finalizado":
			if self.tipo_de_origen == 'Gestion':
				frappe.db.sql("update `tabIssue Detalle` set estado = %(estado)s where issue = %(so)s;",{"estado":self.workflow_state,"so":self.name})		
			try:
				solucion = self.solucion
			except:
				solucion = None
			if not solucion:
				frappe.msgprint("Inserte una solución")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
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
					'tipo': 'Prospect',
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
					'opportunity_prospect': self.opportunity_prospect,
					'site_order': self.name,
					'latitud': self.latitud,
					'longitud': self.longitud,
					#'tecnico':self.tecnico,
					'nodo':self.nodo
				})	
				od.insert(ignore_permissions=True)
				frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
				frappe.db.set_value("Service Order", self.name,"site_order",od.name)	
				item_name = frappe.db.get_value("Item",{"name": self.item_opportunity},"item_name")
				opportunity_prospect = frappe.get_doc("Opportunity Prospect", {"name": self.opportunity_prospect})
				if opportunity_prospect.proveedor_section == 'IBW':
					rate = (float(opportunity_prospect.tasa) * float(opportunity_prospect.uom.replace(' Mbps', '')))/float(opportunity_prospect.compresion.replace(':1',''))
				else:
					rate = 0
				cambio = frappe.db.get_value("Currency Exchange",{"date":today()},"exchange_rate")			
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
					'parentfield' : 'items'
				})	
				oi.insert(ignore_permissions=True)
				
			if self.tipo_de_orden == "PRESUPUESTO" and self.factible == 'El proyecto es factible':
				equipos = frappe.db.sql(""" select count(*) from `tabEquipos BOM` where parent = %(parent)s """, {"parent": self.name})
				try:
					equipos = int(equipos[0][0])
				except:
					equipos = 0
				if equipos < 1:
					frappe.msgprint(f"Debe insertar al menos un equipo en el BOM de Materiales")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return 
				
				ootc = frappe.get_doc({
					'doctype': "Opportunity Item OTC",
					'item': 'Instalacion y Configuracion',
					'qty': 1,
					'proveedor':self.proveedor_section,
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

			if self.tipo_de_orden == "SUSPENSION" and  self.tipo_de_origen=='Suspensiones':	
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
								frappe.msgprint('suspenderAprovisionador("suspenderYota",equipo.equipos)')
								#suspenderAprovisionador("suspenderYota",equipo.equipos)
							else:
								frappe.msgprint('suspenderAprovisionador("suspenderNetspan",equipo.equipos)')
								# suspenderAprovisionador("suspenderNetspan",equipo.equipos)
							susp = True
						if 'HFC' in self.portafolio:
							frappe.msgprint('suspenderAprovisionador("suspenderHfc",equipo.equipos)' + ' ' + equipo.equipos)
							# suspenderAprovisionador("suspenderHfc",equipo.equipos)
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

			if self.tipo_de_orden == "DESINSTALACION" and  self.tipo_de_origen=='Subscription':	
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
								frappe.msgprint('eliminarAprovisionador ("eliminarYota",equipo.serial_no)')
								#eliminarAprovisionador ("eliminarYota",equipo.serial_no)
							else:
								frappe.msgprint('eliminarAprovisionador ("eliminarNetspan",equipo.serial_no)')
								# eliminarAprovisionador ("eliminarNetspan",equipo.serial_no)
							aprov = True
						if 'HFC' in self.portafolio:
							frappe.msgprint('eliminarAprovisionador ("eliminarHFC",equipo.serial_no)' + ' ' + equipo.serial_no)
							# eliminarAprovisionador ("eliminarHFC",equipo.serial_no)
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
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"detalle":"Plan desinstalado",
					"fecha": now(),
					"usuario":frappe.session.user,
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"Service Order",
					"tercero":self.name
					})
				bitacora_detalle.insert(ignore_permissions=True)

		
			if self.tipo_de_orden == "INSTALACION" and  self.tipo_de_origen=='Subscription':		
				susc = frappe.get_doc("Subscription", {"name": self.nombre_de_origen})	
				if int(susc.periodo_de_facturacion)>1:
					p = add_months(self.fecha_finalizado, int(susc.periodo_de_facturacion)-1)
				else:
					p=self.fecha_finalizado
				p = formatdate(frappe.utils.get_last_day(p), "yyyy-MM-dd")
				hay_planes_activos = False
				for plan in susc.plans:
					if plan.estado_plan == 'Activo':
						hay_planes_activos = True
				if hay_planes_activos and susc.tipo_contrato=='NUEVO':
				
					susc.update(
						{
							'workflow_state':'Instalado'
						}
						)
					susc.save()
					
				else:
					susc.update(
						{
							'current_invoice_start': date,
							'current_invoice_end':p,
							'workflow_state':'Instalado'
						}
						)
					susc.save()
					# frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Instalado', current_invoice_start = %(fecha_finalizado)s , current_invoice_end = %(current_invoice_end)s where name =%(nombre_de_origen)s;""",{"fecha_finalizado":self.fecha_finalizado,"current_invoice_end":p,"nombre_de_origen":self.nombre_de_origen})
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
					if plan.plan == 'TV Combo GPON' or plan.plan == 'TV Combo HFC':
						tv += 1
						if plan.plan == 'TV Combo GPON':
							tv_gpon +=1
						elif plan.plan == 'TV Combo HFC':
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
							spd.save()
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
							bitacora_detalle = frappe.get_doc({
								"doctype": "Detalle Bitacora Planes",
								"detalle":"Plan Activado",
								"fecha": now(),
								"usuario":frappe.session.user,
								"parent": bitacora_plan.name,
								"parentfield":"detalle",
								"parenttype": "Bitacora de Planes",
								"tipo_transaccion":"Service Order",
								"tercero":self.name
								})
							bitacora_detalle.insert(ignore_permissions=True)
						elif "TV" in plan.plan:
							spd.update(
								{
									'estado_plan': 'Activo',
									'longitud':self.longitud,
									'latitud':self.latitud,
									'service_start':date,
									'nodo':self.nodo
								}
							)
							spd.save()
				else:
					spd = frappe.get_doc("Subscription Plan Detail", {"name": self.plan_de_subscripcion})
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
					spd.save()
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
						
					bitacora_detalle = frappe.get_doc({
						"doctype": "Detalle Bitacora Planes",
						"detalle":"Plan Activado",
						"fecha": now(),
						"usuario":frappe.session.user,
						"parent": bitacora_plan.name,
						"parentfield":"detalle",
						"parenttype": "Bitacora de Planes",
						"tipo_transaccion":"Service Order",
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
						
				cust = frappe.get_doc("Customer", {"name": self.tercero})
				cust.update(
					{
						'estado_cliente': 'ACTIVO',
						'item_group':insert_portafolio[0][0] 
					}
				)
				cust.save()

			if self.tipo_de_orden == "REACTIVACION" and  self.tipo_de_origen=='Subscription':
			
				upd_spd = frappe.get_doc("Subscription Plan Detail", {"name": self.plan_de_subscripcion})
				upd_spd.update(
							{
								"estado_plan": "Activo",
								"service_reactivation": now(),
							})
				upd_spd.save()
				frappe.db.commit()
				upd_sus = frappe.get_doc("Subscription", {"name": upd_spd.parent})
				posting_date = frappe.db.sql(""" select posting_date from `tabSales Invoice` where customer = %(customer)s order by posting_date desc limit 1;""",{"customer":upd_sus.party})
			
				if frappe.utils.formatdate(posting_date[0][0], "MMMM") == frappe.utils.formatdate(today(), "MMMM"):
					workflow_state = 'Activo'
				else:
					workflow_state = 'Instalado'
				upd_sus.update(
							{
								"workflow_state":workflow_state,
								"current_invoice_start":today(),
								"current_invoice_end": formatdate(frappe.utils.get_last_day(today()), "yyyy-MM-dd")
							})
				upd_sus.save()
				frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'ACTIVO' where name = %(customer)s; """,{"customer":upd_sus.party})
				
				if upd_spd.plan not in ('TV Combo GPON','TV Combo HFC'):
					if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion}):
						bitacora_plan = frappe.get_doc({
							'doctype': "Bitacora de Planes",
							'plan': upd_spd.plan,
							'cliente':  upd_sus.party,
							'estado_plan': "Activo",
							'direccion': upd_spd.direccion,
							'currency': upd_spd.currency,
							'costo':upd_spd.cost,
							'intervalo_de_facturacion':upd_spd.billing_interval_count,
							'subscription_plan_detail': upd_spd.name

						})
						bitacora_plan.insert(ignore_permissions=True)
					
					bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": self.plan_de_subscripcion})
							
					bitacora_detalle = frappe.get_doc({
						"doctype": "Detalle Bitacora Planes",
						"detalle":"Plan reactivado",
						"fecha": now(),
						"usuario":frappe.session.user,
						"parent": bitacora_plan.name,
						"parentfield":"detalle",
						"parenttype": "Bitacora de Planes",
						"tipo_transaccion":"Service Order",
						"tercero":self.name
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
								frappe.msgprint("""cambiarVelocidadAprovisionador("cambiarVelocidadYota",equipo.serial_no,frappe.db.get_value("Aprovisionamiento",{"mac":equipo.serial_no},'provisor_speed_id'))""")
								#cambiarVelocidadAprovisionador("cambiarVelocidadYota",equipo.serial_no,frappe.db.get_value("Aprovisionamiento",{"mac":equipo.serial_no},'provisor_speed_id'))
							else:
								frappe.msgprint('activarAprovisionador("activarNetspan",equipo.serial_no)')
								# activarAprovisionador("activarNetspan",equipo.serial_no)
							actv = True
						if 'HFC' in self.portafolio:
							frappe.msgprint('activarAprovisionador("activarHfc",equipo.serial_no)' + ' ' + equipo.serial_no)
							# activarAprovisionador("activarHfc",equipo.serial_no)
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
				# except Exception as e:
				# 	frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))
			
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

			if self.tipo_de_orden == "INSTALACION":
				equipos = frappe.db.sql(""" select count(*) from `tabEquipo_Orden_Servicio` where parent = %(parent)s """, {"parent": self.name})
				try:
					equipos = int(equipos[0][0])
				except:
					equipos = 0
				if self.portafolio in ['GPON','GPON-CORPORATIVO','GPON-INT-PYME','GPON-INT-RESIDENCIAL','GPON-TV-CORPORATIVO','GPON-TV-PYME','GPON-TV-RESIDENCIAL','HFC', 'HFC 3.0', 'IMOVIL', 'INET', 'Wimax']:
					if equipos < 1:
						frappe.msgprint(f"El portafolio {self.portafolio} debe tener al menos un item")
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
						frappe.msgprint(f"El portafolio {self.portafolio} debe tener al menos un SIM Card y un segundo item")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						self.reload()
						return
				almacenes = []
				if frappe.db.exists("Almacenes de Tecnico",{'parent':self.tecnico},"almacen"):
					for almacen in frappe.db.get_values("Almacenes de Tecnico",{'parent':self.tecnico},"almacen"):
						almacenes.append(almacen[0])
				else:
					frappe.msgprint("El tecnico no tiene bodegas asignadas")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return
				if len(self.equipo_orden_servicio) > 0:
					for equipo in self.equipo_orden_servicio:
						if frappe.db.get_value("Serial No",equipo.serial_no,"warehouse") not in almacenes:							
							frappe.msgprint("El equipo " + equipo.serial_no + " no pertenece a la bodega del técnico")
							frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
							self.reload()
							return
								
								
						
			if not solucion:
				frappe.msgprint("Inserte una solución")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
				self.reload()
				return
			try:
				tecnico = self.tecnico
			except:
				tecnico = None
			if self.tipo_de_orden not in ('SUSPENSION','REACTIVACION','CORTE','RECONEXION','APROVISIONAMIENTO'):
				if not tecnico or tecnico=="":
					frappe.msgprint("Asigne un técnico para esta orden de servicio")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return				
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
				spd.update({
							'direccion':self.direccion_de_traslado,
							'address_line':self.nueva_direccion,
							'latitud':self.latitud_traslado,
							'longitud':self.longitud_traslado,
							'nodo':nuevo_nodo
						})
				spd.save(ignore_permissions=True)
				#nueva direccion al plan
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
					frappe.msgprint("Error en fecha y hora insertada")
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
		# 	lista_materiales = frappe.get_doc({
		# 		"doctype": "Materiales detalles",
		# 		"material": m[0],
		# 		"cantidad":m[1],
		# 		"parent": name,
		# 		"parentfield":"productos",
		# 		"parenttype": "Service Order",
		# 		})
		# 	lista_materiales.insert()			
		# 	lista_materiales.save()
		# frappe.db.commit()
	
@frappe.whitelist()
def filtrar_productos_disponibles(tecnico):
	materiales = []
	almacen = []
	item_codes= frappe.db.sql(""" select item_code from `tabItem`; """)
	bodegas = frappe.db.sql(""" select almacen from `tabAlmacenes de Tecnico` where parent = %(tecnico)s; """,{"tecnico":tecnico})
	for item in item_codes:	
		for bodega in bodegas:
			if "USADO" not in (bodega[0]).upper():
				actual_qty = frappe.db.sql(""" select qty_after_transaction from `tabStock Ledger Entry` where item_code = %(item_code)s and 
					warehouse = %(bodega)s and is_cancelled = 0 order by (creation) desc limit 1 """,{"item_code":item[0],"bodega":bodega[0]})
				try:
					actual_qty = actual_qty[0][0]
				except:
					actual_qty = 0
				if actual_qty > 0:
					almacen.append(bodega[0])
					materiales.append(item[0])
		
	return materiales,almacen
	
@frappe.whitelist()
def filtrar_productos_disponibles_usados(tecnico):
	materiales = []
	almacen = []
	item_codes= frappe.db.sql(""" select item_code from `tabItem`; """)
	bodegas = frappe.db.sql(""" select almacen from `tabAlmacenes de Tecnico` where parent = %(tecnico)s; """,{"tecnico":tecnico})
	for item in item_codes:
		for bodega in bodegas:
			if "USADO" in (bodega[0]).upper():
				
				actual_qty = frappe.db.sql(""" select qty_after_transaction from `tabStock Ledger Entry` where item_code = %(item_code)s and 
					warehouse = %(bodega)s and is_cancelled = 0 order by (creation) desc limit 1 """,{"item_code":item[0],"bodega":bodega[0]})
				try:
					actual_qty = actual_qty[0][0]
				except:
					actual_qty = 0
				if actual_qty > 0:
					almacen.append(bodega[0])
					materiales.append(item[0])
		
	return materiales,almacen

@frappe.whitelist()
def filtrar_encuesta(doctype,name):
	if frappe.db.exists("Feedback", {"tercero": name}):
		frappe.msgprint("Ya se ha respondido una encuesta para esta orden")
		return
	return [encuesta[0] for encuesta in frappe.db.get_values("Encuestas",{'modulo':doctype},'name')]

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
	feedback.save()
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