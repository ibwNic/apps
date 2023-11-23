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
	
	sles = obtener_movimientos_de_inventario(filters)
	return sles


def obtener_movimientos_de_inventario(filters):
	# aqui va tu query
	query = """   select * from movimientos_de_inventario where """

	query = query + " tecnico = (SELECT t.name from `tabTecnico` t where t.usuario_reporte = " + "'" + frappe.session.user + "'" + " limit 1)"

	if filters.warehouse:
		query = query + " and warehouse = " + "'" + filters.warehouse + "'" 

	if filters.item_code:
		query = query + " and item_code = " + "'" + filters.item_code + "'" 

	if filters.from_date:
		query = query + " and  posting_date >= " + "'" + filters.from_date + "' COLLATE utf8mb4_general_ci" 

	if filters.to_date:
		query = query + " and  posting_date <= " + "'" + filters.to_date + "' COLLATE utf8mb4_general_ci" 

	if filters.tipo_movimiento:
		query = query + " and tipo_movimiento = " + "'" + filters.tipo_movimiento + "' COLLATE utf8mb4_general_ci"
	
	query = query + "  ORDER BY posting_time asc"

	return frappe.db.sql(query)


def get_columns():
	return [
			{
			"fieldname": "posting_time",
			"fieldtype": "Datetime",
			"label": _("Fecha y hora"),
			
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
			"fieldname": "stock_uom",
			"fieldtype": "Data",
			"label": _("UOM"),
		},
		{
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"label": _("Cantidad en movimiento"),
		},
		{
			"fieldname": "qty_after_transaction",
			"fieldtype": "Float",
			"label": _("Cantidad despues de movimiento"),
		},
		{
			"fieldname": "orden_de_servicio",
			"fieldtype": "Data",
			"label": _("Orden de Servicio"),
		},
		{
			"fieldname": "cliente",
			"fieldtype": "Data",
			"label": _("Cliente"),
		},
		{
			"fieldname": "tipo_movimiento",
			"fieldtype": "Select",
			"label": _("Tipo Movimiento"),
			"options": ["Entrada", "Salida"],
		},
	
		{
			"fieldname": "voucher_no",
			"fieldtype": "Data",
			"label": _("Voucher No"),
		
		},
		{
			"fieldname": "tecnico",
			"fieldtype": "Data",
			"label": _("Tecnico"),
		
		},
		
	]




