# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import json
from datetime import * 
import frappe
from frappe import _, msgprint
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cstr, flt, get_link_to_form, getdate, new_line_sep, nowdate, now

from erpnext.buying.utils import check_on_hold_or_closed_status, validate_for_items
from erpnext.controllers.buying_controller import BuyingController
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.stock_balance import get_indented_qty, update_bin_qty

form_grid_templates = {"items": "templates/form_grid/material_request_grid.html"}


class MaterialRequest(BuyingController):
	def get_feed(self):
		return

	def check_if_already_pulled(self):
		pass

	def validate_qty_against_so(self):
		so_items = {}  # Format --> {'SO/00001': {'Item/001': 120, 'Item/002': 24}}
		for d in self.get("items"):
			if d.sales_order:
				if not d.sales_order in so_items:
					so_items[d.sales_order] = {d.item_code: flt(d.qty)}
				else:
					if not d.item_code in so_items[d.sales_order]:
						so_items[d.sales_order][d.item_code] = flt(d.qty)
					else:
						so_items[d.sales_order][d.item_code] += flt(d.qty)

		for so_no in so_items.keys():
			for item in so_items[so_no].keys():
				already_indented = frappe.db.sql(
					"""select sum(qty)
					from `tabMaterial Request Item`
					where item_code = %s and sales_order = %s and
					docstatus = 1 and parent != %s""",
					(item, so_no, self.name),
				)
				already_indented = already_indented and flt(already_indented[0][0]) or 0

				actual_so_qty = frappe.db.sql(
					"""select sum(stock_qty) from `tabSales Order Item`
					where parent = %s and item_code = %s and docstatus = 1""",
					(so_no, item),
				)
				actual_so_qty = actual_so_qty and flt(actual_so_qty[0][0]) or 0

				if actual_so_qty and (flt(so_items[so_no][item]) + already_indented > actual_so_qty):
					frappe.throw(
						_("Material Request of maximum {0} can be made for Item {1} against Sales Order {2}").format(
							actual_so_qty - already_indented, item, so_no
						)
					)

	def validate(self):
		super(MaterialRequest, self).validate()

		self.validate_schedule_date()
		self.check_for_on_hold_or_closed_status("Sales Order", "sales_order")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_material_request_type()

		if not self.status:
			self.status = "Draft"

		from erpnext.controllers.status_updater import validate_status

		validate_status(
			self.status,
			[
				"Draft",
				"Submitted",
				"Stopped",
				"Cancelled",
				"Pending",
				"Partially Ordered",
				"Ordered",
				"Issued",
				"Transferred",
				"Received",
			],
		)

		validate_for_items(self)

		self.set_title()
		# self.validate_qty_against_so()
		# NOTE: Since Item BOM and FG quantities are combined, using current data, it cannot be validated
		# Though the creation of Material Request from a Production Plan can be rethought to fix this

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("set_from_warehouse", "items", "from_warehouse")

	def before_update_after_submit(self):
		self.validate_schedule_date()

	def validate_material_request_type(self):
		"""Validate fields in accordance with selected type"""

		if self.material_request_type != "Customer Provided":
			self.customer = None

	def set_title(self):
		"""Set title as comma separated list of items"""
		if not self.title:
			items = ", ".join([d.item_name for d in self.items][:3])
			self.title = _("{0} Request for {1}").format(self.material_request_type, items)[:100]

	def on_submit(self):
		# frappe.db.set(self, 'status', 'Submitted')
		self.update_requested_qty()
		self.update_requested_qty_in_production_plan()
		if self.material_request_type == "Purchase":
			self.validate_budget()

	def before_save(self):
		self.set_status(update=True)

	def before_submit(self):
		self.set_status(update=True)

	def before_cancel(self):
		# if MRQ is already closed, no point saving the document
		check_on_hold_or_closed_status(self.doctype, self.name)

		self.set_status(update=True, status="Cancelled")

	def check_modified_date(self):
		mod_db = frappe.db.sql(
			"""select modified from `tabMaterial Request` where name = %s""", self.name
		)
		date_diff = frappe.db.sql(
			"""select TIMEDIFF('%s', '%s')""" % (mod_db[0][0], cstr(self.modified))
		)

		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(_(self.doctype), self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.status_can_change(status)
		self.set_status(update=True, status=status)
		self.update_requested_qty()

	def status_can_change(self, status):
		"""
		validates that `status` is acceptable for the present controller status
		and throws an Exception if otherwise.
		"""
		if self.status and self.status == "Cancelled":
			# cancelled documents cannot change
			if status != self.status:
				frappe.throw(
					_("{0} {1} is cancelled so the action cannot be completed").format(
						_(self.doctype), self.name
					),
					frappe.InvalidStatusError,
				)

		elif self.status and self.status == "Draft":
			# draft document to pending only
			if status != "Pending":
				frappe.throw(
					_("{0} {1} has not been submitted so the action cannot be completed").format(
						_(self.doctype), self.name
					),
					frappe.InvalidStatusError,
				)

	def on_cancel(self):
		self.update_requested_qty()
		self.update_requested_qty_in_production_plan()

	def update_completed_qty(self, mr_items=None, update_modified=True):
		if self.material_request_type == "Purchase":
			return

		if not mr_items:
			mr_items = [d.name for d in self.get("items")]

		for d in self.get("items"):
			if d.name in mr_items:
				if self.material_request_type in ("Material Issue", "Material Transfer", "Customer Provided"):
					d.ordered_qty = flt(
						frappe.db.sql(
							"""select sum(transfer_qty)
						from `tabStock Entry Detail` where material_request = %s
						and material_request_item = %s and docstatus = 1""",
							(self.name, d.name),
						)[0][0]
					)
					mr_qty_allowance = frappe.db.get_single_value("Stock Settings", "mr_qty_allowance")

					if mr_qty_allowance:
						allowed_qty = d.qty + (d.qty * (mr_qty_allowance / 100))
						if d.ordered_qty and d.ordered_qty > allowed_qty:
							frappe.throw(
								_(
									"The total Issue / Transfer quantity {0} in Material Request {1}  cannot be greater than allowed requested quantity {2} for Item {3}"
								).format(d.ordered_qty, d.parent, allowed_qty, d.item_code)
							)

					elif d.ordered_qty and d.ordered_qty > d.stock_qty:
						frappe.throw(
							_(
								"The total Issue / Transfer quantity {0} in Material Request {1} cannot be greater than requested quantity {2} for Item {3}"
							).format(d.ordered_qty, d.parent, d.qty, d.item_code)
						)

				elif self.material_request_type == "Manufacture":
					d.ordered_qty = flt(
						frappe.db.sql(
							"""select sum(qty)
						from `tabWork Order` where material_request = %s
						and material_request_item = %s and docstatus = 1""",
							(self.name, d.name),
						)[0][0]
					)

				frappe.db.set_value(d.doctype, d.name, "ordered_qty", d.ordered_qty)

		self._update_percent_field(
			{
				"target_dt": "Material Request Item",
				"target_parent_dt": self.doctype,
				"target_parent_field": "per_ordered",
				"target_ref_field": "stock_qty",
				"target_field": "ordered_qty",
				"name": self.name,
			},
			update_modified,
		)

	def update_requested_qty(self, mr_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []
		for d in self.get("items"):
			if (
				(not mr_item_rows or d.name in mr_item_rows)
				and [d.item_code, d.warehouse] not in item_wh_list
				and d.warehouse
				and frappe.db.get_value("Item", d.item_code, "is_stock_item") == 1
			):
				item_wh_list.append([d.item_code, d.warehouse])

		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {"indented_qty": get_indented_qty(item_code, warehouse)})

	def update_requested_qty_in_production_plan(self):
		production_plans = []
		for d in self.get("items"):
			if d.production_plan and d.material_request_plan_item:
				qty = d.qty if self.docstatus == 1 else 0
				frappe.db.set_value(
					"Material Request Plan Item", d.material_request_plan_item, "requested_qty", qty
				)

				if d.production_plan not in production_plans:
					production_plans.append(d.production_plan)

		for production_plan in production_plans:
			doc = frappe.get_doc("Production Plan", production_plan)
			doc.set_status()
			doc.db_set("status", doc.status)


def update_completed_and_requested_qty(stock_entry, method):
	
	if stock_entry.doctype == "Stock Entry":
			material_request_map = {}
			d = str(stock_entry.posting_date)
			t = str(stock_entry.posting_time)
			date_time = d + ' ' + t
			for d in stock_entry.get("items"):
				if d.material_request:
					material_request_map.setdefault(d.material_request, []).append(d.material_request_item)

			for mr, mr_item_rows in material_request_map.items():

				if mr and mr_item_rows:
					mr_obj = frappe.get_doc("Material Request", mr)

					if mr_obj.status in ["Stopped", "Cancelled"]:
						frappe.throw(
							_("{0} {1} is cancelled or stopped").format(_("Material Request"), mr),
							frappe.InvalidStatusError,
						)

					mr_obj.update_completed_qty(mr_item_rows)
					mr_obj.update_requested_qty(mr_item_rows)

			prefijo_erp = '%PREC-%'
			equipos = frappe.db.sql(""" select count(service_order) from `tabStock Entry Detail` where parent = %(parent)s and service_order not like %(prefijo_erp)s; """, {"parent":stock_entry.name, "prefijo_erp":prefijo_erp})
			equipos = equipos[0][0]
			ordenes = frappe.db.sql(""" select service_order, serial_no from `tabStock Entry Detail` where parent = %(parent)s  and serial_no is not null and serial_no <> '';""", {"parent":stock_entry.name})
			customer = ''		
			materiales = frappe.db.sql(""" select service_order, item_code, qty, uom, valuation_rate, amount from `tabStock Entry Detail` where parent =  %(parent)s and (serial_no is null or serial_no = '' );""", {"parent":stock_entry.name})
			
			if method == "on_submit" and stock_entry.stock_entry_type == "Material Issue" and equipos > 0:
				
				for orden in range(len(ordenes)):
					head, sep, tail = ordenes[orden][0].partition('-')	
					idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":ordenes[orden][1]})	
					try:
						idx = int(idx[0][0]) + 1
					except:
						idx = 1	
					lista_portafolio = 	[]
					if head == "OS":
						# frappe.msgprint("entra os")
						customer = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'tercero')
						frappe.db.set_value('Serial No', ordenes[orden][1], 'customer', customer)	
						frappe.db.sql(""" update `tabService Order` set ordered_on_stock = 1 where name = %(orden)s""",{"orden":ordenes[orden][0]})				
						suscripcion = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'nombre_de_origen')
						planname = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'plan_de_subscripcion')
						# planname = frappe.db.get_value('Subscription Plan Detail', {"plan": plan,"parent":suscripcion}, 'name')
						if frappe.db.get_value('Subscription Plan Equipos', {"parent":suscripcion,"equipo": ordenes[orden][1]}):
							frappe.get_doc("Subscription Plan Equipos",{"parent":suscripcion, "equipo": ordenes[orden][1]}).delete(ignore_permissions=True)

						lista_portafolio.append(frappe.db.get_value('Service Order',ordenes[orden][0],"portafolio"))

					elif head == "ISS":				
						customer = frappe.db.get_value('Issue', {"name": ordenes[orden][0]}, 'customer')
						frappe.db.set_value('Serial No', ordenes[orden][1], 'customer', customer)	
						issue = frappe.db.sql(""" select equipo from `tabIssue_Equipos` where  parent = %(orden)s and equipo_nuevo = %(equipo)s; """,{"orden":ordenes[orden][0], "equipo":ordenes[orden][1]} )
						# issue = frappe.db.sql("""  select equipo from `tabIssue_Equipos` ie inner join  `tabMateriales detalles` md on ie.parent = md.parent 
						# 				where  md.parent = %(orden)s and (ie.equipo_nuevo = %(equipo)s or md.serial_no= %(equipo)s) """,{"orden":ordenes[orden][0], "equipo":ordenes[orden][1]})
						try:
							issue =issue[0][0]
						except:
							issue =	None
						if issue:
							frappe.db.set_value('Serial No', issue, 'customer', None)
						frappe.db.sql(""" update `tabIssue` set ordered_on_stock = 1 where name = %(orden)s""",{"orden":ordenes[orden][0]})				

						orden_issue = frappe.db.sql(""" select t3.equipo , t3.equipo_nuevo, t2.parent, t1.name from  `tabSubscription Plan Detail` t1 inner join 
							`tabSubscription Plan Equipos` t2 on t1.parent = t2.parent inner join
							`tabIssue_Equipos` t3 on t3.equipo = t2.equipo inner join
							`tabStock Entry Detail` t4 on t4.service_order = t3.parent
							where t4.parent = %(parent)s and t3.equipo_nuevo = %(equipo)s limit 1 """, {"parent":stock_entry.name, "equipo":ordenes[orden][1]})						
						try:
							suscripcion = orden_issue[0][2]
							planname=orden_issue[0][3]
							if frappe.db.get_value('Subscription Plan Equipos', {"parent":suscripcion,"equipo":orden_issue[0][0]}):
								frappe.get_doc("Subscription Plan Equipos",{"parent":suscripcion, "equipo":orden_issue[0][0]}).delete(ignore_permissions=True)
						except:
							planname = None

						# lista_portafolio.append(frappe.db.get_value('Issue',ordenes[orden][0],"portafolio"))
						lista_portafolio.append(frappe.db.get_value('Issue',ordenes[orden][0],"servicio"))

					else:
						planname = None		
						frappe.db.sql(""" update `tabOrden de Servicio Interno` set ordered_on_stock = 1 where name = %(orden)s""",{"orden":ordenes[orden][0]})						
				
					portafolios_permitidos = ['GPON','GPON-CORPORATIVO','GPON-INT-PYME','GPON-INT-RESIDENCIAL','HFC', 'HFC 3.0', 'IMOVIL', 'INET', 'Wimax','IPTV','LTE', 'LTE Productos']
					if planname and tienen_dato_en_comun(lista_portafolio,portafolios_permitidos):
						add_equipos = frappe.get_doc({
							"doctype": "Subscription Plan Equipos",
							"plan":planname,
							"equipo": ordenes[orden][1],
							"parent":suscripcion,
							"parentfield":"equipos",
							"parenttype": "Subscription",
						})
						add_equipos.insert(ignore_permissions=True)
						spd = frappe.get_doc("Subscription Plan Detail",add_equipos.plan)
							
						
						if not frappe.db.exists("Bitacora de Planes", {"subscription_plan_detail": spd.name}):
							bitacora_plan = frappe.get_doc({
								'doctype': "Bitacora de Planes",
								'plan': spd.plan,			
								'cliente':  customer,
								'estado_plan': "Activo",
								'direccion': spd.direccion,
								'currency': spd.currency,
								'costo':spd.cost,
								'intervalo_de_facturacion':spd.billing_interval_count,
								'subscription_plan_detail': spd.name
							})
							bitacora_plan.insert(ignore_permissions=True)
					

						if frappe.db.exists("Aprovisionamiento",ordenes[orden][1]):
							# frappe.db.set_value("Aprovisionamiento",ordenes[orden][1],"plan",planname)
							frappe.db.sql("""  update `tabAprovisionamiento` set plan= %(plan)s, customer=%(customer)s  where name=	%(name)s""", {"plan":spd.name, "customer":customer, "name":ordenes[orden][1]})
							# frappe.msgprint(ordenes[orden][1])
							# frappe.msgprint(planname)

						idx=int(frappe.db.sql(""" select (case when max(idx)is null then "1" else max(idx)+ 1 end)  from `tabDetalle Bitacora Planes` where parent= %(parent)s """,{"parent":spd.name})[0][0])					
						bitacora_plan = frappe.get_doc("Bitacora de Planes", {"subscription_plan_detail": spd.name})

						spd = frappe.get_doc("Subscription Plan Detail",add_equipos.plan)		
						bitacora_detalle = frappe.get_doc({
							"doctype": "Detalle Bitacora Planes",
							"detalle":"Asignacion de equipo a plan",
							"idx":idx,
							"fecha": now(),
							"usuario":frappe.session.user,
							"parent": frappe.db.get_value("Service Order",ordenes[orden][0],"plan_de_subscripcion") if head == 'OS' else frappe.db.get_value("Issue",ordenes[orden][0],"planes"),
							"parentfield":"detalle",
							"parenttype": "Bitacora de Planes",
							"tipo_transaccion":"Service Order" if head == 'OS' else "Issue",
							"tercero":ordenes[orden][0],
							'estado_plan': "Activo",
							})
						bitacora_detalle.insert(ignore_permissions=True)
					
					add_to_bitacora_a = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Stock Entry',
						"transaccion":stock_entry.stock_entry_type,
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": stock_entry.name,
						"idx":idx
					})
					idx+=1
					add_to_bitacora_a.insert(ignore_permissions=True)
					add_to_bitacora_b = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Customer',
						"transaccion":"Entrega",
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": customer,
						"idx":idx
					})
					add_to_bitacora_b.insert(ignore_permissions=True)

				if materiales:			
					for orden in materiales:
						#frappe.msgprint(str(orden))
						head, sep, tail = orden[0].partition('-')
						if  head != "OSI":
							plan = frappe.db.get_value("Service Order",orden[0],"plan_de_subscripcion") if  head == "OS" else frappe.db.get_value("Issue",orden[0],"planes")
							add_to_bitacora_material = frappe.get_doc({
								"doctype": "Materiales de Plan",
								"fecha_transaccion":now(),
								"item_code": orden[1],
								"qty":orden[2],
								"uom":orden[3],
								"basic_rate":orden[4],
								"basic_amount":orden[5],
								"origen": stock_entry.name,
								"parent":plan,
								"parentfield":"materiales_de_plan",
								"parenttype": "Bitacora de Planes",
							})
							add_to_bitacora_material.insert(ignore_permissions=True)
						# except:
						# 	pass
			if method == "on_submit" and stock_entry.stock_entry_type == "Material Receipt" and equipos > 0:
				for orden in range(len(ordenes)):
					if ordenes[orden][0]:
						head, sep, tail = ordenes[orden][0].partition('-')	
						idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":ordenes[orden][1]})	
					try:
						idx = int(idx[0][0]) + 1
					except:
						idx = 1		
					frappe.db.set_value('Serial No', ordenes[orden][1], 'customer', None)			
					if head == "OS":
						frappe.db.set_value('Service Order',ordenes[orden][0], 'ordered_on_stock', 1)
						suscripcion = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'nombre_de_origen')							
						if frappe.db.get_value('Subscription Plan Equipos', {"parent":suscripcion,"equipo":ordenes[orden][1]}):
							frappe.db.sql("delete from `tabSubscription Plan Equipos` where parent = %(parent)s and equipo = %(equipo)s",{"parent":suscripcion, "equipo":ordenes[orden][1]})					
						
					elif head == "ISS":
						frappe.db.set_value('Issue',ordenes[orden][0], 'desinstalacion_equipos', 1)
					elif head == "OSI":
						frappe.db.set_value('Issue',ordenes[orden][0], 'desinstalacion_equipos', 1)
 	
					add_to_bitacora_a = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Stock Entry',
						"transaccion":stock_entry.stock_entry_type,
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": stock_entry.name,
						"idx":idx
						})
					add_to_bitacora_a.insert(ignore_permissions=True,ignore_links=True)
					idx += 1
					add_to_bitacora_b = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Warehouse',
						"transaccion":"Entrega",
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": stock_entry.to_warehouse,
						"idx":idx
					})
					add_to_bitacora_b.insert(ignore_permissions=True,ignore_links=True)

					if frappe.db.exists("Aprovisionamiento",ordenes[orden][1]):
						frappe.db.sql("""  update `tabAprovisionamiento` set plan= null, customer=null  where name=	%(name)s""", {"name":ordenes[orden][1]})														
			if method == "on_submit" and equipos == 0  and stock_entry.stock_entry_type == "Material Issue":
				ordenes = frappe.db.get_values("Stock Entry Detail", {"parent":stock_entry.name},"service_order")
				if len(ordenes) > 0:
					try:
						for orden in ordenes:
							if "OS-" in orden[0]:
								frappe.db.sql(""" update `tabService Order` set ordered_on_stock = 1 where name = %(orden)s""",{"orden":orden[0]})	
							elif "OSI-" in orden[0]:
								frappe.db.sql(""" update `tabOrden de Servicio Interno` set ordered_on_stock = 1 where name = %(orden)s""",{"orden":orden[0]})						

							else:
								frappe.db.sql(""" update `tabIssue` set ordered_on_stock = 1 where name = %(orden)s""",{"orden":orden[0]})									
					except:
						pass


				for serie in frappe.db.sql(""" select serial_no from `tabStock Entry Detail` where parent = %(parent)s """, {"parent":stock_entry.name}):	
					if serie[0]:				
						if "\n" in serie[0]:
							series = serie[0].split("\n")
							for s in series:
								idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":s})		
								try:
									idx = int(idx[0][0]) + 1
								except:
									idx = 1		
								add_to_bitacora_a = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Stock Entry',
									"transaccion":stock_entry.stock_entry_type,
									"parent":s,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.name,
									"idx":idx
									})
								add_to_bitacora_a.insert(ignore_permissions=True)
								idx+=1
								add_to_bitacora_b = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Warehouse',
									"transaccion":"Salida",
									"parent":s,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.from_warehouse if stock_entry.from_warehouse else 'Las mercancías en tránsito - NI',
									"idx":idx
								})
								add_to_bitacora_b.insert(ignore_permissions=True)
						else:
							idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":serie[0]})		
							try:
								idx = int(idx[0][0]) + 1
							except:
								idx = 1		
							add_to_bitacora_a = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Stock Entry',
								"transaccion":stock_entry.stock_entry_type,
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.name,
								"idx":idx
								})
							add_to_bitacora_a.insert(ignore_permissions=True)
							idx+=1
							add_to_bitacora_b = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Warehouse',
								"transaccion":"Salida",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.from_warehouse,
								"idx":idx
							})
							add_to_bitacora_b.insert(ignore_permissions=True)
			if method == "on_cancel" and equipos == 0  and stock_entry.stock_entry_type == "Material Issue":
				ordenes = frappe.db.get_values("Stock Entry Detail", {"parent":stock_entry.name},"service_order")
				if len(ordenes) > 0:
					for orden in ordenes:
						try:
							if "OS-" in orden[0]:
								frappe.db.sql(""" update `tabService Order` set ordered_on_stock = 0 where name = %(orden)s""",{"orden":orden[0]})	
							elif "OSI-" in orden[0]:
								frappe.db.sql(""" update `tabOrden de Servicio Interno` set ordered_on_stock = 0 where name = %(orden)s""",{"orden":orden[0]})	

							else:
								frappe.db.sql(""" update `tabIssue` set ordered_on_stock = 0 where name = %(orden)s""",{"orden":orden[0]})	
						except:
							pass

				for serie in frappe.db.sql(""" select serial_no from `tabStock Entry Detail` where parent = %(parent)s """, {"parent":stock_entry.name}):	
					if serie[0]:				
						if "\n" in serie[0]:
							series = serie[0].split("\n")
							for s in series:
								idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":s})		
								try:
									idx = int(idx[0][0]) + 1
								except:
									idx = 1		
								add_to_bitacora_a = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Stock Entry',
									"transaccion":stock_entry.stock_entry_type + " CANCELADO",
									"parent":s,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.name,
									"idx":idx
									})
								add_to_bitacora_a.insert(ignore_permissions=True)
								idx+=1
								add_to_bitacora_b = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Warehouse',
									"transaccion":"Salida CANCELADA",
									"parent":s,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.from_warehouse,
									"idx":idx
								})
								add_to_bitacora_b.insert(ignore_permissions=True)
						else:
							idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":serie[0]})		
							try:
								idx = int(idx[0][0]) + 1
							except:
								idx = 1		
							add_to_bitacora_a = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Stock Entry',
								"transaccion":stock_entry.stock_entry_type + " CANCELADO",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.name,
								"idx":idx
								})
							add_to_bitacora_a.insert(ignore_permissions=True)
							idx+=1
							add_to_bitacora_b = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Warehouse',
								"transaccion":"Salida CANCELADA",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.from_warehouse,
								"idx":idx
							})
							add_to_bitacora_b.insert(ignore_permissions=True)
			if method == "on_submit" and equipos == 0  and stock_entry.stock_entry_type == "Material Receipt":				
				for serie in frappe.db.sql(""" select serial_no from `tabStock Entry Detail` where parent = %(parent)s """, {"parent":stock_entry.name}):	
					if serie[0]:
						if "\n" in serie[0]:
							series = serie[0].split("\n")							
							for s in series:
								idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":s})		
								try:
									idx = int(idx[0][0]) + 1
								except:
									idx = 1									
								add_to_bitacora_a = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Stock Entry',
									"transaccion":stock_entry.stock_entry_type,
									"parent":s,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.name,
									"idx":idx
									})
								add_to_bitacora_a.insert(ignore_permissions=True)
								idx+=1
								add_to_bitacora_b = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Warehouse',
									"transaccion":"Entrega",
									"parent":s,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.to_warehouse,
									"idx":idx
								})
								add_to_bitacora_b.insert(ignore_permissions=True)
						else:					
							idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":serie[0]})		
							try:
								idx = int(idx[0][0]) + 1
							except:
								idx = 1	
							add_to_bitacora_a = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Stock Entry',
								"transaccion":stock_entry.stock_entry_type,
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.name,
								"idx":idx
								})
							add_to_bitacora_a.insert(ignore_permissions=True)
							idx+=1
							add_to_bitacora_b = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Warehouse',
								"transaccion":"Entrega",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.to_warehouse,
								"idx":idx
							})
							add_to_bitacora_b.insert(ignore_permissions=True)								
			if method == "on_submit" and stock_entry.stock_entry_type == "Material Transfer":
				
				for serie in frappe.db.sql(""" select serial_no, service_order from `tabStock Entry Detail` where parent = %(parent)s """, {"parent":stock_entry.name}):	
					if serie[0]:
						if "\n" in serie[0]:
							series = serie[0].split("\n")
							for s_no in series:

								idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":s_no})		
								try:
									idx = int(idx[0][0]) + 1
								except:
									idx = 1		
								# frappe.msgprint(f"agregando a bitacora de {serie[0]}")	
								add_to_bitacora_a = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Stock Entry',
									"transaccion":stock_entry.stock_entry_type,
									"parent":s_no,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.name,
									"idx":idx
									})
								add_to_bitacora_a.insert(ignore_permissions=True)
								idx+=1
								add_to_bitacora_b = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Warehouse',
									"transaccion":"Entrega",
									"parent":s_no,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.to_warehouse,
									"idx":idx
								})
								add_to_bitacora_b.insert(ignore_permissions=True)
								idx+=1
								add_to_bitacora_c = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Warehouse',
									"transaccion":"Salida",
									"parent":s_no,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.from_warehouse,
									"idx":idx
								})
								add_to_bitacora_c.insert(ignore_permissions=True)
						else:
							idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":serie[0]})		
							try:
								idx = int(idx[0][0]) + 1
							except:
								idx = 1		
							# frappe.msgprint(f"agregando a bitacora de {serie[0]}")	
							add_to_bitacora_a = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Stock Entry',
								"transaccion":stock_entry.stock_entry_type,
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.name,
								"idx":idx
								})
							add_to_bitacora_a.insert(ignore_permissions=True)
							idx+=1
							add_to_bitacora_b = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Warehouse',
								"transaccion":"Entrega",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.to_warehouse,
								"idx":idx
							})
							add_to_bitacora_b.insert(ignore_permissions=True)
							idx+=1
							add_to_bitacora_c = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Warehouse',
								"transaccion":"Salida",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.from_warehouse,
								"idx":idx
							})
							add_to_bitacora_c.insert(ignore_permissions=True)	
					if serie[1]:
						frappe.db.set_value('Service Order',serie[1], 'ordered_on_stock', 1)
			if method == "on_cancel" and stock_entry.stock_entry_type == "Material Transfer":
				
				for serie in frappe.db.sql(""" select serial_no, service_order from `tabStock Entry Detail` where parent = %(parent)s """, {"parent":stock_entry.name}):	
					if serie[0]:
						if "\n" in serie[0]:
							series = serie[0].split("\n")

							for s_no in series:

								idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":s_no})		
								try:
									idx = int(idx[0][0]) + 1
								except:
									idx = 1		
									
								add_to_bitacora_a = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Stock Entry',
									"transaccion":stock_entry.stock_entry_type + " CANCELADA",
									"parent":s_no,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.name,
									"idx":idx
									})
								add_to_bitacora_a.insert(ignore_permissions=True)
								idx+=1
								add_to_bitacora_b = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Warehouse',
									"transaccion":"Entrega CANCELADA",
									"parent":s_no,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.to_warehouse,
									"idx":idx
								})
								add_to_bitacora_b.insert(ignore_permissions=True)
								idx+=1
								add_to_bitacora_c = frappe.get_doc({
									"doctype": "Bitacora Equipos",
									"fecha_transaccion":now(),
									"fecha_contabilizacion":date_time,
									"tipo_transaccion": 'Warehouse',
									"transaccion":"Salida CANCELADA",
									"parent":s_no,
									"parentfield":"bitacora_equipos",
									"parenttype": "Serial No",
									"tercero": stock_entry.from_warehouse,
									"idx":idx
								})
								add_to_bitacora_c.insert(ignore_permissions=True)
						else:
							idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":serie[0]})		
							try:
								idx = int(idx[0][0]) + 1
							except:
								idx = 1		
							# frappe.msgprint(f"agregando a bitacora de {serie[0]}")	
							add_to_bitacora_a = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Stock Entry',
								"transaccion":stock_entry.stock_entry_type + " CANCELADA",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.name,
								"idx":idx
								})
							add_to_bitacora_a.insert(ignore_permissions=True)
							idx+=1
							add_to_bitacora_b = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Warehouse',
								"transaccion":"Entrega CANCELADA",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.to_warehouse,
								"idx":idx
							})
							add_to_bitacora_b.insert(ignore_permissions=True)
							idx+=1
							add_to_bitacora_c = frappe.get_doc({
								"doctype": "Bitacora Equipos",
								"fecha_transaccion":now(),
								"fecha_contabilizacion":date_time,
								"tipo_transaccion": 'Warehouse',
								"transaccion":"Salida CANCELADA",
								"parent":serie[0],
								"parentfield":"bitacora_equipos",
								"parenttype": "Serial No",
								"tercero": stock_entry.from_warehouse,
								"idx":idx
							})
							add_to_bitacora_c.insert(ignore_permissions=True)		
					if serie[1]:
						frappe.db.set_value('Service Order',serie[1], 'ordered_on_stock', 0)
			if method == "on_cancel" and equipos>0 and stock_entry.stock_entry_type == "Material Issue":
				for orden in range(len(ordenes)):	
					head, sep, tail = ordenes[orden][0].partition('-')
					idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":ordenes[orden][1]})	
					try:
						idx = int(idx[0][0]) + 1
					except:
						idx = 1		
					if head == "OS":
						suscripcion = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'nombre_de_origen')							
						frappe.db.sql(""" update `tabService Order` set ordered_on_stock = 0 where name = %(orden)s""",{"orden":ordenes[orden][0]})					
						frappe.db.set_value('Serial No', ordenes[orden][1], 'customer', None)
						if frappe.db.get_value('Subscription Plan Equipos', {"parent":suscripcion,"equipo":ordenes[orden][1]}):
							frappe.get_doc("Subscription Plan Equipos",{"parent":suscripcion, "equipo":ordenes[orden][1]}).delete()
							frappe.db.sql(""" delete from `tabSubscription Plan Equipos` where parent = %(subsc)s """,{"subsc":suscripcion})
						plan = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'plan_de_subscripcion')
						#linea de abajo no trabaja#
						frappe.db.sql("""Delete from `tabDetalle Bitacora Planes` where parent = %(plan)s and tercero = %(tercero)s and detalle='Asignacion de equipo a plan';""",{"plan":plan,"tercero":ordenes[orden][0]})

					elif head == "ISS":
						orden_issue = frappe.db.sql(""" select t3.equipo , t3.equipo_nuevo, t2.parent, t1.name from  `tabSubscription Plan Detail` t1 inner join 
							`tabSubscription Plan Equipos` t2 on t1.parent = t2.parent inner join
							`tabIssue_Equipos` t3 on t3.equipo_nuevo = t2.equipo inner join
							`tabStock Entry Detail` t4 on t4.service_order = t3.parent
							where t4.parent = %(parent)s and t3.equipo_nuevo = %(equipo)s limit 1 """, {"parent":stock_entry.name, "equipo":ordenes[orden][1]})					
						try:
							suscripcion = orden_issue[0][2]
							plan=orden_issue[0][3]	
							#linea de abajo no trabaja#
						except:
							plan = None
						
						if plan:
							frappe.db.sql("""Delete from `tabDetalle Bitacora Planes` where parent = %(plan)s and tercero = %(tercero)s and detalle='Asignacion de equipo a plan';""",{"plan":plan,"tercero":ordenes[orden][0]})
						
							frappe.db.sql(""" update `tabIssue` set ordered_on_stock = 0 where name = %(orden)s""",{"orden":ordenes[orden][0]})					
							frappe.db.set_value('Serial No', ordenes[orden][1], 'customer', None)
							if frappe.db.get_value('Subscription Plan Equipos', {"parent":suscripcion,"equipo":ordenes[orden][1]}):
								frappe.get_doc("Subscription Plan Equipos",{"parent":suscripcion, "equipo":ordenes[orden][1]}).delete()
								add_equipos = frappe.get_doc({
									"doctype": "Subscription Plan Equipos",
									"plan":plan,
									"equipo": orden_issue[0][0],
									"parent":suscripcion,
									"parentfield":"equipos",
									"parenttype": "Subscription",
								})
								add_equipos.insert()
							customer = frappe.db.get_value('Issue', {"name": ordenes[orden][0]}, 'customer')
							frappe.db.set_value('Serial No', orden_issue[0][0], 'customer', customer)
					else:
						frappe.db.sql(""" update `tabOrden de Servicio Interno` set ordered_on_stock = 0 where name = %(orden)s""",{"orden":ordenes[orden][0]})					

					if frappe.db.exists("Aprovisionamiento",ordenes[orden][1]):
						frappe.db.set_value("Aprovisionamiento",ordenes[orden][1],"plan",None)
					add_to_bitacora_a = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Stock Entry',
						"transaccion":stock_entry.stock_entry_type + " CANCELADO",
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": stock_entry.name,
						"idx":idx,
					})
					add_to_bitacora_a.insert(ignore_permissions=True)
					idx+=1
					add_to_bitacora_b = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Customer',
						"transaccion":"Entrega" + " CANCELADO",
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": customer,
						"idx":idx
					})
					add_to_bitacora_b.insert(ignore_permissions=True)
				frappe.db.sql("""Delete from `tabMateriales de Plan` where origen = %(origen)s""",{"origen":stock_entry.name})
			if method == "on_cancel" and equipos>0 and stock_entry.stock_entry_type == "Material Receipt":	
				for orden in range(len(ordenes)):
					head, sep, tail = ordenes[orden][0].partition('-')	
					idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":ordenes[orden][1]})	
					try:
						idx = int(idx[0][0]) + 1
					except:
						idx = 1		
					if head == "OS":
						customer = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'tercero')
						frappe.db.set_value('Serial No', ordenes[orden][1], 'customer', customer)
						frappe.db.set_value('Service Order',ordenes[orden][0], 'ordered_on_stock', 0)
						suscripcion = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'nombre_de_origen')
						planname = frappe.db.get_value('Service Order', {"name": ordenes[orden][0]}, 'plan_de_subscripcion')
						# planname = frappe.db.get_value('Subscription Plan Detail', {"plan": plan,"parent":suscripcion}, 'name')
						if frappe.db.get_value('Subscription Plan Equipos', {"parent":suscripcion,"equipo": ordenes[orden][1]}):
							frappe.get_doc("Subscription Plan Equipos",{"parent":suscripcion, "equipo": ordenes[orden][1]}).delete()						
						add_equipos = frappe.get_doc({
						"doctype": "Subscription Plan Equipos",
						"plan":planname,
						"equipo": ordenes[orden][1],
						"parent":suscripcion,
						"parentfield":"equipos",
						"parenttype": "Subscription",
						})					
						add_equipos.insert(ignore_permissions=True)
					elif head == "ISS":
						customer = frappe.db.get_value('Issue', {"name": ordenes[orden][0]}, 'customer')
						frappe.db.set_value('Serial No', ordenes[orden][1], 'customer', customer)	
						frappe.db.set_value('Issue',ordenes[orden][0], 'desinstalacion_equipos', 0)
					elif head == "OSI":
						frappe.db.set_value('Issue',ordenes[orden][0], 'desinstalacion_equipos', 0)

									
					add_to_bitacora_a = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Stock Entry',
						"transaccion":stock_entry.stock_entry_type + " CANCELADO",
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": stock_entry.name,
						"idx":idx
						})
					add_to_bitacora_a.insert(ignore_permissions=True, ignore_links=True)
					idx+=1
					add_to_bitacora_b = frappe.get_doc({
						"doctype": "Bitacora Equipos",
						"fecha_transaccion":now(),
						"fecha_contabilizacion":date_time,
						"tipo_transaccion": 'Warehouse',
						"transaccion":"Entrega CANCELADO",
						"parent":ordenes[orden][1],
						"parentfield":"bitacora_equipos",
						"parenttype": "Serial No",
						"tercero": stock_entry.to_warehouse,
						"idx":idx
					})
					add_to_bitacora_b.insert(ignore_permissions=True, ignore_links=True)	
			if method == "on_cancel" and equipos == 0  and stock_entry.stock_entry_type == "Material Receipt":
					for serie in frappe.db.sql(""" select serial_no from `tabStock Entry Detail` where parent = %(parent)s """, {"parent":stock_entry.name}):	
						if serie[0]:
							
							if "\n" in serie[0]:
								series = serie[0].split("\n")
							
								for s in series:
									idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":s})		
									try:
										idx = int(idx[0][0]) + 1
									except:
										idx = 1	
								
									add_to_bitacora_a = frappe.get_doc({
										"doctype": "Bitacora Equipos",
										"fecha_transaccion":now(),
										"fecha_contabilizacion":date_time,
										"tipo_transaccion": 'Stock Entry',
										"transaccion":stock_entry.stock_entry_type  + " CANCELADO",
										"parent":s,
										"parentfield":"bitacora_equipos",
										"parenttype": "Serial No",
										"tercero": stock_entry.name,
										"idx":idx
										})
									add_to_bitacora_a.insert(ignore_permissions=True)
									idx+=1
									add_to_bitacora_b = frappe.get_doc({
										"doctype": "Bitacora Equipos",
										"fecha_transaccion":now(),
										"fecha_contabilizacion":date_time,
										"tipo_transaccion": 'Warehouse',
										"transaccion":"Entrega CANCELADO",
										"parent":s,
										"parentfield":"bitacora_equipos",
										"parenttype": "Serial No",
										"tercero": stock_entry.to_warehouse,
										"idx":idx
									})
									add_to_bitacora_b.insert(ignore_permissions=True)
							else:
								idx = frappe.db.sql(""" select idx from `tabBitacora Equipos` where parent=%(parent)s ORDER BY fecha_transaccion DESC LIMIT 1 """,{"parent":serie[0]})	
								try:
									idx = int(idx[0][0]) + 1
								except:
									idx = 1		
				
									add_to_bitacora_a = frappe.get_doc({
										"doctype": "Bitacora Equipos",
										"fecha_transaccion":now(),
										"fecha_contabilizacion":date_time,
										"tipo_transaccion": 'Stock Entry',
										"transaccion":stock_entry.stock_entry_type + " CANCELADO",
										"parent":serie[0],
										"parentfield":"bitacora_equipos",
										"parenttype": "Serial No",
										"tercero": stock_entry.name,
										"idx":idx
										})
									add_to_bitacora_a.insert(ignore_permissions=True)
									idx+=1
									add_to_bitacora_b = frappe.get_doc({
										"doctype": "Bitacora Equipos",
										"fecha_transaccion":now(),
										"fecha_contabilizacion":date_time,
										"tipo_transaccion": 'Warehouse',
										"transaccion":"Entrega CANCELADO",
										"parent":serie[0],
										"parentfield":"bitacora_equipos",
										"parenttype": "Serial No",
										"tercero": stock_entry.to_warehouse,
										"idx":idx
									})
									add_to_bitacora_b.insert(ignore_permissions=True)


def set_missing_values(source, target_doc):
	if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) < getdate(
		nowdate()
	):
		target_doc.schedule_date = None
	target_doc.run_method("set_missing_values")
	target_doc.run_method("calculate_taxes_and_totals")


def update_item(obj, target, source_parent):
	target.conversion_factor = obj.conversion_factor
	target.qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty)) / target.conversion_factor
	target.stock_qty = target.qty * target.conversion_factor
	if getdate(target.schedule_date) < getdate(nowdate()):
		target.schedule_date = None


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Material Request"),
		}
	)

	return list_context


@frappe.whitelist()
def update_status(name, status):
	material_request = frappe.get_doc("Material Request", name)
	material_request.check_permission("write")
	material_request.update_status(status)


@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def postprocess(source, target_doc):
		if frappe.flags.args and frappe.flags.args.default_supplier:
			# items only for given default supplier
			supplier_items = []
			for d in target_doc.items:
				default_supplier = get_item_defaults(d.item_code, target_doc.company).get("default_supplier")
				if frappe.flags.args.default_supplier == default_supplier:
					supplier_items.append(d)
			target_doc.items = supplier_items

		set_missing_values(source, target_doc)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True

		return d.ordered_qty < d.stock_qty and child_filter

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Purchase Order",
				"validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["uom", "stock_uom"],
					["uom", "uom"],
					["sales_order", "sales_order"],
					["sales_order_item", "sales_order_item"],
				],
				"postprocess": update_item,
				"condition": select_item,
			},
		},
		target_doc,
		postprocess,
	)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Request for Quotation",
				"validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
			},
			"Material Request Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["uom", "uom"],
				],
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_purchase_order_based_on_supplier(source_name, target_doc=None, args=None):
	mr = source_name

	supplier_items = get_items_based_on_default_supplier(args.get("supplier"))

	def postprocess(source, target_doc):
		target_doc.supplier = args.get("supplier")
		if getdate(target_doc.schedule_date) < getdate(nowdate()):
			target_doc.schedule_date = None
		target_doc.set(
			"items",
			[
				d for d in target_doc.get("items") if d.get("item_code") in supplier_items and d.get("qty") > 0
			],
		)

		set_missing_values(source, target_doc)

	target_doc = get_mapped_doc(
		"Material Request",
		mr,
		{
			"Material Request": {
				"doctype": "Purchase Order",
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["uom", "stock_uom"],
					["uom", "uom"],
				],
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.qty,
			},
		},
		target_doc,
		postprocess,
	)

	return target_doc


@frappe.whitelist()
def get_items_based_on_default_supplier(supplier):
	supplier_items = [
		d.parent
		for d in frappe.db.get_all(
			"Item Default", {"default_supplier": supplier, "parenttype": "Item"}, "parent"
		)
	]

	return supplier_items


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_material_requests_based_on_supplier(doctype, txt, searchfield, start, page_len, filters):
	conditions = ""
	if txt:
		conditions += "and mr.name like '%%" + txt + "%%' "

	if filters.get("transaction_date"):
		date = filters.get("transaction_date")[1]
		conditions += "and mr.transaction_date between '{0}' and '{1}' ".format(date[0], date[1])

	supplier = filters.get("supplier")
	supplier_items = get_items_based_on_default_supplier(supplier)

	if not supplier_items:
		frappe.throw(_("{0} is not the default supplier for any items.").format(supplier))

	material_requests = frappe.db.sql(
		"""select distinct mr.name, transaction_date,company
		from `tabMaterial Request` mr, `tabMaterial Request Item` mr_item
		where mr.name = mr_item.parent
			and mr_item.item_code in ({0})
			and mr.material_request_type = 'Purchase'
			and mr.per_ordered < 99.99
			and mr.docstatus = 1
			and mr.status != 'Stopped'
			and mr.company = '{1}'
			{2}
		order by mr_item.item_code ASC
		limit {3} offset {4} """.format(
			", ".join(["%s"] * len(supplier_items)), filters.get("company"), conditions, page_len, start
		),
		tuple(supplier_items),
		as_dict=1,
	)

	return material_requests


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_default_supplier_query(doctype, txt, searchfield, start, page_len, filters):
	doc = frappe.get_doc("Material Request", filters.get("doc"))
	item_list = []
	for d in doc.items:
		item_list.append(d.item_code)

	return frappe.db.sql(
		"""select default_supplier
		from `tabItem Default`
		where parent in ({0}) and
		default_supplier IS NOT NULL
		""".format(
			", ".join(["%s"] * len(item_list))
		),
		tuple(item_list),
	)


@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	def postprocess(source, target_doc):
		set_missing_values(source, target_doc)

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Supplier Quotation",
				"validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
			},
			"Material Request Item": {
				"doctype": "Supplier Quotation Item",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"sales_order": "sales_order",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist


@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		qty = (
			flt(flt(obj.stock_qty) - flt(obj.ordered_qty)) / target.conversion_factor
			if flt(obj.stock_qty) > flt(obj.ordered_qty)
			else 0
		)
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		if (
			source_parent.material_request_type == "Material Transfer"
			or source_parent.material_request_type == "Customer Provided"
		):
			target.t_warehouse = obj.warehouse
		else:
			target.s_warehouse = obj.warehouse

		if source_parent.material_request_type == "Customer Provided":
			target.allow_zero_valuation_rate = 1

		if source_parent.material_request_type == "Material Transfer":
			target.s_warehouse = obj.from_warehouse

	def set_missing_values(source, target):
		target.purpose = source.material_request_type
		if source.job_card:
			target.purpose = "Material Transfer for Manufacture"

		if source.material_request_type == "Customer Provided":
			target.purpose = "Material Receipt"

		target.set_missing_values()
		target.set_stock_entry_type()
		target.set_job_card_data()

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Stock Entry",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["in", ["Material Transfer", "Material Issue", "Customer Provided"]],
				},
			},
			"Material Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom",
					"job_card_item": "job_card_item",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.stock_qty,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def raise_work_orders(material_request):
	mr = frappe.get_doc("Material Request", material_request)
	errors = []
	work_orders = []
	default_wip_warehouse = frappe.db.get_single_value(
		"Manufacturing Settings", "default_wip_warehouse"
	)

	for d in mr.items:
		if (d.stock_qty - d.ordered_qty) > 0:
			if frappe.db.exists("BOM", {"item": d.item_code, "is_default": 1}):
				wo_order = frappe.new_doc("Work Order")
				wo_order.update(
					{
						"production_item": d.item_code,
						"qty": d.stock_qty - d.ordered_qty,
						"fg_warehouse": d.warehouse,
						"wip_warehouse": default_wip_warehouse,
						"description": d.description,
						"stock_uom": d.stock_uom,
						"expected_delivery_date": d.schedule_date,
						"sales_order": d.sales_order,
						"sales_order_item": d.get("sales_order_item"),
						"bom_no": get_item_details(d.item_code).bom_no,
						"material_request": mr.name,
						"material_request_item": d.name,
						"planned_start_date": mr.transaction_date,
						"company": mr.company,
					}
				)

				wo_order.set_work_order_operations()
				wo_order.save()

				work_orders.append(wo_order.name)
			else:
				errors.append(
					_("Row {0}: Bill of Materials not found for the Item {1}").format(
						d.idx, get_link_to_form("Item", d.item_code)
					)
				)

	if work_orders:
		work_orders_list = [get_link_to_form("Work Order", d) for d in work_orders]

		if len(work_orders) > 1:
			msgprint(
				_("The following {0} were created: {1}").format(
					frappe.bold(_("Work Orders")), "<br>" + ", ".join(work_orders_list)
				)
			)
		else:
			msgprint(
				_("The {0} {1} created sucessfully").format(frappe.bold(_("Work Order")), work_orders_list[0])
			)

	if errors:
		frappe.throw(
			_("Work Order cannot be created for following reason: <br> {0}").format(new_line_sep(errors))
		)

	return work_orders


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
	doc = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Pick List",
				"field_map": {"material_request_type": "purpose"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Material Request Item": {
				"doctype": "Pick List Item",
				"field_map": {"name": "material_request_item", "qty": "stock_qty"},
			},
		},
		target_doc,
	)

	doc.set_item_locations()

	return doc

def tienen_dato_en_comun(lista1, lista2):
    for elemento1 in lista1:
        if elemento1 in lista2:
            return True
    return False