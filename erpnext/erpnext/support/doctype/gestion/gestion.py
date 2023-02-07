# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
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


class Gestion(Document):
	
	def on_update(self):
		if self.workflow_state == 'Finalizado':
			if self.tipo_gestion == 'Cancelaciones':
				if self.estado_cancelacion == 'Aceptada':
					frappe.db.sql(""" update `tabGestion` set estado = 'Aceptado' where name = %(name)s; """,{"name":self.name})
				elif self.estado_cancelacion == 'Retenida' and self.medida_retencion:
					frappe.db.sql(""" update `tabGestion` set estado = 'Finalizado' where name = %(name)s; """,{"name":self.name})
			# if self.tipo_gestion == "Suspension Temporal":
			# 	programar_suspensiones_temporales()

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
def obtener_planes_de_cliente(name):
	g = frappe.get_doc("Gestion", name)
	if g.tipo_gestion == "Cancelaciones":
		g.estado = 'En Proceso'
	if not g.cambiar_planes:
		try:
			contratos = frappe.db.get_values("Subscription",{"party":g.customer, "workflow_state":"Activo"},'name')
			contratos = [c[0] for c in contratos]
			if contratos:
				planes = frappe.db.sql("""select name, plan, parent from `tabSubscription Plan Detail` where parent in %(parent)s and estado_plan = "Activo";""",{"parent":contratos})
				for plan in planes:
					item1 = g.append('cambiar_planes', {"plan": ""})
					item1.plan = plan[0]				
					item1.plan_name = plan[1]
					item1.contrato = plan[2]
				g.save()
				return 'True'	
		except:
			frappe.msgprint("Este cliente no tiene planes activos")	
			return 'False'
	else:
		return 'False'

@frappe.whitelist()
def estado_gestion(name):
	# frappe.db.set_value("Gestion",name,'estado','Aceptado')
	# frappe.db.set_value("Gestion",name,'docstatus',1)
	gestion = frappe.get_doc("Gestion",name)
	if gestion.estado_cancelacion == 'Aceptada':
		frappe.db.sql(""" update `tabGestion` set estado = 'Aceptado' where name = %(name)s; """,{"name":name})
	elif gestion.estado_cancelacion == 'Retenida' and gestion.medida_retencion:
		frappe.db.sql(""" update `tabGestion` set estado = 'Finalizado' where name = %(name)s; """,{"name":name})

# @frappe.whitelist()
# def obtener_planes_de_cliente(customer):
# 	mr = frappe.new_doc('Gestion')
# 	mr.update({
# 		'customer': customer,
# 	})
# 	contratos = frappe.db.get_values("Subscription",{"party":customer, "workflow_state":"Activo"},'name')
# 	contratos = [c[0] for c in contratos]
# 	if contratos:
# 		planes = frappe.db.sql("""select name, plan, parent from `tabSubscription Plan Detail` where parent in %(parent)s and estado_plan = "Activo";""",{"parent":contratos})
# 		for plan in planes:
# 			item1 = mr.append('cambiar_planes', {"plan": ""})				
# 			item1.plan_name = plan[1]
# 			item1.contrato = plan[2]
# 		return {'docs': mr.as_dict()}
# 	else:
# 		return

	# def on_update(self):
	# 	if self.workflow_state == 'Finalizado':
	# 		if self.tipo_gestion == 'Cancelaciones':
	# 			if self.estado_cancelacion == 'Aceptada':
	# 				frappe.db.sql(""" update `tabGestion` set estado = 'Aceptado' where name = %(name)s; """,{"name":self.name})
	# 			elif self.estado_cancelacion == 'Retenida' and self.medida_retencion:
	# 				frappe.db.sql(""" update `tabGestion` set estado = 'Finalizado' where name = %(name)s; """,{"name":self.name})	
	# 		# if self.tipo_gestion == 'Suspension Temporal':
	# 		# 	for plan in self.cambiar_planes:
	# 		# 		upd_suspe = frappe.get_doc("Subscription Plan Detail", {"name": plan.plan})	
	# 		# 		upd_suspe.update(
	# 		# 			{
	# 		# 			"estado_plan": "SUSPENDIDO: Temporal",
	# 		# 			"service_suspend": now(),
	# 		# 			}
	# 		# 		)
	# 		# 		upd_suspe.save()
	# 		# 		# frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Suspendido' where name = %(subsc)s; """,{"subsc":upd_suspe.parent})
					
	# 		# 		p_susp = 0
	# 		# 		susc = frappe.get_doc("Subscription",upd_suspe.parent)
	# 		# 		for p in susc.plans:
	# 		# 			if p.estado_plan not in ('Activo','Inactivo'):
	# 		# 				p_susp += 1
					
	# 		# 		if p_susp == len(susc.plans):
	# 		# 			frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Suspendido' where name = %(subsc)s; """,{"subsc":upd_suspe.parent})
									
	# 		# 		susc_cliente = frappe.db.get_values("Subscription",{"party":self.customer,"workflow_state":["in",["Activo","Instalado"]]},"name")
	# 		# 		if len(susc_cliente) == 0:
	# 		# 			frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'SUSPENDIDO (Temporal)' where name = %(customer)s; """,{"customer":self.customer})

	# 		# 		if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": upd_suspe.name}):
	# 		# 			bitacora_plan = frappe.get_doc({
	# 		# 				'doctype': "Bitacora de Planes",
	# 		# 				'plan': upd_suspe.plan,
	# 		# 				'cliente':  self.customer,
	# 		# 				'estado_plan': "SUSPENDIDO: Temporal",
	# 		# 				'direccion': upd_suspe.direccion,
	# 		# 				'currency': upd_suspe.currency,
	# 		# 				'costo':upd_suspe.cost,
	# 		# 				'intervalo_de_facturacion':upd_suspe.billing_interval_count,
	# 		# 				'subscription_plan_detail': upd_suspe.name

	# 		# 			})
	# 		# 			bitacora_plan.insert()					
	# 		# 		bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": upd_suspe.name})						
	# 		# 		bitacora_detalle = frappe.get_doc({
	# 		# 			"doctype": "Detalle Bitacora Planes",
	# 		# 			"detalle":"Plan suspendido temporal",
	# 		# 			"fecha": now(),
	# 		# 			"usuario":frappe.session.user,
	# 		# 			"parent": bitacora_plan.name,
	# 		# 			"parentfield":"detalle",
	# 		# 			"parenttype": "Bitacora de Planes"
	# 		# 			})
	# 		# 		bitacora_detalle.insert()	

	# 		frappe.db.sql(""" update `tabGestion` set estado = 'Finalizado' where name = %(name)s; """,{"name":self.name})
	# 	if self.workflow_state == 'En Proceso':
	# 		if self.tipo_gestion == 'Suspension Temporal':
	# 			if not self.fecha_inicio_suspension_temporal or not self.fecha_fin_de_suspension_temporal:
	# 				frappe.msgprint("ingresar fechas de suspensión temporal")
	# 				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Abierto')
	# 				self.reload()
	# 				return
	# 			frappe.msgprint(str(programar_suspensiones_temporales()))
	# 	self.reload()



def programar_suspensiones_temporales():
	""" suspender planes, contratos y clientes desde gestiones finalizadas """
	gestiones = frappe.db.sql(""" select name, customer from `tabGestion` where tipo_gestion = 'Suspension Temporal' and workflow_state = 'Finalizado' and fecha_inicio_suspension_temporal = CURDATE()""")
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
					"usuario":frappe.session.user,
					"parent": bitacora_plan.name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes"
					})
				bitacora_detalle.insert()	


