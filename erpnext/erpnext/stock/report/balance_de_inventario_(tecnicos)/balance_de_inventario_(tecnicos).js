// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Balance de Inventario (Tecnicos)"] = {
	"filters": [
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
		}
	]
};



