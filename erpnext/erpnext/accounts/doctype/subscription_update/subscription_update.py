# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
import random
import string
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
	formatdate,
	get_last_day,
	getdate,
	nowdate,
	today,
	now
)

class SubscriptionUpdate(Document):
	pass

@frappe.whitelist()
def obtener_planes_de_contrato(contrato,customer,name=None,nuevo_plan=None):
	
	if frappe.db.exists("Subscription", {"name":contrato,"party":customer}):
		frappe.db.set_value("Subscription Update",name,'contrato',contrato)
		frappe.db.set_value("Subscription Update",name,'customer',customer)
		planes = frappe.db.get_values("Subscription Plan Detail", {"parent":contrato},"name")
		lista_planes = [plan[0] for plan in planes]
		try:
			frappe.db.sql(
					"""
					DELETE FROM `tabSubscription Update Planes`
					WHERE parent = %(parent)s""",{"parent": name}
				)	
			time.sleep(1)
		except:
			pass
		try:
			if frappe.db.exists("Subscription Update", name):
				su = frappe.get_doc("Subscription Update", name)
				for plan in lista_planes:
					
					child = frappe.new_doc("Subscription Update Planes")
					child.update(
						{
							"parent": name,
							"parentfield": "actualizar_planes_de_contrato",
							"parenttype": "Subscription Update",
							"plan":plan,
							"nuevo_plan":nuevo_plan		
						}
					)
					su.actualizar_planes_de_contrato.append(child)	
					su.save()
			else:
				su = frappe.new_doc("Subscription Update")
				for plan in lista_planes:
					item = su.append('actualizar_planes_de_contrato')
					item.plan = plan
		except:
			pass
	else:
		try:
			frappe.db.sql(
					"""
					DELETE FROM `tabSubscription Update Planes`
					WHERE parent = %(parent)s""",{"parent": name}
				)	
			time.sleep(1)
		except:
			pass

@frappe.whitelist()
def filtrar_planes_de_usuario(contrato=None,customer=None):
	if contrato != None and customer != None:
		planes = frappe.db.sql(""" select spd.name from  `tabSubscription Plan Detail` spd 
				inner join  `tabSubscription` s on s.name = spd.parent 
				where spd.estado_plan='Activo' and s.name = %(contrato)s and s.party = %(customer)s;""",{"contrato":contrato,"customer":customer})
		return [plan[0] for plan in planes]

@frappe.whitelist()
def filtrar_plan(name):
	plan = frappe.db.get_value("Subscription Plan Detail",{"name": name},"plan")
	return plan

def randStr(chars = string.ascii_uppercase + string.digits, N=4):
	return ''.join(random.choice(chars) for _ in range(N))

@frappe.whitelist()
def crear_nuevo_contrato(name):
	subscription_up = frappe.get_doc("Subscription Update",name)
	if subscription_up.docstatus == 1:
		frappe.msgprint("El contrato está hecho")
		return
	plan_row = []
	combos = tv = gpon = hfc = tv_gpon = tv_hfc = 0			
	for plan in subscription_up.actualizar_planes_de_contrato:
		if not plan.nuevo_plan:
			frappe.msgprint("No puede dejar campos vacíos en la tabla")
			return
		if '+ TV' in plan.nuevo_plan:
			combos +=1
			if not frappe.db.exists("Subscription Update Planes", {"parent": name,"nuevo_plan":["in",["TV Combo GPON","TV Combo HFC"]]}):
				frappe.msgprint(f"Hace falta agregar plan TV para el combo {plan.nuevo_plan}")
				return
			if 'GPON' in plan.nuevo_plan:
				gpon += 1
			elif 'HFC' in plan.nuevo_plan:
				hfc += 1			
		if plan.nuevo_plan == 'TV Combo GPON' or plan.nuevo_plan == 'TV Combo HFC':
			tv += 1
			if plan.nuevo_plan == 'TV Combo GPON':
				tv_gpon += 1
			elif plan.nuevo_plan == 'TV Combo HFC': 
				tv_hfc += 1
	if tv == combos and hfc == tv_hfc and gpon == tv_gpon:
		for plan in subscription_up.actualizar_planes_de_contrato:
			if plan.plan:			
				spd = frappe.get_doc("Subscription Plan Detail",  plan.plan)
			sp = frappe.get_doc("Subscription Plan",  plan.nuevo_plan)
			plan_row.append([plan.nuevo_plan,spd.qty,spd.direccion,spd.longitud,spd.latitud,sp.billing_interval_count,spd.es_combo,sp.currency,plan.coston,plan.plan, spd.nodo, spd.cost,plan.descuento])
			
			if plan.plan:
				old_plan_detail = frappe.get_doc("Subscription Plan Detail",plan.plan)
				old_plan_detail.update(
						{
							"estado_plan": "Plan Cerrado",
							"motivo_finalizado": 'Cambio de tipo de Servicio IBW',
							"service_end": now()
						}
					)
				old_plan_detail.save()
				p_cerrados = 0
				susc = frappe.get_doc("Subscription",old_plan_detail.parent)
				for p in susc.plans:
					if p.estado_plan not in ('Activo','Inactivo'):
						p_cerrados += 1
				
				if p_cerrados == len(susc.plans):
					frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Terminado', docstatus=1, subscription_update = %(su)s  where name = %(name)s; """,{"name":susc.name, "su":name})
					
				if old_plan_detail.plan not in ("TV Combo GPON","TV Combo HFC"):
					if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": plan.plan}):
						bitacora_plan = frappe.get_doc({
							'doctype': "Bitacora de Planes",
							'plan': spd.plan,
							'cliente':  subscription_up.customer,
							'estado_plan': "Plan Cerrado",
							'direccion': spd.direccion,
							'currency': spd.currency,
							'costo':spd.cost,
							'intervalo_de_facturacion':spd.billing_interval_count,
							'subscription_plan_detail': spd.name,
							'nodo': spd.nodo
						})
						bitacora_plan.insert()
					
					bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": plan.plan})
							
					bitacora_detalle = frappe.get_doc({
						"doctype": "Detalle Bitacora Planes",
						"detalle":"PLAN CERRADO POR " + subscription_up.tipo_contrato,
						"fecha": now(),
						"usuario":frappe.session.user,
						"parent": bitacora_plan.name,
						"parentfield":"detalle",
						"parenttype": "Bitacora de Planes",
						"tipo_transaccion":"Subscription Update",
						"tercero":name
						})
					bitacora_detalle.insert()
				equipos = frappe.db.get_values("Subscription Plan Equipos",{"plan": plan.plan, "parent":subscription_up.contrato},'equipo')
				if equipos:
					for equipo in equipos:
						idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1; """,{"parent":equipo})	
						try:
							idx = int(idx[0][0]) + 1
						except:
							idx = 1
						# add_to_bitacora_a = frappe.get_doc({
						# 		"doctype": "Bitacora Equipos",
						# 		"fecha_transaccion":now(),
						# 		"tipo_transaccion": 'Subscription Update',
						# 		"transaccion":'Cambio de tipo de Servicio IBW',
						# 		"parent":equipo,
						# 		"parentfield":"bitacora_equipos",
						# 		"parenttype": "Serial No",
						# 		"tercero": name,
						# 		"idx":idx
						# 	})
						# add_to_bitacora_a.insert()
						ran = str(randStr(chars='abcdefghijklmnopqrstuvwxyz1234567890'))
						frappe.db.sql(""" insert into `tabBitacora Equipos` (name,fecha_transaccion,tipo_transaccion,transaccion,parent,parentfield,parenttype,tercero,idx) 
									values (%(name)s,%(fecha_transaccion)s,'Subscription Update','Cambio de tipo de Servicio IBW',%(parent)s,"bitacora_equipos","Serial No",%(tercero)s,%(idx)s);""",{"name":ran,"fecha_transaccion":now(),"parent":equipo,"tercero":name,"idx":idx})

	else:
		frappe.msgprint("Debe agregar un plan de TV correspondiente a cada combo")
		return 	
	subscription = frappe.get_doc("Subscription",subscription_up.contrato)
	"""" crear planes de suscripcion a partir de subscription items """	

	suscripcion = frappe.new_doc('Subscription')
	suscripcion.party_type = subscription.party_type
	suscripcion.party = subscription.party
	suscripcion.company = subscription.company
	suscripcion.start_date = nowdate()
	suscripcion.current_invoice_start = nowdate()
	suscripcion.current_invoice_end = formatdate(frappe.utils.get_last_day(nowdate()), "yyyy-MM-dd")
	suscripcion.lista_de_planes = subscription.lista_de_planes
	suscripcion.cost_center = subscription.cost_center
	suscripcion.tipo_contrato = subscription_up.tipo_contrato
	suscripcion.no_contrato = subscription_up.no_de_contrato
	suscripcion.vendedor = subscription_up.vendedor
	suscripcion.subscription_update = name
	mismo_precio = True
	for item in plan_row:
		estado_plan = ''
		contador_inactivos = 0
		item_group_nuevo = frappe.db.get_value("Subscription Plan",item[0],"item_group")
		if item[9]:
			item_group_viejo = frappe.db.get_value("Subscription Plan", frappe.db.get_value("Subscription Plan Detail",item[9],"plan"),"item_group")
		else:
			item_group_viejo = ''
		if ("GPON" in item_group_nuevo and "GPON" in item_group_viejo) or (item_group_nuevo in ["HFC 3.0.","HFC", "INET"] and item_group_viejo in ["HFC 3.0.","HFC", "INET"]) or (item_group_nuevo == item_group_viejo):
			estado_plan = 'Activo'
		else:
			estado_plan = 'Inactivo'
			contador_inactivos += 1
		plans = {
				"plan": item[0],
				"qty": item[1],
				"estado_plan":estado_plan,
				"direccion": item[2],
				"longitud":item[3],
				"latitud":item[4],
				"currency":item[7],
				"cost":item[8],
				"billing_interval_count":item[5],
				"es_combo":item[6],
				"old_plan": item[9],
				"nodo": item[10],
				"service_start":now(),
				"descuento":item[12]
			}
		suscripcion.append("plans", plans)

		if item[8] != item[11]:
			mismo_precio = False
	
	if mismo_precio  and contador_inactivos == 0:
		suscripcion.workflow_state='Activo'
	elif  not(mismo_precio)  and contador_inactivos == 0:
		suscripcion.workflow_state='Instalado'
	else:
		suscripcion.workflow_state='Grabado'
	suscripcion.save()
	
	for plan in suscripcion.plans:
		if plan.old_plan and plan.estado_plan == 'Activo':
			equipos = frappe.db.get_values("Subscription Plan Equipos",{"plan": plan.old_plan, "parent":subscription_up.contrato},'equipo')
			if equipos:
				frappe.db.sql(""" update  `tabSubscription Plan Equipos` set plan= %(newplan)s , parent=%(newsuscription)s 
								where plan= %(oldplan)s and parent=%(Oldsuscription)s; """, {"newplan":plan.name, "newsuscription":suscripcion.name,"oldplan":plan.old_plan,"Oldsuscription":subscription_up.contrato})
		if plan.plan not in ("TV Combo GPON","TV Combo HFC"):
			if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": plan.name}):
				bitacora_plan = frappe.get_doc({
					'doctype': "Bitacora de Planes",
					'plan': plan.plan,
					'cliente':  subscription_up.customer,
					'estado_plan': plan.estado_plan,
					'direccion': plan.direccion,
					'currency': plan.currency,
					'costo':plan.cost,
					'intervalo_de_facturacion':plan.billing_interval_count,
					'subscription_plan_detail': plan.name,
					'nodo': plan.nodo
				})
				bitacora_plan.insert()		
			bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": plan.name})					
			bitacora_detalle = frappe.get_doc({
				"doctype": "Detalle Bitacora Planes",
				"detalle":"PLAN ABIERTO POR " + subscription_up.tipo_contrato,
				"fecha": now(),
				"usuario":frappe.session.user,
				"parent": bitacora_plan.name,
				"parentfield":"detalle",
				"parenttype": "Bitacora de Planes",
				"tipo_transaccion":"Subscription Update",
				"tercero":name
				})
			bitacora_detalle.insert()
	
	frappe.msgprint(frappe._('Nueva Suscripción con ID {0}').format(suscripcion.name))
	frappe.db.sql(""" update  `tabSubscription Update` set nuevo_contrato= %(newplan)s , docstatus=1 
		where name= %(name)s ; """, {"newplan":suscripcion.name, "name":name})		
	return suscripcion.name
	# except Exception as e:
	# 	frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))	


@frappe.whitelist()
def filtrar_planes_nuevos(customer):
	cg = frappe.db.get_value("Customer",customer,'customer_group')
	if cg == 'Individual':
		return False
	planes = frappe.db.sql(""" select sp.name from `tabSubscription Plan` sp inner join  `tabOpportunity` op 
		on sp.oportunidad = op.name where op.customer = %(customer)s ;""",{"customer":customer})
	return [p[0] for p in planes]