# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime
from frappe.utils import date_diff, get_datetime, now_datetime, now,time_diff_in_seconds, unique
import frappe
from frappe.model.document import Document

class AveriasMasivas(Document):
	# pass
	def on_update(self):
		# frappe.msgprint(self.workflow_state)
		if self.workflow_state=="Abierto":
			frappe.db.set_value(self.doctype, self.name, 'fecha_creado', now())
		
		if self.workflow_state=="Finalizado":
			# frappe.db.set_value(self.doctype, self.name, 'fecha_finalizado', now())
			frappe.db.set_value("Issue", {"name": i.issue_id}, 'workflow_state', "Finalizado",)
		
		if self.workflow_state=="Cancelar":
			frappe.db.set_value(self.doctype, self.name, 'fecha_cancelado', now())



		try:
			if self.workflow_state=="Finalizado":
				for i in self.incidencias:
					# frappe.msgprint(i.issue_id)
					update_issue = frappe.get_doc("Issue", {"name": i.issue_id})
					update_issue.update(
							{
								# "workflow_state": "Finalizado",
								"status":"Closed",
								"docstatus":1,
								"fecha_finalizado":datetime.now()
							}
						)
					update_issue.save()
					frappe.db.set_value("Issue", {"name": i.issue_id}, 'workflow_state', "Finalizado",)
		except Exception as e:
				frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))					
				# frappe.db.set_value("Issue", {"name": i.issue_id}, 'fecha_finalizado', now())
			# upd_fecha_s = frappe.get_doc("Issue", {"averia_masivo": self.name})	
			

@frappe.whitelist()
def get_Portafolio(Nodo,name):
		if not frappe.db.exists("Portafolio AveriasMasivas", {"parent": name }):
			doc = frappe.get_doc("AveriasMasivas",name)
			n = doc.name
			# frappe.msgprint(n)
			get_portafolios = frappe.db.sql(
				"""select portafolio from `tabPortafolio Vinculado` where parent = %(Nodo)s""",
				{"Nodo": Nodo},
				)	
			#return get_portafolios
			try:
					for nodo in get_portafolios:
						
						nodoadd = frappe.new_doc("Portafolio AveriasMasivas")
						nodoadd.update(
							{
								"portafolio": nodo[0],
								"parent": n,
								"parentfield": "portafolio",
								"paremttype": "AveriasMasivas"
							}
						)
						doc.portafolio.append(nodoadd)	
					doc.save()
					frappe.db.commit()
			except Exception as e:
					frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))

@frappe.whitelist()
def get_IncidenciasVinculadas(name):
		if not frappe.db.exists("Issue Vinculado Averia", {"parent": name }):
			doc = frappe.get_doc("AveriasMasivas",name)
			n = doc.name
			frappe.msgprint(n)
			get_Issue = frappe.db.sql(
				"""select name from `tabIssue` where averia_masivo = %(nameId)s""",
				{"nameId": name},
				)	
			# return get_Issue
			try:
					for issue in get_Issue:

						issueadd = frappe.new_doc("Issue Vinculado Averia")
						issueadd.update(
							{
								"issue_id": issue[0],
								"parent": n,
								"parentfield": "incidencias",
							}
						)
						doc.incidencias.append(issueadd)	
					doc.save()
					frappe.db.commit()
			except Exception as e:
					frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))
