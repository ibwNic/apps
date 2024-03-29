# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# modificado 20/01/23 15:20

import frappe
import time
from collections import deque
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.mapper import get_mapped_doc
from erpnext.crm.utils import CRMNote, copy_comments, link_communications, link_open_events
from frappe.model.document import Document
from frappe.utils import cstr, flt, get_link_to_form, getdate, new_line_sep, nowdate, now


class Suspensiones(Document):
	pass

def Suspender_clientes(susp, customer):

	planes_suspendidos = Suspender_Planes(susp.name,customer)
	if planes_suspendidos:
		#frappe.msgprint(customer)
		frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'SUSPENDIDO (Manual)' where name = %(customer)s; """,{"customer":customer})
		detalle_suspension = frappe.get_doc("Detalle Suspension", {"customer": customer, "parent":susp.name})
		detalle_suspension.update(
			{
			"estado_cliente": "Suspendido"
			}
		)
		detalle_suspension.save()	


def Suspender_Planes(name, customer):
	try:
		plans = frappe.db.sql(
		"""select spd.name,s.name,i.item_group from `tabItem` i
			inner join `tabSubscription Plan`sp on i.name=sp.item
			inner join `tabSubscription Plan Detail` spd on sp.name=spd.plan
			inner join `tabSubscription` s on s.name=spd.parent 
			where spd.cost>0 and spd.estado_plan='Activo' 
			and s.party=%(party)s order by i.item_group desc""",
		{"party": customer },
		)
		
		for plan in plans: 
		
			upd_suspe = frappe.get_doc("Subscription Plan Detail", {"name": plan[0]})	
			upd_suspe.update(
				{
				"estado_plan": "SUSPENDIDO: Manual",
				"service_suspend": now(),
				}
			)
			upd_suspe.save()

			frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Suspendido' where name = %(plan)s; """,{"plan":plan[1]})
		
			if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": upd_suspe.name}):
				bitacora_plan = frappe.get_doc({
					'doctype': "Bitacora de Planes",
					'plan': upd_suspe.plan,
					'cliente':  customer,
					'estado_plan': "SUSPENDIDO: Manual",
					'direccion': upd_suspe.direccion,
					'currency': upd_suspe.currency,
					'costo':upd_suspe.cost,
					'intervalo_de_facturacion':upd_suspe.billing_interval_count,
					'subscription_plan_detail': upd_suspe.name

				})
				bitacora_plan.insert()
			
			bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": upd_suspe.name})
					
			bitacora_detalle = frappe.get_doc({
				"doctype": "Detalle Bitacora Planes",
				"detalle":"Plan suspendido",
				"fecha": now(),
				"usuario":frappe.session.user,
				"parent": bitacora_plan.name,
				"parentfield":"detalle",
				"parenttype": "Bitacora de Planes"
				})
			bitacora_detalle.insert()		
		return True
	except Exception as e:
		frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))
		return False


@frappe.whitelist()
def generar_vista_previa(name):
	suspension = frappe.get_doc("Suspensiones", name)

	customer_group = suspension.customer_group
	if customer_group == "Todas las categorías de clientes":
		customer_group = ''

	query = """  select * from vw_clientes_saldo_pendiente where customer_group like """ + "'%" + customer_group + "%'"

	if suspension.portafolios:
		lista_portafolio = []
		for portafolio in suspension.portafolios:
			lista_portafolio.append(portafolio.portafolio)
		lista_portafolio = str([p for p in lista_portafolio]).replace("[","(").replace("]",")")
		query = query +  " and Portafolio in " + lista_portafolio
		
	if suspension.territory:
		query = query +  " and territory = " + "'" + suspension.territory + "'" 
	if suspension.municipio:
		query = query +  " and Municipio = " + "'" + suspension.municipio + "'" 
	if suspension.barrio:
		query = query +  " and Barrio = " + "'" + suspension.barrio + "'" 
	
	if suspension.treinta == 1 or suspension.sesenta == 1 or suspension.noventa == 1 or suspension.mas == 1:
		query = query + 'and ('
		if suspension.treinta == 1:
			query = query +  " treinta >= " + str(suspension.deuda_minima_30)
		if suspension.sesenta == 1:
			if query[-1] == '(':
				query = query +  " sesenta >= " + str(suspension.deuda_minima_60)
			else:
				query = query +  " or sesenta >= " + str(suspension.deuda_minima_60)
		if suspension.noventa == 1:
			if query[-1] == '(':
				query = query +  " noventa >= " + str(suspension.deuda_minima_90)
			else:
				query = query +  " or noventa >= " + str(suspension.deuda_minima_90)
		if suspension.mas == 1:
			if query[-1] == '(':
				query = query +  " mas >= " + str(suspension.deuda_minima_90_a_más)
			else:
				query = query +  " or mas >= " + str(suspension.deuda_minima_90_a_más)
		query = query + ')'
		
	excepciones = frappe.db.get_values("Excepciones",{"parent": name},"cliente")
	if excepciones:
		clientes_excepciones = str([ex[0] for ex in excepciones]).replace("[","(").replace("]",")")
		query = query +  " and name not in " + clientes_excepciones
	
	resultado = frappe.db.sql(query)
	
	frappe.db.sql(
			"""
			DELETE FROM `tabDetalle Suspension`
			WHERE parent = %(parent)s""",{"parent": name}
		)	
	time.sleep(1)
	
	try:
		for res in resultado:
			
			child = frappe.new_doc("Detalle Suspension")
			child.update(
				{
					"parent": name,
					"parentfield": "detalle_suspension",
					"parenttype": "Suspensiones",
					"customer":res[0],
					"nombre":res[1],
					"portafolio":res[2],
					"territory":res[3],
					"municipio":res[4],
					"barrio":res[5],
					"tipo_de_cliente":res[6],
					"estado_cliente":res[7],
					"de_0_a_30":res[8],
					"de_31_a_60":res[9],
					"de_61_a_90":res[10],
					"mayor_a_90":res[11],
					"importe_total_pendiente":res[12],
				
					
				}
			)
			suspension.detalle_suspension.append(child)	
			suspension.save()
	except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))	

	return query

@frappe.whitelist()
def process_de_Suspencion(name):
	
	susp = frappe.get_doc("Suspensiones", name)
	clientes = []
	Customers_f = frappe.db.sql(
	"""select customer,estado_cliente from `tabDetalle Suspension` where parent=%(pt)s   limit 10000""",
	{"pt": name},
	)
	

	for cliente in Customers_f: 
		if cliente[1]=='ACTIVO':
			clientes.append(cliente[0])
		
	clientes = str(clientes).replace("[","(").replace("]",")")
	query = """select spd.name,s.name,i.item_group,s.party from `tabItem` i
			inner join `tabSubscription Plan`sp on i.name=sp.item
			inner join `tabSubscription Plan Detail` spd on sp.name=spd.plan
			inner join `tabSubscription` s on s.name=spd.parent 
			where spd.cost>0 and spd.estado_plan='Activo' 
			and s.party in """
	query = query + clientes + """ order by i.item_group desc """
	plans = frappe.db.sql(query,{"party": clientes } )

	portafolio_list = []
	[portafolio_list.append(item[2]) for item in plans if item[2] not in portafolio_list]

	portafolios = dict()

	for p in portafolio_list:		
		portafolios[p] = deque()
	for item_group in plans: 
		portafolios[item_group[2]].append([item_group[3], item_group[1], item_group[0],item_group[2]])

	for portafolio in portafolios:
		if portafolio == 'ITV':
			continue
		od = frappe.new_doc('Service Order')
		od.tipo_de_orden = "SUSPENSION"
		od.workflow_state = "Abierto"
		od.tipo_de_origen = "Suspensiones"
		od.tipo =  "Suspensiones"
		od.portafolio = portafolio
		od.nombre_de_origen = name
		od.tercero = name
		od.save()
		frappe.msgprint(frappe._('Nueva orden de suspension con ID {0}').format(od.name))
		
		for susc in portafolios[portafolio]:
			equipos = frappe.db.sql("""select name, item_code from `tabSerial No` where name in (select equipo from `tabSubscription Plan Equipos` where parent = %(parent)s)""",{"parent":susc[1]})	
			if equipos:
				
				for e in equipos:				
					so_detalle = frappe.new_doc('SO Detalle Clientes Suspendidos')
					so_detalle.parent =  od.name
					so_detalle.parentfield = "so_detalle_clientes_suspendidos"
					so_detalle.parenttype = "Service Order"
					so_detalle.cliente =  susc[0]
					so_detalle.subscription_plan_detail = susc[2]
					so_detalle.subscription = susc[1]
					so_detalle.equipos = e[0]
					so_detalle.modelo = e[1]
					so_detalle.save()	
			else:		
				so_detalle = frappe.new_doc('SO Detalle Clientes Suspendidos')
				so_detalle.parent =  od.name
				so_detalle.parentfield = "so_detalle_clientes_suspendidos"
				so_detalle.parenttype = "Service Order"
				so_detalle.cliente =  susc[0]
				so_detalle.subscription_plan_detail = susc[2]
				so_detalle.subscription = susc[1]
				so_detalle.save()		
	for cliente in Customers_f: 
		if cliente[1]=='ACTIVO':
			Suspender_clientes(susp,cliente[0])
			time.sleep(1)
	frappe.db.sql(""" update `tabSuspensiones` set docstatus = 1 where name = %(name)s; """,{"name":name})

@frappe.whitelist()
def limpiar_campos_territorio(name):	
	frappe.db.set_value("Suspensiones",name,'territory',None)	
	frappe.db.set_value("Suspensiones",name,'municipio',None)	
	frappe.db.set_value("Suspensiones",name,'barrio',None)	


@frappe.whitelist()
def obtener_excepciones_clientes(name):
	if not frappe.db.exists("Excepciones", {"parent":name}):
		clientes = frappe.db.sql("select cliente, motivo from `tabClientes VIP`;")
		for cliente in clientes:
			excepciones = frappe.get_doc({
			"doctype": "Excepciones",
			"cliente": cliente[0],
			"motivo": cliente[1],
			"parent": name,
			"parentfield":"excepciones",
			"parenttype": "Suspensiones"
			})
			excepciones.insert()
	
