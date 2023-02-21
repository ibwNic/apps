# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
#ultima modificacion: 23/01/2023 16:09

import random
import string
import frappe
from frappe import _
from frappe.model.document import Document
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


	def generate_invoice_tv_add(self,plan):
		try:
			doctype = "Sales Invoice"
			invoice = self.create_invoice_tv_add(plan)
			self.append("invoices", {"document_type": doctype, "invoice": invoice.name})
			self.save()
		except Exception as e:
			frappe.msgprint(frappe._('generate_invoice_tv_add : Fatality Error Project {0} ').format(e))

	def generate_invoice(self, prorate=0):
		"""
		Creates a `Invoice` for the `Subscription`, updates `self.invoices` and
		saves the `Subscription`.
		"""
		try:

			doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
			
			invoice = self.create_invoice(prorate)
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


	def create_invoice_tv_add(self,plan):
		try:
			
			doctype = "Sales Invoice"
			invoice = frappe.new_doc(doctype)
			invoice.naming_series = "B-"
			invoice.tipo_factura="TV Adicional"
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


			## Add dimensions in invoice for subscription:
			accounting_dimensions = get_accounting_dimensions()

			for dimension in accounting_dimensions:
				if self.get(dimension):
					invoice.update({dimension: self.get(dimension)})

			# Subscription is better suited for service items. I won't update `update_stock`
			# for that reason
			# items_list = self.get_items_from_plans(self.plans, invoice.currency,paralela,prorate)
			
			if invoice.currency=="NIO":
				items_list = {
				"item_code": 'TV Adicional GPON' if 'GPON' in plan else 'TV Adicional HFC' ,
				"qty": 1,
				"rate": (5)*float(paralela),
				"cost_center": '',
				"plan_detail":plan,
				}

			else:
				items_list = {
					"item_code": 'TV Adicional GPON' if 'GPON' in plan else 'TV Adicional HFC',
					"qty": 1,
					"rate":5,
					"cost_center": '',
					"plan_detail":plan,
				}
			

			items_list["cost_center"] = self.cost_center
			invoice.append("items", items_list)

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
			invoice.submit()
			# if self.submit_invoice:
			# 	invoice.submit()
			return invoice
		except Exception as e:
			frappe.msgprint(frappe._('generate_invoice tv : Fatality Error Project {0} ').format(e))

	def create_invoice(self, prorate):
		try:
			"""
			Creates a `Invoice`, submits it and returns it
			"""
			doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"

			invoice = frappe.new_doc(doctype)
			invoice.naming_series = "B-"
			invoice.tipo_factura="Prorrateo"
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
			paralela =get_exchange_rate('USD','NIO', today(), throw=True)
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
			invoice.submit()
			# if self.submit_invoice:
			# 	invoice.submit()

			return invoice
		except Exception as e:
			frappe.msgprint(frappe._('create_invoice : Fatality Error Project {0} ').format(e))


	def get_items_from_plans(self, plans,currency_invoice,paralela,prorate=0):
		"""
		Returns the `Item`s linked to `Subscription Plan`
		"""
		
		if prorate:
			prorate_factor = get_prorata_factor(
				self.current_invoice_end, self.current_invoice_start, self.generate_invoice_at_period_start
			)
			# frappe.msgprint(str(self.current_invoice_start))
			# frappe.msgprint(str(self.current_invoice_end))
			# return
		
		items = []
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
							# frappe.msgprint(str(paralela))
							# return
						else:
							item = {
								"item_code": item_code,
								"qty": plan.qty,
								"rate":get_plan_rate_NEW(plan.cost,
										plan.qty,
										party,
										self.current_invoice_start,
										self.current_invoice_end,
										prorate_factor,
									),
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
	try:
		doc = frappe.get_doc("Subscription", name)
		if doc.campana == 'Referido' and not doc.referido_por:
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
				if not frappe.db.exists("Subscription Plan Detail", {"parent": name,"plan":["in",["TV Combo GPON","TV Combo HFC"]]}):
					frappe.msgprint(f"Hace falta agregar plan TV para el combo {plan.plan}")
					return
			if plan.plan == 'TV Combo GPON' or plan.plan == 'TV Combo HFC':
				tv += 1
				if plan.plan == 'TV Combo GPON':
					tv_gpon +=1
				elif plan.plan == 'TV Combo HFC':
					tv_hfc +=1
		
		if tv == combos and hfc == tv_hfc and gpon == tv_gpon:
			for plan in doc.get('plans'):
				if plan.plan == 'TV Combo GPON' or plan.plan == 'TV Combo HFC':
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
					if plan.estado_plan!="Activo":

						portafolio=get_portafolio_plan(plan.plan)
						direccion=frappe.get_doc("Address", plan.direccion)

						od = frappe.get_doc({
							'doctype': "Service Order",
							'tipo_de_orden': "INSTALACION",
							'workflow_state': "Abierto",
							'tipo_de_origen': doc.doctype,
							'nombre_de_origen': doc.name,
							'descripcion': frappe._('Ejecutar instalacion de {0}').format(plan.plan),
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
							'longitud':plan.longitud
						})
						od.insert()
						frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
					else:
						frappe.msgprint("No se pueden crear ordenes de trabajo para planes activos")
		else:
			frappe.msgprint("Debe agregar un plan de TV correspondiente a cada combo")
			return 
	except Exception as e:
		frappe.msgprint(frappe._('Get Item : Fatality Error Project {0} ').format(e))

@frappe.whitelist()
def crear_orden_Desinstalacion(name):
	try:
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
						'longitud':plan.longitud
					})
					od.insert()
					frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))

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
							eos.insert()
				else:
					frappe.msgprint("No se pueden crear ordenes de trabajo para planes activos")
	except Exception as e:
				frappe.msgprint(frappe._('Get Item : Fatality Error Project {0} ').format(e))



def get_portafolio_plan(plan):
	portafolio = frappe.db.sql(
	"""Select t1.item_group
	from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item where t2.name=%(plan)s limit 1 """,
	{"plan": plan},)
	return portafolio

def get_equipo_plan(plan):
	portafolio = frappe.db.sql(
	"""Select t1.item_group
	from  `tabItem` t1 inner join `tabSubscription Plan` t2  on t1.name=t2.item where t2.name=%(plan)s limit 1 """,
	{"plan": plan},)
	return portafolio


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
def filtrar_planes(lista_de_planes):
	planes = frappe.db.sql(""" select t1.name from `tabSubscription Plan` t1
		where t1.activo = 1 and t1.tipo_de_plan = %(lista_de_planes)s and t1.tarifa_ibw=1 """,{"lista_de_planes":lista_de_planes})
	lista =[plan[0] for plan in planes]
	return lista


@frappe.whitelist()
def process_de_Facturacion(name):
	
	susc = frappe.get_doc("Subscription", name)

	if  frappe.db.exists("promotions campaign", {"name": susc.campana}):

		promo = frappe.get_doc("promotions campaign", susc.campana)

		if promo.promo_primera_factura_gratis:

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
		item_group = frappe.db.get_value("Subscription Plan",plan.plan,"item_group")
		if item_group in ['GPON','GPON-CORPORATIVO','GPON-INT-PYME','GPON-INT-RESIDENCIAL','GPON-TV-CORPORATIVO','GPON-TV-PYME','GPON-TV-RESIDENCIAL','HFC', 'HFC 3.0', 'IMOVIL', 'INET', 'Wimax','LTE', 'LTE Productos']:
			if not frappe.db.exists("Subscription Plan Equipos", {"plan": plan.name,"parent":name}) and plan.plan!="TV Combo HFC" and plan.plan != "TV Combo GPON":
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
	frappe.msgprint(frappe._('Factura B : {0} ').format(factura))


# @frappe.whitelist
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
	if estado == 'SUSPENDIDO: Manual' or estado == 'SUSPENDIDO: Temporal':
		if not frappe.db.sql(""" select so.workflow_state from `tabService Order` so
			inner join  `tabSO Detalle Clientes Suspendidos` sd on sd.parent=so.name
			where sd.subscription_plan_detail=%(name)s and so.workflow_state<>'Finalizado'""",{"name": name}):
			try:
				upd_spd = frappe.get_doc("Subscription Plan Detail", {"name": name})
		
				upd_sus = frappe.get_doc("Subscription", {"name": upd_spd.parent})

				portafolio=get_portafolio_plan(upd_spd.plan)
				portafolio = str(portafolio[0][0])

				if portafolio not in ('IPTV','ITV'):
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
						frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))

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
						frappe.msgprint("No se pueden crear ordenes de trabajo para planes activos")	
			
			except Exception as e:
				frappe.msgprint(frappe._('Get Item : Fatality Error Project {0} ').format(e))
		else:
			frappe.msgprint("Para reactivar necesita finalizar la orden de suspensión vinculado a este plan")	
	else:
		frappe.msgprint("Se activa solo para planes suspendidos")

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
					frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
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
					"service_end": now()
				}
			)
		plan_detail.save()
		p_cerrados = 0
		susc = frappe.get_doc("Subscription",plan_detail.parent)
		for p in susc.plans:
			if p.estado_plan not in ('Activo','Inactivo'):
				p_cerrados += 1
		
		if p_cerrados == len(susc.plans):
		
			frappe.db.sql(""" update `tabSubscription` set workflow_state = 'Terminado', docstatus=1 where name = %(name)s; """,{"name":susc.name})
			
		
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
		descuento = 0
		frappe.db.set_value("Subscription",name,"campana",'')

	subscription = frappe.get_doc("Subscription",name)
	for plan in subscription.plans:
		if "ITV" in frappe.db.get_value("Subscription Plan",plan.plan,"item") or "IPTV" in frappe.db.get_value("Subscription Plan",plan.plan,"item") or "DIALUP" in frappe.db.get_value("Subscription Plan",plan.plan,"item") or "GPON-TV" in frappe.db.get_value("Subscription Plan",plan.plan,"item"):
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

@frappe.whitelist()
def tv_adicional(name):
	plan = frappe.get_doc("Subscription Plan Detail",name)
	if(plan.plan in ("TV Combo GPON","TV Combo HFC","Servicio TV HFC")):
		subs = frappe.get_doc("Subscription", {"name": plan.parent})
		portafolio=get_portafolio_plan(plan.plan)
		portafolio = str(portafolio[0][0])	
		var = False
		status =''
		if frappe.db.exists("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"INSTALACION OTC","nombre_de_origen":subs.name,"plan_de_subscripcion":name}):
			so= frappe.get_doc("Service Order", {"tipo_de_origen": "Subscription","tipo_de_orden":"INSTALACION OTC","nombre_de_origen":subs.name,"plan_de_subscripcion":name})
			if so.workflow_state=="Cancelado" or so.workflow_state=="Finalizado":
				status = "Pasa"
			else:
				status = "No Pasa"
		else:
			var = True
		if status=="Pasa" or var:		
			direccion=frappe.get_doc("Address", plan.direccion)
			od = frappe.get_doc({
				'doctype': "Service Order",
				'tipo_de_orden': "INSTALACION OTC",
				'workflow_state': "Abierto",
				'tipo_de_origen': "Subscription",
				'nombre_de_origen': subs.name,
				'descripcion': frappe._('Ejecutar instalación de TV ADICIONAL'),
				'tipo': 'Customer',
				'tercero': subs.party,
				'plan_de_subscripcion': name,
				'direccion_de_instalacion': plan.direccion,
				'portafolio': portafolio,
				'departamento': direccion.departamento,
				'municipio': direccion.municipio,
				'barrio': direccion.barrio,
				'direccion': direccion.address_line1,
				'latitud':plan.latitud,
				'longitud':plan.longitud,
				'nodo':plan.nodo
			})
			od.insert()
			frappe.msgprint(frappe._('Nueva orden de {0} con ID {1}').format(frappe._(od.tipo_de_orden), od.name))
		else:
			frappe.msgprint("Ya existe una orden de instalacion de tv adicional para este contrato")

@frappe.whitelist()
def factura_tv_adicional(name):
	try:
		plan = frappe.get_doc("Subscription Plan Detail",name)	
		susc = frappe.get_doc("Subscription", plan.parent)
		if(plan.plan in ("TV Combo GPON","TV Combo HFC","Servicio TV HFC")):
			factura=Subscription.generate_invoice_tv_add(susc,plan.plan)
			frappe.msgprint(frappe._('Factura B : {0} ').format(factura))

			
	except Exception as e:
		frappe.msgprint(frappe._('factura_tv_adicional : Fatality Error Project {0} ').format(e))