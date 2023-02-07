# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Colectores(Document):
	pass

@frappe.whitelist()
def get_account(account):
	acc ='%'+ account +'%'
	
	account = frappe.db.sql(
		"""select name from tabAccount where name like %(filtro)s""",
		{"filtro": acc},
	)

	# #lista = get_barrio  
	lista = []
	try:

		for i in range(len(account)):
			lista.append(account[i][0])
		
		
	except:
		pass

	return lista