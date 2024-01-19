# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RutasdeFacturacion(Document):
	pass

# @frappe.whitelist()
# def get_barrios():
# 		get_barrio = frappe.db.sql(
# 			""" select t2.name,t2.parent_territory as municipio, (select t1.parent_territory from `tabTerritory` t1 where t1.name=t2.parent_territory) departamento from `tabTerritory` t2 
#  			where t2.tipo_territorio='Barrio' and  t2.parent_territory in (select t1.name from `tabTerritory` t1 where t1.parent_territory='managua') 
#  			and t2.name not like '%tipi%' and t2.parent_territory not like '%Tipitapa%' and name not in (select barrios from `tabBarrios y Rutas`); """,
# 		)

# 		#lista = get_barrio  
# 		lista = []
# 		for i in range (len(get_barrio)):
# 			lista.append(get_barrio[i][0])
		
# 		return lista

