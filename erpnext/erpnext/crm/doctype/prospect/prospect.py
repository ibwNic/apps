# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.mapper import get_mapped_doc

from erpnext.crm.utils import CRMNote, copy_comments, link_communications, link_open_events
from frappe.utils.data import (
	add_days,
	add_months,
	add_to_date,
	cint,
	cstr,
	date_diff,
	flt,
	get_last_day,
	getdate,
	nowdate,
	formatdate,
)

class Prospect(CRMNote):
	def onload(self):
		load_address_and_contact(self)

	def on_update(self):
		self.link_with_lead_contact_and_address()
		
		if self.overview!=self.estado_anterior or self.fecha_anterior != self.fecha_de_cierre:
			idx = frappe.db.sql(""" select idx from `tabBitacora Prospectos` where parent=%(parent)s ORDER BY creation DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	


			bitacora_Prospect = frappe.get_doc({
				"doctype": "Bitacora Prospectos",
				"estado":self.overview,
				"parent": self.name,
				"parentfield":"bitacora_prospecto",
				"fecha":nowdate(),
				"fecha_cierre":self.fecha_de_cierre,
				"parenttype": "Prospect",
				"idx":idx
				})
			bitacora_Prospect.insert()	

		frappe.db.set_value(self.doctype, self.name, 'estado_anterior', self.overview)
		frappe.db.set_value(self.doctype, self.name, 'fecha_anterior', self.fecha_de_cierre)
		self.reload()

	def on_trash(self):
		self.unlink_dynamic_links()

	def after_insert(self):
		carry_forward_communication_and_comments = frappe.db.get_single_value(
			"CRM Settings", "carry_forward_communication_and_comments"
		)

		for row in self.get("leads"):
			if carry_forward_communication_and_comments:
				copy_comments("Lead", row.lead, self)
				link_communications("Lead", row.lead, self)
			link_open_events("Lead", row.lead, self)

		for row in self.get("opportunities"):
			if carry_forward_communication_and_comments:
				copy_comments("Opportunity", row.opportunity, self)
				link_communications("Opportunity", row.opportunity, self)
			link_open_events("Opportunity", row.opportunity, self)

	def link_with_lead_contact_and_address(self):
		for row in self.leads:
			links = frappe.get_all(
				"Dynamic Link",
				filters={"link_doctype": "Lead", "link_name": row.lead},
				fields=["parent", "parenttype"],
			)
			for link in links:
				linked_doc = frappe.get_doc(link["parenttype"], link["parent"])
				exists = False

				for d in linked_doc.get("links"):
					if d.link_doctype == self.doctype and d.link_name == self.name:
						exists = True

				if not exists:
					linked_doc.append("links", {"link_doctype": self.doctype, "link_name": self.name})
					linked_doc.save(ignore_permissions=True)

	def unlink_dynamic_links(self):
		links = frappe.get_all(
			"Dynamic Link",
			filters={"link_doctype": self.doctype, "link_name": self.name},
			fields=["parent", "parenttype"],
		)

		for link in links:
			linked_doc = frappe.get_doc(link["parenttype"], link["parent"])

			if len(linked_doc.get("links")) == 1:
				linked_doc.delete(ignore_permissions=True)
			else:
				to_remove = None
				for d in linked_doc.get("links"):
					if d.link_doctype == self.doctype and d.link_name == self.name:
						to_remove = d
				if to_remove:
					linked_doc.remove(to_remove)
					linked_doc.save(ignore_permissions=True)





@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.customer_type = "Company"
		target.company_name = source.name
		target.customer_group = source.customer_group or frappe.db.get_default("Customer Group")

	doclist = get_mapped_doc(
		"Prospect",
		source_name,
		{
			"Prospect": {
				"doctype": "Customer",
				"field_map": {"company_name": "customer_name", "currency": "default_currency", "fax": "fax"},
			}
		},
		target_doc,
		set_missing_values,
		ignore_permissions=False,
	)

	return doclist


@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):

	try:
		direccion = frappe.db.sql(""" select address_line1 from `tabAddress` where name in (select parent from `tabDynamic Link` 
		where link_doctype = 'Prospect' and link_name =%(source_name)s and parenttype = 'Address') limit 1;""", {"source_name":source_name})[0][0]
	except:
		direccion = None
	if not direccion:
		frappe.msgprint(
			msg='Requerido ingresar dirección para crear oportunidad',
			title='No se pudo crear',
			indicator='red'
		)
		return 
	
	phones = frappe.db.sql(""" select name, phone, mobile_no from `tabContact` where name in (select parent from `tabDynamic Link` 
		where link_doctype = 'Prospect' and link_name =%(source_name)s and parenttype = 'Contact')""",{"source_name":source_name})
	try:
		phones = phones[0][0] or phones[0][1] or phones[0][2]
	except:
		phones = None
	if not phones:
		frappe.msgprint(
			msg='Requerido ingresar contacto crear oportunidad. Debe haber al menos un teléfono marcado como principal.',
			title='No se pudo crear',
			indicator='red'
		)
		return 
		


	def set_missing_values(source, target):
		target.opportunity_from = "Prospect"
		target.customer_name = source.company_name
		target.customer = source.cliente_existente
		target.customer_group = source.customer_group or frappe.db.get_default("Customer Group")

	doclist = get_mapped_doc(
		"Prospect",
		source_name,
		{
			"Prospect": {
				"doctype": "Opportunity",
				"field_map": {"name": "party_name", "prospect_owner": "opportunity_owner"},
			}
		},
		target_doc,
		set_missing_values,
		ignore_permissions=False,
	)

	return doclist


@frappe.whitelist()
def get_opportunities(prospect):
	return frappe.get_all(
		"Opportunity",
		filters={"opportunity_from": "Prospect", "party_name": prospect},
		fields=[
			"opportunity_owner",
			"sales_stage",
			"status",
			"expected_closing",
			"probability",
			"opportunity_amount",
			"currency",
			"contact_person",
			"contact_email",
			"contact_mobile",
			"creation",
			"name",
		],
	)

@frappe.whitelist()
def vincular_prospecto(name,lead_name,status,prospect=None):
	if prospect != None:
		try:
			if not frappe.db.exists("Prospect Lead", {"lead":name}):
				lead = frappe.get_doc({
					'doctype': "Prospect Lead",
					'lead': name,
					'lead_name': lead_name,
					'parent':prospect,
					'status':status,
					'parentfield': 'leads',
					'parenttype':'Prospect'			
				})	
				lead.insert(ignore_permissions=True)
			direcciones = frappe.db.get_values("Dynamic Link",{"link_doctype": "Prospect","parenttype": "Address", "link_name": prospect},"parent")
			for dir in direcciones:
				if not frappe.db.exists("Dynamic Link", {"parent":dir[0], "link_doctype":"Lead","link_name":name}):
					dir = frappe.get_doc({
						'doctype': "Dynamic Link",
						'link_doctype': "Lead",
						'link_name':  name,
						'link_title': lead_name,
						'parent': dir[0],
						'parentfield': "links",
						'parenttype':"Address"
					})
					dir.insert(ignore_permissions=True)
			contactos = frappe.db.get_values("Dynamic Link",{"link_doctype": "Prospect","parenttype": "Contact", "link_name": prospect},"parent")
			for con in contactos:
				if not frappe.db.exists("Dynamic Link", {"parent":con[0], "link_doctype":"Lead","link_name":name}):
					con = frappe.get_doc({
						'doctype': "Dynamic Link",
						'link_doctype': "Lead",
						'link_name':  name,
						'link_title': lead_name,
						'parent': con[0],
						'parentfield': "links",
						'parenttype':"Contact"
					})
					con.insert(ignore_permissions=True)
		except:
			pass
		#return direcciones

@frappe.whitelist()
def actualizar_prospecto_customer(lead_name, customer):
	if not lead_name:
		frappe.msgprint("Hace falta llenar un campo de estos: lead_name")
	if frappe.db.exists("Prospect Lead", {"lead":lead_name}):	
		prospect_lead = frappe.get_doc("Prospect Lead", {"lead": lead_name})				
		prospect_lead.update(
			{
				"customer":customer
			}
		)
		prospect_lead.save(ignore_permissions=True)

@frappe.whitelist()
def vincular_direccion_cliente_existente(name):
	try:
		prospect = frappe.get_doc("Prospect", name)

		direcciones = frappe.db.get_values("Dynamic Link",{"parenttype": "Address", "link_name": prospect.cliente_existente},'parent')
		if direcciones:
			for dir in direcciones:
				if not frappe.db.exists("Dynamic Link", {"parenttype": "Address","parent":dir[0], "link_doctype":"Prospect","link_name":prospect.name}):
					#return 'sis'
					dir = frappe.get_doc({
						'doctype': "Dynamic Link",
						'link_doctype': "Prospect",
						'link_name':  name,
						'link_title': prospect.company_name,
						'parent': dir[0],
						'parentfield': "links",
						'parenttype':"Address"
					})
					dir.insert(ignore_permissions=True)
		contactos = frappe.db.get_values("Dynamic Link",{"parenttype": "Contact", "link_name": prospect.cliente_existente},'parent')
		if contactos:
			for con in contactos:
				if not frappe.db.exists("Dynamic Link", {"parenttype": "Contact","parent":con[0], "link_doctype":"Prospect","link_name":prospect.name}):
					#return 'sis'
					con = frappe.get_doc({
						'doctype': "Dynamic Link",
						'link_doctype': "Prospect",
						'link_name':  name,
						'link_title': prospect.company_name,
						'parent': con[0],
						'parentfield': "links",
						'parenttype':"Contact"
					})
					con.insert(ignore_permissions=True)
	except Exception as e:
		frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))

# @frappe.whitelist
# def fecha_finalizacion(name):
# 	frappe.db.set_value(prospect, name, 'fecha_de_cierre', add_days(nowdate(), cint(15)))


@frappe.whitelist()
def verificar_company_name(customer):
	company_name = frappe.db.get_value("Prospect",{"company_name":frappe.db.get_value("Customer",customer,"customer_name")},"company_name")

	if not company_name:
		return frappe.db.get_value("Customer",customer,"customer_name")
	else:
		customer_name = "%" + frappe.db.get_value("Customer",customer,"customer_name") + "%"
		company_name = frappe.db.sql("select company_name from `tabProspect` where company_name like %(customer_name)s order by creation desc limit 1",{"customer_name":customer_name})
		
		if company_name:
			head, sep, tail = company_name[0][0].partition(' --- ')

			if tail.isnumeric():
				number = int(tail)
				number = number + 1
				number = str(number)
				return head + sep + number
			else:
				return company_name[0][0]
		else:
			return company_name +   " --- " + "1"

