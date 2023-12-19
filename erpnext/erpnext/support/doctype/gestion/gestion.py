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
		if self.workflow_state == 'Finalizado' and self.tipo_gestion == 'Cancelaciones' and self.estado_cancelacion == 'Retenida':
			frappe.msgprint("Si el cliente es retenido debe escalar a BO")
			frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
			self.reload()
		if self.workflow_state == 'Escalado' and self.tipo_gestion == 'Cancelaciones' and self.estado_cancelacion == 'Aceptada':
			frappe.msgprint("Si la cancelación es aceptada no puede escalar a BO, solo finalizar la gestion")
			frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
			self.reload()
		if self.workflow_state == 'Escalado' and self.tipo_gestion in ("Reclamos","Suspensiones","Consulta"):
			frappe.msgprint("No puedes escalar una gestión de tipo " + self.subgestion + ", solo finalizar.")
			frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
			self.reload()
		if self.workflow_state == 'Escalado' and self.tipo_gestion == "Tramites" and self.subgestion == "Cobranza":
			frappe.msgprint("No puedes escalar una gestión de tipo " + self.subgestion + ", solo finalizar.")
			frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
			self.reload()

		
		if self.workflow_state == 'Finalizado' or self.workflow_state == 'Escalado':
			# if self.tipo_gestion == 'Clientes Terminados' and self.subgestion == 'Reactivacion':
			# 	for plan in self.cambiar_planes:
			# 		generar_orden_de_reactivacion(plan.plan,self.name)

			if self.tipo_gestion == 'Cancelaciones' and self.estado_cancelacion != 'Aceptada':
				if not self.medida_retencion:
					frappe.msgprint("Indicar medida de retención")
					frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
					self.reload()
				if not self.motivo or not self.estado_cancelacion:
					frappe.msgprint("Indicar el estado de la cancelacion y el motivo")
					frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
					self.reload()
					
			
			if self.tipo_gestion not in ('Cancelaciones','Suspensiones','Clientes Terminados'):
				if not self.issue and self.subgestion != 'Nueva Venta':
					frappe.msgprint("Debe generar una ticket, un trámite o una avería para finalizar la gestion")
					frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
					self.reload()
					return
				else:
					for iss in self.issue:
						if iss.tipo_documento == 'Issue' and iss.estado not in ('Finalizado','Cancelado'):
							frappe.msgprint("Para finalizar la gestion debe finalizar todas las incidencias")
							frappe.db.sql(""" update `tabGestion` set workflow_state = 'En Proceso' , docstatus = 0 where name = %(name)s; """,{"name":self.name})
							self.reload()
							return

			if self.tipo_gestion != 'Cancelaciones':
				frappe.db.sql(""" update `tabGestion` set estado = %(wf)s where name = %(name)s; """,{"name":self.name,"wf":self.workflow_state})
			
			if self.tipo_gestion == 'Suspensiones' and self.subgestion == 'Suspension Manual':
				generar_suspension_manual(self.name,self.customer)
		
		if self.workflow_state == 'En Proceso':
			if self.tipo_gestion == 'Suspensiones' and self.subgestion == 'Suspension Temporal':
				if not self.fecha_inicio_suspension_temporal:
					frappe.msgprint("ingresar fecha de suspensión temporal")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
					self.reload()
					return
		if self.tipo_gestion not in  ["Cancelaciones","Suspensiones"] and self.subgestion != "Reactivacion":
			frappe.db.sql("Delete from `tabDetalle Cambio de Razon Social` where parent = %(name)s; ",{"name":self.name})
		if self.subgestion != "Borra Saldo":
			frappe.db.sql("Delete from `tabSubscription Invoice` where parent = %(name)s; ",{"name":self.name})

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
def validar_issue_abierta(customer,tipo_orden):
	query = frappe.db.sql(""" select name from  `tabIssue` where workflow_state not in ('Finalizado', 'Cancelado') 
	and tipo_de_orden = %(tipo_orden)s and customer = %(customer)s limit 1;""",{"tipo_orden":tipo_orden,"customer":customer})
	try:
		return query[0][0]
	except:
		return False

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
	contratos = frappe.db.get_values("Subscription",{"party":customer},'name')
	contratos = [c[0] for c in contratos]
	if contratos:
		planes = frappe.db.sql("""select name, plan, parent from `tabSubscription Plan Detail` where parent in %(parent)s and estado_plan in ("Activo","SUSPENDIDO: Manual","SUSPENDIDO: Temporal");""",{"parent":contratos})
		for plan in planes:
			item1 = g.append('cambiar_planes', {"plan": ""})
			item1.plan = plan[0]				
			item1.plan_name = plan[1]
			item1.contrato = plan[2]			
	return {'docs': g.as_dict()}	

@frappe.whitelist()
def obtener_planes_de_cliente_Terminados(customer, tipo_gestion, subgestion):
	g = frappe.new_doc('Gestion')
	g.update({
		'customer': customer,	
		'tipo_gestion': tipo_gestion,
		'subgestion': subgestion
	})
	contratos = frappe.db.get_values("Subscription",{"party":customer, "workflow_state":["in",["Terminado","Activo","Suspendido"]]},'name')
	contratos = [c[0] for c in contratos]
	if contratos:
		planes = frappe.db.sql("""select name, plan, parent from `tabSubscription Plan Detail` where parent in %(parent)s and estado_plan in ("Plan Cerrado");""",{"parent":contratos})
		for plan in planes:
			item1 = g.append('cambiar_planes', {"plan": ""})
			item1.plan = plan[0]				
			item1.plan_name = plan[1]
			item1.contrato = plan[2]
		
	return {'docs': g.as_dict()}	


@frappe.whitelist()
def obtener_facturas_pendientes(customer, tipo_gestion, subgestion):
	g = frappe.new_doc('Gestion')
	g.update({
		'customer': customer,	
		'tipo_gestion': tipo_gestion,
		'subgestion':subgestion
	})
	facturas = frappe.db.sql(""" select name, currency, grand_total, posting_date from `tabSales Invoice` where customer = %(customer)s and outstanding_amount > 1; """, {"customer":customer})
	if facturas:
		for f in facturas:
			item1 = g.append('facturas_pendientes', {"invoice": ""})
			item1.document_type = 'Sales Invoice'				
			item1.invoice = f[0]
			item1.currency = f[1]	
			item1.saldo = f[2]
			item1.posting_date= f[3]
	return {'docs': g.as_dict()}

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
def generar_orden_de_servicio(name,issue):
	gestion = frappe.get_doc("Gestion",name)	
	if gestion.tipo_gestion != "Tramites":
		return

	incidencia = frappe.get_doc("Issue",issue)

	if frappe.db.exists("Service Order",{"nombre_de_origen":name,"plan_de_subscripcion":incidencia.planes}):
		frappe.msgprint("Orden ya fue creada")
		return
	if gestion.subgestion == 'Traslado de Servicio':
		#creacion de orden
		spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
		od = frappe.get_doc({
			'doctype': "Service Order",
			'tipo_de_orden': "TRASLADO",
			'workflow_state': "Abierto",
			'tipo_de_origen': "Gestion",
			'portafolio':incidencia.servicio,
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
			'informacion_de_contacto':spd.contacto,
			'latitud':spd.latitud,
			'longitud':spd.longitud,
			'nodo':spd.nodo,
			'direccion_de_traslado': incidencia.nueva_direccion
		})
		od.insert(ignore_permissions=True)
		frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden),frappe.utils.get_link_to_form("Service Order", od.name)))
		doc = frappe.get_doc("Subscription",spd.parent)
		for equipos in doc.equipos:
			ran = random_string(6)
			ran = ran + equipos.name
			if od.plan_de_subscripcion==equipos.plan:
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
	elif gestion.subgestion == 'TV Adicional':	
		spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
		od = frappe.get_doc({
			'doctype': "Service Order",
			'tipo_de_orden': "TV ADICIONAL",
			'portafolio':incidencia.servicio,
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
			'informacion_de_contacto':spd.contacto,
			'latitud':spd.latitud,
			'longitud':spd.longitud,
			'nodo':spd.nodo
		})
		od.insert(ignore_permissions=True)
		frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))
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

	elif gestion.subgestion == 'Cableado':
		spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
		od = frappe.get_doc({
			'doctype': "Service Order",
			'tipo_de_orden': "CABLEADO",
			'portafolio':incidencia.servicio,
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
			'informacion_de_contacto':spd.contacto,
			'latitud':spd.latitud,
			'longitud':spd.longitud,
			'nodo':spd.nodo
		})
		od.insert(ignore_permissions=True)
		frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))
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
		spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
		od = frappe.get_doc({
			'doctype': "Service Order",
			'tipo_de_orden': "RECONEXION",
			'workflow_state': "Abierto",
			'portafolio':incidencia.servicio,
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
			'informacion_de_contacto':spd.contacto,
			'latitud':spd.latitud,
			'longitud':spd.longitud,
			'nodo':spd.nodo
		})
		od.insert(ignore_permissions=True)
		frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))
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

	elif gestion.subgestion == 'Instalacion OTC':
		spd = frappe.get_doc("Subscription Plan Detail",incidencia.planes)
		od = frappe.get_doc({
			'doctype': "Service Order",
			'tipo_de_orden': "INSTALACION OTC",
			'portafolio':incidencia.servicio,
			'workflow_state': "Abierto",
			'tipo_de_origen': "Gestion",
			'nombre_de_origen': name,
			'descripcion': frappe._('Ejecutar instalación INSTALACION OTC de {0}').format(spd.plan),
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
			'informacion_de_contacto':spd.contacto,
			'latitud':spd.latitud,
			'longitud':spd.longitud,
			'nodo':spd.nodo
		})
		od.insert(ignore_permissions=True)
		frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))
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
		
	frappe.db.set_value("Gestion",name,"convertido",1)
	if incidencia.cortesia == 0:
		frappe.db.sql("update `tabGestion` set workflow_state = 'Atendido', estado = 'Atendido', docstatus =1  where name = %(name)s ",{"name":name})
	else:
		frappe.db.sql("update `tabGestion` set workflow_state = 'Finalizado',  estado = 'Atendido', docstatus =1  where name = %(name)s ",{"name":name})

def generar_suspension_manual(gestion,customer):
	
	for p in frappe.db.get_values("Detalle Cambio de Razon Social", {"parenttype":"Gestion","parent":gestion},"plan"):
		if p[0]:
			spd = frappe.get_doc("Subscription Plan Detail", {"name": p[0]})	
			frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan =  'SUSPENDIDO: Manual', service_suspend = %(service_suspend)s where name = %(name)s;""", {"service_suspend": now(),"name":p[0]})
			p_susp = 0
			susc = frappe.get_doc("Subscription",spd.parent)
			for p in susc.plans:
				if p.estado_plan not in ('Activo','Inactivo'):
					p_susp += 1
			
			if p_susp == len(susc.plans):
				frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Suspendido' where name = %(subsc)s; """,{"subsc":spd.parent})
							
			susc_cliente = frappe.db.get_values("Subscription",{"party":customer,"workflow_state":["in",["Activo","Instalado"]]},"name")
			if len(susc_cliente) == 0:
				frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'SUSPENDIDO (Manual)' where name = %(customer)s; """,{"customer":customer})
				
			idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":spd.name})	
			idx_b = idx_b[0][0]			
			if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": spd.name}):
				bitacora_plan = frappe.get_doc({
					'doctype': "Bitacora de Planes",
					'plan': spd.plan,
					'cliente':  customer,
					'estado_plan': "SUSPENDIDO: Manual",
					'direccion': spd.direccion,
					'currency': spd.currency,
					'costo':spd.cost,
					'intervalo_de_facturacion':spd.billing_interval_count,
					'subscription_plan_detail': spd.name
				})
				bitacora_plan.insert()					
			bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": spd.name})	
			bitacora_plan.update(
				{
					"estado_plan": "SUSPENDIDO: Manual",
				})
			bitacora_plan.save(ignore_permissions=True)						
			bitacora_detalle = frappe.get_doc({
				"doctype": "Detalle Bitacora Planes",
				"idx":idx_b,
				"detalle":"SUSPENDIDO: Manual",
				"fecha": now(),
				"usuario":frappe.session.user,
				"parent": bitacora_plan.name,
				"tipo_transaccion":"Gestion",
				"tercero":gestion,
				"parentfield":"detalle",
				"parenttype": "Bitacora de Planes",
				"estado_plan":"SUSPENDIDO: Manual",
				})
			bitacora_detalle.insert()	
			
			upd_spd = frappe.get_doc("Subscription Plan Detail", {"name": spd.name})
			upd_sus = frappe.get_doc("Subscription", {"name": upd_spd.parent})

			direccion=frappe.get_doc("Address", upd_spd.direccion)
			od = frappe.get_doc({
				'doctype': "Service Order",
				'tipo_de_orden': "SUSPENSION",
				'workflow_state': "Abierto",
				'tipo_de_origen': "Subscription",
				'tipo_cliente': frappe.db.get_value('Customer', {"name": upd_sus.party}, 'customer_group'),
				'nombre': frappe.db.get_value('Customer', {"name": upd_sus.party}, 'customer_name'),
				'nombre_de_origen': upd_sus.name,
				'descripcion': frappe._('Ejecutar SUSPENSION de {0}').format(upd_spd.plan),
				'tipo': 'Customer',
				'tercero': upd_sus.party,
				'plan_de_subscripcion': upd_spd.name,
				'direccion_de_instalacion': upd_spd.direccion,
				'portafolio': frappe.db.get_value("Subscription Plan", upd_spd.plan, "item_group"),
				'departamento': direccion.departamento,
				'municipio': direccion.municipio,
				'barrio': direccion.barrio,
				'direccion': direccion.address_line1,
				'latitud':upd_spd.latitud,
				'longitud':upd_spd.longitud,
				'nodo':upd_spd.nodo
			})
			od.insert()
			for equipos in upd_sus.equipos:
				ran = random_string(6)
				ran = ran + equipos.name
				if od.plan_de_subscripcion==equipos.plan:
					code = frappe.db.get_value('Serial No', {"name": equipos.equipo}, 'item_code')
					frappe.db.sql(""" insert into `tabEquipo_Orden_Servicio` (name,serial_no,parent,parenttype,parentfield,item_code) 
						values (%(name)s,%(serial_no)s,%(parent)s,'Service Order','equipo_orden_servicio',%(item_code)s) """, {"name":ran,"serial_no":equipos.equipo,"parent":od.name,"item_code":code})

			frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))

	frappe.db.sql(""" update `tabGestion` set convertido = 1 where name = %(name)s;""",{"name":gestion})


def programar_suspensiones_temporales():
	""" suspender planes, contratos y clientes desde gestiones finalizadas """
	gestiones = frappe.db.sql(""" select name, customer from `tabGestion` where subgestion = 'Suspension Temporal' and workflow_state = 'Finalizado' and fecha_inicio_suspension_temporal <= CURDATE() and convertido = 0;""")
	for g in gestiones:
		for p in frappe.db.get_values("Detalle Cambio de Razon Social", {"parenttype":"Gestion","parent":g[0]},"plan"):
			if p[0]:
				spd = frappe.get_doc("Subscription Plan Detail", {"name": p[0]})
				
				idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":spd.name})	
				idx_b = idx_b[0][0]
				frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan =  'SUSPENDIDO: Temporal', service_suspend = %(service_suspend)s where name = %(name)s;""", {"service_suspend": now(),"name":p[0]})
				
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
				bitacora_plan.update(
					{
						"estado_plan": "SUSPENDIDO: Temporal",
					})
				bitacora_plan.save(ignore_permissions=True)					
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"detalle":"SUSPENDIDO: Temporal",
					"fecha": now(),
					"idx":idx_b,
					#"usuario":frappe.session.user,
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"tipo_transaccion":"Gestion",
					"tercero":g[0],
					"parenttype": "Bitacora de Planes",
					'estado_plan': "SUSPENDIDO: Temporal",
					})
				bitacora_detalle.insert()	
		frappe.db.sql(""" update `tabGestion` set convertido = 1 where name = %(name)s;""",{"name":g[0]})

def get_portafolio_plan(plan):
	portafolio = frappe.db.sql(
	"""Select t1.item_group
	from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item where t2.name=%(plan)s limit 1 """,
	{"plan": plan},)
	return portafolio

@frappe.whitelist()
def generar_orden_de_reactivacion(plan, gestion):
	upd_spd = frappe.get_doc("Subscription Plan Detail", {"name": plan})
	upd_sus = frappe.get_doc("Subscription", {"name": upd_spd.parent})
	portafolio=get_portafolio_plan(upd_spd.plan)
	portafolio = str(portafolio[0][0])

	if portafolio not in ('IPTV'):
		var = False
		status =''
		if frappe.db.exists("Service Order", {"tipo_de_origen": "Gestion","tipo_de_orden":"REACTIVACION","nombre_de_origen":gestion,"plan_de_subscripcion":plan}):
			so= frappe.get_doc("Service Order", {"tipo_de_origen": "Gestion","tipo_de_orden":"REACTIVACION","nombre_de_origen":gestion,"plan_de_subscripcion":plan})
			if so.workflow_state=="Cancelado" or so.workflow_state=="Finalizado":
				status = "Pasa"
			else:
				status = "No Pasa"

		elif frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"DESINSTALACION","nombre_de_origen":upd_sus.name,"plan_de_subscripcion":plan}):
			so_des = frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"DESINSTALACION","nombre_de_origen":upd_sus.name,"plan_de_subscripcion":plan})
			if so_des.workflow_state=="Abierto" or so_des.workflow_state=="Finalizado" or so_des.workflow_state=="Cancelado":
				status = "Pasa"
				if so_des.workflow_state=="Abierto":
					so_des.update({
						"workflow_state":"Cancelado",
						"docstatus" : 1,
						"solucion":"CANCELADO POR REACTIVACION"		
					})
					so_des.save()
					frappe.db.sql(""" update `tabService Order` set workflow_state = 'Cancelado', estado = 'Cancelado', docstatus = 1 where name = %(orden)s; """,{"orden":so_des.name})
			else:
				status = "No Pasa"

		else:
			var = True
		if status=="Pasa" or var:
			direccion=frappe.get_doc("Address", upd_spd.direccion)
			od = frappe.get_doc({
				'doctype': "Service Order",
				'tipo_de_orden': "REACTIVACION",
				'workflow_state': "Abierto",
				'tipo_de_origen': "Gestion",
				'tipo_cliente': frappe.db.get_value('Customer', {"name": upd_sus.party}, 'customer_group'),
				'nombre': frappe.db.get_value('Customer', {"name": upd_sus.party}, 'customer_name'),
				'nombre_de_origen': gestion,
				'descripcion': frappe._('Ejecutar Reactivacion de {0}').format(upd_spd.plan),
				'tipo': 'Customer',
				'tercero': upd_sus.party,
				'plan_de_subscripcion': plan,
				'direccion_de_instalacion': upd_spd.direccion,
				'portafolio': portafolio,
				'departamento': direccion.departamento,
				'municipio': direccion.municipio,
				'barrio': direccion.barrio,
				'direccion': direccion.address_line1,
				'latitud':upd_spd.latitud,
				'longitud':upd_spd.longitud,
				'nodo':upd_spd.nodo
			})
			od.insert()
			frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))

			for equipos in upd_sus.equipos:
				if plan==equipos.plan:
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
			frappe.db.sql("Update `tabGestion` set workflow_state = 'Finalizado', estado = 'Finalizado' where name = %(gestion)s",{"gestion":gestion})
		else:
			frappe.msgprint("La orden no se pudo generar: La orden de reactivacion ya fue creada o existe una desinstalación en curso")


def programar_cancelaciones():
	""" cancelar planes, contratos y clientes desde gestiones finalizadas """
	gestiones = frappe.db.sql(""" select name, customer, motivo from `tabGestion` where tipo_gestion = 'Cancelaciones' and workflow_state = 'Finalizado' and estado_cancelacion = 'Aceptada' and convertido = 0; """)
	for g in gestiones:
		for p in frappe.db.get_values("Detalle Cambio de Razon Social", {"parenttype":"Gestion","parent":g[0]},"plan"):
			if p[0]:
				spd = frappe.get_doc("Subscription Plan Detail", {"name": p[0]})
				
				idx_b = frappe.db.sql(""" select case when max(idx) + 1 is not null then max(idx) + 1 else 1  end from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":spd.name})	
				idx_b = idx_b[0][0]
				
					# spd.update(
				# 	{
				# 	"estado_plan": "SUSPENDIDO: Temporal",
				# 	"service_suspend": now(),
				# 	}
				# )
				frappe.db.sql(""" update `tabSubscription Plan Detail` set estado_plan =  'Plan Cerrado', service_end = %(service_end)s, motivo_finalizado = %(motivo)s,
									detalle_finalizado = CONCAT('Plan cerrado por cancelación programada. Motivo: ', %(motivo)s)  where name = %(name)s;""", {"service_end": now(),"name":p[0], "motivo":g[2]})
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
				
				od.nodo = spd.nodo
				od.informacion_de_contacto= spd.contacto
				od.latitud = spd.latitud
				od.longitud = spd.longitud
				od.save()
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
				bitacora_plan.update(
					{
						"estado_plan": 'Plan Cerrado',
					})
				bitacora_plan.save(ignore_permissions=True)						
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"idx":idx_b,
					"detalle":"Plan cerrado por cancelación programada. Motivo: " + g[2],
					"fecha": now(),
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"Gestion",
					"tercero":g[0],
					'estado_plan': 'Plan Cerrado',
					})
				bitacora_detalle.insert()

		frappe.db.sql(""" update `tabGestion` set convertido = 1 where name = %(name)s;""",{"name":g[0]})

@frappe.whitelist()
def finalizar_gestion(gestion):
	if frappe.db.get_value("Gestion",gestion,"workflow_state") != 'Finalizado':
		frappe.db.sql("Update `tabGestion` set workflow_state = 'Finalizado', estado = 'Finalizado' where name = %(gestion)s",{"gestion":gestion})


