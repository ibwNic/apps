# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import time
from frappe.model.document import Document

class SalidadeBodegaERP(Document):
	pass

@frappe.whitelist()
def generar_vista_previa(name):
	salida = frappe.get_doc("Salida de Bodega ERP", name)
	if not salida.fecha_desde or not salida.fecha_hasta:
		return
	#frappe.msgprint(str(salida.fecha_desde))
	like = '%OS%'
	query = frappe.db.sql("""  select (select posting_date from `tabStock Entry` where name=t1.parent) as posting_date,t1.parent, t1.item_code, t1.qty, t1.uom, t1.serial_no, t1.service_order,
		(select portafolio from  `tabService Order` where name = t1.service_order union all 
		select servicio from  `tabIssue` where name = t1.service_order  ) as portafolio,
		(select tecnico from  `tabService Order` where name = t1.service_order union all
		select tecnico from  `tabIssue` where name = t1.service_order) as Tecnico, 
		(select tercero from  `tabService Order` where name = t1.service_order union all
		select customer from  `tabIssue` where name = t1.service_order) as Tercero,
		CASE WHEN  t1.service_order LIKE %(like)s THEN
		(select tipo_de_orden from  `tabService Order` where name = t1.service_order) ELSE 
		(select tipo_de_orden from  `tabIssue` where name = t1.service_order)  END AS tipo_de_orden
		from `tabStock Entry Detail` t1
		where t1.parent in (select name from `tabStock Entry` where stock_entry_type = 'Material Issue' and docstatus = 1) 
		and t1.service_order is not null 
		and t1.parent in (select name from `tabStock Entry` where posting_date>= %(desde)s and posting_date<= %(hasta)s)
		order by service_order desc limit 5000 ;""",{"desde":str(salida.fecha_desde),"hasta":str(salida.fecha_hasta),"like":like})

#	resultado = frappe.db.sql(query,{"desde":str(salida.fecha_desde),"hasta":str(salida.fecha_hasta)})
	
	frappe.db.sql(
			"""
			DELETE FROM `tabMateriales Liquidados`
			WHERE parent = %(parent)s""",{"parent": name}
		)	
	time.sleep(1)

#name, creation, modified, modified_by, owner, docstatus, idx, stock_entry, item_code,
#  qty, uom, order, order_type, posting_date, parent, parentfield, parenttype, serial_no, tecnico, customer
	
	try:
		for res in query:
			
			child = frappe.new_doc("Materiales Liquidados")
			child.update(
				{
					"parent": name,
					"parentfield": "materiales_liquidados",
					"parenttype": "Salida de Bodega ERP",
					"posting_date":res[0],
					"stock_entry":res[1],
					"item_code":res[2],
					"qty":res[3],
					"uom":res[4],
					"serial_no":res[5],
					"order":res[6],
					"portafolio":res[7],
					"tecnico":res[8],
					"customer":res[9],
					"order_type":res[10],
				
					
				}
			)
			salida.materiales_liquidados.append(child)	
			salida.save(ignore_permissions=True)
	except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))	

	return query