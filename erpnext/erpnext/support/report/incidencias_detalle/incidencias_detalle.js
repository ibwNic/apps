// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Incidencias Detalle"] = {
	"filters": [
		{
			"fieldname": "from_date_f",
			"fieldtype": "Date",
			"label": "Fecha Finalizado Desde",
		},
		{
			"fieldname": "to_date_f",
			"fieldtype": "Date",
			"label": "Fecha Finalizado Hasta",
		},
		{
			"fieldname": "from_date_s",
			"fieldtype": "Date",
			"label": "Fecha Solicitado Desde",
		},
		{
			"fieldname": "to_date_s",
			"fieldtype": "Date",
			"label": "Fecha Solicitado Hasta",
		},
		{
			"fieldname": "tipo_de_orden",
			"fieldtype": "Select",
			"label": "Tipo de Orden",
			"options": ["","Tramite","Averia","Ticket Iexpress","Ticket"],
		},
		{
			"fieldname": "orden",
			"fieldtype": "Link",
			"label": "Orden",
			"options": "Issue",
		},
		{
			"fieldname": "estado",
			"fieldtype": "Select",
			"label": "Estado",
			"options": ["","Abierto","Seguimiento","Atendido","Finalizado", "Pendiente"],
		},
		{
			"fieldname": "customer",
			"fieldtype": "Link",
			"label": "Cliente",
			"options": "Customer",
		},
		{
			"fieldname": "nombre",
			"fieldtype": "Data",
			"label": "Nombre Cliente",
		},
		{
			"fieldname": "customer_group",
			"fieldtype": "Link",
			"label": "Tipo Cliente",
			"options": "Customer Group",
		},
		{
			"fieldname": "servicio",
			"fieldtype": "Link",
			"label": "Servicio",
			"options": "Item Group",
		},
		{
			"fieldname": "averia_masiva",
			"fieldtype": "Link",
			"label": "Averia Masiva",
			"options": "AveriasMasivas",
		}
		
	]
};
