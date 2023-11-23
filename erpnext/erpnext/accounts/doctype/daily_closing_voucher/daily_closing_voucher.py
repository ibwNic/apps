# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model import default_fields
from frappe.utils import flt, cint, today
from frappe.utils import now, today
from datetime import datetime

class DailyClosingVoucher(Document):
	# pass
	def on_update(self):
		if self.docstatus==1:
			frappe.db.set_value(self.doctype, self.name, 'closing_date', now())
			# self.fecha_finalizado=now()
	
	def validate(self):
		self.details = []
		# frappe.msgprint("Se cerro "+ self.name)
		
		# frappe.db.set_value(self.doctype, self.name, 'closing_date',  datetime.now())
		# frappe.db.set_value(self.doctype, self.name, 'docstatus', 1)
		# self.reload()

		# for reference in list(self.references):
		# 	if frappe.db.get_value(reference.document_type, reference.document_name, 'docstatus') == 2:
		# 		self.references.remove(reference)
		# 		reference = reference.as_disct()
		# 		for field in default_fields:
		# 			reference.pop(field, None)
		# 		reference.doctype = "Daily Closing Cancelled Reference"
		# 		self.append('cancelled', reference)
		# 	else:
		# 		for account in frappe.get_all('Journal Entry Account',fields=['*'],filters={'parent': reference.document_name}):
		# 			det = self.get('details',{'account':account.account})
		# 			if det:
		# 				det = det[0]
		# 				append = 0
		# 			else:
		# 				det = frappe._dict({
		# 					"account": account.account,
		# 					"currency": account.account_currency,
		# 					"amount": 0.0,
		# 					"amount_in_company_currency": 0.0
		# 				})
		# 				append = 1
					
		# 			if account.debit:
		# 				det.amount += account.debit_in_account_currency
		# 				det.amount_in_company_currency += float(account.debit)
		# 			else:
		# 				det.amount -= account.credit_in_account_currency
		# 				det.amount_in_company_currency -= float(account.credit)
					
		# 			if append:
		# 				self.append('details',det)

@frappe.whitelist()
def cierre_dealer():
	
	data = frappe.db.sql("""select name from `tabDaily Closing Voucher` where docstatus = 0 and owner in ('lafise@ibw.com','bac1524@ibw.com','airpack@ibw.com','multipagos@ibw.com');""", as_dict=0)

	for cierre in data:
		doc = frappe.get_doc('Daily Closing Voucher',cierre[0])

		doc.flags.ignore_submit_comment = True
		doc.submit()
				
	return 'ok'