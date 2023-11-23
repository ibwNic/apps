// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Movimientos de Inventario"] = {
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
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "actual_qty" && data && data.actual_qty > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}
		else if (column.fieldname == "actual_qty" && data && data.actual_qty < 0) {
			value = "<span style='color:red'>" + value + "</span>";
		}

		return value;
	}
};
