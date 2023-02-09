# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
# modificado 23/01/23

from curses.ascii import NUL
import json
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


class Issue(Document):
	def get_feed(self):
		return "{0}: {1}".format(_(self.status), self.subject)
		
	def validate(self):
		if self.is_new() and self.via_customer_portal:
			self.flags.create_communication = True

		if not self.raised_by:
			self.raised_by = frappe.session.user

		self.set_lead_contact(self.raised_by)

	def on_update(self):
		# Add a communication in the issue timeline	
		
		# frappe.db.sql("update `Issue Detalle` set estado='Seguimiento' where issue=%s", self.name)
		# frappe.db.commit()

		
		if self.workflow_state=="Seguimiento":
			#frappe.db.set_value(self.doctype, self.name, 'fecha_seguimiento', now())
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			if self.estado_anterior == 'ABIERTO':
				date = now()
				frappe.db.sql(""" update `tabIssue` set fecha_seguimiento = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
			
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado ABIERTO a estado SEGUIMIENTO",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_y_hora),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_incidencia",
					"parenttype": "Issue",
					"idx":idx
					})
				bitacora_orden.insert()	
			if self.estado_anterior == 'PENDIENTE':
				date = now()
				frappe.db.sql(""" update `tabIssue` set fecha_seguimiento = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
			
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado PENDIENTE a estado SEGUIMIENTO",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_pendiente),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_incidencia",
					"parenttype": "Issue",
					"idx":idx
					})
				bitacora_orden.insert()	
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'SEGUIMIENTO')
		
		if self.workflow_state=="Atendido":
			try:
				solucion = self.detalle_solucion
			except:
				solucion = None
			try:
				tecnico = self.tecnico
			except:
				tecnico = None
			try:
				resolution_details = self.resolution_details
			except:
				resolution_details = None

			if self.tipo_de_orden == "Averia":
				equipos = frappe.db.sql(""" select count(*) from `tabIssue_Equipos` where parent = %(parent)s """, {"parent": self.name})
				try:
					equipos = int(equipos[0][0])
				except:
					equipos = 0
				if self.servicio in ['GPON','GPON-CORPORATIVO','GPON-INT-PYME','GPON-INT-RESIDENCIAL','GPON-TV-CORPORATIVO','GPON-TV-PYME','GPON-TV-RESIDENCIAL','HFC', 'HFC 3.0', 'IMOVIL', 'INET', 'Wimax']:
					if equipos < 1:
						frappe.msgprint(f"El portafolio {self.servicio} debe tener al menos un item")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						self.reload()
						return
				elif self.servicio in ['LTE', 'LTE Productos']:
					sim = frappe.db.sql(""" select count(*) from `tabSerial No` where item_code = 'SIM Card' and name in (select equipo from `tabIssue_Equipos` where parent = %(parent)s ) """, {"parent": self.name})
					try:
						sim = int(sim[0][0])
					except:
						sim = 0
					if equipos < 2 or sim < 1:
						frappe.msgprint(f"El portafolio {self.servicio} debe tener al menos un SIM Card y un segundo item")
						frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
						self.reload()
						return
			if self.tipo_de_orden != "Tramite":
				if not tecnico:
					frappe.msgprint("Inserte un técnico")
					frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
					self.reload()
					return
			if not solucion or not resolution_details:
				frappe.msgprint("Inserte una solución y/o resolución")
				frappe.db.set_value(self.doctype, self.name, 'workflow_state', 'Seguimiento')
				self.reload()
				return
			#frappe.db.set_value(self.doctype, self.name, 'fecha_atendido', now())
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			if self.estado_anterior == 'SEGUIMIENTO':
				date = now()
				frappe.db.sql(""" update `tabIssue` set fecha_atendido = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
			
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado SEGUIMIENTO a estado ATENDIDO",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_seguimiento),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_incidencia",
					"parenttype": "Issue",
					"idx":idx
					})
				bitacora_orden.insert()	
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'ATENDIDO')

		if self.workflow_state=="Pending":
			#frappe.db.set_value(self.doctype, self.name, 'fecha_pendiente', now())
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			if self.estado_anterior == 'ATENDIDO':
				date = now()
				frappe.db.sql(""" update `tabIssue` set fecha_pendiente = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
			
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden cambió de estado ATENDIDO a estado PENDIENTE",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_atendido),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_incidencia",
					"parenttype": "Issue",
					"idx":idx
					})
				bitacora_orden.insert()	
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'PENDIENTE')
		
		if self.workflow_state=="Finalizado":
			#frappe.db.set_value(self.doctype, self.name, 'fecha_finalizado', now())
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			if self.estado_anterior == 'ATENDIDO':
				date = now()
				frappe.db.sql(""" update `tabIssue` set fecha_finalizado = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
			
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden FINALIZADA",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_atendido),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_incidencia",
					"parenttype": "Issue",
					"idx":idx
					})
				bitacora_orden.insert()	
			frappe.db.set_value(self.doctype, self.name, 'finalizado_por', frappe.session.user)
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'FINALIZADO')

		if self.workflow_state=="Cancelado":
			#frappe.db.set_value(self.doctype, self.name, 'fecha_cancelado', now())
			idx = frappe.db.sql(""" select idx from `tabBitacora Orden` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":self.name})	
			try:
				idx = int(idx[0][0]) + 1
			except:
				idx = 1	
			if self.estado_anterior == 'ABIERTO':
				date = now()
				frappe.db.sql(""" update `tabIssue` set fecha_cancelado = %(date)s where name = %(name)s""", {"date":date,"name":self.name})
			
				bitacora_orden = frappe.get_doc({
					"doctype": "Bitacora Orden",
					"detalle":"Orden CANCELADA",
					"fecha_transaccion": now(),
					"usuario":frappe.session.user,
					"tiempo_transcurrido":time_diff_in_seconds(date,self.fecha_y_hora),
					"fecha_definida_por_usuario": date,
					"parent": self.name,
					"parentfield":"bitacora_incidencia",
					"parenttype": "Issue",
					"idx":idx
					})
				bitacora_orden.insert()	
			frappe.db.set_value(self.doctype, self.name, 'estado_anterior', 'CANCELADO')
		total_abierto = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado ABIERTO a estado SEGUIMIENTO' and parent = %(name)s; """, {"name":self.name})[0][0])
		total_seguimiento = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado SEGUIMIENTO a estado ATENDIDO' and parent = %(name)s; """, {"name":self.name})[0][0])
		total_atendido = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle in ('Orden cambió de estado ATENDIDO a estado PENDIENTE','Orden FINALIZADA') and parent = %(name)s; """, {"name":self.name})[0][0])
		total_pendiente = str(frappe.db.sql(""" SELECT  (case when SUM(tiempo_transcurrido) is null then 0 else SUM(tiempo_transcurrido) end) from `tabBitacora Orden`  WHERE detalle = 'Orden cambió de estado PENDIENTE a estado SEGUIMIENTO' and parent = %(name)s; """, {"name":self.name})[0][0])
	

		frappe.db.sql(""" update `tabIssue` set total_abierto = %(total_abierto)s, total_seguimiento = %(total_seguimiento)s, total_atendido = %(total_atendido)s, total_pendiente = %(total_pendiente)s where name = %(name)s""", {"total_abierto":total_abierto, "total_seguimiento":total_seguimiento, "total_atendido":total_atendido, "total_pendiente":total_pendiente,"name":self.name})	
		
		self.reload()
		

		
		if  frappe.db.exists("Gestion", {"name": self.gestion}):			
			if not frappe.db.exists("Issue Detalle", {"issue": self.name}):
				add_gestion = frappe.get_doc({
					"doctype": "Issue Detalle",
					"issue": self.name,
					"parent": self.gestion,
					"parentfield": "issue",
					"parenttype": "Gestion",
					"estado": self.workflow_state,
					"tipo": self.tipo_de_orden,
					"problema": self.issue_type
				})
				add_gestion.insert()

		if  frappe.db.exists("Issue Detalle", {"issue": self.name}):
			upd_fecha_s = frappe.get_doc("Issue Detalle", {"issue": self.name})	
			upd_fecha_s.update(
				{
					"estado": self.workflow_state
				}
			)
			upd_fecha_s.save()


		if  frappe.db.exists("AveriasMasivas", {"name": self.averia_masivo}):	
			
			if frappe.db.exists("Issue Vinculado Averia", {"issue_id": self.name} ):		
				if not frappe.db.exists("Issue Vinculado Averia", {"issue_id": self.name , "parent":self.averia_masivo}):
						upd_fecha_s = frappe.get_doc("Issue Vinculado Averia", {"issue_id": self.name})	
						upd_fecha_s.update(
							{
								"parent": self.averia_masivo,
							}
						)
						upd_fecha_s.save()
			else:
						add_AveriasMasivas = frappe.get_doc({
							"doctype": "Issue Vinculado Averia",
							"issue_id": self.name,
							"parent": self.averia_masivo,
							"parentfield": "incidencias",
							"parenttype": "AveriasMasivas"
						})
						add_AveriasMasivas.insert()

		if self.flags.create_communication and self.via_customer_portal:
			self.create_communication()
			self.flags.communication_created = None	
		


	def set_lead_contact(self, email_id):
		import email.utils

		email_id = email.utils.parseaddr(email_id)[1]
		if email_id:
			if not self.lead:
				self.lead = frappe.db.get_value("Lead", {"email_id": email_id})

			if not self.contact and not self.customer:
				self.contact = frappe.db.get_value("Contact", {"email_id": email_id})

				if self.contact:
					contact = frappe.get_doc("Contact", self.contact)
					self.customer = contact.get_link_for("Customer")

			if not self.company:
				self.company = frappe.db.get_value("Lead", self.lead, "company") or frappe.db.get_default(
					"Company"
				)

	def create_communication(self):
		
		communication = frappe.new_doc("Communication")
		communication.update(
			{
				"communication_type": "Communication",
				"communication_medium": "Email",
				"sent_or_received": "Received",
				"email_status": "Open",
				"subject": self.subject,
				"sender": self.raised_by,
				"content": self.description,
				"status": "Linked",
				"reference_doctype": "Issue",
				"reference_name": self.name,
			}
		)
		communication.ignore_permissions = True
		communication.ignore_mandatory = True
		communication.save()

@frappe.whitelist()
def split_issue(self, subject, communication_id):
	# Bug: Pressing enter doesn't send subject
	from copy import deepcopy

	replicated_issue = deepcopy(self)
	replicated_issue.subject = subject
	replicated_issue.issue_split_from = self.name
	replicated_issue.first_response_time = 0
	replicated_issue.first_responded_on = None
	replicated_issue.creation = now_datetime()

	# Reset SLA
	if replicated_issue.service_level_agreement:
		replicated_issue.service_level_agreement_creation = now_datetime()
		replicated_issue.service_level_agreement = None
		replicated_issue.agreement_status = "First Response Due"
		replicated_issue.response_by = None
		replicated_issue.resolution_by = None
		replicated_issue.reset_issue_metrics()

	frappe.get_doc(replicated_issue).insert()

	# Replicate linked Communications
	# TODO: get all communications in timeline before this, and modify them to append them to new doc
	comm_to_split_from = frappe.get_doc("Communication", communication_id)
	communications = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": "Issue",
			"reference_name": comm_to_split_from.reference_name,
			"creation": (">=", comm_to_split_from.creation),
		},
	)

	for communication in communications:
		doc = frappe.get_doc("Communication", communication.name)
		doc.reference_name = replicated_issue.name
		doc.save(ignore_permissions=True)

	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Issue",
			"reference_name": replicated_issue.name,
			"content": " - Split the Issue from <a href='/app/Form/Issue/{0}'>{1}</a>".format(
				self.name, frappe.bold(self.name)
			),
		}
	).insert(ignore_permissions=True)

	return replicated_issue.name

def reset_issue_metrics(self):
	self.db_set("resolution_time", None)
	self.db_set("user_resolution_time", None)


def get_list_context(context=None):
	return {
		"title": _("Issues"),
		"get_list": get_issue_list,
		"row_template": "templates/includes/issue_row.html",
		"show_sidebar": True,
		"show_search": True,
		"no_breadcrumbs": True,
	}


def get_issue_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
	from frappe.www.list import get_list

	user = frappe.session.user
	contact = frappe.db.get_value("Contact", {"user": user}, "name")
	customer = None

	if contact:
		contact_doc = frappe.get_doc("Contact", contact)
		customer = contact_doc.get_link_for("Customer")

	ignore_permissions = False
	if is_website_user():
		if not filters:
			filters = {}

		if customer:
			filters["customer"] = customer
		else:
			filters["raised_by"] = user

		ignore_permissions = True

	return get_list(
		doctype, txt, filters, limit_start, limit_page_length, ignore_permissions=ignore_permissions
	)



@frappe.whitelist()
def set_multiple_status(names, status):

	for name in json.loads(names):
		frappe.db.set_value("Issue", name, "status", status)


@frappe.whitelist()
def set_status(name, status):
	frappe.db.set_value("Issue", name, "status", status)


def auto_close_tickets():
	"""Auto-close replied support tickets after 7 days"""
	auto_close_after_days = (
		frappe.db.get_value("Support Settings", "Support Settings", "close_issue_after_days") or 7
	)

	table = frappe.qb.DocType("Issue")
	issues = (
		frappe.qb.from_(table)
		.select(table.name)
		.where(
			(table.modified < (Now() - Interval(days=auto_close_after_days))) & (table.status == "Replied")
		)
	).run(pluck=True)

	for issue in issues:
		doc = frappe.get_doc("Issue", issue)
		doc.status = "Closed"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()


def has_website_permission(doc, ptype, user, verbose=False):
	from erpnext.controllers.website_list_for_contact import has_website_permission

	permission_based_on_customer = has_website_permission(doc, ptype, user, verbose)

	return permission_based_on_customer or doc.raised_by == user


def update_issue(contact, method):
	"""Called when Contact is deleted"""
	frappe.db.sql("""UPDATE `tabIssue` set contact='' where contact=%s""", contact.name)


@frappe.whitelist()
def make_task(source_name, target_doc=None):
	return get_mapped_doc("Issue", source_name, {"Issue": {"doctype": "Task"}}, target_doc)


@frappe.whitelist()
def make_issue_from_communication(communication, ignore_communication_links=False):
	"""raise a issue from email"""

	doc = frappe.get_doc("Communication", communication)
	issue = frappe.get_doc(
		{
			"doctype": "Issue",
			"subject": doc.subject,
			"communication_medium": doc.communication_medium,
			"raised_by": doc.sender or "",
			"raised_by_phone": doc.phone_no or "",
		}
	).insert(ignore_permissions=True)

	link_communication_to_document(doc, "Issue", issue.name, ignore_communication_links)

	return issue.name


def get_time_in_timedelta(time):
	"""
	Converts datetime.time(10, 36, 55, 961454) to datetime.timedelta(seconds=38215)
	"""
	return timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)


def set_first_response_time(communication, method):
	if communication.get("reference_doctype") == "Issue":
		issue = get_parent_doc(communication)
		if is_first_response(issue) and issue.service_level_agreement:
			first_response_time = calculate_first_response_time(
				issue, get_datetime(issue.first_responded_on)
			)
			issue.db_set("first_response_time", first_response_time)


def is_first_response(issue):
	responses = frappe.get_all(
		"Communication", filters={"reference_name": issue.name, "sent_or_received": "Sent"}
	)
	if len(responses) == 1:
		return True
	return False


def calculate_first_response_time(issue, first_responded_on):
	issue_creation_date = issue.service_level_agreement_creation or issue.creation
	issue_creation_time = get_time_in_seconds(issue_creation_date)
	first_responded_on_in_seconds = get_time_in_seconds(first_responded_on)
	support_hours = frappe.get_cached_doc(
		"Service Level Agreement", issue.service_level_agreement
	).support_and_resolution

	if issue_creation_date.day == first_responded_on.day:
		if is_work_day(issue_creation_date, support_hours):
			start_time, end_time = get_working_hours(issue_creation_date, support_hours)

			# issue creation and response on the same day during working hours
			if is_during_working_hours(issue_creation_date, support_hours) and is_during_working_hours(
				first_responded_on, support_hours
			):
				return get_elapsed_time(issue_creation_date, first_responded_on)

			# issue creation is during working hours, but first response was after working hours
			elif is_during_working_hours(issue_creation_date, support_hours):
				return get_elapsed_time(issue_creation_time, end_time)

			# issue creation was before working hours but first response is during working hours
			elif is_during_working_hours(first_responded_on, support_hours):
				return get_elapsed_time(start_time, first_responded_on_in_seconds)

			# both issue creation and first response were after working hours
			else:
				return 1.0  # this should ideally be zero, but it gets reset when the next response is sent if the value is zero

		else:
			return 1.0

	else:
		# response on the next day
		if date_diff(first_responded_on, issue_creation_date) == 1:
			first_response_time = 0
		else:
			first_response_time = calculate_initial_frt(
				issue_creation_date, date_diff(first_responded_on, issue_creation_date) - 1, support_hours
			)

		# time taken on day of issue creation
		if is_work_day(issue_creation_date, support_hours):
			start_time, end_time = get_working_hours(issue_creation_date, support_hours)

			if is_during_working_hours(issue_creation_date, support_hours):
				first_response_time += get_elapsed_time(issue_creation_time, end_time)
			elif is_before_working_hours(issue_creation_date, support_hours):
				first_response_time += get_elapsed_time(start_time, end_time)

		# time taken on day of first response
		if is_work_day(first_responded_on, support_hours):
			start_time, end_time = get_working_hours(first_responded_on, support_hours)

			if is_during_working_hours(first_responded_on, support_hours):
				first_response_time += get_elapsed_time(start_time, first_responded_on_in_seconds)
			elif not is_before_working_hours(first_responded_on, support_hours):
				first_response_time += get_elapsed_time(start_time, end_time)

		if first_response_time:
			return first_response_time
		else:
			return 1.0


def get_time_in_seconds(date):
	return timedelta(hours=date.hour, minutes=date.minute, seconds=date.second)


def get_working_hours(date, support_hours):
	if is_work_day(date, support_hours):
		weekday = frappe.utils.get_weekday(date)
		for day in support_hours:
			if day.workday == weekday:
				return day.start_time, day.end_time


def is_work_day(date, support_hours):
	weekday = frappe.utils.get_weekday(date)
	for day in support_hours:
		if day.workday == weekday:
			return True
	return False


def is_during_working_hours(date, support_hours):
	start_time, end_time = get_working_hours(date, support_hours)
	time = get_time_in_seconds(date)
	if time >= start_time and time <= end_time:
		return True
	return False


def get_elapsed_time(start_time, end_time):
	return round(time_diff_in_seconds(end_time, start_time), 2)


def calculate_initial_frt(issue_creation_date, days_in_between, support_hours):
	initial_frt = 0
	for i in range(days_in_between):
		date = issue_creation_date + timedelta(days=(i + 1))
		if is_work_day(date, support_hours):
			start_time, end_time = get_working_hours(date, support_hours)
			initial_frt += get_elapsed_time(start_time, end_time)

	return initial_frt


def is_before_working_hours(date, support_hours):
	start_time, end_time = get_working_hours(date, support_hours)
	time = get_time_in_seconds(date)
	if time < start_time:
		return True
	return False


def get_holidays(holiday_list_name):
	holiday_list = frappe.get_cached_doc("Holiday List", holiday_list_name)
	holidays = [holiday.holiday_date for holiday in holiday_list.holidays]
	return holidays


@frappe.whitelist()
def get_plan_Susc_cust(customer):
		get_plan_cust = frappe.db.sql(
			"""Select t1.name from `tabSubscription Plan Detail` t1 inner join `tabSubscription` t2 on t1.parent=t2.name
				where t2.party=%(customer)s and t1.estado_plan ='Activo' """,
			{"customer": customer},
		)	
	
		return get_plan_cust		
		# get_plan_cust =frappe.db.sql(f"""Select t1.plan from `tabSubscription Plan Detail` t1 inner join `tabSubscription` t2 on t1.parent=t2.name where t2.party='{customer}' """, as_dict=True)	
						
		# return get_plan_cust

@frappe.whitelist()
def get_plan_Portafolio(plan):
		
		get_plan_Portafolio = frappe.db.sql(
		"""Select t1.item_group,t4.departamento,t4.municipio,t4.barrio,t4.address_line1, t3.nodo, t3.latitud, t3.longitud from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item 
		inner join `tabSubscription Plan Detail` t3 on t3.plan=t2.name inner join `tabAddress` t4 on t4.name=t3.direccion  where t3.name=%(plan)s limit 1 """,
		{"plan": plan},
		)	
		return get_plan_Portafolio

@frappe.whitelist()
def get_phone(customer):
	phones= frappe.db.sql(
	"""select t2.phone from `tabDynamic Link` t1 inner join 
		`tabContact Phone` t2 on t1.name = t2.parent
		where t1.link_name =%(customer)s""",
	{"customer": customer},
	)
		
	telefono = []
	for phone in range(len(phones)): 
			telefono.append(phones[phone][0])

	cadena=""
	for t in telefono:
		if t == telefono[-1]:
			cadena= cadena + t
		else :
			cadena= cadena + t + " / "
	return cadena
	# return phone


@frappe.whitelist()
def get_Equipos_issue(plan,name):
	# frappe.msgprint(name)
	
	if not frappe.db.exists("Issue_Equipos", {"parent": name ,"id_namesubscription_plan_detail": plan}):

		get_Equipos_issue = frappe.db.sql(
		"""select t1.equipo, t3.item_name,t2.name from `tabSubscription Plan Equipos` t1 inner join 
			`tabSubscription Plan Detail` t2 on t1.plan = t2.name and t1.parent=t2.parent inner join
			`tabSerial No` t3 on t3.name = t1.equipo where t2.name=%(plan)s""",
		{"plan": plan},
		)	

		try:
			for equipo in get_Equipos_issue:

				add_equipos = frappe.get_doc({
					"doctype": "Issue_Equipos",
					"equipo": equipo[0],
					"modelo": equipo[1],
					"parenttype": "Issue",
					"parent": name,
					"parentfield": "equipos",
					"id_namesubscription_plan_detail" : equipo[2],
				})
				add_equipos.insert()

		except Exception as e:
				frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))

# @frappe.whitelist()
# def Filtrar_Equipos(plan,name):
# 		#frappe.msgprint(plan,name)
# 		Filtrar = frappe.db.sql(
# 		"""select parent from `tabIssue_Equipos` where parent =%(name)s and id_namesubscription_plan_detail = %(plan)s limnit 1""",
# 		{"name": name,"plan": plan},
# 		)
# 		frappe.msgprint(Filtrar)
# 		return Filtrar	



##############################################################################

		# if  frappe.db.exists("Issue Detalle", {"name": name}):
		# 	upd_fecha_s = frappe.db.delete("Issue Detalle", {"issue": ("")})	
		# 	upd_fecha_s.update(
		# 		{
		# 			"estado": self.workflow_state
		# 		}
		# 	)
		# 	upd_fecha_s.save()



		# get_Equipos_issue = frappe.db.sql(
		# """select equipo,t4.item_name,t3.name from `tabSubscription Plan Equipos`   t1  inner join   `tabSubscription` t2 on t1.parent=t2.name 
 		# 	inner join `tabSubscription Plan Detail` t3 on t1.plan=t3.name
 		# 	inner join `tabSerial No` t4 on t1.equipo=t4.name
		# 	 where t3.name=%(plan)s""",
		# {"plan": plan},
		# )	
		# #return get_Equipos_issue	
		# # frappe.msgprint(fact.name)
		# try:
		# 	for equipo in get_Equipos_issue:
				
		# 		equipoadd = frappe.new_doc("Issue_Equipos")
		# 		equipoadd.update(
		# 			{
		# 			"equipo": equipo[0],
		# 			"modelo": equipo[1],
		# 			"parent": "Issue",
		# 			"parentfield": "equipos",
		# 			"id_namesubscription_plan_detail" : equipo[2],
		# 			}
		# 		)
		# 		doc.equipos.append(equipoadd)	
		# 	doc.save()
		# 	frappe.db.commit()
		# except Exception as e:
		# 	frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))

		

# @frappe.whitelist()
# def crear_issue_averia(name):
	
# 	doc = frappe.get_doc("Issue", name)	
# 	# frappe.msgprint(doc.subject)
# 	if doc.workflow_state=="Finalizado":
		
# 			add_issue = frappe.get_doc({
# 				"doctype": "Issue",
# 				"subject": doc.subject,
# 				"customer": doc.customer,
# 				"status": "Open",
# 				"priority": doc.priority,
# 				"workflow_state": "Abierto",
# 				"description": doc.description,
# 				"issue_type": doc.issue_type,
# 				"tipo_de_orden": "Averia",
# 				"gestion": doc.gestion
# 			})

# 			add_issue.insert()

			
# 			frappe.msgprint(frappe._('Nueva orden de {0} ').format(add_issue.name))
@frappe.whitelist()
def get_portafolio():
	portafolio = frappe.db.sql(
		"""select * from `tabItem Group` where is_group = 0 and parent_item_group not in ('Productos','Todos los grupos de artículos')""",
	)
	lista = []
	for i in range (len(portafolio)):
		lista.append(portafolio[i][0])
	return lista