// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Ordenes de Servicio Detalle"] = {
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
			"options": ["","INSTALACION","TRASLADO","SITE SURVEY","INSTALACION OTC","CABLEADO","REACTIVACION","APROVISIONAMIENTO","CORTE","RECONEXION","TV ADICIONAL","PRESUPUESTO",""],
		},
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"label": "Orden",
			"options": "Service Order",
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
			"fieldname": "porfafolio",
			"fieldtype": "Link",
			"label": "Servicio",
			"options": "Item Group",
		},
		
	]
};
