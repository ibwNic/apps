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
	
	sles = obtener_detalle_service_order(filters)
	return sles


def obtener_detalle_service_order(filters):
	# aqui va tu query
	query = """  select * from service_order_ot where fecha_solicitud > '2023-05-08 00:00:00.000000 '"""
	if filters.from_date_f:
		query = query + " and  fecha_finalizado >= " + "'" + filters.from_date_f + "' COLLATE utf8mb4_general_ci " 
	if filters.to_date_f:
		query = query + " and  fecha_finalizado <= " + "'" + filters.to_date_f + "' COLLATE utf8mb4_general_ci "
	if filters.from_date_s:
		query = query + " and  fecha_solicitud >= " + "'" + filters.from_date_s + "' COLLATE utf8mb4_general_ci " 
	if filters.to_date_s:
		query = query + " and  fecha_solicitud <= " + "'" + filters.to_date_s + "' COLLATE utf8mb4_general_ci "
	if filters.name:
		query = query + " and name = " + "'" + filters.name + "'"  
	if filters.customer:
		query = query + " and tercero = " + "'" + filters.customer + "'" 
	if filters.nombre:
		query = query + " and nombre like " + "'%" + filters.nombre + "%'" 
	if filters.portafolio:
		query = query + " and portafolio = " + "'" + filters.portafolio + "'"  
	if filters.tipo_de_orden:
		query = query + " and tipo_de_orden = " + "'" + filters.tipo_de_orden + "'"  
	if filters.estado:
		query = query + " and workflow_state = " + "'" + filters.estado + "'" 


	return frappe.db.sql(query)


def get_columns():
	return [
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"options":"Service Order",
			"label": _("No de Orden"),
			
		},
		{
			"fieldname": "tercero",
			"fieldtype": "Date",
			"fieldtype": "Link",
			"options":"Customer",
			"label": _("Cliente"),
		
		},
		{
			"fieldname": "nombre",
			"fieldtype": "Data",
			"label": _("Nombre de Cliente"),
		},
		{
			"fieldname": "tipo_cliente",
			"fieldtype": "Data",
			"label": _("Tipo Cliente"),
		},
		{
			"fieldname": "direccion",
			"fieldtype": "Data",
			"label": _("Direccion"),
		},
		{
			"fieldname": "tipo_de_orden",
			"fieldtype": "Data",
			"label": _("Tipo de Orden"),
		},
		{
			"fieldname": "portafolio",
			"fieldtype": "Data",
			"label": _("Servicio"),
		},
		{
			"fieldname": "workflow_state",
			"fieldtype": "Data",
			"label": _("Estado"),
		},
		{
			"fieldname": "fecha_solicitud",
			"fieldtype": "Datetime",
			"label": _("Fecha solicitud"),
		},
		{
			"fieldname": "solicitado_por",
			"fieldtype": "Data",
			"label": _("Solicitado por"),
		},
		{
			"fieldname": "fecha_finalizado",
			"fieldtype": "Datetime",
			"label": _("fecha Finalizado"),
		},
		{
			"fieldname": "finalizado_por",
			"fieldtype": "Data",
			"label": _("Finalizado por"),
		},
		{
			"fieldname": "descripcion",
			"fieldtype": "Data",
			"label": _("descripcion"),
		},
		{
			"fieldname": "solucion",
			"fieldtype": "Data",
			"label": _("solucion"),
		},
		{
			"fieldname": "vendedor",
			"fieldtype": "Data",
			"label": _("Vendedor"),
		},
		{
			"fieldname": "barrio",
			"fieldtype": "Data",
			"label": _("Barrio"),
		},
		{
			"fieldname": "municipio",
			"fieldtype": "Data",
			"label": _("Municipio"),
		},
		{
			"fieldname": "departamento",
			"fieldtype": "Data",
			"label": _("Departamento"),
		},
		{
			"fieldname": "tiempo",
			"fieldtype": "Duration",
			"label": _("Tiempo"),
		},
		{
			"fieldname": "horas",
			"fieldtype": "Float",
			"label": _("Horas"),
		},
		{
			"fieldname": "equipo",
			"fieldtype": "Data",
			"label": _("equipo"),
		},
		{
			"fieldname": "fecha_seguimiento",
			"fieldtype": "Datetime",
			"label": _("Fecha seguimiento"),
		},
		{
			"fieldname": "fecha_atendido",
			"fieldtype": "Datetime",
			"label": _("Fecha atendido"),
		},
		{
			"fieldname": "Tiempo_O",
			"fieldtype": "Duration",
			"label": _("Tiempo_O"),
		},
		{
			"fieldname": "Tiempo_O_horas",
			"fieldtype": "Float",
			"label": _("Tiempo_O_horas"),
		},
		{
			"fieldname": "cuadrilla",
			"fieldtype": "Data",
			"label": _("cuadrilla"),
		},
		
		
	]