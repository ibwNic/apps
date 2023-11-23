// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Altas del mes y contabilizacion"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "Fecha Desde",
			"reqd":1,
			"default": frappe.datetime.get_today()

		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": "Fecha Hasta",
			"reqd":1,
			"default": frappe.datetime.get_today()

		},
		{
			"fieldname":"cliente",
			"fieldtype":"Link",
			"label": "Cliente",
			"options": "Customer",
		},
		{
			"fieldname":"vendedor",
			"fieldtype":"Link",
			"label": "Vendedor",
			"options": "Sales Person",
		},
		{
			"fieldname": "portafolio",
			"fieldtype": "Link",
			"label": "Portafolio",
			"options": "Item Group",
		}
	],
};
