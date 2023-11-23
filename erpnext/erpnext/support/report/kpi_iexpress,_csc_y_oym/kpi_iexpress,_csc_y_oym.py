# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of
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

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	# if not any([filters.user]):
	# 	frappe.throw(_("Any one of following filters required: user"))
	
	sles = obtener_detalle_incidencias(filters)
	return sles


def obtener_detalle_incidencias(filters):
	# aqui va tu query
	query = """ select orden, customer, nombre, customer_group, municipio, address_line1, 
	tipo_de_orden, numero_de_telefono, servicio, estado, encuesta, canal, solicitado_por, 
	fecha_solicitud, fecha_finalizado, finalizado_por, tecnico, priority, duracion, averia, 
	sub_averia, detalla_avaria, averia_masiva, mes_dia, mes, hora, dia, year
	 from kpi_incidencias where estado = 'Finalizado' """
	if filters.from_date_f:
		query = query + " and  fecha_finalizado >= " + "'" + filters.from_date_f + "' COLLATE utf8mb4_general_ci " 
	if filters.to_date_f:
		query = query + " and  fecha_finalizado <= " + "'" + add_days(filters.to_date_f, 1) + "' COLLATE utf8mb4_general_ci "
	if filters.from_date_s:
		query = query + " and  fecha_solicitud >= " + "'" + filters.from_date_s + "' COLLATE utf8mb4_general_ci " 
	if filters.to_date_s:
		query = query + " and  fecha_solicitud <= " + "'" + add_days(filters.to_date_s, 1)+ "' COLLATE utf8mb4_general_ci "
	if filters.orden:
		query = query + " and orden = " + "'" + filters.orden + "'"  
	if filters.customer:
		query = query + " and customer = " + "'" + filters.customer + "'" 
	if filters.nombre:
		query = query + " and nombre like " + "'%" + filters.nombre + "%'" 
	if filters.customer_group:
		query = query + " and customer_group = " + "'" + filters.customer_group + "'" 
	if filters.servicio:
		query = query + " and servicio = " + "'" + filters.servicio + "'"  
	if filters.tipo_de_orden:
		query = query + " and tipo_de_orden = " + "'" + filters.tipo_de_orden + "'"  
	if filters.averia_masiva:
		query = query + " and averia_masiva = " + "'" + filters.averia_masiva + "'"  


	query = query + " order by fecha_finalizado desc "

	return frappe.db.sql(query)


def get_columns():
	return [
		{
			"fieldname": "orden",
			"fieldtype": "Link",
			"options":"Issue",
			"label": _("No de Orden"),
			
		},
		{
			"fieldname": "customer",
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
			"fieldname": "customer_group",
			"fieldtype": "Data",
			"label": _("Tipo Cliente"),
		},
		{
			"fieldname": "municipio",
			"fieldtype": "Data",
			"label": _("Municipio"),
		},
		{
			"fieldname": "address_line1",
			"fieldtype": "Data",
			"label": _("Direccion"),
		},
		{
			"fieldname": "tipo_de_orden",
			"fieldtype": "Data",
			"label": _("Tipo de Orden"),
		},
		{
			"fieldname": "numero_de_telefono",
			"fieldtype": "Data",
			"label": _("Telefonos"),
		},
		{
			"fieldname": "servicio",
			"fieldtype": "Data",
			"label": _("Servicio"),
		},
	
		{
			"fieldname": "estado",
			"fieldtype": "Data",
			"label": _("Estado"),
		
		},
		{
			"fieldname": "encuesta",
			"fieldtype": "Link",
			"options":"Feedback",
			"label": _("Encuesta"),	
		},
		{
			"fieldname": "canal",
			"fieldtype": "Data",
			"label": _("Canal"),	
		},
		{
			"fieldname": "solicitado_por",
			"fieldtype": "Data",
			"label": _("Solicitado por"),	
		},
		{
			"fieldname": "fecha_solicitud",
			"fieldtype": "Datetime",
			"label": _("Fecha Solicitud"),	
		},
		{
			"fieldname": "fecha_finalizado",
			"fieldtype": "Datetime",
			"label": _("Fecha Finalizado"),	
		},
		{
			"fieldname": "finalizado_por",
			"fieldtype": "Data",
			"label": _("Finalizado por"),	
		},
		{
			"fieldname": "tecnico",
			"fieldtype": "Data",
			"label": _("Tecnico"),	
		},
		{
			"fieldname": "priority",
			"fieldtype": "Data",
			"label": _("Prioridad"),	
		},
		{
			"fieldname": "duracion",
			"fieldtype": "Duration",
			"label": _("Tiempo total"),	
		},
		{
			"fieldname": "averia",
			"fieldtype": "Data",
			"label": _("Averia"),	
		},
		{
			"fieldname": "sub_averia",
			"fieldtype": "Data",
			"label": _("Sub Averia"),	
		},
		{
			"fieldname": "detalla_avaria",
			"fieldtype": "Data",
			"label": _("Detalle averia"),	
		},
		{
			"fieldname": "averia_masiva",
			"fieldtype": "Link",
			"label": _("Averia Masiva"),
			"options":"AveriasMasivas"	
		},
		{
			"fieldname": "mes_dia",
			"fieldtype": "Data",
			"label": _("Mes_dia"),	
		},
		{
			"fieldname": "mes",
			"fieldtype": "Data",
			"label": _("Mes"),	
		},
		{
			"fieldname": "hora",
			"fieldtype": "Data",
			"label": _("Hora"),	
		},
		{
			"fieldname": "dia",
			"fieldtype": "Data",
			"label": _("Dia"),	
		},
		{
			"fieldname": "year",
			"fieldtype": "Data",
			"label": _("Año"),	
		},
		
		
	]