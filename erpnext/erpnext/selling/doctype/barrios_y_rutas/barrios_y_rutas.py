# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BarriosyRutas(Document):
	pass

@frappe.whitelist()
def get_barrios():
		get_barrio = frappe.db.sql(
			"""select * from `tabTerritory` where name not in (select barrios from `tabBarrios y Rutas`); """,
		)	
	
		return get_barrio




	


