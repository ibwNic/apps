import json

import frappe
import frappe.defaults
from frappe import _, msgprint
from frappe.utils import cint, cstr, flt, get_formatted_email, today

print("hola")
# frappe.db.sql(""" update `tabCustomer` custo   inner join   
#     ( select c2.name, GROUP_CONCAT(DISTINCT sp2.item_group SEPARATOR ', ') portafolios  from `tabCustomer` c2 inner join `tabSubscription` s2  on s2.party = c2.name
#     inner join `tabSubscription Plan Detail` spd2 on s2.name = spd2.parent inner join
#     `tabSubscription Plan` sp2 on sp2.name=spd2.plan
#     where c2.estado_cliente in ('ACTIVO') and spd2.estado_plan != 'Plan Cerrado'
#     group by c2.name) as subquery
#     ON subquery.name = custo.name
#     SET custo.todos_los_portafolios = subquery.portafolios, custo.info_updated = now()
#     where custo.name = subquery.name;
#     """)


