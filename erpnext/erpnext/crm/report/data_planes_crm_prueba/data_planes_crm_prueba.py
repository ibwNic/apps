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
	query = """  SELECT * FROM vw_Data_Planes_all WHERE cliente is not null; """

	if filters.cliente:
		query = query + " and cliente = " + "'" + filters.cliente + "'" 

	if filters.customer_name:
		query = query + " and customer_name like " + "'%" + filters.customer_name + "%'" 

	if filters.estado:
		query = query + " and estado = " + "'" + filters.estado + "'" 

	if filters.from_date:
		query = query + " and  portafolio = " + "'" + filters.portafolio + "'" 

	if filters.Municipio_Cliente:
		query = query + " and Municipio_Cliente = " + "'" + filters.Municipio_Cliente + "'"
	

	return frappe.db.sql(query)


def get_columns():
	return [
		{
			"fieldname": "cliente",
			"fieldtype": "Link",
			"label": _("Cliente"),
			"options": "Customer",			
		},
		{
			"fieldname": "nombre",
			"fieldtype": "Data",
			"label": _("Nombre"),
		},
		{
			"fieldname": "Compania",
			"fieldtype": "Data",
			"label": _("Compañia"),
		},
		{
			"fieldname": "first_name",
			"fieldtype": "Data",
			"label": _("Nombres"),
		},
		{
			"fieldname": "last_name",
			"fieldtype": "Data",
			"label": _("Apellidos"),
		},
		{
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"label": _("Nombre completo"),
		},
		{
			"fieldname": "estado_cliente",
			"fieldtype": "Data",
			"label": _("Estado Cliente"),
		},
		{
			"fieldname": "departamento_Cliente",
			"fieldtype": "Data",
			"label": _("Departamento cliente"),
		},
		{
			"fieldname": "Municipio_Cliente",
			"fieldtype": "Data",
			"label": _("Municipio cliente"),
		},
		{
			"fieldname": "Barrio_Cliente",
			"fieldtype": "Data",
			"label": _("Barrio cliente"),
		},
	
		{
			"fieldname": "departamento",
			"fieldtype": "Data",
			"label": _("Departamento plan"),
		
		},
		{
			"fieldname": "municipio",
			"fieldtype": "Data",
			"label": _("Municipio plan"),
		
		},
		{
			"fieldname": "barrio",
			"fieldtype": "Data",
			"label": _("Barrio plan"),
		
		},
		{
			"fieldname": "vendedor",
			"fieldtype": "Data",
			"label": _("vendedor"),
		
		},
		{
			"fieldname": "N_Celular",
			"fieldtype": "Data",
			"label": _("N Celular"),
		
		},
		
	]




