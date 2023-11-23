# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NotadeCredito(Document):
	def on_submit(self):
		self.agregar_cod_Nta_Arreglo()

	def on_cancel(self):
		for documento in self.get("detalle"):
			je = frappe.get_doc("Journal Entry", documento.documento)
			je.cancel()

	def agregar_cod_Nta_Arreglo(self):
		if self.codigo_arreglo_de_pago:
			frappe.db.set_value('Arreglo de Pago', self.codigo_arreglo_de_pago, 'nota_de_credito', self.name)