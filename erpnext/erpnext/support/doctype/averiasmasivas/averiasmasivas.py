# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime
from frappe.utils import date_diff, get_datetime, now_datetime, now,time_diff_in_seconds, unique
import frappe
from frappe.model.document import Document

class AveriasMasivas(Document):
	pass
	def on_update(self):
		if self.workflow_state == "Finalizado":

			incidencias = frappe.db.sql(
			"""select * from `tabIssue` where averia_masivo=%(cis)s and workflow_state not in ('Cancelado','Finalizado') limit 20000""",
			{"cis": self.name},
			)

			
				# frappe.msgprint("try")	
			for issue in incidencias:
				
				add_AveriasMasivas = frappe.get_doc({
					"doctype": "Issue Vinculado Averia",
					"issue_id": issue[0],
					"parent": self.name,
					"parentfield": "incidencias",
					"parenttype": "AveriasMasivas"
				})
				add_AveriasMasivas.insert()

			if self.ordenes:
				for orden in self.ordenes:
					if orden.estado != "Finalizado":
						frappe.msgprint(f"No puedes finalizar esta avería porque la orden {orden.issue} no se ha finalizado.")
						frappe.db.set_value(self.doctype,self.name,"workflow_state","Abierto")
						frappe.db.set_value(self.doctype,self.name,"docstatus",0)
						
			if not self.solucion:
				frappe.msgprint(f"Para finalizar averia masiva debe escribir una solucion")
				frappe.db.set_value(self.doctype,self.name,"workflow_state","Abierto")
				frappe.db.set_value(self.doctype,self.name,"docstatus",0)
			
						
			if self.incidencias and self.solucion:
				for i in self.incidencias:
					frappe.db.sql(""" update `tabIssue` set workflow_state = "Finalizado", fecha_finalizado = now(), docstatus = 1, resolution_details = %(solucion)s where name = %(issue)s;""",{"issue":i.issue_id,"solucion":self.solucion})
					frappe.db.sql(""" update `tabIssue Detalle` set estado = "Finalizado", docstatus = 1 where issue = %(issue)s;""",{"issue":i.issue_id,"solucion":self.solucion})

@frappe.whitelist()
def get_Portafolio(Nodo,name):
	if not frappe.db.exists("Portafolio AveriasMasivas", {"parent": name }):
		doc = frappe.get_doc("AveriasMasivas",name)
		n = doc.name
		get_portafolios = frappe.db.sql(
			"""select portafolio from `tabPortafolio Vinculado` where parent = %(Nodo)s""",
			{"Nodo": Nodo},
			)	
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


def cerrar_incidencias_masivas():
	frappe.db.sql(""" UPDATE `tabIssue` i inner join `tabAveriasMasivas` av on i.averia_masivo = av.name
			SET i.workflow_state = 'Finalizado', i. docstatus = 1, i.resolution_details = av.solucion
			WHERE i.workflow_state != 'Finalizado' and av.workflow_state = 'Finalizado'; """)