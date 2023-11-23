// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Data Planes CRM Prueba"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "Fecha Desde",
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": "Fecha Hasta",
		},
		{
			"fieldname":"tecnico",
			"fieldtype":"Link",
			"label": "Tecnico de bodega",
			"options": "Tecnico",
			get_query: function() {
				return {
					filters: {activo: 1}
				}
			}
		},
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": "Producto",
			"options": "Item",
			get_query: function() {
				return {
					filters: {is_stock_item: 1}
				}
			}
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": "Almacén",
			"options": "Warehouse",
		},
		{
			"fieldname": "tipo_movimiento",
			"fieldtype": "Select",
			"label": "Tipo Movimiento",
			"options": ["","Entrada","Salida"]
		},
	]
	
};
