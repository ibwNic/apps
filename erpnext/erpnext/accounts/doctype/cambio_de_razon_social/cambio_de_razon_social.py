# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from frappe.model.document import Document
import frappe
from frappe import _
from erpnext import get_default_company
from frappe.utils.data import (
	add_days,
	add_to_date,
	add_months,
	add_to_date,
	cint,
	cstr,
	date_diff,
	flt,
	get_last_day,
	getdate,
	nowdate,
	today,
	now
)

class CambiodeRazonSocial(Document):
	pass


@frappe.whitelist()
def obtener_planes_de_cliente(cliente):
	time.sleep(1)
	contratos = frappe.db.get_values("Subscription",{"party":cliente, "workflow_state":"Activo"},'name')
	contratos = [c[0] for c in contratos]
	planes = frappe.db.sql("""select name, plan, parent from `tabSubscription Plan Detail` where parent in %(parent)s and estado_plan = "Activo";""",{"parent":contratos})
	crs = frappe.new_doc('Cambio de Razon Social')
	crs.update({
		'cliente': cliente,	
	})
	for plan in planes:
		item1 = crs.append('cambiar_planes', {"plan": ""})				
		item1.plan = plan[0]
		item1.plan_name = plan[1]
		item1.contrato = plan[2]
	#crs.save()		
	return {'docs': crs.as_dict()}

@frappe.whitelist()
def crear_nuevo_contrato(name):
	try:
		crs = frappe.get_doc("Cambio de Razon Social",name)
		if not crs.nuevo_cliente or not crs.fecha_de_inicio_de_contrato or not crs.duracion_de_contrato or not crs.current_invoice_start or not crs.current_invoice_end or not crs.numero_de_nuevo_contrato:
			frappe.msgprint("Ingrese datos a los campos: \n Fecha de Inicio de Contrato, \n Duracion de Contrato, \n Fecha de Inicio de la Factura Actual, \n Fecha de Finalización de la Factura Actual, \n Nuevo Cliente, \n Numero de Nuevo Contrato")	
			return 
		combos = tv = gpon = hfc = tv_gpon = tv_hfc = 0
		subsc = subsc2 = ''
		pasa = True		
		for plan in crs.cambiar_planes:
			if '+ TV' in plan.plan_name:
				combos +=1
				subsc = plan.contrato
				if not frappe.db.exists("Detalle Cambio de Razon Social", {"parent": name,"plan_name":["in",["TV Combo GPON","TV Combo HFC"]]}):
					frappe.msgprint(f"Hace falta agregar plan TV para el combo {plan.plan_name}")
					return
				if 'GPON' in plan.plan_name:
					gpon += 1
				elif 'HFC' in plan.plan_name:
					hfc += 1
			if plan.plan_name == 'TV Combo GPON' or plan.plan_name == 'TV Combo HFC':
				tv += 1		
				subsc2 = plan.contrato	
				if plan.plan_name == 'TV Combo GPON':
					tv_gpon += 1
				elif plan.plan_name == 'TV Combo HFC': 
					tv_hfc += 1			
		if tv == combos and hfc == tv_hfc and gpon == tv_gpon and pasa:
			if subsc != subsc2:
				frappe.msgprint("Plan de TV y plan de internet son de contratos diferentes")
				return
			contratos=[]
			Nuevos_contratos(name)
			for plan in crs.cambiar_planes:
				contratos.append(plan.contrato)
				contratos = list(set(contratos))
			for contrato in contratos:
				return Cambiar_estado_contratos_anteriores(contrato,name)	

		else:
			frappe.msgprint("Debe agregar un plan de TV correspondiente a cada combo")
			return 
		frappe.db.sql(""" update `tabCambio de Razon Social` set docstatus = 1 where name = %(name)s; """,{"name":name})

	except Exception as e:
		frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))

def Cambiar_estado_contratos_anteriores(contrato,crs):
	try:
		crs = frappe.get_doc("Cambio de Razon Social",crs)
		planes = frappe.db.sql(""" Select plan from `tabDetalle Cambio de Razon Social` where parent = %(parent)s and contrato = %(contrato)s;""",{"parent":crs.name,"contrato":contrato})
		planes = [p[0] for p in planes]
		for plan in planes:
			old_plan_detail = frappe.get_doc("Subscription Plan Detail",plan)
			old_plan_detail.update(
					{
						"estado_plan": "Plan Cerrado",
						"motivo_finalizado": 'Cambio de Razón Social',
						"service_end": now()
					}
				)
			old_plan_detail.save()
			
			if old_plan_detail.plan not in ("TV Combo GPON","TV Combo HFC"):
				if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": plan}):
					bitacora_plan = frappe.get_doc({
						'doctype': "Bitacora de Planes",
						'plan': old_plan_detail.plan,
						'cliente':  crs.cliente,
						'estado_plan': "Plan Cerrado",
						'direccion': old_plan_detail.direccion,
						'currency': old_plan_detail.currency,
						'costo':old_plan_detail.cost,
						'intervalo_de_facturacion':old_plan_detail.billing_interval_count,
						'subscription_plan_detail': old_plan_detail.name
					})
					bitacora_plan.insert()

				bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": plan})
				
				bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"detalle":"PLAN CERRADO POR CAMBIO DE RAZON SOCIAL ",
					"fecha": now(),
					"usuario":frappe.session.user,
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"Cambio de Razon Social",
					"tercero":crs.name
					})
				bitacora_detalle.insert()
			equipos = frappe.db.get_values("Subscription Plan Equipos",{"plan": plan, "parent":contrato},'equipo')

			if equipos:
				for equipo in equipos:
					frappe.db.sql(""" update `tabSerial No` set customer = %(customer)s where name =%(name)s; """,{"customer":crs.nuevo_cliente,"name":equipo})
					
					idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1; """,{"parent":equipo})	
					try:
						idx = int(idx[0][0]) + 1
					except:
						idx = 1
					add_to_bitacora_a = frappe.get_doc({
							"doctype": "Bitacora Equipos",
							"fecha_transaccion":now(),
							"tipo_transaccion": 'Cambio de Razon Social',
							"transaccion":'Asignacion de equipos a nuevo cliente por cambio de Razon Social',
							"parent":equipo,
							"parentfield":"bitacora_equipos",
							"parenttype": "Serial No",
							"tercero": crs.name,
							"idx":idx
						})
					add_to_bitacora_a.insert()
		p_cerrados = 0
		susc = frappe.get_doc("Subscription",contrato)
		for p in susc.plans:
			if p.estado_plan not in ('Activo','Inactivo'):
				p_cerrados += 1	
		if p_cerrados == len(susc.plans):
			frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Terminado', docstatus=1 where name = %(name)s; """,{"name":contrato})
		if int(frappe.db.sql(""" select count(*) from `tabSubscription` where workflow_state in ('Activo','Instalado','Grabado') and party=%(party)s; """,{"party":crs.cliente})[0][0]) == 0:
			frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'TERMINADO' where name = %(name)s; """,{"name":crs.cliente})
	except Exception as e:
		frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))


def Nuevos_contratos(crs):
	crs = frappe.get_doc("Cambio de Razon Social",crs)
	
	planes = frappe.db.sql(""" Select plan from `tabDetalle Cambio de Razon Social` where parent = %(parent)s;""",{"parent":crs.name})
	planes = [p[0] for p in planes]
	detalles_de_plan=[]
	
	for plan in planes:
		old_plan_detail = frappe.get_doc("Subscription Plan Detail",plan)
		detalles_de_plan.append([old_plan_detail.plan,old_plan_detail.qty,old_plan_detail.estado_plan,old_plan_detail.direccion,old_plan_detail.longitud,old_plan_detail.latitud,old_plan_detail.currency,old_plan_detail.cost,old_plan_detail.billing_interval_count,old_plan_detail.es_combo,old_plan_detail.service_start,old_plan_detail.name,old_plan_detail.nodo])

		dynamic_link = frappe.get_doc({
						"doctype": "Dynamic Link",
						"link_doctype":'Customer',
						"link_name":crs.nuevo_cliente,
						"link_title":frappe.db.get_value("Customer",crs.nuevo_cliente,'customer_name'),
						"parent":old_plan_detail.direccion,
						"parentfield":"links",
						"parenttype": "Address",
					})
		dynamic_link.insert()

	new_suscripcion = frappe.new_doc('Subscription')
	new_suscripcion.party_type = 'Customer'
	new_suscripcion.party = crs.nuevo_cliente
	new_suscripcion.start_date = crs.fecha_de_inicio_de_contrato
	new_suscripcion.end_date =  add_months(crs.fecha_de_inicio_de_contrato, int(crs.duracion_de_contrato))
	new_suscripcion.current_invoice_start = crs.current_invoice_start
	new_suscripcion.current_invoice_end = crs.current_invoice_end
	new_suscripcion.cost_center = 'Principal - NI'
	new_suscripcion.tipo_contrato = 'CAMBIO DE RAZON SOCIAL'
	new_suscripcion.no_contrato = crs.numero_de_nuevo_contrato
	for item in detalles_de_plan:
		plans = {
					"plan": item[0],
					"qty": item[1],
					"estado_plan":item[2],
					"direccion": item[3],
					"longitud":item[4],
					"latitud":item[5],
					"currency":item[6],
					"cost":item[7],
					"billing_interval_count":item[8],
					"es_combo":item[9],
					"service_start":item[10],
					"old_plan": item[11],
					"nodo": item[12]
				}
		new_suscripcion.append("plans", plans)
	new_suscripcion.workflow_state='Activo'
	new_suscripcion.save()


	for plan in new_suscripcion.plans:
		equipos = frappe.db.get_values("Subscription Plan Equipos",{"plan": plan.old_plan},'equipo')
		if equipos:
			frappe.db.sql(""" update  `tabSubscription Plan Equipos` set plan= %(newplan)s , parent=%(newsuscription)s 
							where plan= %(oldplan)s; """, {"newplan":plan.name, "newsuscription":new_suscripcion.name,"oldplan":plan.old_plan})
		if plan.plan not in ("TV Combo GPON","TV Combo HFC"):
			if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": plan.name}):
				bitacora_plan = frappe.get_doc({
					'doctype': "Bitacora de Planes",
					'plan': plan.plan,
					'cliente':  new_suscripcion.party,
					'estado_plan': plan.estado_plan,
					'direccion': plan.direccion,
					'currency': plan.currency,
					'costo':plan.cost,
					'intervalo_de_facturacion':plan.billing_interval_count,
					'subscription_plan_detail': plan.name,
					'nodo':plan.nodo
				})
				bitacora_plan.insert()		
			bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": plan.name})					
			bitacora_detalle = frappe.get_doc({
				"doctype": "Detalle Bitacora Planes",
				"detalle":"PLAN ABIERTO POR CAMBIO DE RAZON SOCIAL",
				"fecha": now(),
				"usuario":frappe.session.user,
				"parent": bitacora_plan.name,
				"parentfield":"detalle",
				"parenttype": "Bitacora de Planes",
				"tipo_transaccion":"Cambio de Razon Social",
				"tercero":crs.name
				})
			bitacora_detalle.insert()
		
	frappe.msgprint(frappe._('Nueva Suscripción con ID {0}').format(new_suscripcion.name))
	frappe.db.set_value("Cambio de Razon Social",crs.name,'nuevo_contrato',new_suscripcion.name)
	frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'ACTIVO' where name = %(name)s; """,{"name":crs.nuevo_cliente})


@frappe.whitelist()
def obtener_clientes_con_contratos():
	contratos = frappe.db.sql(""" select party from `tabSubscription` where workflow_state='Activo';""")
	return [c[0] for c in contratos]