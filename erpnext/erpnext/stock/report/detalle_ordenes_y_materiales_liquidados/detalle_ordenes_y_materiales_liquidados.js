// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Detalle Ordenes y Materiales Liquidados"] = {
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
			"fieldname": "tipo_de_orden",
			"fieldtype": "Select",
			"label": "Tipo de Orden",
			"options": ["","INSTALACION","TRASLADO","INSTALACION OTC","TV ADICIONAL","Liquidacion de Materiales Atrasada","CABLEADO","Averia","Ticket Iexpress","Ticket"],
		},
		{
			"fieldname": "portafolio",
			"fieldtype": "Link",
			"label": "Portafolio",
			"options": "Item Group",
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
			get_query: function() {
				return {
					filters: {disabled: 0}
				}
			}
		},
		{
			"fieldname": "Tecnico_principal",
			"fieldtype": "Link",
			"label": "Tecnico principal",
			"options": "Tecnico",
			get_query: function() {
				return {
					filters: {activo: 1}
				}
			}
		}
	 ]
};
