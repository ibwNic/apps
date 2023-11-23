# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
import random
import string
from frappe.utils import random_string
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
	now,
)
from erpnext.accounts.doctype.subscription.subscription import get_portafolio_plan
from erpnext.aprovisionamiento_api import eliminarAprovisionador, cambiarVelocidadAprovisionador, activarAprovisionador, suspenderAprovisionador


class SubscriptionUpdate(Document):
	def on_update(self):
		gestion=frappe.get_doc("Gestion",self.gestion)
		frappe.db.sql("update `tabGestion` set subscription_update = %(name)s where name = %(gestion)s;",{"name":self.name,"gestion":gestion.name})

		if self.desde_oportunidad:
			frappe.db.set_value("Opportunity",self.desde_oportunidad,"actualizacion_de_contrato",self.name)
			frappe.db.set_value('Opportunity', self.desde_oportunidad, 'status', 'Closed')
			frappe.db.set_value('Opportunity', self.desde_oportunidad, 'docstatus', 1)

		if gestion.convertido == 0:
			frappe.db.set_value("Gestion",self.gestion,"convertido",1)
			frappe.db.sql("update `tabGestion` set workflow_state = 'Atendido', estado = 'Atendido' where name = %(gestion)s;",{"gestion":gestion.name})


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
			#time.sleep(1)
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
			
		except:
			pass

@frappe.whitelist()
def filtrar_gestiones():
	gestiones = frappe.db.sql("select gestion from `tabSubscription Update` where gestion is not null")
	return [g[0] for g in gestiones]

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
	if not subscription_up.gestion:
		frappe.msgprint("Para crear el nuevo contrato debe seleccionar una gestión")
		return
	if subscription_up.docstatus == 1:
		frappe.msgprint("El contrato está hecho")
		return
	g = frappe.get_doc("Gestion",subscription_up.gestion)
	if g.workflow_state == 'Finalizado':
		frappe.msgprint("La gestion de esta actualización de contrato ya fue finalizada.")
	plan_row = []
	direccion = ''
	combos = tv = gpon = hfc = tv_gpon = tv_hfc = 0			
	for plan in subscription_up.actualizar_planes_de_contrato:
		#frappe.msgprint(plan.nuevo_plan)
		if not plan.nuevo_plan:
			frappe.msgprint("No puede dejar campos vacíos en la tabla")
			return
		if '+' in plan.nuevo_plan and 'TV' in  plan.nuevo_plan:
			#frappe.msgprint("+ TV")
			combos +=1
			if not frappe.db.exists("Subscription Update Planes", {"parent": name,"nuevo_plan":["like","%TV Combo GPON%"]}) and not frappe.db.exists("Subscription Update Planes", {"parent": name,"nuevo_plan":["like","%TV Combo HFC%"]}):
				frappe.msgprint(f"Hace falta agregar plan TV")
				return
			if 'GPON' in plan.nuevo_plan:
				#frappe.msgprint("GPON")
				gpon += 1
			elif 'HFC' in plan.nuevo_plan:
				#frappe.msgprint("HFC")
				hfc += 1			
		if 'TV Combo GPON' in plan.nuevo_plan  or  'TV Combo HFC' in plan.nuevo_plan:
			tv += 1
			if 'TV Combo GPON' in plan.nuevo_plan:
				tv_gpon += 1
			elif 'TV Combo HFC' in plan.nuevo_plan: 
				tv_hfc += 1
		if plan.plan:
			direccion =  frappe.db.get_value("Subscription Plan Detail",plan.plan,'direccion')
	if tv == combos and hfc == tv_hfc and gpon == tv_gpon:
		for plan in subscription_up.actualizar_planes_de_contrato:
			if plan.plan:			
				spd = frappe.get_doc("Subscription Plan Detail",  plan.plan)
				sp = frappe.get_doc("Subscription Plan",  plan.nuevo_plan)

				item_group_new = frappe.db.get_values("Subscription Plan",plan.nuevo_plan,'item_group')
				item_group_old = frappe.db.get_values("Subscription Plan",spd.plan,'item_group')
				
				plan_row.append([plan.nuevo_plan,spd.qty,spd.direccion,spd.longitud,spd.latitud,sp.billing_interval_count,spd.es_combo,sp.currency,plan.coston,plan.plan, spd.nodo, spd.cost,plan.descuento,spd.contacto])
				
				if item_group_new==item_group_old:
					old_plan_detail = frappe.get_doc("Subscription Plan Detail",plan.plan)
					old_plan_detail.update(
							{
								"estado_plan": "Plan Cerrado",
								"motivo_finalizado": 'Cambio de Servicio',
								"service_end": now(),
								"detalle_finalizado":"PLAN CERRADO POR " + subscription_up.tipo_contrato,
							}
						)
					old_plan_detail.save(ignore_permissions=True)
				else:
					old_plan_detail = frappe.get_doc("Subscription Plan Detail",plan.plan)
					old_plan_detail.update(
							{
								"estado_plan": "Plan Cerrado",
								"motivo_finalizado": 'Cambio de tipo de Servicio IBW',
								"service_end": now(),
								"detalle_finalizado":"PLAN CERRADO POR " + subscription_up.tipo_contrato,
							}
						)
					old_plan_detail.save(ignore_permissions=True)

				p_cerrados = 0
				susc = frappe.get_doc("Subscription",old_plan_detail.parent)
				for p in susc.plans:
					if p.estado_plan not in ('Activo','Inactivo'):
						p_cerrados += 1
				
				if p_cerrados == len(susc.plans):
					frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Terminado', docstatus=1, subscription_update = %(su)s  where name = %(name)s; """,{"name":susc.name, "su":name})
					
				#if old_plan_detail.plan not in ("TV Combo GPON","TV Combo HFC") and "ITV" not in old_plan_detail.plan:
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
						'subscription_plan_detail': plan.plan,
						'nodo': spd.nodo
					})
					bitacora_plan.insert(ignore_permissions=True)
				
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
				bitacora_detalle.insert(ignore_permissions=True)
				equipos = frappe.db.get_values("Subscription Plan Equipos",{"plan": plan.plan, "parent":subscription_up.contrato},'equipo')
				if equipos:
					for equipo in equipos:
						idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1; """,{"parent":equipo})	
						try:
							idx = int(idx[0][0]) + 1
						except:
							idx = 1
				
						ran = str(randStr(chars='abcdefghijklmnopqrstuvwxyz1234567890'))
						frappe.db.sql(""" insert into `tabBitacora Equipos` (name,fecha_transaccion,tipo_transaccion,transaccion,parent,parentfield,parenttype,tercero,idx) 
									values (%(name)s,%(fecha_transaccion)s,'Subscription Update','Cambio de tipo de Servicio IBW',%(parent)s,"bitacora_equipos","Serial No",%(tercero)s,%(idx)s);""",{"name":ran,"fecha_transaccion":now(),"parent":equipo,"tercero":name,"idx":idx})
			else:
				sp = frappe.get_doc("Subscription Plan",  plan.nuevo_plan)
				plan_row.append([plan.nuevo_plan,1,direccion,None,None,sp.billing_interval_count,sp.es_combo,sp.currency,plan.coston,None, None, 0,plan.descuento,None,None])
	else:
		frappe.msgprint("Debe agregar un plan de TV correspondiente a cada combo.")
		return 	
	subscription = frappe.get_doc("Subscription",subscription_up.contrato)
	"""" crear planes de suscripcion a partir de subscription items """	
	customer_group = frappe.db.get_value("Customer",subscription.party,"customer_group")

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
	suscripcion.naming_series = "CORP-" if customer_group != "Individual" else "SUB-"
	suscripcion.no_contrato = subscription_up.no_de_contrato 
	suscripcion.vendedor = subscription_up.vendedor
	suscripcion.subscription_update = name
	suscripcion.campana = subscription_up.campana
	suscripcion.sales_tax_template = subscription.sales_tax_template
	mismo_precio = True
	for item in plan_row:
		
		# frappe.msgprint(frappe._('Fatality Error Project {0} ').format(item))	
		estado_plan = ''
		contador_inactivos = 0
		item_group_nuevo = frappe.db.get_value("Subscription Plan",item[0],"item_group")
		if item[9]:
			item_group_viejo = frappe.db.get_value("Subscription Plan", frappe.db.get_value("Subscription Plan Detail",item[9],"plan"),"item_group")
		else:
			item_group_viejo = ''
		if ("GPON" in item_group_nuevo and "GPON" in item_group_viejo) or (item_group_nuevo in ["HFC 3.0.","HFC", "INET","ITV"] and item_group_viejo in ["HFC 3.0.","HFC", "INET","ITV"]) or (item_group_nuevo == item_group_viejo):
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
				"descuento":item[12],
				"contacto":item[13],
				# "site_survey":item[14],
			}
		suscripcion.append("plans", plans)

		# if item[8] > item[11]:
		# 	mismo_precio = False

	old_total_cost = 0
	new_total_cost = 0
	for plan in subscription_up.actualizar_planes_de_contrato:
		old_total_cost = old_total_cost + float(plan.costo)
		new_total_cost = new_total_cost + float(plan.coston)
	if new_total_cost > old_total_cost:
		mismo_precio = False
	
	if mismo_precio  and contador_inactivos == 0:
		posting_date = frappe.db.sql(""" select posting_date from `tabSales Invoice` where customer = %(customer)s and tipo_factura in ('Recurrente','Prorrateo') order by posting_date desc limit 1;""",{"customer":subscription_up.customer})
		try:
			posting_date = frappe.utils.formatdate(posting_date[0][0], "MMMM")
		except:
			posting_date = None
		if posting_date:
			if posting_date == frappe.utils.formatdate(nowdate(), "MMMM"):
				suscripcion.workflow_state = 'Activo'
			else:
				suscripcion.workflow_state = 'Instalado'
		else:
			suscripcion.workflow_state = 'Instalado'

		# suscripcion.workflow_state='Activo'
		suscripcion.current_invoice_start = subscription.current_invoice_start
		suscripcion.current_invoice_end = subscription.current_invoice_end

	elif  not(mismo_precio)  and contador_inactivos == 0:
		suscripcion.workflow_state='Instalado'
	else:
		suscripcion.workflow_state='Grabado'
		for p in suscripcion.plans:
			if p.old_plan and p.estado_plan == 'Inactivo':
				old_plan_detail = frappe.get_doc("Subscription Plan Detail",p.old_plan)
				old_plan_detail.update(
						{
							"estado_plan": "Activo",
							"service_end": None
						}
					)
				old_plan_detail.save()

	suscripcion.save()
	
	if customer_group != "Individual":
		frappe.db.set_value("Subscription", suscripcion.name, "no_contrato", suscripcion.name)

	for plan in suscripcion.plans:
		frappe.db.set_value("Subscription Plan Detail",plan.name,"planid",plan.name)
		if plan.old_plan and plan.estado_plan == 'Activo':
			equipos = frappe.db.get_values("Subscription Plan Equipos",{"plan": plan.old_plan, "parent":subscription_up.contrato},'equipo')
			if equipos:
				frappe.db.sql(""" update  `tabSubscription Plan Equipos` set plan= %(newplan)s , parent=%(newsuscription)s 
								where plan= %(oldplan)s and parent=%(Oldsuscription)s; """, {"newplan":plan.name, "newsuscription":suscripcion.name,"oldplan":plan.old_plan,"Oldsuscription":subscription_up.contrato})
				for e in equipos:
					if frappe.db.exists("Aprovisionamiento", e[0]):
						frappe.db.set_value("Aprovisionamiento",e[0],"plan",plan.name)
			
				if (frappe.db.get_value("Subscription Plan",plan.plan,"item") != frappe.db.get_value("Subscription Plan",frappe.db.get_value("Subscription Plan Detail",plan.old_plan,"plan"),"item")):
					crear_orden_aprovisionamiento(plan.name,[e[0] for e in equipos])

	for plan in suscripcion.plans:
		if plan.old_plan:
			costo = frappe.db.get_value("Subscription Update Planes",{"plan":plan.old_plan},"coston")
			frappe.db.sql(""" update `tabSubscription Plan Detail` set cost = %(costo)s where old_plan = %(old_plan)s 
			and parent = %(parent)s; """,{"costo":costo,"old_plan":plan.old_plan,"parent":suscripcion.name})
		else:
			costo = frappe.db.get_value("Subscription Update Planes",{"nuevo_plan":plan.plan},"coston")
			frappe.db.sql(""" update `tabSubscription Plan Detail` set cost = %(costo)s where plan = %(plan)s 
			and parent = %(parent)s; """,{"costo":costo,"plan":plan.plan,"parent":suscripcion.name})

	frappe.msgprint(frappe._('Nueva Suscripción con ID {0}').format(frappe.utils.get_link_to_form("Subscription", suscripcion.name)))
	
	

	if subscription_up.campana:
		from erpnext.accounts.doctype.subscription.subscription import aplicar_promocion
		aplicar_promocion(subscription_up.campana,suscripcion.name)
	
	frappe.db.sql(""" update  `tabSubscription Update` set nuevo_contrato= %(newplan)s , docstatus=1 
		where name= %(name)s ; """, {"newplan":suscripcion.name, "name":name})	
	frappe.db.sql("update `tabGestion` set workflow_state = 'Finalizado', estado = 'Finalizado'  where name = %(gestion)s;",{"gestion":subscription_up.gestion})

	if g.tipo_gestion == "Cancelaciones":
		frappe.db.set_value("Detalle Cambio de Razon Social", {"parenttype":"Gestion","parent":subscription_up.gestion, "contrato":subscription_up.contrato},"nuevo_contrato",subscription_up.name)

	for plan in suscripcion.plans:
		if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": plan.name}):
			bitacora_plan = frappe.get_doc({
				'doctype': "Bitacora de Planes",
				'plan': plan.plan,
				'cliente':  subscription_up.customer,
				'estado_plan': plan.estado_plan,
				'direccion': plan.direccion,
				'currency': plan.currency,
				'costo':frappe.db.get_value("Subscription Plan Detail",plan.name,"cost"),
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

	return suscripcion.name


		
	
@frappe.whitelist()
def filtrar_planes_nuevos(customer,desde_oportunidad=None):
	# cg = frappe.db.get_value("Customer",customer,'customer_group')
	# if cg == 'Individual':
	# 	return False
	if desde_oportunidad:
		planes = frappe.db.sql(""" select sp.name from `tabSubscription Plan` sp inner join  `tabOpportunity` op 
			on sp.oportunidad = op.name where op.customer = %(customer)s and op.name = %(oportunidad)s;""",{"customer":customer,"oportunidad":desde_oportunidad})
		return [p[0] for p in planes]
	else:
		[]


def crear_orden_aprovisionamiento(plan,equipos):
	spd = frappe.get_doc("Subscription Plan Detail", {"name": plan})
	doc = frappe.get_doc("Subscription", {"name": spd.parent})
	status = ''
	var = False
	if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"APROVISIONAMIENTO","plan_de_subscripcion":plan}):
		so = frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"TRASLADO","plan_de_subscripcion":plan})
		if so.workflow_state=="Cancelado":
			status = "Pasa"
		else:
			status = "No Pasa"
			frappe.msgprint(frappe._('Ya existe una orden de APROVISIONAMIENTO para este plan con ID {0}').format(so.name))
	else:
		var = True

	if status=="Pasa" or var:
		if spd.estado_plan=="Activo":
			portafolio=get_portafolio_plan(spd.plan)
			direccion=frappe.get_doc("Address", spd.direccion)
			od = frappe.get_doc({
				'doctype': "Service Order",
				'tipo_de_orden': "APROVISIONAMIENTO",
				'workflow_state': "Abierto",
				'tipo_de_origen': "Subscription",
				'nombre_de_origen': spd.parent,
				'descripcion': frappe._('Ejecutar APROVISIONAMIENTO de {0}').format(spd.plan),
				'tipo': 'Customer',
				'tercero': frappe.db.get_value("Subscription",spd.parent,"party"),
				'nombre': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_name'),
				'tipo_cliente': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_group'),
				'plan_de_subscripcion': plan,
				'direccion_de_instalacion': spd.direccion,
				'informacion_de_contacto':spd.contacto,
				'portafolio': str(portafolio[0][0]),
				'departamento': direccion.departamento,
				'municipio': direccion.municipio,
				'barrio': direccion.barrio,
				'direccion': direccion.address_line1,
				'latitud':spd.latitud,
				'longitud':spd.longitud,
				'nodo':spd.nodo
			})
			od.insert(ignore_permissions=True)
			frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))

			
			for equipo in equipos:
				ran = random_string(6)
				ran = ran + equipo	
				code = frappe.db.get_value('Serial No', {"name": equipo}, 'item_code')
				frappe.db.sql(""" insert into `tabEquipo_Orden_Servicio` (name,serial_no,parent,parenttype,parentfield,item_code) 
					values (%(name)s,%(serial_no)s,%(parent)s,'Service Order','equipo_orden_servicio',%(item_code)s) """, {"name":ran,"serial_no":equipo,"parent":od.name,"item_code":code})