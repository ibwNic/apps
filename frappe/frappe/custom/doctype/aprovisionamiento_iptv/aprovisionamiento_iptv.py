# Copyright (c) 2023, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _, msgprint, scrub
from frappe.model.document import Document

class AprovisionamientoIPTv(Document):
	pass
	# def on_update(self):
	# 	if self.estado == 'Activo':
	# 		self.Habilitar_Cliente()
		
	# 	if self.estado == 'Suspendido':
	# 		self.Deshabilitar_Cliente()
	

	# def Deshabilitar_Cliente(Regnumber):
	# 	url = "https://itvplus.groupinmotion.com/api/disable-client"
	# 	messages = []
	# 	dictionary = {'identificador': str(Regnumber),'cortarPlan':True}
	# 	payload = json.dumps(dictionary,indent=4)

	# 	headerss = {'Content-Type': 'application/json'}

	# 	response = requests.post(url,headers = headerss,data= payload)

	# 	js = json.loads(response.text)
	# 	# joson.load(response)
	# 	dicc = dict(js)
	# 	messages.append(dicc['message'])
	# 	# return dicc['message']
	# 	# return {'messages':messages}
	# 	frappe.msgprint(_(messages))

	# def Habilitar_Cliente(Regnumber):
	# 	url = "https://itvplus.groupinmotion.com/api/enable-client"
	# 	messages = []
	# 	dic = {'identificador': str(Regnumber)}

	# 	payload = json.dumps(dic,indent=4)
		
	# 	headerss = {'Content-Type': 'application/json'}

	# 	response = requests.request("POST",url,headers = headerss,data= payload)
	# 	js = json.loads(response.text)
	# 	# joson.load(response)
	# 	dicc = dict(js)
	# 	messages.append(dicc['message'])
	# 	# return dicc['message']
	# 	# return {'messages':messages}
	# 	frappe.msgprint(_(messages))
	

# IPTV
@frappe.whitelist()
def Registrar_Cliente(Regnumber):
	url = "https://itvplus.groupinmotion.com/api/register-client"
	messages = []
	customer = frappe.get_doc("Customer", {"name": ["like", "%{}".format(Regnumber)]})

	if not customer:
		return "Error, Cliente no encontrado"
	
	disp = frappe.get_doc("Aprovisionamiento IPTv", {"name": ["like", "%{}".format(Regnumber)]})
	mac = []
	for dis in disp.dispositivos:
		mac.append(dis.mac)

	dictionary = {'root': {'usuario':{'nombres':customer.customer_name,'identificador':customer.name,'cedula':customer.cedula,'appaterno':customer.first_name,'apmaterno':customer.last_name,'telefono':str(84855671),'direccion':{'pais':{'id':"43",'nombre':"Nicaragua"},'region':{'id':"1",'nombre':"."},'comuna':{'id':1,'nombre':"."},'ciudad':{'nombre':customer.municipio}}},'carroCompra':{'macs':mac,'cantidadDispositivos':{'movil':1}}}}
	payload = json.dumps(dictionary,indent=4)

	headerss = {'Content-Type': 'application/json'}

	response = requests.post(url,headers = headerss,data= payload)

	js = json.loads(response.text)
	# joson.load(response)
	dicc = dict(js)
	messages.append(dicc['message'])
	if bool(dicc['error']) == False:
		frappe.db.set_value('Aprovisionamiento IPTv',disp.name,'estado','Activo')
	
	return {'messages':messages}

@frappe.whitelist()
def Deshabilitar_Cliente(Regnumber):
		url = "https://itvplus.groupinmotion.com/api/disable-client"
		messages = []
		dictionary = {'identificador': str(Regnumber),'cortarPlan':True}
		payload = json.dumps(dictionary,indent=4)

		headerss = {'Content-Type': 'application/json'}

		response = requests.post(url,headers = headerss,data= payload)

		js = json.loads(response.text)
		# joson.load(response)
		dicc = dict(js)
		messages.append(dicc['message'])
		# return dicc['message']
		if bool(dicc['error']) == False:
			disp = frappe.get_doc("Aprovisionamiento IPTv", {"name": ["like", "%{}".format(Regnumber)]})
			frappe.db.set_value('Aprovisionamiento IPTv',disp.name,'estado','Suspendido')
		return {'messages':messages}
		# frappe.msgprint(_(messages))

@frappe.whitelist()
def Habilitar_Cliente(Regnumber):
	url = "https://itvplus.groupinmotion.com/api/enable-client"
	messages = []
	dic = {'identificador': str(Regnumber)}

	payload = json.dumps(dic,indent=4)
	
	headerss = {'Content-Type': 'application/json'}

	response = requests.request("POST",url,headers = headerss,data= payload)
	js = json.loads(response.text)
	# joson.load(response)
	dicc = dict(js)
	messages.append(dicc['message'])
	# return dicc['message']
	if bool(dicc['error']) == False:
		disp = frappe.get_doc("Aprovisionamiento IPTv", {"name": ["like", "%{}".format(Regnumber)]})
		frappe.db.set_value('Aprovisionamiento IPTv',disp.name,'estado','Activo')
	return {'messages':messages}
	# frappe.msgprint(_(messages))

@frappe.whitelist()
def Enlazar_STB(Regnumber,Cantidad):
	url = "https://itvplus.groupinmotion.com/api/modify-client"

	macs = []

	dic = {'identificador': str(Regnumber),'cantidad_dispositivos':str(Cantidad),'macs':macs}

	payload = json.dumps(dic,indent=4)
	
	headerss = {'Content-Type': 'application/json'}

	response = requests.request("POST",url,headers = headerss,data= payload)
	js = json.loads(response.text)
	# joson.load(response)
	dicc = dict(js)
	# return dicc['message']
	return dicc

@frappe.whitelist()
def Eliminar_Cliente(Regnumber):
	url = "https://itvplus.groupinmotion.com/api/delete-client"
	messages = []
	dic = {'identificador': str(Regnumber)}

	payload = json.dumps(dic,indent=4)
	
	headerss = {'Content-Type': 'application/json'}

	response = requests.request("POST",url,headers = headerss,data= payload)
	js = json.loads(response.text)
	# joson.load(response)
	dicc = dict(js)
	# return dicc['message']
	messages.append(dicc['message'])
	if bool(dicc['error']) == False:
		disp = frappe.get_doc("Aprovisionamiento IPTv", {"name": ["like", "%{}".format(Regnumber)]})
		frappe.db.set_value('Aprovisionamiento IPTv',disp.name,'estado','Inactivo')
	return {'messages':messages}