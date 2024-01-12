# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
#ultima modificacion: 23/01/2023 16:09

import random
import string
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import random_string
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

import erpnext
from erpnext import get_default_company
from frappe.utils import flt, get_fullname, format_time, formatdate, getdate, nowdate,nowtime
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate_NEW
from erpnext.accounts.party import get_party_account_currency


class Subscription(Document):
	def before_insert(self):
		# update start just before the subscription doc is created
		# self.update_subscription_period(self.start_date)
		pass

	def update_subscription_period(self, date=None, return_date=False):
		"""
		Subscription period is the period to be billed. This method updates the
		beginning of the billing period and end of the billing period.

		The beginning of the billing period is represented in the doctype as
		`current_invoice_start` and the end of the billing period is represented
		as `current_invoice_end`.

		If return_date is True, it wont update the start and end dates.
		This is implemented to get the dates to check if is_current_invoice_generated
		"""
		_current_invoice_start = self.get_current_invoice_start(date)
		_current_invoice_end = self.get_current_invoice_end(_current_invoice_start)

		if return_date:
			return _current_invoice_start, _current_invoice_end

		self.current_invoice_start = _current_invoice_start
		self.current_invoice_end = _current_invoice_end

	def get_current_invoice_start(self, date=None):
		"""
		This returns the date of the beginning of the current billing period.
		If the `date` parameter is not given , it will be automatically set as today's
		date.
		"""
		_current_invoice_start = None

		if (
			self.is_new_subscription()
			and self.trial_period_end
			and getdate(self.trial_period_end) > getdate(self.start_date)
		):
			_current_invoice_start = add_days(self.trial_period_end, 1)
		elif self.trial_period_start and self.is_trialling():
			_current_invoice_start = self.trial_period_start
		elif date:
			_current_invoice_start = date
		else:
			_current_invoice_start = nowdate()

		return _current_invoice_start

	def get_current_invoice_end(self, date=None):
		"""
		This returns the date of the end of the current billing period.

		If the subscription is in trial period, it will be set as the end of the
		trial period.

		If is not in a trial period, it will be `x` days from the beginning of the
		current billing period where `x` is the billing interval from the
		`Subscription Plan` in the `Subscription`.
		"""
		_current_invoice_end = None

		if self.is_trialling() and getdate(date) < getdate(self.trial_period_end):
			_current_invoice_end = self.trial_period_end
		else:
			billing_cycle_info = self.get_billing_cycle_data()
			if billing_cycle_info:
				if self.is_new_subscription() and getdate(self.start_date) < getdate(date):
					_current_invoice_end = add_to_date(self.start_date, **billing_cycle_info)

					# For cases where trial period is for an entire billing interval
					if getdate(self.current_invoice_end) < getdate(date):
						_current_invoice_end = add_to_date(date, **billing_cycle_info)
				else:
					_current_invoice_end = add_to_date(date, **billing_cycle_info)
			else:
				_current_invoice_end = get_last_day(date)

			if self.follow_calendar_months:
				billing_info = self.get_billing_cycle_and_interval()
				billing_interval_count = billing_info[0]["billing_interval_count"]
				calendar_months = get_calendar_months(billing_interval_count)
				calendar_month = 0
				current_invoice_end_month = getdate(_current_invoice_end).month
				current_invoice_end_year = getdate(_current_invoice_end).year

				for month in calendar_months:
					if month <= current_invoice_end_month:
						calendar_month = month

				if cint(calendar_month - billing_interval_count) <= 0 and getdate(date).month != 1:
					calendar_month = 12
					current_invoice_end_year -= 1

				_current_invoice_end = get_last_day(
					cstr(current_invoice_end_year) + "-" + cstr(calendar_month) + "-01"
				)

			if self.end_date and getdate(_current_invoice_end) > getdate(self.end_date):
				_current_invoice_end = self.end_date

		return _current_invoice_end

	@staticmethod
	def validate_plans_billing_cycle(billing_cycle_data):
		"""
		Makes sure that all `Subscription Plan` in the `Subscription` have the
		same billing interval
		"""
		if billing_cycle_data and len(billing_cycle_data) != 1:
			frappe.throw(_("You can only have Plans with the same billing cycle in a Subscription"))

	def get_billing_cycle_and_interval(self):
		"""
		Returns a dict representing the billing interval and cycle for this `Subscription`.

		You shouldn't need to call this directly. Use `get_billing_cycle` instead.
		"""
		plan_names = [plan.plan for plan in self.plans]

		subscription_plan = frappe.qb.DocType("Subscription Plan")
		billing_info = (
			frappe.qb.from_(subscription_plan)
			.select(subscription_plan.billing_interval, subscription_plan.billing_interval_count)
			.distinct()
			.where(subscription_plan.name.isin(plan_names))
		).run(as_dict=1)

		return billing_info

	def get_billing_cycle_data(self):
		"""
		Returns dict contain the billing cycle data.

		You shouldn't need to call this directly. Use `get_billing_cycle` instead.
		"""
		billing_info = self.get_billing_cycle_and_interval()

		self.validate_plans_billing_cycle(billing_info)

		if billing_info:
			data = dict()
			interval = billing_info[0]["billing_interval"]
			interval_count = billing_info[0]["billing_interval_count"]
			if interval not in ["Day", "Week"]:
				data["days"] = -1
			if interval == "Day":
				data["days"] = interval_count - 1
			elif interval == "Month":
				data["months"] = interval_count
			elif interval == "Year":
				data["years"] = interval_count
			# todo: test week
			elif interval == "Week":
				data["days"] = interval_count * 7 - 1

			return data

	def set_status_grace_period(self):
		"""
		Sets the `Subscription` `status` based on the preference set in `Subscription Settings`.

		Used when the `Subscription` needs to decide what to do after the current generated
		invoice is past it's due date and grace period.
		"""
		subscription_settings = frappe.get_single("Subscription Settings")
		if self.status == "Past Due Date" and self.is_past_grace_period():
			self.status = "Cancelled" if cint(subscription_settings.cancel_after_grace) else "Unpaid"

	def set_subscription_status(self):
		"""
		Sets the status of the `Subscription`
		"""
		if self.is_trialling():
			self.status = "Trialling"
		elif self.status == "Active" and self.end_date and getdate() > getdate(self.end_date):
			self.status = "Completed"
		elif self.is_past_grace_period():
			subscription_settings = frappe.get_single("Subscription Settings")
			self.status = "Cancelled" if cint(subscription_settings.cancel_after_grace) else "Unpaid"
		elif self.current_invoice_is_past_due() and not self.is_past_grace_period():
			self.status = "Past Due Date"
		# elif not self.has_outstanding_invoice():
		# 	self.status = "Active"
		# elif self.is_new_subscription():
		# 	self.status = "Active"
		self.save()

	def is_trialling(self):
		"""
		Returns `True` if the `Subscription` is in trial period.
		"""
		return not self.period_has_passed(self.trial_period_end) and self.is_new_subscription()

	@staticmethod
	def period_has_passed(end_date):
		"""
		Returns true if the given `end_date` has passed
		"""
		# todo: test for illegal time
		if not end_date:
			return True

		end_date = getdate(end_date)
		return getdate() > getdate(end_date)

	def is_past_grace_period(self):
		"""
		Returns `True` if the grace period for the `Subscription` has passed
		"""
		current_invoice = self.get_current_invoice()
		if self.current_invoice_is_past_due(current_invoice):
			subscription_settings = frappe.get_single("Subscription Settings")
			grace_period = cint(subscription_settings.grace_period)

			return getdate() > add_days(current_invoice.due_date, grace_period)

	def current_invoice_is_past_due(self, current_invoice=None):
		"""
		Returns `True` if the current generated invoice is overdue
		"""
		if not current_invoice:
			current_invoice = self.get_current_invoice()

		if not current_invoice or self.is_paid(current_invoice):
			return False
		else:
			return getdate() > getdate(current_invoice.due_date)

	def get_current_invoice(self):
		"""
		Returns the most recent generated invoice.
		"""
		doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"

		if len(self.invoices):
			current = self.invoices[-1]
			if frappe.db.exists(doctype, current.get("invoice")):
				doc = frappe.get_doc(doctype, current.get("invoice"))
				return doc
			else:
				frappe.throw(_("Invoice {0} no longer exists").format(current.get("invoice")))

	def is_new_subscription(self):
		"""
		Returns `True` if `Subscription` has never generated an invoice
		"""
		return len(self.invoices) == 0

	def validate(self):
		self.validate_trial_period()
		self.validate_plans_billing_cycle(self.get_billing_cycle_and_interval())
		self.validate_end_date()
		self.validate_to_follow_calendar_months()
		self.cost_center = erpnext.get_default_cost_center(self.get("company"))

	def validate_trial_period(self):
		"""
		Runs sanity checks on trial period dates for the `Subscription`
		"""
		if self.trial_period_start and self.trial_period_end:
			if getdate(self.trial_period_end) < getdate(self.trial_period_start):
				frappe.throw(_("Trial Period End Date Cannot be before Trial Period Start Date"))

		if self.trial_period_start and not self.trial_period_end:
			frappe.throw(_("Both Trial Period Start Date and Trial Period End Date must be set"))

		if self.trial_period_start and getdate(self.trial_period_start) > getdate(self.start_date):
			frappe.throw(_("Trial Period Start date cannot be after Subscription Start Date"))

	def validate_end_date(self):
		billing_cycle_info = self.get_billing_cycle_data()
		end_date = add_to_date(self.start_date, **billing_cycle_info)

		if self.end_date and getdate(self.end_date) <= getdate(end_date):
			frappe.throw(
				_("Subscription End Date must be after {0} as per the subscription plan").format(end_date)
			)

	def validate_to_follow_calendar_months(self):
		if self.follow_calendar_months:
			billing_info = self.get_billing_cycle_and_interval()

			if not self.end_date:
				frappe.throw(_("Subscription End Date is mandatory to follow calendar months"))

			if billing_info[0]["billing_interval"] != "Month":
				frappe.throw(
					_("Billing Interval in Subscription Plan must be Month to follow calendar months")
				)

	def after_insert(self):
		# todo: deal with users who collect prepayments. Maybe a new Subscription Invoice doctype?
		self.set_subscription_status()


	def generate_invoice_otc(self,plan,costo,subgestion, planid):
		try:
			doctype = "Sales Invoice"

			invoice = self.create_invoice_otc(plan,costo,subgestion, planid)
			# frappe.msgprint(frappe._('generate_invoice_tv_add : Fatality Error Project {0} ').format(invoice.name))

			# self.append("invoices", {"document_type": doctype, "invoice": invoice.name})
			# self.save()
			# s_invoice = frappe.get_doc({
			# 		"doctype": "Subscription Invoice",
			# 		"document_type":"doctype",
			# 		"invoice":invoice.name,
			# 		"parent":self.name,
			# 		"parentfield":"invoices",
			# 		"parenttype": "Subscription"
			# 		})
			# s_invoice.insert(ignore_permissions=True)
			frappe.db.sql(""" insert into `tabSubscription Invoice`
			(name,document_type,invoice,parent,parentfield,parenttype) values
			(%(name)s, %(document_type)s,%(invoice)s,%(parent)s,'invoices','Subscription')""",{"name":random_string(8), "document_type":doctype, "invoice": invoice.name,"parent": self.name})
			return invoice.name
		except Exception as e:
			frappe.msgprint(frappe._('generate_invoice_otc : Fatality Error Project {0} ').format(e))

	def generate_invoice(self, prorate=0):
		"""
		Creates a `Invoice` for the `Subscription`, updates `self.invoices` and
		saves the `Subscription`.
		"""
		try:


			debit=0
			if self.subscription_update:
				costo = frappe.db.sql(
				"""select total from `tabSales Invoice` where customer = %(name)s and posting_date and docstatus=1  and month(posting_date)=month(now()) and year(posting_date)=year(now()) order by posting_date 
				and tipo_factura='Recurrente' desc limit 1;""",
				{"name": self.party   },
				)
				if costo:	
					costo_2 = frappe.db.sql(
					"""select sum(cost) from `tabSubscription Plan Detail` where cost>0 and estado_plan='Activo' and parent=%(name)s;""",
					{"name": self.name   },
					)
					debit=float(costo_2[0][0])-float(costo[0][0])


			doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
			if debit>0:
				invoice = self.create_invoice(prorate,debit)				
			else:
				invoice = self.create_invoice(prorate)	
				
			# invoice.submit()

			self.append("invoices", {"document_type": doctype, "invoice": invoice.name})
			self.save()
			intervalo=int(self.periodo_de_facturacion)
			i=add_days(self.current_invoice_end, 1)

			p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")

			if self.campana:
				promo = frappe.get_doc("promotions campaign", self.campana)
				if promo:
					if not promo.primer_mes_de_cortesia:
						if intervalo>1:
							p = add_months(p, intervalo-1)

						upd_suscrip = frappe.get_doc("Subscription", {"name": self.name})
						upd_suscrip.update(
							{
								"current_invoice_start":i ,
								"current_invoice_end":p,
								"workflow_state":"Activo"
							}
						)
						upd_suscrip.save()
			else:
				if intervalo>1:
					p = add_months(p, intervalo-1)

				upd_suscrip = frappe.get_doc("Subscription", {"name": self.name})
				upd_suscrip.update(
					{
						"current_invoice_start":i ,
						"current_invoice_end":p,
						"workflow_state":"Activo"
					}
				)
				upd_suscrip.save()				


			# if promo.primer_mes_de_cortesia:
			# 	intervalo=int(self.periodo_de_facturacion)
			# 	i=add_days(self.current_invoice_end, 1)
			# 	p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")
			# 	if intervalo > 1:
			# 		p = add_months(p, intervalo)
			# 	upd_suscrip = frappe.get_doc("Subscription", {"name": self.name})
			# 	upd_suscrip.update(
			# 		{
			# 			"current_invoice_start":i ,
			# 			"current_invoice_end":p,
			# 			"workflow_state":"Activo"
			# 		}
			# 	)
			# 	upd_suscrip.save()	
			# else:
			# if promo:
			# 	if not promo.primer_mes_de_cortesia:
			# 		if intervalo>1:
			# 			p = add_months(p, intervalo-1)

			# 		upd_suscrip = frappe.get_doc("Subscription", {"name": self.name})
			# 		upd_suscrip.update(
			# 			{
			# 				"current_invoice_start":i ,
			# 				"current_invoice_end":p,
			# 				"workflow_state":"Activo"
			# 			}
			# 		)
			# 		upd_suscrip.save()
			# else:
			# 		if intervalo>1:
			# 			p = add_months(p, intervalo-1)

			# 		upd_suscrip = frappe.get_doc("Subscription", {"name": self.name})
			# 		upd_suscrip.update(
			# 			{
			# 				"current_invoice_start":i ,
			# 				"current_invoice_end":p,
			# 				"workflow_state":"Activo"
			# 			}
			# 		)
			# 		upd_suscrip.save()
			if invoice:
				for e in self.equipos:
					portafolio=frappe.db.get_value("Subscription Plan Detail",e.plan,"plan")  

					if "IPTV" in portafolio:

						upd_suscrip_equipos = frappe.get_doc("Subscription Plan Equipos", {"plan": e.plan})
						upd_suscrip_equipos.update(
							{
								"cuotas_pendientes":float(upd_suscrip_equipos.numero_de_cuotas)-1 ,
							}
						)
						upd_suscrip_equipos.save()	


			return invoice
		except Exception as e:
			frappe.msgprint(frappe._('generate_invoice : Fatality Error Project {0} ').format(e))


	def generate_invoice_Recurrente_B(self, prorate=0):
		"""
		Creates a `Invoice` for the `Subscription`, updates `self.invoices` and
		saves the `Subscription`.
		"""
		try:

			doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"

			invoice = self.create_invoice_recurrente_B(0)
			# invoice.submit()

			self.append("invoices", {"document_type": doctype, "invoice": invoice.name})
			self.save()
			intervalo=int(self.periodo_de_facturacion)
			i=add_days(self.current_invoice_end, 1)


			p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")


			if intervalo>1:
				p = add_months(p, intervalo-1)

			upd_suscrip = frappe.get_doc("Subscription", {"name": self.name})
			upd_suscrip.update(
				{
					"current_invoice_start":i ,
					"current_invoice_end":p,
					"workflow_state":"Activo"
				}
			)
			upd_suscrip.save()

			return invoice
		except Exception as e:
			frappe.msgprint(frappe._('generate_invoice : Fatality Error Project {0} ').format(e))



	def create_invoice_otc(self,plan,costo,subgestion,planid):
		try:


			doctype = "Sales Invoice"
			invoice = frappe.new_doc(doctype)
			invoice.naming_series = "B-"
			invoice.tipo_factura=subgestion
			company = self.get("company") or get_default_company()
			if not company:
				frappe.throw(
					_("Company is mandatory was generating invoice. Please set default company in Global Defaults")
				)

			invoice.company = company
			invoice.set_posting_time = 1

			invoice.posting_date = now()

			invoice.due_date =add_days(now(), 20)

			invoice.cost_center = self.cost_center
			invoice.currency = get_party_account_currency("Customer", self.party, company)
			paralela =get_exchange_rate('USD','NIO', today(), throw=True)
			invoice.tc_facturas = paralela
			invoice.customer = self.party

			if invoice.currency == "USD":
				invoice.conversion_rate=paralela
			else:
				invoice.conversion_rate=1

			

			accounting_dimensions = get_accounting_dimensions()

			for dimension in accounting_dimensions:
				if self.get(dimension):
					invoice.update({dimension: self.get(dimension)})


			if subgestion == 'TV Adicional':
				if invoice.currency=="NIO":
					items_list = {
					"item_code": frappe.db.get_value("Subscription Plan",plan,"item") ,
					"qty": 1,
					"rate": (costo)*float(paralela),
					"cost_center": '',
					"plan_detail":planid,
					"descripcion": "TV Adicional de " + plan
					}

				else:
					items_list = {
						"item_code": frappe.db.get_value("Subscription Plan",plan,"item") ,
						"qty": 1,
						"rate":costo,
						"cost_center": '',
						"plan_detail":planid,
						"descripcion": "TV Adicional de " + plan
					}
			elif subgestion == 'Cableado':
				if invoice.currency=="NIO":
					items_list = {
					"item_code": frappe.db.get_value("Subscription Plan",plan,"item"),
					"qty": 1,
					"rate": (costo)*float(paralela),
					"cost_center": '',
					"plan_detail":planid,
					"descripcion": "Cableado de " + plan
					}

				else:
					items_list = {
					"item_code": frappe.db.get_value("Subscription Plan",plan,"item"),
					"qty": 1,
					"rate": costo,
					"cost_center": '',
					"plan_detail":planid,
					"descripcion": "Cableado de " + plan
					}
			elif subgestion == 'Instalacion OTC':
				if invoice.currency=="NIO":
					items_list = {
					"item_code":frappe.db.get_value("Subscription Plan",plan,"item"),
					"qty": 1,
					"rate": (costo)*float(paralela),
					"cost_center": '',
					"plan_detail":planid,
					"descripcion": "Instalacion OTC de " + plan
					}

				else:
					items_list = {
						"item_code":frappe.db.get_value("Subscription Plan",plan,"item"),
						"qty": 1,
						"rate":costo,
						"cost_center": '',
						"plan_detail":planid,
						"descripcion": "Instalacion OTC de " + plan
					}		
			else:
				if invoice.currency=="NIO":
					items_list = {
					"item_code": frappe.db.get_value("Subscription Plan",plan,"item") ,
					"qty": 1,
					"rate": (costo)*float(paralela),
					"cost_center": '',
					"plan_detail":planid,
					"descripcion": "Traslado de " + plan
					}

				else:
					items_list = {
						"item_code": frappe.db.get_value("Subscription Plan",plan,"item") ,
						"qty": 1,
						"rate":costo,
						"cost_center": '',
						"plan_detail":planid,
						"descripcion": "Traslado de " + plan
					}


			items_list["cost_center"] = self.cost_center
			invoice.append("items", items_list)

			# Taxes
			tax_template = frappe.db.get_value("Customer", {"name": self.party}, "sales_tax_template")
			if tax_template !="":
				invoice.taxes_and_charges = tax_template
				invoice.set_taxes()


			# # Due date
			if self.days_until_due:
				invoice.append(
					"payment_schedule",
					{
						"due_date": add_days(invoice.posting_date, cint(self.days_until_due)),
						"invoice_portion": 100,
					},
				)

			# # Discounts
			if self.is_trialling():
				invoice.additional_discount_percentage = 100
			else:
				if self.additional_discount_percentage:
					invoice.additional_discount_percentage = self.additional_discount_percentage

				if self.additional_discount_amount:
					invoice.discount_amount = self.additional_discount_amount

				if self.additional_discount_percentage or self.additional_discount_amount:
					discount_on = self.apply_additional_discount
					invoice.apply_discount_on = discount_on if discount_on else "Grand Total"

			# frappe.msgprint(frappe._('Factura {0} ').format(str(items_list)))


			# # Subscription period
			invoice.from_date = self.current_invoice_start
			invoice.to_date = self.current_invoice_end

			invoice.flags.ignore_mandatory = True

			invoice.set_missing_values()
			invoice.save()
			# invoice.submit()
			# frappe.msgprint(frappe._('Factura {0} ').format(str(invoice)))

			return invoice
		except Exception as e:
			frappe.msgprint(frappe._('create_invoice_otc : Fatality Error Project {0} ').format(e))

	def create_invoice(self, prorate,upgrate=0):
		# try:
		"""
		Creates a `Invoice`, submits it and returns it
		"""
		doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"

		invoice = frappe.new_doc(doctype)
		invoice.naming_series = "B-"
		invoice.tipo_factura="Prorrateo"
		paralela =get_exchange_rate('USD','NIO', today(), throw=True)
		invoice.tc_facturas = paralela
		# For backward compatibility
		# Earlier subscription didn't had any company field
		company = self.get("company") or get_default_company()
		if not company:
			frappe.throw(
				_("Company is mandatory was generating invoice. Please set default company in Global Defaults")
			)

		invoice.company = company
		invoice.set_posting_time = 1
		# invoice.posting_date = (
		# 	self.current_invoice_start
		# 	if self.generate_invoice_at_period_start
		# 	else self.current_invoice_end
		# )
		invoice.posting_date =self.current_invoice_start

		invoice.due_date =add_days(self.current_invoice_start, 20)

		invoice.cost_center = self.cost_center

		if doctype == "Sales Invoice":
			invoice.customer = self.party
		else:
			invoice.supplier = self.party
			if frappe.db.get_value("Supplier", self.party, "tax_withholding_category"):
				invoice.apply_tds = 1


		### Add party currency to invoice
		# invoice.currency = get_party_account_currency(self.party_type, self.party, self.company)
		invoice.currency = get_party_account_currency("Customer", self.party, company)


		# frappe.msgprint(str(get_exchange_rate('NIO','USD', today(), throw=True)))
		# frappe.msgprint(str(invoice.currency))
		# frappe.msgprint(str(currency2))

		# paralela =get_exchange_rate('USD','NIO', today(), throw=True)

		# frappe.msgprint(str(paralela))
		# return

		if invoice.currency == "USD":
			invoice.conversion_rate=paralela
		else:
			invoice.conversion_rate=1


		## Add dimensions in invoice for subscription:
		accounting_dimensions = get_accounting_dimensions()

		for dimension in accounting_dimensions:
			if self.get(dimension):
				invoice.update({dimension: self.get(dimension)})

		# Subscription is better suited for service items. I won't update `update_stock`
		# for that reason
		# frappe.msgprint(self.plans.plan)
		# frappe.msgprint(paralela)
		# frappe.msgprint(prorate)
		# return
		
		if upgrate>0:
			items_list = self.get_items_from_plans_pro(self.plans, invoice.currency,paralela,upgrate,prorate)
			invoice.tipo_factura = "Prorrateo+"
		else:				
			items_list = self.get_items_from_plans(self.plans, invoice.currency,paralela,prorate)	
		# get_items_from_plans(self, plans,currency_invoice,paralela,prorate=0)
		# frappe.msgprint(frappe._('items_list : Fatality Error Project {0} ').format(self.plans))
		for item in items_list:
			item["cost_center"] = self.cost_center
			invoice.append("items", item)

		# Taxes
		tax_template = frappe.db.get_value("Customer", {"name": self.party}, "sales_tax_template")
		if tax_template !="":
			invoice.taxes_and_charges = tax_template
			invoice.set_taxes()

		# if doctype == "Sales Invoice" and self.sales_tax_template:
		# 	tax_template = self.sales_tax_template
		# if doctype == "Purchase Invoice" and self.purchase_tax_template:
		# 	tax_template = self.purchase_tax_template

		# if tax_template:
		# 	invoice.taxes_and_charges = tax_template
		# 	invoice.set_taxes()

		# Due date
		if self.days_until_due:
			invoice.append(
				"payment_schedule",
				{
					"due_date": add_days(invoice.posting_date, cint(self.days_until_due)),
					"invoice_portion": 100,
				},
			)

		# Discounts
		if self.is_trialling():
			invoice.additional_discount_percentage = 100
		else:
			if self.additional_discount_percentage:
				invoice.additional_discount_percentage = self.additional_discount_percentage

			if self.additional_discount_amount:
				invoice.discount_amount = self.additional_discount_amount

			if self.additional_discount_percentage or self.additional_discount_amount:
				discount_on = self.apply_additional_discount
				invoice.apply_discount_on = discount_on if discount_on else "Grand Total"

		# Subscription period
		invoice.from_date = self.current_invoice_start
		invoice.to_date = self.current_invoice_end

		invoice.flags.ignore_mandatory = True

		invoice.set_missing_values()
		invoice.save()
		if not self.subscription_update:
			invoice.submit()
		# if self.submit_invoice:
		# 	invoice.submit()

		return invoice
		# except Exception as e:
		# 	frappe.msgprint(frappe._('create_invoice : Fatality Error Project {0} ').format(e))


	def create_invoice_recurrente_B(self, prorate):
		try:
			"""
			Creates a `Invoice`, submits it and returns it
			"""
			doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"

			invoice = frappe.new_doc(doctype)
			invoice.naming_series = "B-"
			invoice.tipo_factura="Recurrente B"

			company = self.get("company") or get_default_company()
			if not company:
				frappe.throw(
					_("Company is mandatory was generating invoice. Please set default company in Global Defaults")
				)

			invoice.company = company
			invoice.set_posting_time = 1

			invoice.posting_date =self.current_invoice_start

			invoice.due_date =add_days(self.current_invoice_start, 20)

			invoice.cost_center = self.cost_center

			if doctype == "Sales Invoice":
				invoice.customer = self.party
			else:
				invoice.supplier = self.party
				if frappe.db.get_value("Supplier", self.party, "tax_withholding_category"):
					invoice.apply_tds = 1



			invoice.currency = get_party_account_currency("Customer", self.party, company)


			paralela =get_exchange_rate('USD','NIO', today(), throw=True)

			if invoice.currency == "USD":
				invoice.conversion_rate=paralela
			else:
				invoice.conversion_rate=1

			invoice.tc_facturas = paralela
			## Add dimensions in invoice for subscription:
			accounting_dimensions = get_accounting_dimensions()

			for dimension in accounting_dimensions:
				if self.get(dimension):
					invoice.update({dimension: self.get(dimension)})


			# items_list = self.get_items_from_plans(self.plans, invoice.currency,paralela,0)
			# frappe.msgprint("self"+ self.name)
			# frappe.msgprint("self.party "+ self.party)
			# frappe.msgprint("currency_invoice "+ invoice.currency)
			# frappe.msgprint("paralela "+str(paralela) )
			# return

			items_list = self.get_items_from_customer(self.party, invoice.currency, paralela)
		

			for item in items_list:
				item["cost_center"] = self.cost_center
				invoice.append("items", item)

			# Taxes
			tax_template = frappe.db.get_value("Customer", {"name": self.party}, "sales_tax_template")
			if tax_template !="":
				invoice.taxes_and_charges = tax_template
				invoice.set_taxes()

			# Due date
			if self.days_until_due:
				invoice.append(
					"payment_schedule",
					{
						"due_date": add_days(invoice.posting_date, cint(self.days_until_due)),
						"invoice_portion": 100,
					},
				)

			# Discounts
			if self.is_trialling():
				invoice.additional_discount_percentage = 100
			else:
				if self.additional_discount_percentage:
					invoice.additional_discount_percentage = self.additional_discount_percentage

				if self.additional_discount_amount:
					invoice.discount_amount = self.additional_discount_amount

				if self.additional_discount_percentage or self.additional_discount_amount:
					discount_on = self.apply_additional_discount
					invoice.apply_discount_on = discount_on if discount_on else "Grand Total"

			# Subscription period
			invoice.from_date = self.current_invoice_start
			invoice.to_date = self.current_invoice_end

			invoice.flags.ignore_mandatory = True

			invoice.set_missing_values()
			invoice.save()
			# if not self.subscription_update:
				# invoice.submit()


			return invoice
		except Exception as e:
			frappe.msgprint(frappe._('create_invoice : Fatality Error Project {0} ').format(e))

	def get_items_from_customer(self,customer,currency_invoice,paralela,prorate=0):
		"""
		Returns the `Item`s linked to `Subscription Plan`
		"""

		# frappe.msgprint("self "+ self.name)
		# frappe.msgprint("customer "+ str(customer))
		# frappe.msgprint("currency_invoice "+ str(currency_invoice))
		# frappe.msgprint("paralela "+ str(paralela))
		# return


		if prorate:
			prorate_factor = get_prorata_factor(
				self.current_invoice_end, self.current_invoice_start, 1
			)

		items = []
		party = customer

		plans = []

		# en las pruebas se esta usando el "current_invoice_end" pero en produccion hay que usar el "current_invoice_start"
		plans = frappe.db.sql(
		"""select t2.plan,t2.qty,t2.currency,t2.cost,t3.periodo_de_facturacion,t2.name,t4.tipocambio from   `tabSubscription Plan Detail` t2
			inner join `tabSubscription`  t3 on  t2.parent =t3.name 
			inner join `tabSubscription Plan` t4 on t4.name= t2.plan  
			where t3.name=%(name)s and t2.estado_plan='Activo' and t4.cost>0""",
			{"name": self.name },
		# {"party": party},
		)

		# for p in plans:
		# 	try:
		# 		frappe.msgprint(frappe._('todo nice {0} ').format(p[0]))
		# 	except Exception as e:
		# 		frappe.msgprint(frappe._('Fatality Error Project Plan: {0} ').format(e))
		# 		return
		# return
		for plan in plans:
			# frappe.msgprint(str(plan[4]) )
			# return
			plan_doc = frappe.get_doc("Subscription Plan", plan[0])

			item_code = plan_doc.item
			deferred_field = "enable_deferred_revenue"


			deferred = frappe.db.get_value("Item", item_code, deferred_field)


			if currency_invoice=="NIO":
				# frappe.msgprint(paralela)
				# return
				if plan[2]=="USD":
					item = {
						"item_code": item_code,
						"qty": plan[1],
						"rate":float(plan[3])*float(paralela)*float(plan[4]),
						"cost_center": plan_doc.cost_center,
						"plan_detail":plan[5],
					}
				else:
					item = {
						"item_code": item_code,
						"qty": plan[1],
						"rate":float(plan[3])*float(plan[4]),
						"cost_center": plan_doc.cost_center,
						"plan_detail":plan[5],
					}
			else:
				if plan[2]=="NIO":
					# frappe.msgprint(frappe._('precio plan {0} ').format(plan[2]))
					if plan[6]>0:
						item = {
							"item_code": item_code,
							"qty": plan[1],
							"rate":(float(plan[3])/float(plan[6]))*float(plan[4]),
							"cost_center": plan_doc.cost_center,
							"plan_detail":plan[5],
						}
					else:
						item = {
							"item_code": item_code,
							"qty": plan[1],
							"rate":(float(plan[3])/float(paralela))*float(plan[4]),
							"cost_center": plan_doc.cost_center,
							"plan_detail":plan[5],
						}
				else:
					
					item = {
						"item_code": item_code,
						"qty": plan[1],
						"rate":float(plan[3])*float(plan[4]),
						"cost_center": plan_doc.cost_center,
						"plan_detail":plan[5],
					}

			# for i in item:
			# 	frappe.msgprint(i.item_code)
			
			if deferred:
				item.update(
					{
						deferred_field: deferred,
						"service_start_date": self.current_invoice_start,
						"service_end_date": self.current_invoice_end,
					}
				)

			accounting_dimensions = get_accounting_dimensions()

			for dimension in accounting_dimensions:
				if plan_doc.get(dimension):
					item.update({dimension: plan_doc.get(dimension)})

			items.append(item)

		return items	

	def get_items_from_plans_pro(self,plans,currency_invoice,paralela,cost,prorate=0):
		#try:
		if prorate:
			prorate_factor = get_prorata_factor(
				self.current_invoice_end, self.current_invoice_start, self.generate_invoice_at_period_start
			)
		items = []
		item2={}
		party = self.party
		pasa=False
		
		cant_planes= frappe.db.sql("""select count(cost) from `tabSubscription Plan Detail` where cost>0 and estado_plan='Activo'
			and parent=%(name)s""",
		{"name": self.name },
		)

		debit=cost/int(cant_planes[0][0])

		for plan in plans:
			if plan.cost>0:
				plan_doc = frappe.get_doc("Subscription Plan", plan.plan)

				if not plan.old_plan:
					pasa=True
				else:
					plan_old_cost = frappe.db.get_value('Subscription Plan Detail', plan.old_plan, 'cost')

					old_plan_name=frappe.db.get_value('Subscription Plan Detail', plan.old_plan, 'plan')
					plan_old_item_group = frappe.db.get_value('Subscription Plan', old_plan_name, 'item_group')


					if plan.cost!=plan_old_cost:
						pasa=True
					if plan_doc.item_group!=plan_old_item_group:
						pasa=True


				if plan.estado_plan=="Activo" and pasa:
					# plan_doc = frappe.get_doc("Subscription Plan", plan.plan)


					item_code = plan_doc.item

					if self.party == "Customer":
						deferred_field = "enable_deferred_revenue"
					else:
						deferred_field = "enable_deferred_expense"

					deferred = frappe.db.get_value("Item", item_code, deferred_field)

					# frappe.msgprint("estoy aqui")
					if currency_invoice=="NIO":
						if plan_doc.currency=="USD":
							item = {
								"item_code": item_code,
								"qty": plan.qty,
								"rate": get_plan_rate_NEW(debit,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion)*float(paralela),
								"cost_center": plan_doc.cost_center,
								"plan_detail":plan.name,
								"descripcion": "UPGRADE - " + item_code +  " De " + frappe.utils.get_datetime(plan.service_start).strftime("%b %d, %y") + " A " + frappe.utils.get_datetime(frappe.utils.get_last_day(plan.service_start)).strftime("%b %d, %y")
							}
							if "IPTV" in plan.plan :
									
								plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
								if plan_equipo.precio_de_venta>0:
									if plan_equipo.deposito>0:
										rate_ip=plan_equipo.deposito
									else:
										rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas

									item2 = {
									"item_code": "Activacion por OTC",
									"qty": 1,
									"rate": float(rate_ip)*float(paralela),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
									}
							# frappe.msgprint(str(paralela))
							# return
							
						else:
							item = {
								"item_code": item_code,
								"qty": plan.qty,
								# tiene 6 parametros
								# "rate":get_plan_rate_NEW(debit,
								# 		plan.qty,
								# 		party,
								# 		self.current_invoice_start,
								# 		self.current_invoice_end,
								# 		prorate_factor,
								# 	),
								"rate": get_plan_rate_NEW(debit,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion),
								"cost_center": plan_doc.cost_center,
								"plan_detail":plan.name,
								"descripcion": "UPGRADE - " + item_code +  " De " + frappe.utils.get_datetime(plan.service_start).strftime("%b %d, %y") + " A " + frappe.utils.get_datetime(frappe.utils.get_last_day(plan.service_start)).strftime("%b %d, %y")
							}

							if "IPTV" in plan.plan :
									
								plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
								if plan_equipo.precio_de_venta>0:
									if plan_equipo.deposito>0:
										rate_ip=plan_equipo.deposito
									else:
										rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas

									item2 = {
									"item_code": "Activacion por OTC",
									"qty": 1,
									"rate": float(rate_ip),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
									}
					else:
						if plan_doc.currency=="NIO":
							# frappe.msgprint(frappe._('precio plan {0} ').format(plan[2]))
							item = {
								"item_code": item_code,
								"qty": plan.qty,
								"rate": get_plan_rate_NEW(debit,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion)/float(paralela),
								"cost_center": plan_doc.cost_center,
								"plan_detail":plan.name,
								"descripcion": "UPGRADE - " + item_code +  " De " + frappe.utils.get_datetime(plan.service_start).strftime("%b %d, %y") + " A " + frappe.utils.get_datetime(frappe.utils.get_last_day(plan.service_start)).strftime("%b %d, %y")
							}
							if "IPTV" in plan.plan :
									
								plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
								if plan_equipo.precio_de_venta>0:
									if plan_equipo.deposito>0:
										rate_ip=plan_equipo.deposito
									else:
										rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas

									item2 = {
									"item_code": "Activacion por OTC",
									"qty": 1,
									"rate": float(rate_ip)/float(paralela),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
									}
						else:

							item = {
								"item_code": item_code,
								"qty": plan.qty,
								"rate": get_plan_rate_NEW(debit,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion),
								"cost_center": plan_doc.cost_center,
								"plan_detail":plan.name,
								"descripcion": "UPGRADE - " + item_code +  " De " + frappe.utils.get_datetime(plan.service_start).strftime("%b %d, %y") + " A " + frappe.utils.get_datetime(frappe.utils.get_last_day(plan.service_start)).strftime("%b %d, %y")
							}
							if "IPTV" in plan.plan :
									
								plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
								if plan_equipo.precio_de_venta>0:
									if plan_equipo.deposito>0:
										rate_ip=plan_equipo.deposito
									else:
										rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas

									item2 = {
									"item_code": "Activacion por OTC",
									"qty": 1,
									"rate": float(rate_ip),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
									}

					if deferred:
						item.update(
							{
								deferred_field: deferred,
								"service_start_date": self.current_invoice_start,
								"service_end_date": self.current_invoice_end,
							}
						)

					accounting_dimensions = get_accounting_dimensions()

					for dimension in accounting_dimensions:
						if plan_doc.get(dimension):
							item.update({dimension: plan_doc.get(dimension)})

					items.append(item)
		# except Exception as e:
		# 	frappe.msgprint(frappe._('get_items_from_plans: Fatality Error Project {0} ').format(e))

		return items

	def get_items_from_plans(self, plans,currency_invoice,paralela,prorate=0):
		"""
		Returns the `Item`s linked to `Subscription Plan`
		"""
		try:
			if prorate:
				prorate_factor = get_prorata_factor(
					self.current_invoice_end, self.current_invoice_start, self.generate_invoice_at_period_start
				)
				# frappe.msgprint(str(self.current_invoice_start))
				# frappe.msgprint(str(self.current_invoice_end))
				# return

			items = []
			item2={}
			party = self.party
			pasa=False
			for plan in plans:
				
				plan_doc = frappe.get_doc("Subscription Plan", plan.plan)

				if not plan.old_plan:
					pasa=True
				else:
					plan_old_cost = frappe.db.get_value('Subscription Plan Detail', plan.old_plan, 'cost')

					old_plan_name=frappe.db.get_value('Subscription Plan Detail', plan.old_plan, 'plan')
					plan_old_item_group = frappe.db.get_value('Subscription Plan', old_plan_name, 'item_group')

					# frappe.msgprint(frappe._('old_plan_name : Fatality Error Project {0} ').format(old_plan_name))
					# frappe.msgprint(frappe._('plan_old_item_group : Fatality Error Project {0} ').format(plan_old_item_group))

					# plan_doc_old = frappe.get_doc("Subscription Plan", plan_old)
					# if plan_doc.item_group==plan_doc_old.item_group and plan_doc.cost==plan_doc_old.cost:
					if plan.cost!=plan_old_cost:
						pasa=True
					if plan_doc.item_group!=plan_old_item_group:
						pasa=True


				if plan.estado_plan=="Activo" and pasa:
					# plan_doc = frappe.get_doc("Subscription Plan", plan.plan)


					item_code = plan_doc.item

					if self.party == "Customer":
						deferred_field = "enable_deferred_revenue"
					else:
						deferred_field = "enable_deferred_expense"

					deferred = frappe.db.get_value("Item", item_code, deferred_field)

					# frappe.msgprint("estoy aqui")
					if not prorate:
						item = {
							"item_code": item_code,
							"qty": plan.qty,
							"rate": get_plan_rate_NEW(plan.cost,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion),
							"cost_center": plan_doc.cost_center,
							"plan_detail" : plan.name
						}
					else:
						# item = {
						# 	"item_code": item_code,
						# 	"qty": plan.qty,
						# 	"rate": get_plan_rate(
						# 		plan.plan,
						# 		plan.qty,
						# 		party,
						# 		self.current_invoice_start,
						# 		self.current_invoice_end,
						# 		prorate_factor,
						# 	),
						# 	"cost_center": plan_doc.cost_center,
						# }
						# frappe.msgprint(str(currency_invoice))
						# frappe.msgprint(str(paralela))
						# frappe.msgprint(str(plan_doc.currency))
						# return
						if currency_invoice=="NIO":
							if plan_doc.currency=="USD":
								item = {
									"item_code": item_code,
									"qty": plan.qty,
									"rate": get_plan_rate_NEW(plan.cost,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion)*float(paralela),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
								}
								if "IPTV" in plan.plan :
									
									plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
									if plan_equipo.precio_de_venta>0:
										if plan_equipo.deposito>0:
											rate_ip=plan_equipo.deposito
										else:											
											rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas
					

										item2 = {
										"item_code": "Activacion por OTC",
										"qty": 1,
										"rate":float(rate_ip)*float(paralela),
										"cost_center": plan_doc.cost_center,
										"plan_detail":plan.name,
										}
								# frappe.msgprint(str(paralela))
								# return
							else:
								item = {
									"item_code": item_code,
									"qty": plan.qty,
									# "rate":get_plan_rate_NEW(plan.cost,
									# 		plan.qty,
									# 		party,
									# 		self.current_invoice_start,
									# 		self.current_invoice_end,
									# 		prorate_factor,
									# 	),
									"rate": get_plan_rate_NEW(plan.cost,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
								}
								if "IPTV" in plan.plan :
									
									plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
									if plan_equipo.precio_de_venta>0:
										if plan_equipo.deposito>0:
											rate_ip=plan_equipo.deposito
										else:
											rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas

										item2 = {
										"item_code": "Activacion por OTC",
										"qty": 1,
										"rate": float(rate_ip),
										"cost_center": plan_doc.cost_center,
										"plan_detail":plan.name,
										}
						else:
							if plan_doc.currency=="NIO":
								# frappe.msgprint(frappe._('precio plan {0} ').format(plan[2]))
								item = {
									"item_code": item_code,
									"qty": plan.qty,
									"rate": get_plan_rate_NEW(plan.cost,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion)/float(paralela),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
								}
								if "IPTV" in plan.plan :
									
									plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
									if plan_equipo.precio_de_venta>0:
										if plan_equipo.deposito>0:
											rate_ip=plan_equipo.deposito
										else:
											rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas

										item2 = {
										"item_code": "Activacion por OTC",
										"qty": 1,
										"rate": float(rate_ip)/float(paralela),
										"cost_center": plan_doc.cost_center,
										"plan_detail":plan.name,
										}
							else:
								# x=get_plan_rate_NEW(plan.plan,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion)
								# frappe.msgprint(frappe._('precio plan {0} ').format(x))
								# return
								item = {
									"item_code": item_code,
									"qty": plan.qty,
									"rate": get_plan_rate_NEW(plan.cost,self.current_invoice_start, self.current_invoice_end,self.periodo_de_facturacion),
									"cost_center": plan_doc.cost_center,
									"plan_detail":plan.name,
								}

								if "IPTV" in plan.plan :

									plan_equipo= frappe.get_doc("Subscription Plan Equipos", {"plan": plan.name})
									if plan_equipo.precio_de_venta>0:
										if plan_equipo.deposito>0:
											rate_ip=plan_equipo.deposito
										else:
											rate_ip=plan_equipo.precio_de_venta/plan_equipo.numero_de_cuotas

										item2 = {
										"item_code": "Activacion por OTC",
										"qty": 1,
										"rate": float(rate_ip),
										"cost_center": plan_doc.cost_center,
										"plan_detail":plan.name,
										}
									# frappe.msgprint(frappe._('precio plan {0} ').format(item))
									# return
								
					if deferred:
						item.update(
							{
								deferred_field: deferred,
								"service_start_date": self.current_invoice_start,
								"service_end_date": self.current_invoice_end,
							}
						)

					accounting_dimensions = get_accounting_dimensions()

					for dimension in accounting_dimensions:
						if plan_doc.get(dimension):
							item.update({dimension: plan_doc.get(dimension)})

					items.append(item)

					if item2:
						items.append(item2)			

			
		except Exception as e:
			frappe.msgprint(frappe._('get_items_from_plans: Fatality Error Project {0} ').format(e))

		return items

	def process(self):
		"""
		To be called by task periodically. It checks the subscription and takes appropriate action
		as need be. It calls either of these methods depending the `Subscription` status:
		1. `process_for_active`
		2. `process_for_past_due`
		"""
		# if self.status == "Active":
		# 	self.process_for_active()
		# elif self.status in ["Past Due Date", "Unpaid"]:
		# 	self.process_for_past_due_date()

		# self.set_subscription_status()

		self.save()

	def is_postpaid_to_invoice(self):
		return getdate() > getdate(self.current_invoice_end) or (
			getdate() >= getdate(self.current_invoice_end)
			and getdate(self.current_invoice_end) == getdate(self.current_invoice_start)
		)

	def is_prepaid_to_invoice(self):
		if not self.generate_invoice_at_period_start:
			return False

		if self.is_new_subscription() and getdate() >= getdate(self.current_invoice_start):
			return True

		# Check invoice dates and make sure it doesn't have outstanding invoices
		return getdate() >= getdate(self.current_invoice_start)

	def is_current_invoice_generated(self, _current_start_date=None, _current_end_date=None):
		invoice = self.get_current_invoice()

		if not (_current_start_date and _current_end_date):
			_current_start_date, _current_end_date = self.update_subscription_period(
				date=add_days(self.current_invoice_end, 1), return_date=True
			)

		if invoice and getdate(_current_start_date) <= getdate(invoice.posting_date) <= getdate(
			_current_end_date
		):
			return True

		return False

	def process_for_active(self):
		"""
		Called by `process` if the status of the `Subscription` is 'Active'.

		The possible outcomes of this method are:
		1. Generate a new invoice
		2. Change the `Subscription` status to 'Past Due Date'
		3. Change the `Subscription` status to 'Cancelled'
		"""

		if not self.is_current_invoice_generated(
			self.current_invoice_start, self.current_invoice_end
		) and (self.is_postpaid_to_invoice() or self.is_prepaid_to_invoice()):

			prorate = frappe.db.get_single_value("Subscription Settings", "prorate")
			self.generate_invoice(prorate)

		if getdate() > getdate(self.current_invoice_end) and self.is_prepaid_to_invoice():
			self.update_subscription_period(add_days(self.current_invoice_end, 1))

		if self.cancel_at_period_end and getdate() > getdate(self.current_invoice_end):
			self.cancel_subscription_at_period_end()

	def cancel_subscription_at_period_end(self):
		"""
		Called when `Subscription.cancel_at_period_end` is truthy
		"""
		if self.end_date and getdate() < getdate(self.end_date):
			return

		self.status = "Cancelled"
		if not self.cancelation_date:
			self.cancelation_date = nowdate()

	def process_for_past_due_date(self):
		"""
		Called by `process` if the status of the `Subscription` is 'Past Due Date'.

		The possible outcomes of this method are:
		1. Change the `Subscription` status to 'Active'
		2. Change the `Subscription` status to 'Cancelled'
		3. Change the `Subscription` status to 'Unpaid'
		"""
		current_invoice = self.get_current_invoice()
		if not current_invoice:
			frappe.throw(_("Current invoice {0} is missing").format(current_invoice.invoice))
		else:
			# if not self.has_outstanding_invoice():
			# 	self.status = "Active"
			# else:
			# 	self.set_status_grace_period()

			if getdate() > getdate(self.current_invoice_end):
				self.update_subscription_period(add_days(self.current_invoice_end, 1))

			# Generate invoices periodically even if current invoice are unpaid
			if (
				self.generate_new_invoices_past_due_date
				and not self.is_current_invoice_generated(self.current_invoice_start, self.current_invoice_end)
				and (self.is_postpaid_to_invoice() or self.is_prepaid_to_invoice())
			):

				prorate = frappe.db.get_single_value("Subscription Settings", "prorate")
				self.generate_invoice(prorate)

	@staticmethod
	def is_paid(invoice):
		"""
		Return `True` if the given invoice is paid
		"""
		return invoice.status == "Paid"

	def has_outstanding_invoice(self):
		"""
		Returns `True` if the most recent invoice for the `Subscription` is not paid
		"""
		doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
		current_invoice = self.get_current_invoice()
		invoice_list = [d.invoice for d in self.invoices]

		outstanding_invoices = frappe.get_all(
			doctype, fields=["name"], filters={"status": ("!=", "Paid"), "name": ("in", invoice_list)}
		)

		if outstanding_invoices:
			return True
		else:
			False

	def cancel_subscription(self):
		"""
		This sets the subscription as cancelled. It will stop invoices from being generated
		but it will not affect already created invoices.
		"""
		if self.status != "Cancelled":
			to_generate_invoice = (
				True if self.status == "Active" and not self.generate_invoice_at_period_start else False
			)
			to_prorate = frappe.db.get_single_value("Subscription Settings", "prorate")
			self.status = "Cancelled"
			self.cancelation_date = nowdate()
			if to_generate_invoice:
				self.generate_invoice(prorate=to_prorate)
			self.save()

	def restart_subscription(self):
		"""
		This sets the subscription as active. The subscription will be made to be like a new
		subscription and the `Subscription` will lose all the history of generated invoices
		it has.
		"""
		if self.status == "Cancelled":
			self.status = "Active"
			self.db_set("start_date", nowdate())
			self.update_subscription_period(nowdate())
			self.invoices = []
			self.save()
		else:
			frappe.throw(_("You cannot restart a Subscription that is not cancelled."))

	def get_precision(self):
		invoice = self.get_current_invoice()
		if invoice:
			return invoice.precision("grand_total")


def get_calendar_months(billing_interval):
	calendar_months = []
	start = 0
	while start < 12:
		start += billing_interval
		calendar_months.append(start)

	return calendar_months


def get_prorata_factor(period_end, period_start, is_prepaid):
	if is_prepaid:
		prorate_factor = 1
	else:
		diff = flt(date_diff(nowdate(), period_start) + 1)
		plan_days = flt(date_diff(period_end, period_start) + 1)
		prorate_factor = diff / plan_days

	return prorate_factor


def process_all():
	"""
	Task to updates the status of all `Subscription` apart from those that are cancelled
	"""
	subscriptions = get_all_subscriptions()
	for subscription in subscriptions:
		process(subscription)


def get_all_subscriptions():
	"""
	Returns all `Subscription` documents
	"""
	return frappe.db.get_all("Subscription", {"status": ("!=", "Cancelled")})


def process(data):
	"""
	Checks a `Subscription` and updates it status as necessary
	"""
	if data:
		try:
			subscription = frappe.get_doc("Subscription", data["name"])
			subscription.process()
			frappe.db.commit()
		except frappe.ValidationError:
			frappe.db.rollback()
			subscription.log_error("Subscription failed")




@frappe.whitelist()
def cancel_subscription(name):
	"""
	Cancels a `Subscription`. This will stop the `Subscription` from further invoicing the
	`Subscriber` but all already outstanding invoices will not be affected.
	"""
	subscription = frappe.get_doc("Subscription", name)
	subscription.cancel_subscription()


@frappe.whitelist()
def restart_subscription(name):
	"""
	Restarts a cancelled `Subscription`. The `Subscription` will 'forget' the history of
	all invoices it has generated
	"""
	subscription = frappe.get_doc("Subscription", name)
	subscription.restart_subscription()


@frappe.whitelist()
def get_subscription_updates(name):
	"""
	Use this to get the latest state of the given `Subscription`
	"""
	subscription = frappe.get_doc("Subscription", name)
	subscription.process()

@frappe.whitelist()
def crear_orden_servicio(name):
	#try:
	doc = frappe.get_doc("Subscription", name)
	
	if doc.campana  in ["Referido","Referido y Captación","Referido y proporcional cortesia","Referido, Captación y Proporcional gratis"] and not doc.referido_por:
		frappe.msgprint("Ingrese cliente de referencia", "No se pudo crear la orden")
		return
	combos = tv = gpon = hfc = tv_gpon = tv_hfc = 0
	for plan in doc.get('plans'):
		if plan.es_combo==1:
			combos +=1
			if "GPON" in plan.plan:
					gpon += 1
			elif "HFC" in plan.plan:
					hfc += 1
			if not frappe.db.exists("Subscription Plan Detail", {"parent": name,"plan":["like","%TV Combo GPON%"]}) and not frappe.db.exists("Subscription Plan Detail", {"parent": name,"plan":["like","%TV Combo HFC%"]}):
				frappe.msgprint(f"Hace falta agregar plan TV para el combo {plan.plan}")
				return
		if  'TV Combo GPON' in plan.plan or 'TV Combo HFC' in plan.plan:
			tv += 1
			if 'TV Combo GPON' in plan.plan:
				tv_gpon +=1
			elif 'TV Combo HFC' in plan.plan:
				tv_hfc +=1
			
	# frappe.msgprint(f"tv: {tv}, combos: {combos}, hfc: {hfc}, tv_hfc: {tv_hfc}, gpon: {gpon} tv_gpon: {tv_gpon}")
	if tv == combos and hfc == tv_hfc and gpon == tv_gpon:
		for plan in doc.get('plans'):
			# var = False
			if ('TV Combo GPON' in plan.plan or 'TV Combo HFC' in  plan.plan) and not doc.subscription_update:
				continue

			var = False
			status =''
			if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"INSTALACION","nombre_de_origen":doc.name,"plan_de_subscripcion":plan.name}):
				so= frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"INSTALACION","nombre_de_origen":doc.name,"plan_de_subscripcion":plan.name})
				if so.workflow_state=="Cancelado" or so.docstatus==2:
					status = "Pasa"
				else:
					status = "No Pasa"
			else:
				var = True

			if status=="Pasa" or var:
				if plan.estado_plan=="Inactivo":

					portafolio=get_portafolio_plan(plan.plan)
					direccion=frappe.get_doc("Address", plan.direccion)
					presupuesto = frappe.db.sql(""" select presupuesto from `tabOpportunity Item OTC` otc inner join
						`tabOpportunity Item` service  on  otc.parent = service.parent where otc.parent = (select oportunidad from `tabSubscription` where name = %(suscripcion)s )
						and item = 'Instalacion y Configuracion' order by presupuesto desc  limit 1; """, {"suscripcion":name})
					try:
						presupuesto = presupuesto[0][0]

					except:
						presupuesto = None
				
					sp = frappe.get_doc("Subscription Plan", plan.plan)
					if sp.compresion:
						comp =  sp.compresion
					else: 
						comp = ''
					od = frappe.get_doc({
						'doctype': "Service Order",
						'tipo_de_orden': "INSTALACION",
						'workflow_state': "Abierto",
						'tipo_de_origen': doc.doctype,
						'nombre_de_origen': doc.name,
						'tipo_cliente': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_group'),
						'descripcion': frappe._('Ejecutar Instalación de {0}').format(plan.plan + ' Compresión '+ comp),
						'tipo': 'Customer',
						'tercero': doc.party,
						'nombre': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_name'),
						'plan_de_subscripcion': plan.name,
						'direccion_de_instalacion': plan.direccion,
						'venta_en_caliente':plan.venta_en_caliente,
						'portafolio': str(portafolio[0][0]),
						'departamento': direccion.departamento,
						'municipio': direccion.municipio,
						'barrio': direccion.barrio,
						'direccion': direccion.address_line1,
						'vendedor':doc.vendedor,
						'latitud':plan.latitud,
						'longitud':plan.longitud,
						'nodo':plan.nodo,
						'orden_de_presupuesto':presupuesto,
						'informacion_de_contacto':plan.contacto,
						'proveedor': plan.proveedor,
					})
					od.insert()
					frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))
				else:
					frappe.msgprint("No se pueden crear ordenes de trabajo para plan " + plan.plan)
	else:
		frappe.msgprint("Debe agregar un plan de TV correspondiente a cada combo")

@frappe.whitelist()
def crear_orden_servicio_atrasada(plan_name, tercero):
	#try:
	plan = frappe.get_doc("Subscription Plan Detail", plan_name)
	

	var = False
	status =''
	if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"Liquidacion de Materiales Atrasada","nombre_de_origen":plan.parent,"plan_de_subscripcion":plan.name}):
		so= frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"Liquidacion de Materiales Atrasada","nombre_de_origen":plan.parent,"plan_de_subscripcion":plan.name})
		if so.workflow_state in ("Cancelado","Finalizado") or so.docstatus==2:
			status = "Pasa"
		else:
			status = "No Pasa"
	else:
		var = True

	if status=="Pasa" or var:

		portafolio=get_portafolio_plan(plan.plan)
		direccion=frappe.get_doc("Address", plan.direccion)
		
		sp = frappe.get_doc("Subscription Plan", plan.plan)
		od = frappe.get_doc({
			'doctype': "Service Order",
			'tipo_de_orden': "Liquidacion de Materiales Atrasada",
			'workflow_state': "Abierto",
			'tipo_de_origen': "Subscription",
			'nombre_de_origen': plan.parent,
			'tipo_cliente': frappe.db.get_value('Customer', {"name": tercero}, 'customer_group'),
			'descripcion': frappe._('Ejecutar Instalación de {0}').format(plan.plan + ' Compresión '+sp.compresion),
			'tipo': 'Customer',
			'tercero': tercero,
			'nombre': frappe.db.get_value('Customer', {"name": tercero}, 'customer_name'),
			'plan_de_subscripcion': plan.name,
			'direccion_de_instalacion': plan.direccion,
			'venta_en_caliente':plan.venta_en_caliente,
			'portafolio': str(portafolio[0][0]),
			'departamento': direccion.departamento,
			'municipio': direccion.municipio,
			'barrio': direccion.barrio,
			'direccion': direccion.address_line1,
			'latitud':plan.latitud,
			'longitud':plan.longitud,
			'nodo':plan.nodo,
			
			'informacion_de_contacto':plan.contacto,
			'proveedor': plan.proveedor,
		})
		od.insert()
		frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))
		

@frappe.whitelist()
def crear_orden_Desinstalacion(name):

	# subscriptions = frappe.db.sql(
	# """select  distinct t3.name from `tabSubscription Plan` t1 
	# 	inner join `tabSubscription Plan Detail`  t2 on  t1.name = t2.plan
	# 	inner join `tabSubscription`  t3 on  t2.parent =t3.name  
	# 	where t2.estado_plan='Plan Cerrado' and t2.motivo_finalizado like '%Cierre Auto / Cliente con 3 meses Suspendido%' and t2.name  in ('251934') limit 20000;"""	)
	# for subscription in subscriptions:
	try:
		# frappe.msgprint(frappe._('name {0} ').format(subscription[0]))
		# doc = frappe.get_doc("Subscription", subscription[0])
		doc = frappe.get_doc("Subscription", name)
		
		for plan in doc.get('plans'):
			var = False
			status =''
			if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"DESINSTALACION","nombre_de_origen":doc.name,"plan_de_subscripcion":plan.name}):
				so= frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"DESINSTALACION","nombre_de_origen":doc.name,"plan_de_subscripcion":plan.name})
				if so.workflow_state=="Cancelado":
					status = "Pasa"
				else:
					status = "No Pasa"
			else:
				var = True

			if status=="Pasa" or var:
				if plan.estado_plan=="Plan Cerrado":
					portafolio=get_portafolio_plan(plan.plan)
					direccion=frappe.get_doc("Address", plan.direccion)
					# frappe.msgprint("entra a la condicion del plan")
					od = frappe.get_doc({
						'doctype': "Service Order",
						'tipo_de_orden': "DESINSTALACION",
						'workflow_state': "Abierto",
						'tipo_de_origen': doc.doctype,
						'nombre_de_origen': doc.name,
						'descripcion': frappe._('Ejecutar Desinstalcion de {0}').format(plan.plan),
						'tipo': 'Customer',
						'tercero': doc.party,
						'nombre': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_name'),
						'tipo_cliente': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_group'),
						'plan_de_subscripcion': plan.name,
						'direccion_de_instalacion': plan.direccion,
						'portafolio': str(portafolio[0][0]),
						'departamento': direccion.departamento,
						'municipio': direccion.municipio,
						'barrio': direccion.barrio,
						'direccion': direccion.address_line1,
						#'vendedor':doc.vendedor,
						'nodo':plan.nodo,
						'latitud':plan.latitud,
						'longitud':plan.longitud,
						'informacion_de_contacto':plan.contacto,
						'proveedor': plan.proveedor,
					})
					# od.insert()
					od.save()
					frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))

					for equipos in doc.get('equipos'):
						if plan.name==equipos.plan:
							# frappe.msgprint("entra a la segunda condicion")
							code = frappe.db.get_value('Serial No', {"name": equipos.equipo}, 'item_code')
							eos = frappe.get_doc({
							'doctype': "Equipo_Orden_Servicio",
							'serial_no': equipos.equipo,
							'parent': od.name,
							'parenttype': "Service Order",
							'parentfield': "equipo_orden_servicio",
							'item_code': code
							})
							eos.save()
				else:
					frappe.msgprint("No se pueden crear ordenes de trabajo para planes activos")
	except Exception as e:
				frappe.msgprint(frappe._('crear_orden_Desinstalacion: Fatality Error Project {0} ').format(e))

@frappe.whitelist()
def crear_orden_Desinstalacion2(plan_name, tercero):
	#try:

	plan = frappe.get_doc("Subscription Plan Detail", plan_name)
	doc = frappe.get_doc("Subscription",plan.parent)

	var = False
	status =''
	if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"DESINSTALACION RCPE","nombre_de_origen":plan.parent,"plan_de_subscripcion":plan.name}):
		so= frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"DESINSTALACION RCPE","nombre_de_origen":plan.parent,"plan_de_subscripcion":plan.name})
		if so.workflow_state in ("Cancelado","Finalizado") or so.docstatus==2:
			status = "Pasa"
		else:
			status = "No Pasa"
	else:
		var = True

	if status=="Pasa" or var:

		portafolio=get_portafolio_plan(plan.plan)
		direccion=frappe.get_doc("Address", plan.direccion)
		# frappe.msgprint("entra a la condicion del plan")
		od = frappe.get_doc({
			'doctype': "Service Order",
			'tipo_de_orden': "DESINSTALACION RCPE",
			'workflow_state': "Abierto",
			'tipo_de_origen': doc.doctype,
			'nombre_de_origen': doc.name,
			'descripcion': frappe._('Ejecutar Desinstalcion de {0}').format(plan.plan),
			'tipo': 'Customer',
			'tercero': tercero,
			'nombre': frappe.db.get_value('Customer', {"name": tercero}, 'customer_name'),
			'tipo_cliente': frappe.db.get_value('Customer', {"name": tercero}, 'customer_group'),
			'plan_de_subscripcion': plan.name,
			'direccion_de_instalacion': plan.direccion,
			'portafolio': str(portafolio[0][0]),
			'departamento': direccion.departamento,
			'municipio': direccion.municipio,
			'barrio': direccion.barrio,
			'direccion': direccion.address_line1,
			#'vendedor':doc.vendedor,
			'nodo':plan.nodo,
			'latitud':plan.latitud,
			'longitud':plan.longitud,
			'informacion_de_contacto':plan.contacto,
			'proveedor': plan.proveedor,
		})
		# od.insert()
		od.save()
		frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))

		for equipos in doc.get('equipos'):
			if plan.name==equipos.plan:
				# frappe.msgprint("entra a la segunda condicion")
				code = frappe.db.get_value('Serial No', {"name": equipos.equipo}, 'item_code')
				eos = frappe.get_doc({
				'doctype': "Equipo_Orden_Servicio",
				'serial_no': equipos.equipo,
				'parent': od.name,
				'parenttype': "Service Order",
				'parentfield': "equipo_orden_servicio",
				'item_code': code
				})
				eos.save()

	# except Exception as e:
	# 			frappe.msgprint(frappe._('crear_orden_Desinstalacion: Fatality Error Project {0} ').format(e))


def get_portafolio_plan(plan):
	portafolio = frappe.db.sql(
	"""Select t1.item_group
	from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item where t2.name=%(plan)s limit 1 """,
	{"plan": plan},)
	return portafolio

# def get_equipo_plan(plan):
# 	portafolio = frappe.db.sql(
# 	"""Select t1.item_group
# 	from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item where t2.name=%(plan)s limit 1 """,
# 	{"plan": plan},)
# 	return portafolio


@frappe.whitelist()
def get_addresses_user(party):
	direcciones = frappe.db.sql(""" select name from `tabAddress` where name in(
		select distinct(parent) from `tabDynamic Link` where link_name=%(party)s) """,{"party": party})
	lista =[]
	for i in range(len(direcciones)):
		plan = str(direcciones[i][0])
		lista.append(plan)
	return lista

@frappe.whitelist()
def vincular_lead(name):
	susc = frappe.get_doc("Subscription", name)
	contratos = frappe.db.sql(""" select count(name) from `tabSubscription` where party=%(party)s """,{"party": susc.party})
	
	if contratos[0][0]==1 and not susc.lead:
		frappe.db.set_value("Subscription",name,"lead",frappe.get_value("Customer", susc.party,"lead_name"))



@frappe.whitelist()
def get_contacts_user(party):
	contactos = frappe.db.sql(""" select name from `tabContact` where name in(
		select distinct(parent) from `tabDynamic Link` where link_name=%(party)s) """,{"party": party})
	lista =[]
	for i in range(len(contactos)):
		plan = str(contactos[i][0])
		lista.append(plan)
	return lista

@frappe.whitelist()
def filtrar_planes(lista_de_planes):
	planes = frappe.db.sql(""" select t1.name from `tabSubscription Plan` t1
		where t1.activo = 1 and t1.tipo_de_plan = %(lista_de_planes)s and t1.tarifa_ibw=1 """,{"lista_de_planes":lista_de_planes})
	lista =[plan[0] for plan in planes]
	return lista


@frappe.whitelist()
def process_de_Facturacion(name):
	susc = frappe.get_doc("Subscription", name)
	service_start = frappe.db.get_value("Subscription Plan Detail",{"parent":name},"service_start")
	
	Mes_service_start = frappe.utils.formatdate(service_start, "MM")
	Ano_service_start = frappe.utils.formatdate(service_start, "YY")

	Mes_current_start = frappe.utils.formatdate(susc.current_invoice_start, "MM")
	Ano_current_start = frappe.utils.formatdate(susc.current_invoice_start, "YY")

	if susc.campana:
		if frappe.db.exists("promotions campaign", {"name": susc.campana}):
			promo = frappe.get_doc("promotions campaign", susc.campana)
			
			if promo.promo_primera_factura_gratis and promo.primer_mes_de_cortesia and (Mes_service_start==Mes_current_start and Ano_service_start==Ano_current_start):
				intervalo=int(susc.periodo_de_facturacion)
				i=add_months(susc.current_invoice_end,1)
				i=add_days(i, 1)
				p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")

				if intervalo > 1:
					p = add_months(p, intervalo)

				upd_suscrip = frappe.get_doc("Subscription", {"name": susc.name})
				upd_suscrip.update(
					{
						"current_invoice_start":i ,
						"current_invoice_end":p,
						"workflow_state":"Activo"
					}
				)
				upd_suscrip.save()
				return

			if promo.promo_primera_factura_gratis and (Mes_service_start==Mes_current_start and Ano_service_start==Ano_current_start):
				intervalo=int(susc.periodo_de_facturacion)
				i=add_days(susc.current_invoice_end, 1)
				p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")
				if intervalo > 1:
					p = add_months(p, intervalo-1)
				upd_suscrip = frappe.get_doc("Subscription", {"name": susc.name})
				upd_suscrip.update(
					{
						"current_invoice_start":i ,
						"current_invoice_end":p,
						"workflow_state":"Activo"
					}
				)
				upd_suscrip.save()
				return
		

	for plan in susc.plans:
		if plan.estado_plan=='Activo':
			item_group = frappe.db.get_value("Subscription Plan",plan.plan,"item_group")
			item = frappe.db.get_value("Subscription Plan",plan.plan,"item")
			if item_group in ['GPON','GPON-CORPORATIVO','GPON-INT-PYME','GPON-INT-RESIDENCIAL','GPON-TV-CORPORATIVO','GPON-TV-PYME','GPON-TV-RESIDENCIAL','HFC', 'HFC 3.0', 'IMOVIL', 'INET', 'Wimax','LTE', 'LTE Productos']:
				if not frappe.db.exists("Subscription Plan Equipos", {"plan": plan.name,"parent":name}):				
					if "TV Combo" not in plan.plan and "SIN VELOCIDAD" not in plan.plan and "SIN VELOCIDAD" not in item:	
								
						frappe.msgprint("favor solicitar a bodega que agregar los equipos antes de hacer la factura B")
						return

	address_line1 = frappe.db.get_value("Customer",susc.party,"address_line1")
	if not address_line1:
		frappe.msgprint(
					msg='No se ha definido la dirección de facturación principal para este cliente.',
					title='No se pudo generar la factura',
					indicator='red'
				)
		return

	factura=Subscription.generate_invoice(susc,1)

	frappe.db.sql("update `tabSubscription` set workflow_state = 'Activo' where name = %(name)s",{"name":susc.name})
	if susc.campana:
		if  frappe.db.exists("promotions campaign", {"name": susc.campana}):
			promo = frappe.get_doc("promotions campaign", susc.campana)
			if promo.primer_mes_de_cortesia and (Mes_service_start==Mes_current_start and Ano_service_start==Ano_current_start):
				intervalo=int(susc.periodo_de_facturacion)
				i=add_days(susc.current_invoice_end, 1)
				p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")

				i =add_days(p, 1)
				p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")
				if intervalo > 1:
					p = add_months(p, intervalo)
				upd_suscrip = frappe.get_doc("Subscription", {"name": susc.name})
				upd_suscrip.update(
					{
						"current_invoice_start":i ,
						"current_invoice_end":p,
						"workflow_state":"Activo"
					}
				)
				upd_suscrip.save()	

	frappe.msgprint(frappe._('Factura B-: {0} ').format(frappe.utils.get_link_to_form("Sales Invoice", factura)))

@frappe.whitelist()
def process_de_Facturacion_Recurrente_B(name):
	# create_invoice(self, customer, prorate)
	susc = frappe.get_doc("Subscription", name)
	intervalo=int(susc.periodo_de_facturacion)
	try:
		data = frappe.db.sql(""" select 
						t1.item_group as Portafolio
						from `tabSubscription Plan` t1 inner join `tabSubscription Plan Detail` t2
						on t1.name = t2.plan
						inner join `tabSubscription` t3
						on t3.name = t2.parent 
						where t3.party = %(regnumber)s and t1.item_group like '%DIALUP%' limit 1;""", {'regnumber':susc.party})
		if data:
			if data[0]['Portafolio'] == 'DIALUP':
				if len(susc.get('correo')) == 0:
					frappe.msgprint("No hay correo registrado, debe de esperar que lo registren.")
		else:
			factura=Subscription.generate_invoice_Recurrente_B(susc,0)
			
			frappe.msgprint(frappe._('{0}').format(frappe.utils.get_link_to_form("Sales Invoice",factura )))		
	except:
		factura=Subscription.generate_invoice_Recurrente_B(susc,0)		
		frappe.msgprint(frappe._('{0}').format(frappe.utils.get_link_to_form("Sales Invoice",factura )))



def get_exchange_rate(from_currency, to_currency, date=None, alternative=True, throw=False):

		if from_currency == to_currency:
			return 1

		exchange1 = '{0}-{1} {2}'.format(
			from_currency, to_currency,
			date or today()
		)
		exchange2 = '{1}-{0} {2}'.format(
			from_currency, to_currency,
			date or today()
		)

		for (ex, divide) in ((exchange1, 0), (exchange2, 1)):
			# flt redondea
			# Daily Exchange Rate
			value = flt(frappe.db.get_value(
				'Currency Exchange',
				ex,
				# 'exchange_rate' if not alternative else 'alternative_exchange_rate'
				'exchange_rate' if not alternative else 'paralela'
			))
			if value:
				if divide:
					value = 1.0 / value
				break

		if not value:
			if not throw:
				frappe.msgprint(frappe._(
					"Unable to find exchange rate for {0} to {1} on {2}".format(
						from_currency, to_currency,
						date or today()
					)
				))
			else:
				# Demas
				frappe.msgprint(frappe._(
					"Unable to find exchange rate for {0} to {1} on {2}".format(
						from_currency, to_currency,
						date or today()
					)
				))
			return 0.0
		return value

@frappe.whitelist()
def reactivacion_plan(name, estado):
	from erpnext.crm.doctype.opportunity.opportunity import consultar_rol
	roles =  consultar_rol()
	if "Back Office" in roles or "Cobranza" in roles or "Departamentos" in roles or "SAC" in roles or "CSC" in roles:
	# if "Back Office" in roles or "Cobranza" in roles or "Departamentos" in roles:

		if estado == 'SUSPENDIDO: Manual' or estado == 'SUSPENDIDO: Temporal' or estado == 'Activo: Temporal' :
			if not frappe.db.sql(""" select so.workflow_state from `tabService Order` so
				inner join  `tabSO Detalle Clientes Suspendidos` sd on sd.parent=so.name
				where sd.subscription_plan_detail=%(name)s and so.workflow_state not in ('Cancelado','Finalizado')""",{"name": name}):
				#try:
				upd_spd = frappe.get_doc("Subscription Plan Detail", {"name": name})

				upd_sus = frappe.get_doc("Subscription", {"name": upd_spd.parent})

				portafolio=get_portafolio_plan(upd_spd.plan)
				portafolio = str(portafolio[0][0])

				# if portafolio not in ('IPTV'):#'ITV' SE QUITÓ PORQUE SE NECESITAN REGISTRAR LA REACTIVACION DE ESAS V.
				var = False
				status =''
				if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"REACTIVACION","nombre_de_origen":upd_sus.name,"plan_de_subscripcion":name}):
					so= frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"REACTIVACION","nombre_de_origen":upd_sus.name,"plan_de_subscripcion":name})
					if so.workflow_state=="Cancelado" or so.workflow_state=="Finalizado":
						status = "Pasa"
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
						'tipo_de_origen': "Subscription",
						'tipo_cliente': frappe.db.get_value('Customer', {"name": upd_sus.party}, 'customer_group'),
						'nombre': frappe.db.get_value('Customer', {"name": upd_sus.party}, 'customer_name'),
						'nombre_de_origen': upd_sus.name,
						'descripcion': frappe._('Ejecutar Reactivacion de {0}').format(name),
						'tipo': 'Customer',
						'tercero': upd_sus.party,
						'plan_de_subscripcion': name,
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
						if name==equipos.plan:
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
				else:
					frappe.msgprint("La orden no se pudo generar: La orden de reactivacion ya fue creada o existe una desinstalación en curso")

				# except Exception as e:
				# 	frappe.msgprint(frappe._('reactivacion_plan : Fatality Error Project {0} ').format(e))
			else:
				frappe.msgprint("Para reactivar necesita finalizar la orden de suspensión vinculado a este plan")
		else:
			frappe.msgprint("Se activa solo para planes suspendidos")
	else:
		frappe.msgprint("Necesita permiso de Back Office, CSC, Departamentos o Cobranza")
def randStr(chars = string.ascii_uppercase + string.digits, N=4):
	return ''.join(random.choice(chars) for _ in range(N))

@frappe.whitelist()
def traslado_de_plan(name, estado):
	try:
		if estado == 'Activo':
			spd = frappe.get_doc("Subscription Plan Detail", {"name": name})
			status = ''
			var = False
			if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"TRASLADO","plan_de_subscripcion":name}):
				so= frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"TRASLADO","plan_de_subscripcion":name})
				if so.workflow_state=="Cancelado":
					status = "Pasa"
				else:
					status = "No Pasa"
					frappe.msgprint(frappe._('Ya existe una orden de traslado para este plan con ID {0}').format(so.name))
			else:
				var = True

			if status=="Pasa" or var:
				if spd.estado_plan=="Activo":
					portafolio=get_portafolio_plan(spd.plan)
					direccion=frappe.get_doc("Address", spd.direccion)
					# frappe.msgprint("entra a la condicion del plan")
					od = frappe.get_doc({
						'doctype': "Service Order",
						'tipo_de_orden': "TRASLADO",
						'workflow_state': "Abierto",
						'tipo_de_origen': "Subscription",
						'nombre_de_origen': spd.parent,
						'descripcion': frappe._('Ejecutar traslado de {0}').format(spd.plan),
						'tipo': 'Customer',
						'tercero': frappe.db.get_value("Subscription",spd.parent,"party"),
						'nombre': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_name'),
						'tipo_cliente': frappe.db.get_value('Customer', {"name": doc.party}, 'customer_group'),
						'plan_de_subscripcion': name,
						'direccion_de_instalacion': spd.direccion,
						'portafolio': str(portafolio[0][0]),
						'departamento': direccion.departamento,
						'municipio': direccion.municipio,
						'barrio': direccion.barrio,
						'direccion': direccion.address_line1,
						'latitud':spd.latitud,
						'longitud':spd.longitud,
						'nodo':spd.nodo
					})
					od.insert()
					frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), frappe.utils.get_link_to_form("Service Order", od.name)))
					doc = frappe.get_doc("Subscription",spd.parent)
					for equipos in doc.equipos:
						ran = randStr(chars='abcdefghijklmnopqrstuvwxyz1234567890')
						ran = ran + equipos.name
						if name==equipos.plan:
							# frappe.msgprint("entra a la segunda condicion")
							code = frappe.db.get_value('Serial No', {"name": equipos.equipo}, 'item_code')
							frappe.db.sql(""" insert into `tabEquipo_Orden_Servicio` (name,serial_no,parent,parenttype,parentfield,item_code)
								values (%(name)s,%(serial_no)s,%(parent)s,'Service Order','equipo_orden_servicio',%(item_code)s) """, {"name":ran,"serial_no":equipos.equipo,"parent":od.name,"item_code":code})
				else:
					frappe.msgprint("No se pueden crear ordenes de trabajo para planes que no sean activos")
		else:
			frappe.msgprint("Solo se pueden hacer traslados para planes activos")
		return
	except Exception as e:
				frappe.msgprint(frappe._('Get Item : Fatality Error Project {0} ').format(e))


@frappe.whitelist()
def finalizacion_de_plan(plan,motivo):
	""" metodo para finalizar planes """
	try:
		plan_detail = frappe.get_doc("Subscription Plan Detail",plan)
		plan_detail.update(
				{
					"estado_plan": "Plan Cerrado",
					"motivo_finalizado": motivo,
					"service_end": now(),
					"detalle_finalizado": "Plan cerrado por " + motivo
				}
			)
		plan_detail.save()
		p_cerrados = 0
		p_Suspendidos=0
		activos = False

		susc = frappe.get_doc("Subscription",plan_detail.parent)
		for p in susc.plans:
			if p.estado_plan == "Plan Cerrado":
				p_cerrados += 1

			if p.estado_plan  in ('SUSPENDIDO: Manual','SUSPENDIDO: Temporal'):
				p_Suspendidos += 1
			 
			if p.estado_plan in ('Activo','Inactivo'):
				activos = True

		if p_cerrados == len(susc.plans):

			frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Terminado', docstatus=1 where name = %(name)s; """,{"name":susc.name})

		if p_Suspendidos > 0 and not activos :

			frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Suspendido', docstatus=0 where name = %(name)s; """,{"name":susc.name})


		if frappe.db.sql("""select count(*) from `tabSubscription` where party = %(party)s and workflow_state != 'Terminado' ;""", {"party": susc.party})[0][0] == 0:

			frappe.db.sql(""" update `tabCustomer` set estado_cliente = 'TERMINADO' where name = %(customer)s; """,{"customer":susc.party})
		if plan_detail.plan not in ('TV Combo GPON','TV Combo HFC'):
			if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": plan}):
				bitacora_plan = frappe.get_doc({
					'doctype': "Bitacora de Planes",
					'plan': plan_detail.plan,
					'cliente':  susc.party,
					'estado_plan': "Plan Cerrado",
					'direccion': plan_detail.direccion,
					'currency': plan_detail.currency,
					'costo':plan_detail.cost,
					'intervalo_de_facturacion':plan_detail.billing_interval_count,
					'subscription_plan_detail': plan_detail.name

				})
				bitacora_plan.insert()

			bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": plan})

			bitacora_detalle = frappe.get_doc({
				"doctype": "Detalle Bitacora Planes",
				"detalle":"Plan cerrado por " + motivo,
				"fecha": now(),
				"usuario":frappe.session.user,
				"parent": bitacora_plan.name,
				"parentfield":"detalle",
				"parenttype": "Bitacora de Planes",
				"tipo_transaccion":"Subscription",
				"tercero": susc.name
				})
			bitacora_detalle.insert()
	except Exception as e:
				frappe.msgprint(frappe._('Get Item : Fatality Error Project {0} ').format(e))

@frappe.whitelist()
def fecha_de_finalizacion(name):
	sub = frappe.get_doc("Subscription",name)
	end_date = add_months(sub.start_date, int(sub.duracion_de_contrato))
	frappe.db.sql(""" update `tabSubscription` set end_date = %(end_date)s where name = %(name)s;""",{"end_date":end_date,"name":name})

@frappe.whitelist()
def aplicar_promocion(promo,name):
	try:
		campana = frappe.get_doc("promotions campaign",promo)
		frappe.db.set_value("Subscription",name,"campana",promo)
		descuento = int(campana.porcentaje_de_mrc_en_promo)
	except:
		campana = None
		descuento = 0
		frappe.db.set_value("Subscription",name,"campana",'')

	subscription = frappe.get_doc("Subscription",name)
	
	for plan in subscription.plans:		

		if len(subscription.plans)!=1 and "ITV" in frappe.db.get_value("Subscription Plan",plan.plan,"item") or "IPTV" in frappe.db.get_value("Subscription Plan",plan.plan,"item") or "DIALUP" in frappe.db.get_value("Subscription Plan",plan.plan,"item") or "GPON-TV" in frappe.db.get_value("Subscription Plan",plan.plan,"item"):
			continue
		else:
			if descuento > 0:
				if frappe.db.get_value("Subscription Plan",plan.plan,"cost") == plan.cost:
					if plan.es_combo:
						frappe.db.set_value("Subscription Plan Detail",plan.name,"cost",((plan.cost + 5)-((plan.cost + 5)*descuento)/100) - 5)
					else:
						frappe.db.set_value("Subscription Plan Detail",plan.name,"cost",plan.cost-(plan.cost*descuento)/100)
			else:
				frappe.db.set_value("Subscription Plan Detail",plan.name,"cost",frappe.db.get_value("Subscription Plan",plan.plan,"cost"))

			if not frappe.db.exists("Bitacora de Planes", {"name": plan.name}):
				# bitacora_plan = frappe.get_doc({
				# 	'doctype': "Bitacora de Planes",
				# 	'plan': plan.plan,
				# 	'cliente':  subscription.party,
				# 	'estado_plan': plan.estado_plan,
				# 	'direccion': plan.direccion,
				# 	'currency': plan.currency,
				# 	'costo':frappe.db.get_value("Subscription Plan Detail",plan.name,"cost"),
				# 	'intervalo_de_facturacion':plan.billing_interval_count,
				# 	'subscription_plan_detail': plan.name,
				# 	'nodo': plan.nodo,
				# 	'campana':promo
				# })
				# bitacora_plan.insert()
				frappe.db.sql(""" insert into `tabBitacora de Planes`
								(name,plan,cliente,estado_plan,direccion,currency,costo,intervalo_de_facturacion,subscription_plan_detail,nodo,campana) values
								(%(name)s, %(plan)s,%(cliente)s,%(estado_plan)s,%(direccion)s,%(currency)s,%(costo)s,%(intervalo)s,
								%(subscription_plan_detail)s,%(nodo)s,%(campana)s)""",{"name":plan.name,"plan":plan.plan,"cliente":subscription.party,"estado_plan":plan.estado_plan,
								"direccion":plan.direccion,"currency":plan.currency,"costo":frappe.db.get_value("Subscription Plan Detail",plan.name,"cost"),"intervalo":plan.billing_interval_count,
								"subscription_plan_detail":plan.name,"nodo":plan.nodo,"campana":campana.name})	
			else:
				frappe.db.set_value("Bitacora de Planes",plan.name,"costo",frappe.db.get_value("Subscription Plan Detail",plan.name,"cost"))
				frappe.db.set_value("Bitacora de Planes", plan.name, "campana",promo)
				if campana:
					frappe.db.sql(""" update `tabBitacora de Planes` set costo = %(costo)s, campana = %(campana)s where name = %(name)s;""",
					{"costo":frappe.db.get_value("Subscription Plan Detail",plan.name,"cost"), "campana":campana.name, "name":plan.name})

@frappe.whitelist()
def get_work_orders(name):
	condicion = "%os%"
	ordenes = frappe.db.sql(""" select * from `vw_ordenes_de_trabajo` where plan in (select name from `tabSubscription Plan Detail` where parent=%(name)s) and orden like %(condicion)s order by fecha_solicitud desc; """, {"name":name, "condicion":condicion})
	return ordenes
	
@frappe.whitelist()
def gestion_generar_factura(costo,gestion):
	g = frappe.get_doc("Gestion", gestion)
	subgestion = g.subgestion
	plan = frappe.db.get_value("Service Order",{"nombre_de_origen":gestion},'plan_de_subscripcion')
	spd = frappe.get_doc("Subscription Plan Detail",plan)
	susc = frappe.get_doc("Subscription", spd.parent)
	factura=Subscription.generate_invoice_otc(susc,spd.plan,costo,subgestion, spd.name)
	frappe.db.set_value("Gestion",gestion,"facturado",0)
	frappe.db.sql("update `tabGestion` set workflow_state = 'Finalizado', estado = 'Finalizado' where name = %(gestion)s;",{"gestion":gestion})

	frappe.msgprint(frappe._('Factura B de {0} creada: {1} ').format(subgestion,frappe.utils.get_link_to_form("Sales Invoice", factura)))

@frappe.whitelist()
def activar_temporalmente(name,estado,cliente):
	from erpnext.crm.doctype.opportunity.opportunity import consultar_rol
	roles =  consultar_rol()
	if "NOC" in roles or "CSC" in roles:
		plan_detail = frappe.get_doc("Subscription Plan Detail",name)
		if estado in ('SUSPENDIDO: Manual','SUSPENDIDO: Temporal'):
			frappe.db.set_value("Subscription Plan Detail",name,"estado_plan","Activo: Temporal")
			frappe.db.set_value("Subscription Plan Detail",name,"activacion_temporal", now())

			if not frappe.db.exists("Bitacora de Planes", {"name": name}):
					bitacora_plan = frappe.get_doc({
						'doctype': "Bitacora de Planes",
						'plan': plan_detail.plan,
						'cliente':  cliente,
						'estado_plan': "Activo: Temporal",
						'direccion': plan_detail.direccion,
						'currency': plan_detail.currency,
						'costo':plan_detail.cost,
						'intervalo_de_facturacion':plan_detail.billing_interval_count,
						'subscription_plan_detail': plan_detail.name
					})
					bitacora_plan.insert()				
			else:
				frappe.db.set_value("Bitacora de Planes",name,"estado_plan","Activo: Temporal")
			bitacora_detalle = frappe.get_doc({
					"doctype": "Detalle Bitacora Planes",
					"detalle":"Activo: Temporal",
					"fecha": now(),
					"usuario":frappe.session.user,
					"parent": name,
					"parentfield":"detalle",
					"parenttype": "Bitacora de Planes",
					"tipo_transaccion":"",
					"tercero": ""
					})
			bitacora_detalle.insert()
		else:
			frappe.msgprint("Solo se puede reactivar temporalmente a planes suspendidos")
	else:
		frappe.msgprint("Permitido solo para NOC y CSC")

def suspender_clientes_activos_temporales():
	planes = frappe.db.sql(""" select name from `tabSubscription Plan Detail` 
	where estado_plan='Activo: Temporal' and TIMESTAMPDIFF(HOUR, activacion_temporal,now())>=48; """)

	for plan in planes:
		plan_detail = frappe.get_doc("Subscription Plan Detail",plan[0])
		cliente = frappe.db.get_value("Subscrtiption",plan_detail.parent,"party")
		if not frappe.db.exists("Bitacora de Planes", {"name": name}):
				bitacora_plan = frappe.get_doc({
					'doctype': "Bitacora de Planes",
					'plan': plan_detail.plan,
					'cliente':  cliente,
					'estado_plan': "SUSPENDIDO: Manual",
					'direccion': plan_detail.direccion,
					'currency': plan_detail.currency,
					'costo':plan_detail.cost,
					'intervalo_de_facturacion':plan_detail.billing_interval_count,
					'subscription_plan_detail': plan_detail.name
				})
				bitacora_plan.insert()				
		else:
			frappe.db.set_value("Bitacora de Planes",name,"estado_plan","SUSPENDIDO: Manual")
		bitacora_detalle = frappe.get_doc({
				"doctype": "Detalle Bitacora Planes",
				"detalle":"SUSPENDIDO: Manual",
				"fecha": now(),
				#"usuario":frappe.session.user,
				"parent": plan_detail.name,
				"parentfield":"detalle",
				"parenttype": "Bitacora de Planes",
				"tipo_transaccion":"",
				"tercero": ""
				})
		bitacora_detalle.insert()

	frappe.db.sql("""  update   estado_plan  set='SUSPENDIDO: Manual'    from `tabSubscription Plan Detail`
	 where estado_plan='Activo: Temporal' and TIMESTAMPDIFF(HOUR, activacion_temporal,now())>=48;  """)