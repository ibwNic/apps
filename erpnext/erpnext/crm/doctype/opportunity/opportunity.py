# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
import random
import string
import frappe
import numpy_financial as npf
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.email.inbox import link_communication_to_document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import DocType, Interval
from frappe.query_builder.functions import Now
from frappe.utils import flt, get_fullname, format_time, formatdate, getdate, nowdate,nowtime
# import numpy_financial as np
from erpnext.crm.utils import (
	CRMNote,
	copy_comments,
	link_communications,
	link_open_events,
	link_open_tasks,
)
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
	today,
)
from frappe.utils import now, today

from erpnext.setup.utils import get_exchange_rate
from erpnext.utilities.transaction_base import TransactionBase


class Opportunity(TransactionBase, CRMNote):

	def onload(self):
		ref_doc = frappe.get_doc(self.opportunity_from, self.party_name)
		load_address_and_contact(ref_doc)
		self.set("__onload", ref_doc.get("__onload"))

	def after_insert(self):
		if self.opportunity_from == "Lead":
			frappe.get_doc("Lead", self.party_name).set_status(update=True)
			self.disable_lead()

			link_open_tasks(self.opportunity_from, self.party_name, self)
			link_open_events(self.opportunity_from, self.party_name, self)
			if frappe.db.get_single_value("CRM Settings", "carry_forward_communication_and_comments"):
				copy_comments(self.opportunity_from, self.party_name, self)
				link_communications(self.opportunity_from, self.party_name, self)

	def validate(self):
		self.make_new_lead_if_required()
		self.validate_item_details()
		self.validate_uom_is_integer("uom", "qty")
		# self.validate_cust_name()
		self.map_fields()
		self.set_exchange_rate()

		if not self.title:
			self.title = self.customer_name

		self.calculate_totals()
		self.update_prospect()

	def map_fields(self):
		for field in self.meta.get_valid_columns():
			if not self.get(field) and frappe.db.field_exists(self.opportunity_from, field):
				try:
					value = frappe.db.get_value(self.opportunity_from, self.party_name, field)
					frappe.db.set(self, field, value)
				except Exception:
					continue

	def set_exchange_rate(self):
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if self.currency == company_currency:
			self.conversion_rate = 1.0
			return

		if not self.conversion_rate or self.conversion_rate == 1.0:
			self.conversion_rate = get_exchange_rate(self.currency, company_currency, self.transaction_date)

	def calculate_totals(self):
		total = base_total = 0
		for item in self.get("items"):
			item.amount = flt(item.rate) * flt(item.qty)
			item.base_rate = flt(self.conversion_rate) * flt(item.rate)
			item.base_amount = flt(self.conversion_rate) * flt(item.amount)
			total += item.amount
			base_total += item.base_amount

		self.total = flt(total)
		self.base_total = flt(base_total)

	def update_prospect(self):
		prospect_name = None
		if self.opportunity_from == "Prospect" and self.party_name:
			prospect_name = self.party_name
		elif self.opportunity_from == "Lead":
			prospect_name = frappe.db.get_value("Prospect Lead", {"lead": self.party_name}, "parent")

		if prospect_name:
			prospect = frappe.get_doc("Prospect", prospect_name)

			opportunity_values = {
				"opportunity": self.name,
				"amount": self.opportunity_amount,
				"stage": self.sales_stage,
				"deal_owner": self.opportunity_owner,
				"probability": self.probability,
				"expected_closing": self.expected_closing,
				"currency": self.currency,
				"contact_person": self.contact_person,
			}

			opportunity_already_added = False
			for d in prospect.get("opportunities", []):
				if d.opportunity == self.name:
					opportunity_already_added = True
					d.update(opportunity_values)
					d.db_update()

			if not opportunity_already_added:
				prospect.append("opportunities", opportunity_values)
				prospect.flags.ignore_permissions = True
				prospect.flags.ignore_mandatory = True
				prospect.save()

	def disable_lead(self):
		if self.opportunity_from == "Lead":
			frappe.db.set_value("Lead", self.party_name, {"disabled": 1, "docstatus": 1})

	def make_new_lead_if_required(self):
		"""Set lead against new opportunity"""
		if (not self.get("party_name")) and self.contact_email:
			# check if customer is already created agains the self.contact_email
			dynamic_link, contact = DocType("Dynamic Link"), DocType("Contact")
			customer = (
				frappe.qb.from_(dynamic_link)
				.join(contact)
				.on(
					(contact.name == dynamic_link.parent)
					& (dynamic_link.link_doctype == "Customer")
					& (contact.email_id == self.contact_email)
				)
				.select(dynamic_link.link_name)
				.distinct()
				.run(as_dict=True)
			)

			if customer and customer[0].link_name:
				self.party_name = customer[0].link_name
				self.opportunity_from = "Customer"
				return

			lead_name = frappe.db.get_value("Lead", {"email_id": self.contact_email})
			if not lead_name:
				sender_name = get_fullname(self.contact_email)
				if sender_name == self.contact_email:
					sender_name = None

				if not sender_name and ("@" in self.contact_email):
					email_name = self.contact_email.split("@")[0]

					email_split = email_name.split(".")
					sender_name = ""
					for s in email_split:
						sender_name += s.capitalize() + " "

				lead = frappe.get_doc(
					{"doctype": "Lead", "email_id": self.contact_email, "lead_name": sender_name or "Unknown"}
				)

				lead.flags.ignore_email_validation = True
				lead.insert(ignore_permissions=True)
				lead_name = lead.name

			self.opportunity_from = "Lead"
			self.party_name = lead_name

	@frappe.whitelist()
	def declare_enquiry_lost(self, lost_reasons_list, competitors, detailed_reason=None):
		if not self.has_active_quotation():
			self.status = "Lost"
			self.lost_reasons = []
			self.competitors = []

			if detailed_reason:
				self.order_lost_reason = detailed_reason

			for reason in lost_reasons_list:
				self.append("lost_reasons", reason)

			for competitor in competitors:
				self.append("competitors", competitor)

			self.save()

		else:
			frappe.throw(_("Cannot declare as lost, because Quotation has been made."))

	def has_active_quotation(self):
		if not self.get("items", []):
			return frappe.get_all(
				"Quotation",
				{"opportunity": self.name, "status": ("not in", ["Lost", "Closed"]), "docstatus": 1},
				"name",
			)
		else:
			return frappe.db.sql(
				"""
				select q.name
				from `tabQuotation` q, `tabQuotation Item` qi
				where q.name = qi.parent and q.docstatus=1 and qi.prevdoc_docname =%s
				and q.status not in ('Lost', 'Closed')""",
				self.name,
			)

	def has_ordered_quotation(self):
		if not self.get("items", []):
			return frappe.get_all(
				"Quotation", {"opportunity": self.name, "status": "Ordered", "docstatus": 1}, "name"
			)
		else:
			return frappe.db.sql(
				"""
				select q.name
				from `tabQuotation` q, `tabQuotation Item` qi
				where q.name = qi.parent and q.docstatus=1 and qi.prevdoc_docname =%s
				and q.status = 'Ordered'""",
				self.name,
			)

	def has_lost_quotation(self):
		lost_quotation = frappe.db.sql(
			"""
			select name
			from `tabQuotation`
			where docstatus=1
				and opportunity =%s and status = 'Lost'
			""",
			self.name,
		)
		if lost_quotation:
			if self.has_active_quotation():
				return False
			return True

	# def validate_cust_name(self):
	# 	if self.party_name:
	# 		if self.opportunity_from == "Customer":
	# 			self.customer_name = frappe.db.get_value("Customer", self.party_name, "customer_name")
	# 		elif self.opportunity_from == "Lead":
	# 			customer_name = frappe.db.get_value("Prospect Lead", {"lead": self.party_name}, "parent")
	# 			if not customer_name:
	# 				lead_name, company_name = frappe.db.get_value(
	# 					"Lead", self.party_name, ["lead_name", "company_name"]
	# 				)
	# 				customer_name = company_name or lead_name

	# 			self.customer_name = customer_name
	# 		elif self.opportunity_from == "Prospect":
	# 			self.customer_name = self.party_name

	def validate_item_details(self):
		if not self.get("items"):
			return

		# set missing values
		item_fields = ("item_name", "description", "item_group", "brand")

		for d in self.items:
			if not d.item_code:
				continue

			item = frappe.db.get_value("Item", d.item_code, item_fields, as_dict=True)
			for key in item_fields:
				if not d.get(key):
					d.set(key, item.get(key))


@frappe.whitelist()
def get_item_details(item_code):
	item = frappe.db.sql(
		"""select item_name, stock_uom, image, description, item_group, brand
		from `tabItem` where name = %s""",
		item_code,
		as_dict=1,
	)
	return {
		"item_name": item and item[0]["item_name"] or "",
		"uom": item and item[0]["stock_uom"] or "",
		"description": item and item[0]["description"] or "",
		"image": item and item[0]["image"] or "",
		"item_group": item and item[0]["item_group"] or "",
		"brand": item and item[0]["brand"] or "",
	}


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges

		quotation = frappe.get_doc(target)

		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")

		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)

		quotation.conversion_rate = exchange_rate

		# get default taxes
		taxes = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=quotation.company
		)
		if taxes.get("taxes"):
			quotation.update(taxes)

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		if not source.get("items", []):
			quotation.opportunity = source.name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Quotation",
				"field_map": {"opportunity_from": "quotation_to", "name": "enq_no"},
			},
			"Opportunity Item": {
				"doctype": "Quotation Item",
				"field_map": {
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"uom": "stock_uom",
				},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.conversion_factor = 1.0

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Request for Quotation"},
			"Opportunity Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [["name", "opportunity_item"], ["parent", "opportunity"], ["uom", "uom"]],
				"postprocess": update_item,
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.opportunity_name = source.name

		if source.opportunity_from == "Lead":
			target.lead_name = source.party_name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Customer",
				"field_map": {"currency": "default_currency", "customer_name": "customer_name"},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Supplier Quotation", "field_map": {"name": "opportunity"}},
			"Opportunity Item": {"doctype": "Supplier Quotation Item", "field_map": {"uom": "stock_uom"}},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		opp = frappe.get_doc("Opportunity", name)
		opp.status = status
		opp.save()


def auto_close_opportunity():
	"""auto close the `Replied` Opportunities after 7 days"""
	auto_close_after_days = (
		frappe.db.get_single_value("CRM Settings", "close_opportunity_after_days") or 15
	)

	table = frappe.qb.DocType("Opportunity")
	opportunities = (
		frappe.qb.from_(table)
		.select(table.name)
		.where(
			(table.modified < (Now() - Interval(days=auto_close_after_days))) & (table.status == "Replied")
		)
	).run(pluck=True)

	for opportunity in opportunities:
		doc = frappe.get_doc("Opportunity", opportunity)
		doc.status = "Closed"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()


@frappe.whitelist()
def make_opportunity_from_communication(communication, company, ignore_communication_links=False):
	from erpnext.crm.doctype.lead.lead import make_lead_from_communication

	doc = frappe.get_doc("Communication", communication)

	lead = doc.reference_name if doc.reference_doctype == "Lead" else None
	if not lead:
		lead = make_lead_from_communication(communication, ignore_communication_links=True)

	opportunity_from = "Lead"

	opportunity = frappe.get_doc(
		{
			"doctype": "Opportunity",
			"company": company,
			"opportunity_from": opportunity_from,
			"party_name": lead,
		}
	).insert(ignore_permissions=True)

	link_communication_to_document(doc, "Opportunity", opportunity.name, ignore_communication_links)

	return opportunity.name

@frappe.whitelist()
def get_services(respuesta):
	
	if respuesta == 'Servicios':
		# items  = frappe.db.sql(""" select name from `tabItem Group` where parent_item_group in ('Corporativo','Pyme','Residencial','Licencias') and item_group_name<>'Equipos' or name='Licencias' union all select distinct item_group from `tabItem` where item_group = 'OTC'; """)
		items  = frappe.db.sql("""select name from `tabItem` where item_group in (select name from `tabItem Group` where parent_item_group in ('Corporativo','Pyme','Residencial','Licencias') 
						and item_group_name<>'Equipos' or name='Licencias' union all select distinct item_group from `tabItem` where item_group = 'OTC') or name in ('EQUIPOS SIN VELOCIDAD')  ; """)
	elif respuesta == 'Productos':
		items  = frappe.db.sql(""" select * from `tabItem Group` where parent_item_group in ('Productos')  or name in ('Instalacion y Configuracion', 'Consumible','EQUIPOS')""")
	lista = [item[0] for item in items]



	return lista

@frappe.whitelist()
def get_producto_presupuesto(respuesta):	

	items  = frappe.db.sql(""" select name,item_group,is_stock_item from `tabItem` where is_stock_item=1 or item_group in ('Instalacion y Configuracion') or bom_de_materiales = 1;""")
	lista = [item[0] for item in items]
	return lista

@frappe.whitelist()
def filtrar_item_servicios(parent):
	respuesta = frappe.db.sql("""select t1.item_code from `tabOpportunity Prospect` t1 inner join
				`tabService Order` t2 on t2.name = t1.service_order where 
				t2.workflow_state = 'Finalizado' and t2.factible = 'El proyecto es factible' and t1.parent =  %(parent)s""",{"parent":parent})
	lista = [item[0] for item in respuesta]
	return lista

@frappe.whitelist()
def calculate_tir(arr):
	
	arr = arr.replace("[","").replace("]","").split(",")
	arr2 = []
	for a in arr:
		arr2.append(float(a))
	if arr2[0] > 0:
		frappe.msgprint("La suma de ingresos iniciales debe ser menor a los egresos iniciales")
	if len(arr2)<2:
		frappe.msgprint("El plazo tiene que ser mayor a 0")

	valor = str(npf.irr(arr2))	
	if valor  == 'nan':
		tir = 0	
	else:
		tir =(npf.irr(arr2)*100)*12
	
	return round(tir)
	


@frappe.whitelist()
def filtrar_contacto_prospecto(tipo, party_name):
	try:
		if tipo == 'Contact':
			items  = frappe.db.sql(""" select name from  `tabContact` where name in (select parent from  `tabDynamic Link` where link_name = %(party_name)s) """, {"party_name":party_name})
		elif tipo == 'Address':
			items  = frappe.db.sql(""" select name from  `tabAddress` where name in (select parent from  `tabDynamic Link` where link_name = %(party_name)s) """, {"party_name":party_name})	

		lista = []
		for item in items:
			lista.append(item[0])
		return lista
	except:
		return []

@frappe.whitelist()
def crear_orden_servicio(name):
	try:
		doc = frappe.get_doc("Opportunity", name)
		
		for plan in doc.get('opportunity_prospect'):
			if not plan.service_order and plan.requiere_site == 1:
				direccion = frappe.get_doc("Address", plan.direccion)
				
				od = frappe.get_doc({
					'doctype': "Service Order",
					'tipo_de_orden': "SITE SURVEY",
					'workflow_state': "Abierto",
					'tipo_de_origen': doc.doctype,
					'nombre_de_origen': doc.name,
					'descripcion': plan.description, #+ '\n' + 'Tipo de Servicio: ' + plan.tipo_servicio  + '\n' + 'Proveedor': plan.proveedor_section,
					'proveedor': plan.nombre_proveedor,
					'tipo_de_servicio':plan.tipo_servicio,
					'tipo': doc.opportunity_from,
					'telefonos':str([t[0] for t in frappe.db.get_values("Contact Phone",{"parent":plan.contacto},'phone','parent')]),
					'tercero': doc.party_name,
					'nombre': doc.customer_name,
					'direccion_de_instalacion': plan.direccion,
					'venta_en_caliente':0,
					'portafolio': plan.portafolio,
					'departamento': direccion.departamento,
					'municipio': direccion.municipio,
					'barrio': direccion.barrio,
					'direccion': direccion.address_line1,
					'item_opportunity':plan.item_code,
					'proveedor_section':plan.proveedor_section,
					'currency':'USD',
					'opportunity_prospect': plan.name,
					'informacion_de_contacto':plan.contacto,
				})	
				od.insert(ignore_permissions=True)
				upd_OP = frappe.get_doc("Opportunity Prospect", {"name":plan.name})	
				upd_OP.update(
					{
					"service_order": od.name
					}
				)
				upd_OP.save()
				frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))	
			elif not plan.service_order and plan.requiere_site == 0:
				item_name = frappe.db.get_value("Item",{"name": plan.item_code},"item_name")
				opportunity_prospect = frappe.get_doc("Opportunity Prospect", {"name": plan.name})
				if opportunity_prospect.proveedor_section == 'IBW':
					if opportunity_prospect.compresion != '0:0' and opportunity_prospect.portafolio != "OTC":
						rate = (float(opportunity_prospect.tasa) * float(opportunity_prospect.uom.replace(' Mbps', '')))/float(opportunity_prospect.compresion.replace(':1',''))
					else:
						rate = 0
				else:
					rate = 0
				if opportunity_prospect.portafolio != "OTC":

					cambio = frappe.db.get_value("Currency Exchange",{"date":today()},"exchange_rate")	
					if not frappe.db.exists("Opportunity Item",{"referencia":opportunity_prospect.name}):
						try:
							spd = frappe.get_doc("Subscription Plan Detail",plan.planid)		
							oi = frappe.get_doc({
								'doctype': "Opportunity Item",
								'referencia':opportunity_prospect.name,
								'precio_tercero': 0.00,
								'importe_ibw': 0.00,
								'descuento_porcentaje':0,
								'base_rate': rate * cambio,
								'base_amount':rate * opportunity_prospect.qty * cambio,
								'rate': rate,
								'amount': rate * opportunity_prospect.qty,
								'proveedor': opportunity_prospect.proveedor_section,
								'nombre_proveedor': opportunity_prospect.nombre_proveedor,
								'item_code': opportunity_prospect.item_code,
								'item_name': item_name,
								'uom':opportunity_prospect.uom,
								'description': plan.description,
								'descripcion_del_plan':plan.description if plan.tipo_servicio == 'Equipo' or not plan.requiere_site else '',
								'departamento': opportunity_prospect.departamento,
								'tipo_servicio': opportunity_prospect.tipo_servicio,
								'qty':opportunity_prospect.qty,
								'compresion':opportunity_prospect.compresion,
								'tasa':opportunity_prospect.tasa,
								'direccion':opportunity_prospect.direccion,
								'contacto':opportunity_prospect.contacto,
								'parent': opportunity_prospect.parent,
								'parenttype' : opportunity_prospect.parenttype,
								#'site_survey' : self.name,
								'parentfield' : 'items',
								"precio_del_plan": spd.cost if spd.currency == 'USD' else spd.cost / doc.conversion_rate,
								"precio_plan_nio": spd.cost if spd.currency == 'NIO' else spd.cost * doc.conversion_rate,
								"divisa_plan": spd.currency
							})	
							oi.insert(ignore_permissions=True)
						except:
							oi = frappe.get_doc({
								'doctype': "Opportunity Item",
								'referencia':opportunity_prospect.name,
								'precio_tercero': 0.00,
								'importe_ibw': 0.00,
								'descuento_porcentaje':0,
								'base_rate': rate * cambio,
								'base_amount':rate * opportunity_prospect.qty * cambio,
								'rate': rate,
								'amount': rate * opportunity_prospect.qty,
								'proveedor': opportunity_prospect.proveedor_section,
								'nombre_proveedor': opportunity_prospect.nombre_proveedor,
								'item_code': opportunity_prospect.item_code,
								'item_name': item_name,
								'uom':opportunity_prospect.uom,
								'description': plan.description,
								'descripcion_del_plan':plan.description if plan.tipo_servicio == 'Equipo' or not plan.requiere_site else '',
								'departamento': opportunity_prospect.departamento,
								'tipo_servicio': opportunity_prospect.tipo_servicio,
								'qty':opportunity_prospect.qty,
								'compresion':opportunity_prospect.compresion,
								'tasa':opportunity_prospect.tasa,
								'direccion':opportunity_prospect.direccion,
								'contacto':opportunity_prospect.contacto,
								'parent': opportunity_prospect.parent,
								'parenttype' : opportunity_prospect.parenttype,
								#'site_survey' : self.name,
								'parentfield' : 'items',
							})	
							oi.insert(ignore_permissions=True)
			else:
				continue
		
	except Exception as e:
		frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))

@frappe.whitelist()
def filtrar_cliente(party_name):
	Prospect = frappe.get_doc("Prospect", party_name)
	lista = []
	if Prospect.cliente_existente:
		cliente=Prospect.cliente_existente
		lista.append(cliente)	
	clientes = frappe.db.sql(""" select distinct(t1.customer) from `tabProspect Lead` t1 inner join 
					`tabOpportunity` t2 on t1.parent = t2.party_name where
					t1.parent = %(party_name)s """, {"party_name": party_name})
	for c in clientes:
		lista.append(c[0])
	#frappe.msgprint(str(lista))
	return lista

def randStr(chars = string.ascii_uppercase + string.digits, N=7):
	return ''.join(random.choice(chars) for _ in range(N))

@frappe.whitelist()
def crear_sus_por_items(name):
	opportunity = frappe.get_doc("Opportunity",name)
	if frappe.db.exists("Subscription", {"oportunidad":name}):
		frappe.msgprint("Ya existe un contrato para esta oportunidad")	
		return
	if opportunity.aprobado_por_ventas_corporativas == 0:
		frappe.msgprint("Requiere aprobación de ventas corporativas")
		return
	if opportunity.aprobado_por_gerencia_general == 0:
		frappe.msgprint("Requiere aprobación de gerencia general")
		return

	"""" crear planes de suscripcion a partir de opportunity items """

	planes = [] 
	for plan in opportunity.items:
		ran = randStr(chars='abcdefghijklmnopqrstuvwxyz1234567890')
		if frappe.db.exists("Subscription Plan", {"planinfoid":ran}):
			ran = 'corp-' + ran + 'x'

		sp = frappe.get_doc({
			'doctype': "Subscription Plan",
			'name': plan.item_code + ' - ' + ran,
			'plan_name': plan.item_name + ' - ' + ran,
			'currency': plan.divisa_plan,
			'item': plan.item_code,
			'cost': plan.precio_del_plan if plan.divisa_plan == 'USD' else plan.precio_plan_nio,
			'billing_interval' : 'Month',
			'billing_interval_count': 1,
			'cost_center': 'Principal - NI',
			'planinfoid':ran,
			'activo': 1,
			'price_determination':'Monthly Rate',
			'compresion': plan.compresion,
			'aprovisionamiento':'Manual',
			'requiere_ot':'INSTALACION',
			'descripcion':plan.description,
			'tipocambio': opportunity.conversion_rate,
			'es_corporativo': 1,
			'tipo_de_plan':'Corporativos',
			'oportunidad':name,
			'descripcion_plan': plan.descripcion_del_plan,
			'site':plan.site_survey,
			'proveedor':plan.nombre_proveedor,
			'vendedor':frappe.db.get_value("Sales Person",{"usuario":opportunity.opportunity_owner},"name")
			})	
		sp.insert()

		precio = plan.precio_del_plan if plan.divisa_plan == 'USD' else plan.precio_plan_nio
		currency_spd = plan.divisa_plan
		
		planes.append([plan.item_code + ' - ' + ran,plan.qty,'Activo',plan.direccion,plan.site_survey,plan.contacto,plan.proveedor,precio,currency_spd])

		if not frappe.db.exists("Dynamic Link", {"parent":plan.direccion, "link_doctype":"Customer"}) and plan.direccion:
			dir = frappe.get_doc({
				'doctype': "Dynamic Link",
				'link_doctype': "Customer",
				'link_name':  opportunity.customer,
				'link_title': opportunity.customer,
				'parent': plan.direccion,
				'parentfield': "links",
				'parenttype':"Address"
			})
			dir.insert()
		

	
	start_date = str(nowdate())
	end_date = formatdate(add_months(start_date, int(opportunity.plazo)), "yyyy-MM-dd")	
	current_invoice_start = str(add_months(formatdate(start_date,"dd-MM-yyyy"), 1))
	current_invoice_end = formatdate(frappe.utils.get_last_day(current_invoice_start), "yyyy-MM-dd")
	current_invoice_start =  current_invoice_start[0:8] + '01'

	try:
		customer_group = frappe.db.get_value("Customer",opportunity.customer,"customer_group")
		suscripcion = frappe.new_doc('Subscription')
		suscripcion.party_type = 'Customer'
		suscripcion.party = opportunity.customer
		suscripcion.company = opportunity.company
		suscripcion.duracion_de_contrato = opportunity.plazo
		suscripcion.workflow_state='Grabado'
		suscripcion.start_date = start_date
		suscripcion.end_date = end_date
		suscripcion.current_invoice_start = current_invoice_start
		suscripcion.current_invoice_end = current_invoice_end
		suscripcion.days_until_due = 0
		suscripcion.lista_de_planes = 'Corporativos'
		suscripcion.cancel_at_period_end = 0
		suscripcion.generate_invoice_at_period_start = 0
		suscripcion.cost_center = 'Principal - NI'
		suscripcion.tipo_contrato = 'NUEVO'
		suscripcion.oportunidad = name,
		
		for item in planes:
			plans = {
					"plan": item[0],
					"qty": item[1],
					"estado_plan":"Inactivo",
					"direccion": item[3],
					"site_survey":item[4],
					"latitud":frappe.get_value("Service Order",item[4],"latitud"),
					"longitud":frappe.get_value("Service Order",item[4],"longitud"),
					"nodo":frappe.get_value("Service Order",item[4],"nodo"),
					"contacto":item[5],
					"proveedor":item[6],
					"cost":item[7],
					"currency":item[8]
				}
			suscripcion.append("plans", plans)

		suscripcion.save()
		if customer_group != "Individual":
			frappe.db.set_value("Subscription", suscripcion.name, "no_contrato", suscripcion.name)

		suscripcion_actualizar = frappe.get_doc("Subscription",  suscripcion.name)		
		suscripcion_actualizar.update(
			{
				"current_invoice_start":str(nowdate()),
				"current_invoice_end":formatdate(frappe.utils.get_last_day(str(nowdate())), "yyyy-MM-dd")
			}
		)
		suscripcion_actualizar.save()
		frappe.db.set_value('Opportunity', name, 'suscripcion', suscripcion.name)
		frappe.db.set_value('Opportunity', name, 'status', 'Closed')
		frappe.db.set_value('Opportunity', name, 'docstatus', 1)
		frappe.msgprint(frappe._('Nueva Suscripción con ID {0}').format(frappe.utils.get_link_to_form("Subscription", suscripcion.name)))	
		frappe.db.set_value('Subscription', suscripcion.name, 'no_contrato', opportunity.name.replace("CRM-OPP","CORP"))
		return suscripcion.name
		

	except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))	


		
@frappe.whitelist()
def consultar_rol():
	""" consultar roles por usuario """
	return [r[0] for r in frappe.db.sql(""" select role from  `tabHas Role` where parent = %(parent)s""", {"parent":frappe.session.user})]



@frappe.whitelist()
def crear_plan(name):
	opportunity = frappe.get_doc("Opportunity",name)
	if frappe.db.exists("Subscription Plan", {"oportunidad":name}):
		frappe.msgprint("Ya se crearon planes nuevos para esta oportunidad")	
		return
	if opportunity.aprobado_por_ventas_corporativas == 0:
		frappe.msgprint("Requiere aprobación de ventas corporativas")
		return
	if opportunity.aprobado_por_gerencia_general == 0:
		frappe.msgprint("Requiere aprobación de gerencia general")
		return

	"""" crear planes de suscripcion a partir de opportunity items """


	for plan in opportunity.items:
		ran = randStr(chars='abcdefghijklmnopqrstuvwxyz1234567890')
		if frappe.db.exists("Subscription Plan", {"planinfoid":ran}):
			ran = ran + 'x'
		sp = frappe.get_doc({
			'doctype': "Subscription Plan",
			'name': plan.item_code + ' - ' + ran,
			'plan_name': plan.item_name + ' - ' + ran,
			'currency': plan.divisa_plan,
			'item': plan.item_code,
			'cost': plan.precio_del_plan if plan.divisa_plan == 'USD' else plan.precio_plan_nio,
			'billing_interval' : 'Month',
			'billing_interval_count': 1,
			'cost_center': 'Principal - NI',
			'planinfoid':ran,
			'activo': 1,
			'price_determination':'Monthly Rate',
			'compresion': plan.compresion,
			'aprovisionamiento':'Manual',
			'requiere_ot':'INSTALACION',
			'descripcion':plan.description,
			'tipocambio': opportunity.conversion_rate,
			'es_corporativo': 1,
			'tipo_de_plan':'Corporativos',
			'oportunidad':name,
			'descripcion_plan': plan.descripcion_del_plan,
			'site':plan.site_survey,
			'proveedor':plan.nombre_proveedor
			})	
		sp.insert()
		frappe.msgprint(frappe._('Plan creado: {0}').format(sp.name))	

@frappe.whitelist()
def verificar_plan_creado(name):
	if frappe.db.exists("Subscription Plan",{"oportunidad":name}):
		return True
	else:
		return False
	
@frappe.whitelist()
def actualizar_contrato(name):
	op = frappe.get_doc("Opportunity",name)
	if not op.customer:
		frappe.msgprint("favor agregar cliente en el flujo")
		return
	if op.actualizacion_de_contrato:
		frappe.msgprint("Documento de actualizacion de contrato ya fue creado")
		return
	if not frappe.db.exists("Gestion",{"detalle_gestion":"ACTUALIZACION DE CONTRATO CORPORATIVO DESDE OPORTUNIDAD " + name,"tipo_gestion":"Tramites","subgestion":"Oferta Comercial"}):
		nueva_gestion = frappe.new_doc("Gestion")
		nueva_gestion.estado = 'Finalizado'
		nueva_gestion.tipo_gestion = 'Tramites'
		nueva_gestion.subgestion = 'Oferta Comercial'
		nueva_gestion.customer = op.customer
		nueva_gestion.nombre = frappe.db.get_value("Customer",op.customer,"customer_name")
		nueva_gestion.detalle_gestion = "ACTUALIZACION DE CONTRATO CORPORATIVO DESDE OPORTUNIDAD " + name
		nueva_gestion.workflow_state = 'Abierto'
		nueva_gestion.save(ignore_permissions=True)

		frappe.db.sql("update `tabGestion` set workflow_state = 'Escalado', docstatus = 1 where name = %(gestion)s",{"gestion":nueva_gestion.name})
	
	gestion = frappe.db.get_value("Gestion",{"detalle_gestion":"ACTUALIZACION DE CONTRATO CORPORATIVO DESDE OPORTUNIDAD " + name,"tipo_gestion":"Tramites","subgestion":"Oferta Comercial"},'name')
	if frappe.db.get_value("Gestion",gestion,"workflow_state") == 'Finalizado':
		frappe.msgprint("El contrato ya fue actualizado")
		return
	return gestion

@frappe.whitelist()
def obtener_planes_nuevos(name):
	return frappe.db.get_values("Subscription Plan",{"oportunidad":name},'name')
	

@frappe.whitelist()
def actualizar_contrato_planes(cliente, name, prospect):
	rows = frappe.db.sql(""" select sp.item,'MRC' as Tipo,sp.item_group,(case when spd.proveedor<>'IBW' then 'Tercero' else 'IBW 'end )Proveedor,spd.proveedor as nombre_proveedor,'Internet' as Tipo_servicio,i.stock_uom as UOM 
			, (case when (select a.departamento from `tabAddress` a where a.name=spd.direccion)='Managua' then 'Managua' else 'Departamentos' end ) as departamento, 0 as requiere_site,spd.direccion,
			spd.descripcion, (select parent from `tabDynamic Link` where (link_name = c.name or link_name = %(prospect)s ) and parenttype='Contact'   limit 1) as contacto,sp.compresion,spd.name, sp.tipocambio, sp.currency
			from `tabSubscription Plan` sp
			inner join `tabSubscription Plan Detail` spd on spd.plan=sp.name
			inner join `tabItem` i on i.name=sp.item
			inner join`tabSubscription` as s on s.name=spd.parent
			inner join `tabCustomer` as c on c.name=s.party
			where  spd.estado_plan='Activo' and c.name = %(cliente)s;""",{"cliente":cliente, "prospect":prospect})

	for row in rows:
		if row[15] == 'NIO':
			frappe.db.set_value("Opportunity",name,"conversion_rate",row[14])

		planes = frappe.get_doc({
			"doctype": "Opportunity Prospect",
			"item_code":row[0],
			"qty": 1,
			"tipo":row[1],
			"compresion":row[12],
			"portafolio": row[2],
			"departamento": row[7],
			"tasa": 1.8 if row[7] == 'Managua' else 2.8 ,
			"proveedor_section": row[3],
			"nombre_proveedor":row[4],
			"tipo_servicio":row[5],
			"uom":row[6],
			"direccion":row[9],
			"contacto":row[11],
			"description": row[10] if row[10] else "PLAN INSTALADO",
			"requiere_site":0,
			"planid":row[13],
			"parent":name,
			"parentfield": "opportunity_prospect",
			"parenttype": "Opportunity",	
			})
		planes.insert(ignore_permissions=True,ignore_links=True)