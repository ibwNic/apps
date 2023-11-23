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
	
	sles = obtener_materiales_liquidados(filters)
	return sles


def obtener_materiales_liquidados(filters):
	# aqui va tu query
	query = """ select * from vw_liquidaciones_oym where tipo_de_orden <> 'DESINSTALACION'  """
	
	if filters.from_date:
		query = query + " and  fecha_liquidado >= " + "'" + filters.from_date + "' COLLATE utf8mb4_general_ci " 

	if filters.to_date:
		query = query + " and  fecha_liquidado <= " + "'" + filters.to_date + "' COLLATE utf8mb4_general_ci "

	if filters.tipo_de_orden:
		query = query + " and tipo_de_orden = " + "'" + filters.tipo_de_orden + "'"  
	
	if filters.portafolio:
		query = query + " and portafolio = " + "'" + filters.portafolio + "'"  

	if filters.item_code:
		query = query + " and item_code = " + "'" + filters.item_code + "'"  

	if filters.s_warehouse:
		query = query + " and s_warehouse = " + "'" + filters.s_warehouse + "'"

	if filters.Tecnico_principal:
		query = query + " and Tecnico_principal = " + "'" + filters.Tecnico_principal + "'"


	query = query + " order by fecha_liquidado desc "

	return frappe.db.sql(query)


def get_columns():
	return [
		{
			"fieldname": "service_order",
			"fieldtype": "Data",
			"label": _("Orden"),
			
		},
		{
			"fieldname": "fecha_liquidado",
			"fieldtype": "Date",
			"label": _("Fecha liquidado"),
		
		},
		{
			"fieldname": "tipo_de_orden",
			"fieldtype": "Data",
			"label": _("Tipo de orden"),
		},
		{
			"fieldname": "portafolio",
			"fieldtype": "Data",
			"label": _("Portafolio"),
		},
		{
			"fieldname": "item_code",
			"fieldtype": "Data",
			"label": _("Producto"),
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
			"fieldname": "s_warehouse",
			"fieldtype": "Data",
			"label": _("Bodega"),
		},
	
		{
			"fieldname": "Tecnico_principal",
			"fieldtype": "Data",
			"label": _("Tecnico Principal"),
		
		},
		{
			"fieldname": "cuadrilla",
			"fieldtype": "Data",
			"label": _("Cuadrilla"),	
		},
		{
			"fieldname": "Cliente",
			"fieldtype": "Data",
			"label": _("Cliente"),	
		},
		{
			"fieldname": "Departamento",
			"fieldtype": "Data",
			"label": _("Departamento"),	
		},
		{
			"fieldname": "Nombre_Cliente",
			"fieldtype": "Data",
			"label": _("Nombre del Cliente"),	
		},
		{
			"fieldname": "clasificacion",
			"fieldtype": "Data",
			"label": _("Clasificacion"),	
		},
		
		
	]