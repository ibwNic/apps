# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	# if not any([filters.user]):
	# 	frappe.throw(_("Any one of following filters required: user"))
	
	sles = obtener_balance_de_inventario(filters)
	return sles


def obtener_balance_de_inventario(filters):
	# aqui va tu query
	# query = """   SELECT sle.posting_date, atec.parent as tecnico, sle.warehouse, sle.item_code, 
	# 		ROUND( SUM(sle.actual_qty) +
	# 		(SELECT slex.qty_after_transaction - slex.actual_qty from `tabStock Ledger Entry` slex  
	# 		where slex.item_code = sle.item_code and slex.warehouse = sle.warehouse
	# 		AND slex.is_cancelled = 0 and slex.posting_date >= '2023-04-30' ORDER BY slex.posting_date asc , slex.posting_time asc limit 1),2 ) 
	# 		as cantidad, sle.stock_uom,
	# 		(SELECT GROUP_CONCAT(name SEPARATOR ', ') FROM `tabSerial No` where warehouse = sle.warehouse and item_code = sle.item_code) as serial_no, 
	# 		sle.voucher_no as ultima_transferencia ,
	# 		(select se.modified_by from `tabStock Entry` se where se.name = sle.voucher_no ) as validado_por
	# 		FROM  `tabStock Ledger Entry` sle
	# 		inner join `tabAlmacenes de Tecnico` atec on sle.warehouse = atec.almacen
	# 		where
	# 		sle.is_cancelled = 0  and sle.posting_date >= '2023-04-30'  """
	query = """   SELECT sle.posting_date, atec.parent as tecnico, sle.warehouse, sle.item_code, 

		ROUND( (SELECT slex.qty_after_transaction  from `tabStock Ledger Entry` slex  
			where slex.item_code = sle.item_code and slex.warehouse = sle.warehouse
			AND slex.is_cancelled = 0 and slex.posting_date >= '2023-04-30' ORDER BY slex.posting_date desc , slex.posting_time desc, slex.creation desc limit 1),2 ) 
		as cantidad,
		
			sle.stock_uom,
		(SELECT GROUP_CONCAT(name SEPARATOR ', ') FROM `tabSerial No` where warehouse = sle.warehouse and item_code = sle.item_code) as serial_no, 
		sle.voucher_no as ultima_transferencia ,
		(select se.modified_by from `tabStock Entry` se where se.name = sle.voucher_no ) as validado_por
		FROM  `tabStock Ledger Entry` sle
		inner join `tabAlmacenes de Tecnico` atec on sle.warehouse = atec.almacen
		where
		sle.is_cancelled = 0  and sle.posting_date >= '2023-04-30'  """

	query = query + " and atec.parent  = (SELECT t.name from `tabTecnico` t where t.usuario_reporte = " + "'" + frappe.session.user + "'" + " limit 1) "

	if filters.warehouse:
		query = query + " and sle.warehouse = " + "'" + filters.warehouse + "'" 

	if filters.item_code:
		query = query + " and sle.item_code = " + "'" + filters.item_code + "'" 

	query = query + " group by sle.item_code, sle.warehouse, atec.parent ORDER BY CONCAT(sle.posting_date, ' ', sle.posting_time)    desc , sle.name desc "

	return frappe.db.sql(query)


def get_columns():
	return [
		{
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"label": _("Fecha"),
			
		},
		{
			"fieldname": "tecnico",
			"fieldtype": "Data",
			"label": _("Tecnico"),
		
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Data",
			"label": _("Almacen"),
		},
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": _("Producto"),
			"options": "Item",
		},
		{
			"fieldname": "cantidad",
			"fieldtype": "Float",
			"label": _("Cantidad"),
		},
		{
			"fieldname": "stock_uom",
			"fieldtype": "Data",
			"label": _("UOM"),
		},
		{
			"fieldname": "serial_no",
			"fieldtype": "Data",
			"label": _("Numero de Serie"),
		},
		{
			"fieldname": "ultima_transferencia",
			"fieldtype": "Data",
			"label": _("Ultima transferencia"),
		},
	
		{
			"fieldname": "validado_por",
			"fieldtype": "Data",
			"label": _("Validado por"),
		
		},
		
		
	]