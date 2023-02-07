# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from warnings import catch_warnings
import base64
import frappe
# import threading
import time
from frappe.model.document import Document
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

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.party import get_party_account_currency
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate



class Facturacion(Document):
	pass

def create_invoice(self, customer, prorate):
	try:	
		"""
		Creates a `Invoice`, submits it and returns it
		"""
		doctype = "Sales Invoice" 

		invoice = frappe.new_doc(doctype)
		invoice.naming_series = "A-"
		# For backward compatibility
		# Earlier subscription didn't had any company field
		company = "IBW-NI"

		invoice.company = company
		invoice.set_posting_time = 1
		invoice.tipo_factura="Recurrente"
		invoice.posting_date =self.current_invoice_start
		# invoice.posting_date = (
		# 	self.current_invoice_start
		# 	if self.generate_invoice_at_period_start
		# 	else self.current_invoice_end
		# )
		invoice.cost_center = "Principal - NI"

		# invoice.customer = customer.cliente	
		invoice.customer = customer

		### Add party currency to invoice
		# invoice.currency = get_party_account_currency("Customer", customer.cliente, company)
		invoice.currency = get_party_account_currency("Customer", customer, company)
		if invoice.currency == "USD":
			invoice.conversion_rate=self.paralela
		else:
			invoice.conversion_rate=1
		# invoice.currency = "USD"
		## Add dimensions in invoice for subscription:
		# accounting_dimensions = get_accounting_dimensions()

		# for dimension in accounting_dimensions:
		# 	if self.get(dimension):
		# 		invoice.update({dimension: self.get(dimension)})

		# Subscription is better suited for service items. I won't update `update_stock`
		# for that reason		
		# items_list = get_items_from_customer(self,customer.cliente, invoice.currency,prorate)
		items_list = get_items_from_customer(self,customer, invoice.currency,prorate)
		for item in items_list:
			item["cost_center"] = "Principal - NI"
			invoice.append("items", item)

		# Taxes
		# tax_template = "Nicaragua Tax - NI"
		
		tax_template = frappe.db.get_value("Customer", {"name": customer}, "sales_tax_template")
		# tax_template = ""
		# if doctype == "Sales Invoice" and self.sales_tax_template:
		# 	tax_template = self.sales_tax_template
		# if doctype == "Purchase Invoice" and self.purchase_tax_template:
		# 	tax_template = self.purchase_tax_template

		if tax_template !="":
			invoice.taxes_and_charges = tax_template
			invoice.set_taxes()

	

		# Due date
		# if self.days_until_due:
		# 	invoice.append(
		# 		"payment_schedule",
		# 		{
		# 			"due_date": add_days(invoice.posting_date, cint(20)),
		# 			"invoice_portion": 100,
		# 		},
		# 	)
		invoice.append(
			"payment_schedule",
			{
				"due_date": add_days(invoice.posting_date, cint(20)),
				"invoice_portion": 100,
			},)
			

		# Discounts
		invoice.additional_discount_percentage = 0
		invoice.discount_amount = 0
		invoice.apply_discount_on = "Grand Total"

		# if self.is_trialling():
		# 	invoice.additional_discount_percentage = 100
		# else:
		# 	if self.additional_discount_percentage:
		# 		invoice.additional_discount_percentage = self.additional_discount_percentage

		# 	if self.additional_discount_amount:
		# 		invoice.discount_amount = self.additional_discount_amount

		# 	if self.additional_discount_percentage or self.additional_discount_amount:
		# 		discount_on = self.apply_additional_discount
		# 		invoice.apply_discount_on = discount_on if discount_on else "Grand Total"

		# Subscription period
		invoice.from_date = self.current_invoice_start
		invoice.to_date = self.current_invoice_end

		invoice.flags.ignore_mandatory = True

		invoice.set_missing_values()
		invoice.save()
		
		invoice.submit()


		return invoice

	except Exception as e:
			frappe.msgprint(frappe._('Create Invoice : Error Project {0} ').format(e))
			frappe.msgprint(frappe._('Create Invoice : Error Project {0} ').format(customer))

def get_items_from_customer(self,customer, currency_invoice,prorate=0):
	try:
		# frappe.msgprint("hola")
		"""
		Returns the `Item`s linked to `Subscription Plan`
		"""
		if prorate:
			prorate_factor = get_prorata_factor(
				self.current_invoice_end, self.current_invoice_start, 1
			)

		items = []
		party = customer

		plans = []

		# en las pruebas se esta usando el "current_invoice_end" pero en produccion hay que usar el "current_invoice_start"
		plans = frappe.db.sql(
		"""select t2.plan,t2.qty,t4.currency,t2.cost,t3.periodo_de_facturacion,t2.name from   `tabSubscription Plan Detail` t2
			inner join `tabSubscription`  t3 on  t2.parent =t3.name 
			inner join `tabSubscription Plan` t4 on t4.name= t2.plan  
			where t3.party=%(party)s and t3.current_invoice_start=%(cis)s and t2.estado_plan='Activo' and t4.cost>0""",
		{"party": customer , "cis":self.current_invoice_start},
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
			# if self.party == "Customer":
			# 	deferred_field = "enable_deferred_revenue"
			# else:
			# 	deferred_field = "enable_deferred_expense"

			deferred = frappe.db.get_value("Item", item_code, deferred_field)

			# frappe.msgprint(frappe._('plan[0] {0} ').format(plan[0]))
			# frappe.msgprint(frappe._('plan[1] {0} ').format(plan[1]))
			# frappe.msgprint(frappe._('plan[2] {0} ').format(plan[2]))
			# frappe.msgprint(frappe._('plan[3] {0} ').format(plan[3]))
			# frappe.msgprint(frappe._('plan[4]) {0} ').format(plan[4]))

			if currency_invoice=="NIO":
				
				if plan[2]=="USD":
					item = {
						"item_code": item_code,
						"qty": plan[1],
						"rate":float(plan[3])*float(self.paralela)*float(plan[4]),
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
					item = {
						"item_code": item_code,
						"qty": plan[1],
						"rate":(float(plan[3])/float(self.paralela))*float(plan[4]),
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

	except Exception as e:
			frappe.msgprint(frappe._('Get Item : Fatality Error Project {0} ').format(e))


		# if not prorate:
		# 	item = {
		# 		"item_code": item_code,
		# 		"qty": plan[1],
		# 		"rate":plan[3],
		# 		# "rate": get_plan_rate(
		# 		# 	plan[0], plan[1], party, self.current_invoice_start, self.current_invoice_end
		# 		# ),
		# 		"cost_center": plan_doc.cost_center,
		# 	}
		# else:
		# 	item = {
		# 		"item_code": item_code,
		# 		"qty": plan[1],
		# 		"rate": get_plan_rate(
		# 			plan[0],
		# 			plan[1],
		# 			party,
		# 			self.current_invoice_start,
		# 			self.current_invoice_end,
		# 			prorate_factor,
		# 		),
		# 		"cost_center": plan_doc.cost_center,
		# 	}



def get_prorata_factor(period_end, period_start, is_prepaid):
	if is_prepaid:
		prorate_factor = 1
	else:
		diff = flt(date_diff(nowdate(), period_start) + 1)
		plan_days = flt(date_diff(period_end, period_start) + 1)
		prorate_factor = diff / plan_days

	return prorate_factor


def update_suscription(customer, period_start):
	try:
		suscriptions = []

		suscriptions = frappe.db.sql(
		"""select t3.name from  `tabSubscription Plan Detail` t2
			inner join `tabSubscription`  t3 on  t2.parent =t3.name   
			where t3.party=%(party)s and t3.current_invoice_start=%(cis)s and t2.estado_plan='Activo'""",
		{"party": customer, "cis":period_start},
		)

			
		# i=add_days(period_start, 1)
			# frappe.msgprint(frappe._('intervalo {0} ').format(intervalo))	


		for suscription in suscriptions:	
			# frappe.msgprint(frappe._(suscription[0]))				

			
			upd_suscrip = frappe.get_doc("Subscription", {"name": suscription[0]})	

			intervalo=int(upd_suscrip.periodo_de_facturacion)
			if intervalo>1:
				i=add_days(upd_suscrip.current_invoice_end, 1)
				# i=add_months(i,intervalo- 1)
				p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")
				p = add_months(p, intervalo-1)	
			else:
				i=add_months(upd_suscrip.current_invoice_start,intervalo)
				p = formatdate(frappe.utils.get_last_day(i), "yyyy-MM-dd")
				# p = add_months(p, intervalo)	
			
			

				

			upd_suscrip.update(
				{
					"current_invoice_start": i,
					"current_invoice_end":p
				}
			)
			upd_suscrip.save()
			frappe.db.commit()
	except Exception as e:
		frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))				

def update_rutas(name):
		Rutas = frappe.db.sql(
		""" select t1.nombre,(select count(cliente) from `tabDetalle Ciclo Facturacion` where ruta=t1.name and parent=%(t5)s ) as conteo from `tabRutas de Facturacion` t1 order by t1.nombre limit 15000""",		
				{"t5": name},
		)
		fact2 = frappe.get_doc("Facturacion", name)

		for ruta in Rutas:
	
			child2 = frappe.new_doc("Detalle Ciclo Facturacion Rutas")
			child2.update(
				{
					"ruta": ruta[0],
					"cantidad_de_clientes": ruta[1],
					"parentfield": "detalle_ciclo_facturacion_rutas",
					"parenttype": "Facturacion",
				}
			)
			fact2.detalle_ciclo_facturacion_rutas.append(child2)	
		fact2.save()



@frappe.whitelist()
def process_de_Facturacion(name):
	# frappe.msgprint(name)
	fact = frappe.get_doc("Facturacion", name)
	
	Customers_f = frappe.db.sql(
	"""select cliente from	`tabDetalle Ciclo Facturacion`  where parent=%(pt)s and sales_invoice is  null  limit 150000""",
	{"pt": name},
	)
	
	# for customer in fact.clientes: 
	# 	if customer.sales_invoice is None:
	# 		factura=create_invoice(fact,customer,0)
	for cliente in Customers_f: 
		# if customer.sales_invoice is None:
			factura=create_invoice(fact,cliente[0],0)
			time.sleep(1)	
			# frappe.msgprint(cliente[0])	
			try:
				update_suscription(cliente[0],fact.current_invoice_start)
				
				# upd_fac = frappe.get_doc("Detalle Ciclo Facturacion", {"cliente": customer.cliente ,"parent" :name})	
				upd_fac = frappe.get_doc("Detalle Ciclo Facturacion", {"cliente": cliente[0] ,"parent" :name})	
				upd_fac.update(
					{
					"sales_invoice": factura.name,
					"moneda":factura.currency,
					"monto":factura.grand_total
					}
				)
				upd_fac.save()
			except Exception as e:
				frappe.msgprint(frappe._('Fatality Error Project Principal {0} ').format(e))				
		# else:	
		#  	frappe.msgprint(frappe._("Listo"))

@frappe.whitelist()
def process_de_Vistaprevia(name):
	fact = frappe.get_doc("Facturacion", name)

	

	Clientes = frappe.db.sql(
	"""select distinct t3.party from `tabSubscription Plan` t1 
	inner join `tabSubscription Plan Detail`  t2 on  t1.name = t2.plan
	inner join `tabSubscription`  t3 on  t2.parent =t3.name  
	where t2.estado_plan='Activo' and t3.current_invoice_start =%(cis)s and t1.cost>0 limit 20000""",
	{"cis": fact.current_invoice_start},
	)

	try:
		# frappe.msgprint("try")	
		for client in Clientes:
			
			child = frappe.new_doc("Detalle Ciclo Facturacion")
			child.update(
				{
					"cliente": client[0],
					"parentfield": "clientes",
					"parenttype": "Facturacion",
					"marck": 0,

				}
			)
			fact.clientes.append(child)	
		fact.save()
		

		try:
			tabEcoF = frappe.db.sql(
			"""select t1.name, t1.cliente from `tabDetalle Ciclo Facturacion` t1 inner join `tabCustomer` t2 on  
			t1.cliente=t2.name where  t2.eco_factura=1 and t1.parent=%(parent)s and t1.marck=0 limit 50000""",
			{"parent": name},
			)

			for client in tabEcoF:	
							
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"name": client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"EcoFactura"
					}
				)
				upd_child.save()
		except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))	

		try:			
			
			tabAP = frappe.db.sql(
			"""select  name from `vw_ruta_apartado_postal` where parent=%(t5)s limit 50000""",
			{"t5": name},
			)

			for client in tabAP:				
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"name": name})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES APARTADO POSTAL"
					}
				)
				upd_child.save()
		except Exception as e:
			frappe.msgprint(frappe._('Fatality en apartado postal {0} ').format(e))				

		try:
			tabDCF = frappe.db.sql(
			"""select t1.name, t1.cliente from `tabDetalle Ciclo Facturacion` t1 inner join `tabCustomer` t2 on  
			t1.cliente=t2.name where t2.customer_type in ("Company","Pyme") and t2.eco_factura=0 and t1.parent=%(parent)s and t1.marck=0 limit 50000""",
			{"parent": name},
			)

			for client in tabDCF:				
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"name": client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES NET"
					}
				)
				upd_child.save()
		except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))				


		tabLeon = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory = 'Leon' 
				and t1.eco_factura=0  and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabLeon:
			upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
			upd_child.update(
				{
					"marck": 1,
					"ruta":"CLIENTES LEON"
				}
			)
			upd_child.save()

		tabCarazo = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='Carazo' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabCarazo:
			upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
			upd_child.update(
				{
					"marck": 1,
					"ruta":"CLIENTES CARAZO"
				}
			)
			upd_child.save()	


		tabRivas = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='Rivas' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabRivas:
			upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
			upd_child.update(
				{
					"marck": 1,
					"ruta":"CLIENTES RIVAS"
				}
			)
			upd_child.save()
			

		tabChinandega = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='Chinandega' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabChinandega:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES CHINANDEGA"
					}
				)
				upd_child.save()
				

		tabGranada = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='Granada' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabGranada:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES GRANADA"
					}
				)
				upd_child.save()
								

		tabEsteli = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='Esteli' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabEsteli:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES ESTELI"
					}
				)
				upd_child.save()
				

		tabJUIGALPA = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where( t1.territory ='Juigalpa' or t1.municipio='Juigalpa')
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabJUIGALPA:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES JUIGALPA"
					}
				)
				upd_child.save()
				

		tabMASAYA = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='Masaya' 
			and t1.eco_factura=0 and  t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabMASAYA:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES MASAYA"
					}
				)
				upd_child.save()

		tabJinotega = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory = 'Jinotega' 
			and t1.eco_factura=0 and  t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabJinotega:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES JINOTEGA"
					}
				)
				upd_child.save()				
				

		tabMATAGALPA = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='Matagalpa' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabMATAGALPA:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES MATAGALPA"
					}
				)
				upd_child.save()
					

		tabRAAN = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='RAAN' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabRAAN:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES RAAN"
					}
				)
				upd_child.save()
				

		tabRAAS = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='RAAS' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabRAAS:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES RAAS"
					}
				)
				upd_child.save()
				

		tabTipitapa = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where (t1.territory ='Tipitapa' or t1.municipio='Tipitapa')
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTipitapa:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES TIPITAPA"
					}
				)
				upd_child.save()
				
		tabNS = frappe.db.sql(
		"""select  distinct t1.name from `tabCustomer` t1 
				inner join `tabDetalle Ciclo Facturacion` t5 on t1.name=t5.cliente
				where t1.territory ='NUEVA SEGOVIA' 
			and t1.eco_factura=0 and t5.parent=%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabNS:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"CLIENTES NUEVA SEGOVIA"
					}
				)
				upd_child.save()


		tabTRuta1 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 1'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta1:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 1"
					}
				)
				upd_child.save()
				

		tabTRuta2 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 2'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta2:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 2"
					}
				)
				upd_child.save()
				

		tabTRuta3 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parentt='RUTA 3'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta3:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 3"
					}
				)
				upd_child.save()
				

		tabTRuta4 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 4'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta4:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 4"
					}
				)
				upd_child.save()
				

		tabTRuta5 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 5'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta5:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 5"
					}
				)
				upd_child.save()
				

		tabTRuta6 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 6'
				and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta6:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 6"
					}
				)
				upd_child.save()
				

		tabTRuta7 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 7'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta7:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 7"
					}
				)
				upd_child.save()
				

		tabTRuta8 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 8'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta8:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 8"
					}
				)
				upd_child.save()
			

		tabTRuta9 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 9'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta9:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 9"
					}
				)
				upd_child.save()
				

		tabTRuta10 = frappe.db.sql(
		""" select distinct t1.name from `tabCustomer` t1 
			inner join `tabBarrios y Rutas` t4 on t1.barrio=t4.barrios  
			inner join `tabDetalle Ciclo Facturacion` t5 on t5.cliente=t1.name
			where  t4.parent='RUTA 10'
			and t1.eco_factura=0 and  t5.parent =%(t5)s and t5.marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTRuta10:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA 10"
					}
				)
				upd_child.save()		



		tabTodas= frappe.db.sql(
		"""select cliente from `tabDetalle Ciclo Facturacion` where parent =%(t5)s and marck=0 limit 50000""",
		{"t5": name},
		)

		for client in tabTodas:
				upd_child = frappe.get_doc("Detalle Ciclo Facturacion", {"parent": name, "cliente":client[0]})	
				upd_child.update(
					{
						"marck": 1,
						"ruta":"RUTA TODAS"
					}
				)
				upd_child.save()


		update_rutas(fact.name)

		
		frappe.db.commit()



	except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))




