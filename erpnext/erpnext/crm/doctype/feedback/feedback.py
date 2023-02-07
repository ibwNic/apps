# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from frappe.model.document import Document
import frappe
from frappe import _
from erpnext import get_default_company
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
class Feedback(Document):
	pass

# @frappe.whitelist()
# def cargar_preguntas(encuesta):
# 	preguntas = frappe.db.get_values("Preguntas Encuesta",{"parent":encuesta},["name","pregunta","respuestas"])
# 	mr = frappe.new_doc('Feedback')
# 	mr.update({
# 		'encuesta':encuesta
# 	})
# 	for m in preguntas:
# 		item1 = mr.append('feedback_preguntas', {"pregunta": ""})	
# 		item1.pregunta_id = m[0]			
# 		item1.pregunta = m[1]
# 	return {'docs': mr.as_dict()}

# @frappe.whitelist()
# def respuestas(name):
# 	resp = frappe.db.get_value("Preguntas Encuesta",{"name":name},"respuestas")
# 	if "\n" in resp:
# 		resp = resp.split("\n")
# 	return resp