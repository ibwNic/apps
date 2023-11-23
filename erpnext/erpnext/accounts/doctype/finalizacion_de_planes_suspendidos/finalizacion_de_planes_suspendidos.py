# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import time
from datetime import timedelta
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
class FinalizaciondePlanesSuspendidos(Document):
	def on_submit(self):
		for plan in self.detalle_de_planes:
			if not plan.estado_plan:
				frappe.msgprint(f"El plan {plan.plan_id} en fila {plan.idx} no tiene estado, favor obtener los estados del plan.")
				self.reload
				return
		
			if "SUSPENDIDO" in plan.estado_plan:
				frappe.db.sql("""update `tabSubscription Plan Detail` set estado_plan = 'Plan Cerrado', service_end = %(service_end)s,
				motivo_finalizado = %(motivo)s, detalle_finalizado = CONCAT('Plan cerrado por cancelación programada. Motivo: ', %(motivo)s)  where name = %(plan)s;""",{"service_end": self.fecha_fin_del_contrato,"motivo":self.motivo,"plan":plan.plan_id})

				spd = frappe.get_doc("Subscription Plan Detail", plan.plan_id)
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
				od.tercero = plan.cliente
				od.nombre = frappe.db.get_value("Customer",plan.cliente,"customer_name")
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

				susc = frappe.get_doc("Subscription", spd.parent)

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
						'cliente':  plan.cliente,
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
					"detalle":"Plan cerrado por falta de pago. Motivo: " + self.motivo,
					"fecha": now(),
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"Finalizacion de Planes Suspendidos",
					"tercero":self.name,
					'estado_plan': 'Plan Cerrado',
					})
				bitacora_detalle.insert()

		for plan2 in self.detalle_de_planes:
			spd = frappe.get_doc("Subscription Plan Detail",plan2.plan_id)
			p_cerrados = 0
			susc = frappe.get_doc("Subscription",spd.parent)
			for plan in susc.plans:
				if plan.estado_plan not in ('Activo','Inactivo','SUSPENDIDO: Manual','SUSPENDIDO: Temporal'):
					p_cerrados += 1
			if p_cerrados == len(susc.plans):
				frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Terminado' where name = %(subsc)s; """,{"subsc":spd.parent})
			susc_cliente = frappe.db.get_values("Subscription",{"party":plan2.cliente,"workflow_state":["in",["Activo","Instalado"]]},"name")
			if len(susc_cliente) == 0:
				frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'TERMINADO' where name = %(customer)s; """,{"customer":plan2.cliente})
				



def get_portafolio_plan(plan):
	portafolio = frappe.db.sql(
	"""Select t1.item_group
	from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item where t2.name=%(plan)s limit 1 """,
	{"plan": plan},)
	return portafolio

@frappe.whitelist()
def obtener_estado_de_planes(name):
	doc = frappe.get_doc("Finalizacion de Planes Suspendidos", name)

	for plan in doc.detalle_de_planes:
		spd = frappe.get_doc("Subscription Plan Detail", plan.plan_id)
		frappe.db.set_value("Detalle Planes A Terminar",{"plan_id":plan.plan_id},"estado_plan",spd.estado_plan)

	frappe.msgprint("Estado de planes ha sido cargado")
	return 



