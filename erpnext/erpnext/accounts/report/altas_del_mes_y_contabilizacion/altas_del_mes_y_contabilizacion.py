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
from erpnext.stock.utils import add_additional_uom_columns, is_reposting_item_valuation_in_progress


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	if not filters.from_date:
		frappe.msgprint(_("Any one of following filters required: Fecha Desde"))
		return
	if not filters.to_date:
		frappe.msgprint(_("Any one of following filters required: Fecha Hasta"))
		return
	
	sles = obtener_detalle_altas(filters)
	return sles


def obtener_detalle_altas(filters):
	# aqui va tu query
	query = """ select
		s.party as cliente,
		s.nombre_del_cliente as nombre,
		cu.company_name as Compania,
		ad.departamento,
		cu.customer_group as Tipo_Cliente,
		spd.name as plan_id,
		sp.compresion as compresion,
		(case when sp.compresion='1:1' then 'Corporativo' when sp.compresion='7:1' then 'Residencial'  else 'Pyme' end ) Tipo_Servicio,
		spd.estado_plan as estado,
		spd.plan,
		(select i.stock_uom from `tabItem` i where i.name=sp.item ) as Velocidad,
		spd.currency as Moneda,
		spd.cost as precio,
				CASE
					WHEN `spd`.`currency` = 'USD' THEN `spd`.`cost`
					WHEN `spd`.`currency` = 'NIO' THEN `sp`.`cost` / `sp`.`tipocambio`
				END AS `precio_dolar`,
		sp.item_group as portafolio,
		spd.service_start,
		s.vendedor,
		(select op.name from `tabCustomer` cus inner join `tabOpportunity` op on  op.customer = cus.name where op.customer = (cu.name) limit 1)as Payback,
		(select sales.parent_sales_person from `tabSales Person` sales where sales.name = (select sales.parent_sales_person from `tabSubscription` sub inner join `tabSales Person` sales on sales.name = sub.vendedor where sales.name = (s.vendedor)limit 1)) as Canal,
		(select canal_general from `tabSales Person` where name = (select sales.parent_sales_person from `tabSales Person` sales where sales.name = (select sales.parent_sales_person from `tabSubscription` sub inner join `tabSales Person` sales on sales.name = sub.vendedor where sales.name = (s.vendedor) limit 1)limit 1) limit 1) as Canal_General,
		(select GROUP_CONCAT(CONCAT('"', equipo, '"')) AS N_Serie from `tabSubscription Plan Equipos` t1 inner join `tabSubscription` t2 on t1.parent = t2.name where t1.parent = (s.name) limit 1) as Mac,
		(select IF(usuario = 'emilio.jimenez@ibw.com', (select parent_sales_person from `tabSales Person` where name = (s.vendedor)),(replace(usuario, '@ibw.com', ''))) as  Coodinador from `tabSales Person` where name = (select sales.parent_sales_person from `tabSales Person` sales where sales.name = (select sales.parent_sales_person from `tabSubscription` sub inner join `tabSales Person` sales on sales.name = sub.vendedor where sales.name = (s.vendedor) limit 1) limit 1)) as Coordinador,
		ad.municipio,
		ad.barrio,
		cu.mobile_no as N_Celular,
		s.campana,
		s.name as contrato,
		s.no_contrato as no_contrato,
		spd.nodo,
		spd.latitud,
		spd.longitud,
		day(spd.service_start) as dia,
		month(spd.service_start) as mes,
		year(spd.service_start) as año,
		spd.address_line as Direccion,


		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.docstatus=1 
					and MONTH(si.posting_date) =  MONTH(spd.service_start) ) as '0',

		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1 
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 1) as '1',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1 
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 2) as '2',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1 
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 3) as '3',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1 
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 4) as '4' ,
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 5) as '5',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 6) as '6',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 7) as '7',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 8) as '8',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 9) as '9',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 10) as '10',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 11) as '11',
		(select sum(sii.amount)
				from `tabSales Invoice Item` sii inner join `tabSales Invoice` si on sii.parent = si.name
					where sii.plan_detail = spd.name and si.customer=cu.name and si.docstatus=1  
					and MONTH(si.posting_date) =   MONTH(spd.service_start) + 12) as '12'

		from `tabSubscription Plan Detail` spd
		inner join   `tabSubscription` s on spd.parent = s.name
		inner join  `tabSubscription Plan` sp on sp.name = spd.plan
		inner join `tabAddress` ad on ad.name = spd.direccion
		inner join `tabCustomer` cu on  cu.name = s.party
		where spd.old_plan is null  and  spd.service_start >='2023-05-06'
		and spd.estado_plan<>'Inactivo' and s.tipo_contrato != 'TEMPORAL'

		"""
	if filters.from_date:
		query = query + " and  spd.service_start >= " + "'" + filters.from_date + "' COLLATE utf8mb4_general_ci " 
	if filters.to_date:
		query = query + " and  spd.service_start <= " + "'" + add_days(filters.to_date, 1) + "' COLLATE utf8mb4_general_ci "
	if filters.portafolio:
		query = query + " and sp.item_group = " + "'" + filters.portafolio + "'"  
	if filters.cliente:
		query = query + " and s.party = " + "'" + filters.cliente + "'" 
	if filters.vendedor:
		query = query + " and s.vendedor = " + "'" + filters.vendedor + "'" 

	return frappe.db.sql(query)


def get_columns():
	return [
		{
			"fieldname": "cliente",
			"fieldtype": "Link",
			"options":"Customer",
			"label": _("Cliente"),
			
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
			"fieldname": "departamento",
			"fieldtype": "Data",
			"label": _("Departamento"),
		},
		{
			"fieldname": "Tipo_Cliente",
			"fieldtype": "Data",
			"label": _("Tipo Cliente"),
		},
		{
			"fieldname": "plan_id",
			"fieldtype": "Data",
			"label": _("Plan Id"),
		},
		{
			"fieldname": "compresion",
			"fieldtype": "Data",
			"label": _("Compresion"),
		},
		{
			"fieldname": "Tipo_Servicio",
			"fieldtype": "Data",
			"label": _("Tipo Servicio"),
		},
		{
			"fieldname": "estado",
			"fieldtype": "Data",
			"label": _("Estado Plan"),
		},
	
		{
			"fieldname": "plan",
			"fieldtype": "Data",
			"label": _("Plan"),
		
		},
		{
			"fieldname": "Velocidad",
			"fieldtype": "Data",
			"label": _("Velocidad"),	
		},
		{
			"fieldname": "Moneda",
			"fieldtype": "Data",
			"label": _("Moneda"),	
		},
		{
			"fieldname": "precio",
			"fieldtype": "float",
			"label": _("Precio"),	
		},
		{
			"fieldname": "precio_dolar",
			"fieldtype": "float",
			"label": _("Precio Dolar"),	
		},
		{
			"fieldname": "portafolio",
			"fieldtype": "Link",
			"options": "Item Group",
			"label": _("Portafolio"),	
		},
		{
			"fieldname": "service_start",
			"fieldtype": "Datetime",
			"label": _("service start"),	
		},
		{
			"fieldname": "vendedor",
			"fieldtype": "Link",
			"options": "Sales Person",
			"label": _("Vendedor"),	
		},
		{
			"fieldname": "Payback",
			"fieldtype": "Data",
			"label": _("Payback"),	
		},
		{
			"fieldname": "Canal",
			"fieldtype": "Data",
			"label": _("Canal"),	
		},
		{
			"fieldname": "Canal_General",
			"fieldtype": "Data",
			"label": _("Canal_General"),	
		},
		{
			"fieldname": "Mac",
			"fieldtype": "Data",
			"label": _("Mac"),	
		},
		{
			"fieldname": "Coordinador",
			"fieldtype": "Data",
			"label": _("Coordinador"),	
		},
		{
			"fieldname": "municipio",
			"fieldtype": "Data",
			"label": _("municipio"),
		},
		{
			"fieldname": "barrio",
			"fieldtype": "Data",
			"label": _("barrio"),	
		},
		{
			"fieldname": "N_Celular",
			"fieldtype": "Data",
			"label": _("N_Celular"),	
		},
		{
			"fieldname": "campana",
			"fieldtype": "Data",
			"label": _("campaña"),	
		},
		{
			"fieldname": "contrato",
			"fieldtype": "Link",
			"options":"Subscription",
			"label": _("contrato"),	
		},
		{
			"fieldname": "no_contrato",
			"fieldtype": "Data",
			"label": _("no_contrato"),	
		},
		{
			"fieldname": "nodo",
			"fieldtype": "Data",
			"label": _("Nodo"),	
		},
		{
			"fieldname": "latitud",
			"fieldtype": "Data",
			"label": _("Latitud"),	
		},
		{
			"fieldname": "longitud",
			"fieldtype": "Data",
			"label": _("longitud"),	
		},
		{
			"fieldname": "dia",
			"fieldtype": "Data",
			"label": _("dia"),	
		},
		{
			"fieldname": "mes",
			"fieldtype": "Data",
			"label": _("mes"),	
		},
		{
			"fieldname": "año",
			"fieldtype": "Data",
			"label": _("año"),	
		},
		{
			"fieldname": "Direccion",
			"fieldtype": "Data",
			"label": _("Direccion"),	
		},
		{
			"fieldname": "0",
			"fieldtype": "Data",
			"label": _("0"),	
		},
		{
			"fieldname": "1",
			"fieldtype": "Data",
			"label": _("1"),	
		},
		{
			"fieldname": "2",
			"fieldtype": "Data",
			"label": _("2"),	
		},
		{
			"fieldname": "3",
			"fieldtype": "Data",
			"label": _("3"),	
		},
		{
			"fieldname": "4",
			"fieldtype": "Data",
			"label": _("4"),	
		},
		{
			"fieldname": "5",
			"fieldtype": "Data",
			"label": _("5"),	
		},
		{
			"fieldname": "6",
			"fieldtype": "Data",
			"label": _("6"),	
		},
		{
			"fieldname": "7",
			"fieldtype": "Data",
			"label": _("7"),	
		},
		{
			"fieldname": "8",
			"fieldtype": "Data",
			"label": _("8"),	
		},
		{
			"fieldname": "9",
			"fieldtype": "Data",
			"label": _("9"),	
		},
		{
			"fieldname": "10",
			"fieldtype": "Data",
			"label": _("10"),	
		},
		{
			"fieldname": "11",
			"fieldtype": "Data",
			"label": _("11"),	
		},
		{
			"fieldname": "12",
			"fieldtype": "Data",
			"label": _("12"),	
		},
		
	]