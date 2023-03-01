# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
import json
import time
from datetime import timedelta
from frappe.utils import random_string
import frappe
from frappe import _
from frappe.core.utils import get_parent_doc
from frappe.email.inbox import link_communication_to_document
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.recorder import status
from frappe.utils import date_diff, get_datetime, now_datetime, now,time_diff_in_seconds, unique

from frappe.utils.data import today

from frappe.utils.user import is_website_user
from pymysql import NULL

class Gestion(Document):
	
	def on_update(self):
		if self.workflow_state == 'Finalizado':
			if self.tipo_gestion == 'Cancelaciones':
				if self.estado_cancelacion == 'Aceptada':
					frappe.db.sql(""" update `tabGestion` set estado = 'Aceptado' where name = %(name)s; """,{"name":self.name})
				# elif self.estado_cancelacion == 'Retenida' and self.medida_retencion:
				# 	frappe.db.sql(""" update `tabGestion` set estado = 'Finalizado' where name = %(name)s; """,{"name":self.name})
			else:
				frappe.db.sql(""" update `tabGestion` set estado = 'Finalizado' where name = %(name)s; """,{"name":self.name})
		if self.workflow_state == 'En Proceso':
			if self.tipo_gestion == 'Suspension Temporal':
				if not self.fecha_inicio_suspension_temporal:
					frappe.msgprint("ingresar fecha de suspensión temporal")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
					self.reload()
					return
		self.reload()


@frappe.whitelist()		
def validar_cliente(customer,tipo_gestion):
	query = frappe.db.sql(""" select distinct customer, name from  `tabGestion` where workflow_state not in ('Finalizado', 'Cancelado') 
	and tipo_gestion = %(tipo_gestion)s;""",{"tipo_gestion":tipo_gestion})
	clientes = [c[0] for c in query]
	names = [n[1] for n in query]
	if customer in clientes:
		frappe.msgprint(frappe._('El cliente {0} tiene una gestion de tipo {1} no finalizada').format(customer,tipo_gestion),"No se pudo crear la gestion")
		return names[clientes.index(customer)] 	

@frappe.whitelist()
def get_address(customer):
		get_add = frappe.db.sql(
			"""select departamento, municipio, barrio from `tabAddress` where is_primary_address = 1 
			and name in (select parent from `tabDynamic Link` where link_name = %(customer)s) limit 1; """,
			{"customer": customer},
		)	
	
		return get_add	

@frappe.whitelist()
def obtener_clientes_con_contratos():
	contratos = frappe.db.sql(""" select party from `tabSubscription` where workflow_state='Activo';""")
	return [c[0] for c in contratos]

@frappe.whitelist()
def obtener_planes_de_cliente(customer, tipo_gestion):
	g = frappe.new_doc('Gestion')
	g.update({
		'customer': customer,	
		'tipo_gestion': tipo_gestion
	})
	contratos = frappe.db.get_values("Subscription",{"party":customer, "workflow_state":"Activo"},'name')
	contratos = [c[0] for c in contratos]
	if contratos:
		planes = frappe.db.sql("""select name, plan, parent from `tabSubscription Plan Detail` where parent in %(parent)s and estado_plan = "Activo";""",{"parent":contratos})
		for plan in planes:
			item1 = g.append('cambiar_planes', {"plan": ""})
			item1.plan = plan[0]				
			item1.plan_name = plan[1]
			item1.contrato = plan[2]			
	return {'docs': g.as_dict()}	


@frappe.whitelist()
def estado_gestion(name):
	try:
		gestion = frappe.get_doc("Gestion",name)
		if gestion.estado_cancelacion == 'Aceptada':
			frappe.db.sql(""" update `tabGestion` set estado = 'Aceptado' where name = %(name)s; """,{"name":name})
		elif gestion.estado_cancelacion == 'Retenida' and gestion.medida_retencion:
			frappe.db.sql(""" update `tabGestion` set estado = 'Retenido' where name = %(name)s; """,{"name":name})
	except:
		pass

@frappe.whitelist()
def ocultar_actualizacion(name):
	g = frappe.get_doc("Gestion",name)
	if g.tipo_gestion != 'Cancelaciones':
		return
	nc = 0
	for plan in g.cambiar_planes:
		if plan.nuevo_contrato:
			nc += 1
	if nc ==len(g.cambiar_planes):
		frappe.db.set_value("Gestion",name,"convertido",1)

@frappe.whitelist()
def ocultar_orden_servicio(name):
	g = frappe.get_doc("Gestion",name)
	if g.tipo_gestion != 'Tramites':
		return
	con_orden = 0
	os = 0
	for iss in g.issue:
		if iss.tipo == 'Tramite' and iss.estado == 'Finalizado':
			con_orden += 1
		if iss.tipo != 'Tramite':
			os +=1
	if con_orden == len(g.issue) - os:
		frappe.db.set_value("Gestion",name,"convertido",1)

@frappe.whitelist()
def generar_orden_de_servicio(name):
	gestion = frappe.get_doc("Gestion",name)
	if gestion.tipo_gestion != "Tramites":
		return
	if gestion.subgestion == 'Traslado de Servicio':
		for iss in gestion.issue:
			if frappe.db.exists("Issue",iss.issue):
				incidencia = frappe.get_doc("Issue",iss.issue)
				if incidencia.workflow_state != 'Finalizado':
					frappe.msgprint("Debe finalizar la incidencia " + iss.issue)
					continue
				#creacion de orden
				spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
				od = frappe.get_doc({
					'doctype': "Service Order",
					'tipo_de_orden': "TRASLADO",
					'workflow_state': "Abierto",
					'tipo_de_origen': "Gestion",
					'nombre_de_origen': name,
					'descripcion': frappe._('Ejecutar TRASLADO de {0}').format(spd.plan),
					'tipo': 'Customer',
					'nombre':frappe.db.get_value("Customer",gestion.customer,'customer_name'),
					'tercero': gestion.customer,
					'plan_de_subscripcion': spd.name,
					'direccion_de_instalacion': spd.direccion,
					'portafolio': incidencia.servicio,
					'departamento': incidencia.departamento,
					'municipio': incidencia.municipio,
					'barrio': incidencia.barrio,
					'direccion': incidencia.address_line1,
					'latitud':spd.latitud,
					'longitud':spd.longitud,
					'nodo':spd.nodo
				})
				od.insert(ignore_permissions=True)
				frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
				doc = frappe.get_doc("Subscription",spd.parent)
				for equipos in doc.equipos:
					ran = random_string(6)
					ran = ran + equipos.name
					if name==equipos.plan:
						code = frappe.db.get_value('Serial No', {"name": equipos.equipo}, 'item_code')
						frappe.db.sql(""" insert into `tabEquipo_Orden_Servicio` (name,serial_no,parent,parenttype,parentfield,item_code) 
							values (%(name)s,%(serial_no)s,%(parent)s,'Service Order','equipo_orden_servicio',%(item_code)s) """, {"name":ran,"serial_no":equipos.equipo,"parent":od.name,"item_code":code})
				tab_issue = frappe.get_doc({
					"doctype": "Issue Detalle",
					"issue":od.name,
					"tipo_documento":od.doctype,
					"estado":od.workflow_state,
					"tipo":od.tipo_de_orden,
					"problema":od.descripcion,
					"parent": name,
					"parentfield":"issue",
					"parenttype": "Gestion",
				})
				tab_issue.insert(
					ignore_permissions=True,
 					ignore_links=True
				)

	elif gestion.subgestion == 'Solicitud TV Adicional':
		for iss in gestion.issue:
			if frappe.db.exists("Issue",iss.issue):
				incidencia = frappe.get_doc("Issue",iss.issue)
				if incidencia.workflow_state != 'Finalizado':
					frappe.msgprint("Debe finalizar la incidencia " + iss.issue)
					continue
				#creacion de orden
				spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
				od = frappe.get_doc({
					'doctype': "Service Order",
					'tipo_de_orden': "TV ADICIONAL",
					'workflow_state': "Abierto",
					'tipo_de_origen': "Gestion",
					'nombre_de_origen': name,
					'descripcion': frappe._('Ejecutar instalación TV ADICIONAL de {0}').format(spd.plan),
					'tipo': 'Customer',
					'nombre':frappe.db.get_value("Customer",gestion.customer,'customer_name'),
					'tercero': gestion.customer,
					'plan_de_subscripcion': spd.name,
					'direccion_de_instalacion': spd.direccion,
					'portafolio': incidencia.servicio,
					'departamento': incidencia.departamento,
					'municipio': incidencia.municipio,
					'barrio': incidencia.barrio,
					'direccion': incidencia.address_line1,
					'latitud':spd.latitud,
					'longitud':spd.longitud,
					'nodo':spd.nodo
				})
				od.insert(ignore_permissions=True)
				frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
				tab_issue = frappe.get_doc({
					"doctype": "Issue Detalle",
					"issue":od.name,
					"tipo_documento":od.doctype,
					"estado":od.workflow_state,
					"tipo":od.tipo_de_orden,
					"problema":od.descripcion,
					"parent": name,
					"parentfield":"issue",
					"parenttype": "Gestion",
				})
				tab_issue.insert(
					ignore_permissions=True,
 					ignore_links=True
				)
	elif gestion.subgestion == 'Solicitud Cableado':
		for iss in gestion.issue:
			if frappe.db.exists("Issue",iss.issue):
				incidencia = frappe.get_doc("Issue",iss.issue)
				if incidencia.workflow_state != 'Finalizado':
					frappe.msgprint("Debe finalizar la incidencia " + iss.issue)
					continue
				#creacion de orden
				spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
				od = frappe.get_doc({
					'doctype': "Service Order",
					'tipo_de_orden': "CABLEADO",
					'workflow_state': "Abierto",
					'tipo_de_origen': "Gestion",
					'nombre_de_origen': name,
					'descripcion': frappe._('Ejecutar CABLEADO de {0}').format(spd.plan),
					'tipo': 'Customer',
					'nombre':frappe.db.get_value("Customer",gestion.customer,'customer_name'),
					'tercero': gestion.customer,
					'plan_de_subscripcion': spd.name,
					'direccion_de_instalacion': spd.direccion,
					'portafolio': incidencia.servicio,
					'departamento': incidencia.departamento,
					'municipio': incidencia.municipio,
					'barrio': incidencia.barrio,
					'direccion': incidencia.address_line1,
					'latitud':spd.latitud,
					'longitud':spd.longitud,
					'nodo':spd.nodo
				})
				od.insert(ignore_permissions=True)
				frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
				tab_issue = frappe.get_doc({
					"doctype": "Issue Detalle",
					"issue":od.name,
					"tipo_documento":od.doctype,
					"estado":od.workflow_state,
					"tipo":od.tipo_de_orden,
					"problema":od.descripcion,
					"parent": name,
					"parentfield":"issue",
					"parenttype": "Gestion",
				})
				tab_issue.insert(
					ignore_permissions=True,
 					ignore_links=True
				)
	elif gestion.subgestion == 'Reconexión':
		for iss in gestion.issue:
			if frappe.db.exists("Issue",iss.issue):
				incidencia = frappe.get_doc("Issue",iss.issue)
				if incidencia.workflow_state != 'Finalizado':
					frappe.msgprint("Debe finalizar la incidencia " + iss.issue)
					continue
				#creacion de orden
				spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
				od = frappe.get_doc({
					'doctype': "Service Order",
					'tipo_de_orden': "RECONEXION",
					'workflow_state': "Abierto",
					'tipo_de_origen': "Gestion",
					'nombre_de_origen': name,
					'descripcion': frappe._('Ejecutar RECONEXION de {0}').format(spd.plan),
					'tipo': 'Customer',
					'nombre':frappe.db.get_value("Customer",gestion.customer,'customer_name'),
					'tercero': gestion.customer,
					'plan_de_subscripcion': spd.name,
					'direccion_de_instalacion': spd.direccion,
					'portafolio': incidencia.servicio,
					'departamento': incidencia.departamento,
					'municipio': incidencia.municipio,
					'barrio': incidencia.barrio,
					'direccion': incidencia.address_line1,
					'latitud':spd.latitud,
					'longitud':spd.longitud,
					'nodo':spd.nodo
				})
				od.insert(ignore_permissions=True)
				frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
				tab_issue = frappe.get_doc({
					"doctype": "Issue Detalle",
					"issue":od.name,
					"tipo_documento":od.doctype,
					"estado":od.workflow_state,
					"tipo":od.tipo_de_orden,
					"problema":od.descripcion,
					"parent": name,
					"parentfield":"issue",
					"parenttype": "Gestion",
				})
				tab_issue.insert(
					ignore_permissions=True,
 					ignore_links=True
				)
def programar_suspensiones_temporales():
	""" suspender planes, contratos y clientes desde gestiones finalizadas """
	gestiones = frappe.db.sql(""" select name, customer from `tabGestion` where tipo_gestion = 'Suspension Temporal' and workflow_state = 'Finalizado' and fecha_inicio_suspension_temporal = CURDATE() and convertido = 0;""")
	for g in gestiones:
		for p in frappe.db.get_values("Detalle Cambio de Razon Social", {"parenttype":"Gestion","parent":g[0]},"plan"):
			if p[0]:
				spd = frappe.get_doc("Subscription Plan Detail", {"name": p[0]})
				# spd.update(
				# 	{
				# 	"estado_plan": "SUSPENDIDO: Temporal",
				# 	"service_suspend": now(),
				# 	}
				# )
				frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan =  'SUSPENDIDO: Temporal', service_suspend = %(service_suspend)s where name = %(name)s;""", {"service_suspend": now(),"name":p[0]})
				#spd.save()
				# frappe.db.commit()
				p_susp = 0
				susc = frappe.get_doc("Subscription",spd.parent)
				for p in susc.plans:
					if p.estado_plan not in ('Activo','Inactivo'):
						p_susp += 1
				
				if p_susp == len(susc.plans):
					frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Suspendido' where name = %(subsc)s; """,{"subsc":spd.parent})
								
				susc_cliente = frappe.db.get_values("Subscription",{"party":g[1],"workflow_state":["in",["Activo","Instalado"]]},"name")
				if len(susc_cliente) == 0:
					frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'SUSPENDIDO (Temporal)' where name = %(customer)s; """,{"customer":g[1]})

				if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": spd.name}):
					bitacora_plan = frappe.get_doc({
						'doctype': "Bitacora de Planes",
						'plan': spd.plan,
						'cliente':  g[1],
						'estado_plan': "SUSPENDIDO: Temporal",
						# 'direccion': spd.direccion,
						'currency': spd.currency,
						'costo':spd.cost,
						'intervalo_de_facturacion':spd.billing_interval_count,
						'subscription_plan_detail': spd.name

					})
					bitacora_plan.insert()					
				bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": spd.name})						
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"detalle":"Plan suspendido temporal",
					"fecha": now(),
					#"usuario":frappe.session.user,
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes"
					})
				bitacora_detalle.insert()	
		frappe.db.sql(""" update `tabGestion` set convertido = 1 where name = %(name)s;""",{"name":g[0]})

def get_portafolio_plan(plan):
	portafolio = frappe.db.sql(
	"""Select t1.item_group
	from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item where t2.name=%(plan)s limit 1 """,
	{"plan": plan},)
	return portafolio


def programar_cancelaciones():
	""" cancelar planes, contratos y clientes desde gestiones finalizadas """
	gestiones = frappe.db.sql(""" select name, customer, motivo from `tabGestion` where tipo_gestion = 'Cancelaciones' and workflow_state = 'Finalizado' and estado = 'Aceptado' and convertido = 0; """)
	for g in gestiones:
		for p in frappe.db.get_values("Detalle Cambio de Razon Social", {"parenttype":"Gestion","parent":g[0]},"plan"):
			if p[0]:
				spd = frappe.get_doc("Subscription Plan Detail", {"name": p[0]})
					# spd.update(
				# 	{
				# 	"estado_plan": "SUSPENDIDO: Temporal",
				# 	"service_suspend": now(),
				# 	}
				# )
				frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan =  'Plan Cerrado', service_end = %(service_end)s, motivo_finalizado = %(motivo)s where name = %(name)s;""", {"service_end": now(),"name":p[0], "motivo":g[2]})
				#spd.save()
				# frappe.db.commit()
				p_cerrados = 0
				susc = frappe.get_doc("Subscription",spd.parent)
				for plan in susc.plans:
					if plan.estado_plan not in ('Activo','Inactivo','SUSPENDIDO: Manual','SUSPENDIDO: Temporal'):
						p_cerrados += 1
				if p_cerrados == len(susc.plans):
					frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Terminado' where name = %(subsc)s; """,{"subsc":spd.parent})
				susc_cliente = frappe.db.get_values("Subscription",{"party":g[1],"workflow_state":["in",["Activo","Instalado"]]},"name")
				if len(susc_cliente) == 0:
					frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'TERMINADO' where name = %(customer)s; """,{"customer":g[1]})
				
				#ordenes de desinstalacion		
				portafolio=get_portafolio_plan(spd.plan)
				direccion=frappe.get_doc("Address", spd.direccion)

				od = frappe.new_doc('Service Order')
				od.tipo_de_orden = "DESINSTALACION"
				od.workflow_state =  "Abierto"
				od.tipo_de_origen = "Subscription"
				od.nombre_de_origen = spd.parent
				od.descripcion = frappe._('Ejecutar Desinstalación de {0}').format(spd.plan)
				od.tipo = 'Customer'
				od.tercero = g[1]
				od.nombre = frappe.db.get_value("Customer",g[1],"customer_name")
				od.plan_de_subscripcion = spd.name
				od.direccion_de_instalacion = spd.direccion
				od.portafolio = str(portafolio[0][0])
				od.departamento = direccion.departamento
				od.municipio = direccion.municipio
				od.barrio = direccion.barrio
				od.direccion = direccion.address_line1
				od.vendedor = susc.vendedor
				od.nodo = spd.nodo
				od.latitud = spd.latitud
				od.longitud = spd.longitud
				od.save()
				od.submit()
				frappe.db.commit()

				for equipos in susc.equipos:
					if spd.name==equipos.plan:
						code = frappe.db.get_value('Serial No', {"name": equipos.equipo}, 'item_code')
						eos = frappe.get_doc({
						'doctype': "Equipo_Orden_Servicio",
						'serial_no': equipos.equipo,
						'parent': od.name,
						'parenttype': "Service Order",
						'parentfield': "equipo_orden_servicio",
						'item_code': code
						})
						eos.insert()

				if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": spd.name}):
					bitacora_plan = frappe.get_doc({
						'doctype': "Bitacora de Planes",
						'plan': spd.plan,
						'cliente':  g[1],
						'estado_plan': 'Plan Cerrado',
						'currency': spd.currency,
						'costo':spd.cost,
						'intervalo_de_facturacion':spd.billing_interval_count,
						'subscription_plan_detail': spd.name

					})
					bitacora_plan.insert()					
				bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": spd.name})						
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"detalle":"Plan cerrado por cancelación programada. Motivo: " + g[2],
					"fecha": now(),
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes"
					})
				bitacora_detalle.insert()

		frappe.db.sql(""" update `tabGestion` set convertido = 1 where name = %(name)s;""",{"name":g[0]})

