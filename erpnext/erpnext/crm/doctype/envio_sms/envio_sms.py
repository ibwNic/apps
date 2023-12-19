# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import json
from types import SimpleNamespace
import requests
import base64
import time
from datetime import datetime

import os
import ftplib
import socket
import time
import logging

class EnvioSMS(Document):
	pass

def build_jason_reporte():
	dictionary = {'land': '505', 'packageStateList': [''], 'packageTypeList': ['']}

	json_string = json.dumps(dictionary, indent=4)

	return json_string

def reporte_sms():
	url = "https://apitellit.aldeamo.com/SmsiWS/packageReportPost"

	payload = build_jason_reporte()

	usrPass = "rene.gomez:c1ODE4NQ=="
	b64Val = base64.b64encode(usrPass.encode()).decode()

	headers = {'Content-Type': 'application/json', 'Authorization': 'Basic %s' % b64Val}

	response = requests.request("POST", url, headers=headers, data=payload)

	return response

@frappe.whitelist()
def verificar_sms(name):
	respuesta = reporte_sms()

	res = json.loads(respuesta.text, object_hook=lambda d: SimpleNamespace(**d))

	return res.result[0].available

@frappe.whitelist()
def envio_sms(country, message, message_format, mobile, factura):
	url = "https://apitellit.aldeamo.com/SmsiWS/smsSendPost"

	if factura:
		payload = build_jason_url(country, message, message_format, mobile, factura)
	else:
		payload = build_jason(country, message, message_format, mobile)

	usrPass = "rene.gomez:c1ODE4NQ=="
	b64Val = base64.b64encode(usrPass.encode()).decode()

	headers = {'Content-Type': 'application/json', 'Authorization': 'Basic %s' % b64Val}

	response = requests.request("POST", url, headers=headers, data=payload)

	return response

def build_jason(country, message, message_format, mobile):
	dictionary = {'country': str(country), 'dateToSend': "2023-03-25 12:34:00", 'message': message, 'encoding': "GSM7", 'messageFormat': message_format, 'addresseeList': [{'mobile': str(mobile)}]}

	json_string = json.dumps(dictionary, indent=4)

	return json_string

def build_jason_url(country, message, message_format, mobile, factura):
	dictionary = {'country': str(country), 'dateToSend': "2023-03-25 12:34:00", 'message': message, 'encoding': "GSM7", 'messageFormat': message_format, 'addresseeList': [{'mobile': str(mobile), 'url':'https://facturas-cloud.ibw.com.ni/download.php?filename='+factura+'.pdf'}]}

	json_string = json.dumps(dictionary, indent=4)

	return json_string

def format_sms(format, predeterminado, saldo, periodo):
	try:
		format = format.replace("xxxx.xx", str(round(saldo,2)))

		if periodo:
			format = format.replace("xxx-xx", periodo)
	except:
		format = predeterminado

	return format

@frappe.whitelist()
def enviar_mensajes_cobro(name):
	enviar = frappe.get_doc('Envio SMS', name)
	respuesta = None

	for a in range(0, len(enviar.numeros)):
		if enviar.numeros[a].transactionid == None:
			respuesta = envio_sms("505", format_sms(enviar.preview_sms, enviar.preset_sms, enviar.numeros[a].saldo, enviar.numeros[a].periodo), 1, enviar.numeros[a].numero, enviar.numeros[a].factura)

			x = json.loads(respuesta.text, object_hook=lambda d: SimpleNamespace(**d))

			sms = enviar.get('numeros', {'name': enviar.numeros[a].name})	

			if x.result.receivedRequests:
				sms[0].transactionid = x.result.receivedRequests[0].transactionId
				sms[0].status = x.result.receivedRequests[0].status
				sms[0].reason = x.result.receivedRequests[0].reason
			
			if x.result.failedRequests:
				sms[0].transactionid = x.result.failedRequests[0].transactionId
				sms[0].status = x.result.failedRequests[0].status
				sms[0].reason = x.result.failedRequests[0].reason
			
			respuesta = None
	
	enviar.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.msgprint("Mensajes Enviados")

@frappe.whitelist()
def obtener_exclusiones_sms(name):
	if not frappe.db.exists("Excepciones SMS", {"parent":name}):
		clientes = frappe.db.sql("select regnumber from `tabExclusion SMS`;")
		for cliente in clientes:
			excepciones = frappe.get_doc({
			"doctype": "Excepciones SMS",
			"cliente": cliente[0],
			"parent": name,
			"parentfield":"exclusiones",
			"parenttype": "Envio SMS"
			})
			excepciones.insert()

@frappe.whitelist()
def generar_vista_previa(name):
	envio = frappe.get_doc("Envio SMS", name)

	tipo_de_cliente = envio.tipo_de_cliente
	if tipo_de_cliente == "Todas las categorías de clientes":
		tipo_de_cliente = ''

	if envio.tipo_sms=="Factura Emitida":
		query = " select customer, c.phone, monto, getMonthYear(0) as periodo, factura, posting_date "
	else:
		if envio.saldo_a_cobrar=="0-30" or envio.saldo_a_cobrar=="Factura del Mes":
			query = " select customer, c.phone, de_0_a_30, getMonthYear(0) as periodo, '' as factura, '' as posting_date "
		if envio.saldo_a_cobrar=="30-60":
			query = " select customer, c.phone, de_31_a_60, getMonthYear(-1) as periodo, '' as factura, '' as posting_date "
		if envio.saldo_a_cobrar=="60-90":
			query = " select customer, c.phone, de_61_a_90, getMonthYear(-2) as periodo, '' as factura, '' as posting_date "
		if envio.saldo_a_cobrar=="90-mas":
			query = " select customer, c.phone, mayor_a_90, getMonthYear(-3) as periodo, '' as factura, '' as posting_date "
		if envio.saldo_a_cobrar=="Saldo Total":
			query = " select customer, c.phone, importe_total_pendiente, null as periodo, '' as factura, '' as posting_date "

	if envio.tipo_sms=="Factura Emitida":
		query = query + " from vw_facturas_emitidas as s"
	else:
		query = query + " from vw_suspensiones as s "

	query = query + " inner join `tabDynamic Link` as dl on s.customer=dl.link_name inner join `tabContact Phone` as c on dl.link_title=c.parent"

	query = query +  " where dl.parenttype='Contact' and estado_cliente='" + envio.estado_de_cliente + "' and tipo_de_cliente like '%" + tipo_de_cliente + "%'"

	if envio.portafolios:
		lista_portafolio = []
		for portafolio in envio.portafolios:
			lista_portafolio.append(portafolio.portafolio)
		lista_portafolio = str([p for p in lista_portafolio]).replace("[","(").replace("]",")")
		query = query +  " and portafolio in " + lista_portafolio
		
	if envio.departamento:
		query = query +  " and territory = '" + envio.departamento + "'" 
	if envio.municipio:
		query = query +  " and municipio = '" + envio.municipio + "'"
	if envio.barrio:
		query = query +  " and barrio = '" + envio.municipio + "'"

	if envio.tipo_sms!="Factura Emitida":
		if envio.deuda=="0-30" or envio.deuda == "Factura del Mes":
			query = query +  " and de_0_a_30 >= " + str(envio.monto_minimo)
		if envio.deuda=="30-60":
			query = query +  " and de_31_a_60 >= " + str(envio.monto_minimo)
		if envio.deuda=="60-90":
			query = query +  " and de_61_a_90 >= " + str(envio.monto_minimo)
		if envio.deuda=="90-mas":
			query = query +  " and mayor_a_90 >= " + str(envio.monto_minimo)
		if envio.deuda=="Saldo Total":
			query = query +  " and importe_total_pendiente >= " + str(envio.monto_minimo)
		
	excepciones = frappe.db.get_values("Excepciones SMS",{"parent": name},"cliente")
	if excepciones:
		clientes_excepciones = str([ex[0] for ex in excepciones]).replace("[","(").replace("]",")")
		query = query +  " and customer not in " + clientes_excepciones

	query = query + " and c.phone not like '2%' "

	try:
		if int(envio.limite_envio_sms) > 0:
			query = query + " LIMIT " + envio.limite_envio_sms + ";"
		else:
			query = query + " LIMIT 10000;"
	except:
		query = query + " LIMIT 10000;"

	resultado = frappe.db.sql(query)

	frappe.db.sql(
			"""
			DELETE FROM `tabNumeros SMS`
			WHERE parent = %(parent)s""",{"parent": name}
		)
	time.sleep(1)
	
	try:
		for res in resultado:
			
			child = frappe.new_doc("Numeros SMS")
			child.update(
				{
					"parent": name,
					"parentfield": "numeros",
					"parenttype": "Envio SMS",
					"regnumber":res[0],
					"numero":res[1],
					"saldo":res[2],
					"periodo":res[3],
					"factura":res[4],
					"fecha_factura":res[5]
				}
			)
			envio.numeros.append(child)	
		envio.save()

		agregar_numeros(name)
	except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))
			return e

	return "OK"

def agregar_numeros(name):
	excepciones = frappe.get_doc({
		"doctype": "Numeros SMS",
		"regnumber": "CUST-910000617",
		"numero":"89055955",
		"saldo":32,
		"periodo": "May-23",
		"parent": name,
		"parentfield":"numeros",
		"parenttype": "Envio SMS",
		"factura":"B-698695",
		"fecha_factura":"2023-05-09"
	})
	excepciones.insert()

	# excepciones = frappe.get_doc({
	# 	"doctype": "Numeros SMS",
	# 	"regnumber": "SCI-310062963",
	# 	"numero":"88730353",
	# 	"saldo":40.25,
	# 	"periodo": "Ago-23",
	# 	"parent": name,
	# 	"parentfield":"numeros",
	# 	"parenttype": "Envio SMS",
	# 	"factura":"A-2248484",
	# 	"fecha_factura":"2023-05-09"
	# })
	# excepciones.insert()

@frappe.whitelist()
def generar_archivos(name):
	enviar = frappe.get_doc('Envio SMS', name)

	for a in range(0, len(enviar.numeros)):
		if enviar.numeros[a].generada == False:
			sms = enviar.get('numeros', {'name': enviar.numeros[a].name})
			sms[0].generada = True
			descargar_factura(sms[0].factura)

	enviar.save(ignore_permissions=True)
	frappe.db.commit()
	
	redirect_ftp()

	frappe.msgprint("Archivos Generados")

	return 'OK'

def descargar_factura(factura):
	url= "https://ibwni-crm.ibw.com/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Invoice&name=" + factura + "&format=FORMATO%20FACTURA%20A&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=es"

	generated_secret = frappe.utils.password.get_decrypted_password("User", "Administrator", fieldname='api_secret')
	api_key = frappe.db.get_value("User", "Administrator", "api_key")
	header = {"Authorization": "token {}:{}".format(api_key, generated_secret)}
	res = requests.get(url, headers=header, verify=False)

	ruta = './ibwni-crm.ibw.com/public/files/facturas_pdf/' + factura + '.pdf'
	open(ruta,'wb').write(res.content)

def redirect_ftp():
	hostname = "192.168.150.35"
	username = "itweb"
	password = "jaBBerEr_521_HOSTeLRY"
	local_dir = "/data/ibw14/sites/ibwni-crm.ibw.com/public/files/facturas_pdf"
	remote_dir = "/public_html/upload_files"

	while True:
    # First try/except block
		try:
			file_list = os.listdir(local_dir)

			# validando si hay archivos
			if not file_list:
				# frappe.msgprint("No hay archivos para subir")
				break		

			with ftplib.FTP(host=hostname, user=username, passwd=password) as ftp:

				ftp.cwd(remote_dir)
				# frappe.msgprint(f"Ingresando {remote_dir}")

				for file_name in file_list:
					# Second try/except block
					try:
						file_path = os.path.join(local_dir, file_name)
						if os.path.isfile(file_path):
							with open(file_path, 'rb') as file:
								# frappe.msgprint(f"Subiendo {file_name}...")
								ftp.storbinary(f'STOR {file_name}', file)
								ftp.sendcmd('SITE CHMOD 644 ' + file_name)
							os.remove(file_path)
					except Exception as e:
						frappe.msgprint(f'Error al subir {file_name}: {str(e)}')
						continue

				# frappe.msgprint(f"Subiendo todos los archivos a {remote_dir}")
			time.sleep(1)

		except socket.gaierror:
			frappe.msgprint('Hostname invalido')
			break

		except ftplib.error_perm:
			frappe.msgprint('username invalido, password o directorio remoto.')
			break

		except FileNotFoundError:
			frappe.msgprint(f'{local_dir} no es un directorio valido. Por favor verificar el directorio.')
			break
