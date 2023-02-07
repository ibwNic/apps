# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Nodo(Document):
	pass

@frappe.whitelist()
def get_portafolio():
		portafolio = frappe.db.sql(
			"""select name from `tabItem Group` where is_group = 0 and parent_item_group not in ('Productos','Todos los grupos de artículos')""",
		)

		#lista = get_barrio  
		lista = []
		for i in range (len(portafolio)):
			lista.append(portafolio[i][0])
		
		return lista