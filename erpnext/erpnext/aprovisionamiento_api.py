import frappe
import json
from frappe.desk.doctype.tag.tag import DocTags
import six
from frappe import _
from frappe.utils import flt, cint, today
from datetime import datetime
from frappe import ValidationError, _, qb, scrub, msgprint
from zeep import client
import requests
import xmltodict, json

from frappe.desk.query_report import run


def parse_nested_dict_list(obj, path, value, label, **kwargs):
	base = obj.copy()
	for d in path.split('.'):
		if d in base:
			base = base[d]
		else:
			base = []
			# print "Skipping Key {0}".format(d)
	if isinstance(base, dict):
		base = [base]
	ret = []
	for item in base:
		ret.append(dict(label=item[label], value=item[value], **kwargs))
	return ret

def parse_nested_dict_str(obj, path):
	base = obj.copy()
	for d in path.split("."):
		if d in base:
			base = base[d]
		else:
			base = ""
			# print "Skipping Key {0}".format(d)
	return base

@frappe.whitelist()
def get_provisioning_options():
	return [
		["Yota", 1],
		["NetSpan", 1],
		["Hfc", 0]
	]

def get_speed_code(provisor, speed_label):
	if provisor == 'NetSpam':
		provisor = 'NetSpan'
	velocidades = call_soap_method('velocidades'+provisor)

	if speed_label.lower() in ("bloqueado", "block"):
		return velocidades[-1].get("value")
	else:
		for speed in velocidades:
			if speed.get("label", "").lower() == speed_label.lower():
				return speed.get("value")

def get_aprovisionador():
	cliente = client("http://192.168.150.186:8082/Aprovisionamiento.asmx?WSDL")
	return cliente

def agregarAprovisionador(provisionador, identificador, velocidad):
	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <"+ provisionador +" xmlns=\"http://tempuri.org/\">\r\n      <identificador>" + identificador + "</identificador>\r\n      <velocidad>"+ velocidad +"</velocidad>\r\n    </"+ provisionador +">\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/'+provisionador
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	addResponse = xmltodict.parse(response.text)
	
	return parse_nested_dict_str(addResponse['soap:Envelope']['soap:Body'], "{0}Response.{0}Result".format(provisionador))

def suspenderAprovisionador(provisionador, identificador):
	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <"+ provisionador +" xmlns=\"http://tempuri.org/\">\r\n      <identificador>" + identificador + "</identificador>\r\n   </"+ provisionador +">\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/'+provisionador
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	addResponse = xmltodict.parse(response.text)
	
	return parse_nested_dict_str(addResponse['soap:Envelope']['soap:Body'], "{0}Response.{0}Result".format(provisionador))

def eliminarAprovisionador(provisionador, identificador):
	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <"+ provisionador +" xmlns=\"http://tempuri.org/\">\r\n      <identificador>" + identificador + "</identificador>\r\n   </"+ provisionador +">\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/'+provisionador
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	addResponse = xmltodict.parse(response.text)
	
	return parse_nested_dict_str(addResponse['soap:Envelope']['soap:Body'], "{0}Response.{0}Result".format(provisionador))

def cambiarVelocidadAprovisionador(provisionador, identificador, velocidad):
	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <"+ provisionador +" xmlns=\"http://tempuri.org/\">\r\n      <identificador>" + identificador + "</identificador>\r\n      <velocidad>"+ velocidad +"</velocidad>\r\n    </"+ provisionador +">\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/'+provisionador
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	addResponse = xmltodict.parse(response.text)
	
	return parse_nested_dict_str(addResponse['soap:Envelope']['soap:Body'], "{0}Response.{0}Result".format(provisionador))

def activarAprovisionador(provisionador, identificador):
	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <"+ provisionador +" xmlns=\"http://tempuri.org/\">\r\n      <identificador>" + identificador + "</identificador>\r\n   </"+ provisionador +">\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/'+provisionador
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	addResponse = xmltodict.parse(response.text)
	
	return parse_nested_dict_str(addResponse['soap:Envelope']['soap:Body'], "{0}Response.{0}Result".format(provisionador))

def	generar_velocidades_yota():
	# cliente = get_aprovisionador()
	# velocidadesYota = cliente.velocidadesYota()

	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <velocidadesYota xmlns=\"http://tempuri.org/\" />\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/velocidadesYota'
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	velocidadesYota=xmltodict.parse(response.text)

	return parse_nested_dict_list(velocidadesYota['soap:Envelope']['soap:Body'], 'velocidadesYotaResponse.velocidadesYotaResult.diffgr:diffgram.NewDataSet.tblTemp', 'perfilyota', 'Velocidad')

def get_velocidades_yota():
	return frappe.cache().get_value('velocidadesYota', generar_velocidades_yota)

def generar_velocidades_netspan():
	# cliente = get_aprovisionador()
	# velocidadesNetspan = cliente.velocidadesNetSpan()

	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <velocidadesNetSpan xmlns=\"http://tempuri.org/\" />\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/velocidadesNetSpan'
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	velocidadesNetspan=xmltodict.parse(response.text)

	return parse_nested_dict_list(velocidadesNetspan['soap:Envelope']['soap:Body'], 'velocidadesNetSpanResponse.velocidadesNetSpanResult.diffgr:diffgram.NewDataSet.velocidadesNetSpan', 'Name', 'Velocidad')

def get_velocidades_netspan():
	return frappe.cache().get_value('velocidadesNetSpan', generar_velocidades_netspan)

def generar_clases_hfc(idcmts):
	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <velocidadesHfc xmlns=\"http://tempuri.org/\">\r\n      <idCmts>" + idcmts + "</idCmts>\r\n    </velocidadesHfc>\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/velocidadesHfc'
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	velocidadesHfc = xmltodict.parse(response.text)

	return velocidadesHfc['soap:Envelope']['soap:Body']

def generar_velocidades_hfc():
	# client = get_aprovisionador()

	url = "http://192.168.150.186:8082/Aprovisionamiento.asmx"

	payload = "<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">\r\n  <soap:Body>\r\n    <cmtsHfc xmlns=\"http://tempuri.org/\" />\r\n  </soap:Body>\r\n</soap:Envelope>"
	headers = {
	'Content-Type': 'text/xml',
	'SOAPAction': 'http://tempuri.org/cmtsHfc'
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	cmtsHfc = xmltodict.parse(response.text)

	velocidades = parse_nested_dict_list(cmtsHfc['soap:Envelope']['soap:Body'], 'cmtsHfcResponse.cmtsHfcResult.diffgr:diffgram.NewDataSet.tblTemp', 'IDCMTS', 'Nombre' , is_group=True)
	ret = []
	for velocidad in velocidades:
		ret.append(velocidad)
		# ret += parse_nested_dict_list(client.velocidadesHfc(idCmts=velocidad['value']), 
		# 	'velocidadesHfcResponse.velocidadesHfcResult.diffgr:diffgram.NewDataSet.tblTemp', 'IDClase', 'Nombre', group=velocidad['value']
		# )
		ret += parse_nested_dict_list(generar_clases_hfc(velocidad['value']), 
			'velocidadesHfcResponse.velocidadesHfcResult.diffgr:diffgram.NewDataSet.tblTemp', 'IDClase', 'Nombre', group=velocidad['value']
		)
	return ret

def get_velocidades_hfc():
	return frappe.cache().get_value('velocidadesHfc', generar_velocidades_hfc)

def build_provisioning_details(tipo_de_aprovisionamiento, ancho_de_banda):
	group = None
	if tipo_de_aprovisionamiento.lower() == "yota":
		speed = filter(lambda s, _id=ancho_de_banda: str(_id) in s.values()[0], get_velocidades_yota())[0]
	elif tipo_de_aprovisionamiento.lower() in ("netspan", 'netspam'):
		speed = filter(lambda s, _id=ancho_de_banda: str(_id) in s.values()[0], get_velocidades_netspan())[0]
	elif tipo_de_aprovisionamiento.lower() == "hfc":
		for speed in get_velocidades_hfc():
			if speed.get('is_group', False):
				group = speed
				continue
			if ancho_de_banda == speed['value']:
				break

	details = ""
	if group:
		details += "CMTS: {0}\n".format(group.get("label"))
	details += "Velocidad: {0}".format(speed.get("label"))
	return details

@frappe.whitelist()
def call_soap_method(method, **kwargs):
	# return method
	if method.lower() == "velocidadeshfc":
		return get_velocidades_hfc()
	elif method.lower() == "velocidadesnetspan":
		return get_velocidades_netspan()
	elif method.lower() == "velocidadesyota":
		return get_velocidades_yota()
	elif method.lower() == "idvelocidad":
		return get_speed_code(**kwargs)
	else:
		# for d in kwargs:
		# 	print(d)

		serial_no = kwargs.pop("serial_no", None)
		# velocidad=kwargs.pop("velocidad", None)
		provisor = kwargs.pop("provisor", None)

		print(kwargs.get("velocidad"))
		print(serial_no)

		# client = get_aprovisionador()
		# method = method.replace('Spa', 'spa').replace('spam', 'span')
		# if method == 'velocidadesNetspan':
		# 	method = 'velocidadesNetSpan'
		# 	provisor = 'NetSpan'
		# if not method in client.operations:
		# 	frappe.throw("Unknown method {0}".format(method))
		# fn = getattr(client, method)

		# response =  fn(**kwargs)

		if method.__contains__("agregar"):
			response = agregarAprovisionador(method, serial_no, kwargs.get("velocidad"))
		elif method.__contains__("suspender"):
			response = suspenderAprovisionador(method, serial_no)
		elif method.__contains__("eliminar"):
			response = eliminarAprovisionador(method, serial_no)
		elif method.__contains__("cambiarVelocidad"):
			response = cambiarVelocidadAprovisionador(method, serial_no, kwargs.get("velocidad"))

		# parsed = parse_nested_dict_str(response['soap:Envelope']['soap:Body'], "{0}Response.{0}Result".format(method))
		parsed = response
		blocked_method = ["eliminar"+provisor, "suspender"+provisor, 'eliminar'+provisor.upper(), 'suspender'+provisor.upper()]
	
		if serial_no:
			values = {}
			
			values['provisor'] = provisor if not method.startswith("eliminar") else None
			values['provisor_speed_id'] = kwargs.get("velocidad") if not method.startswith("eliminar") else None
			# values['evento'] = build_provisioning_details(**values) if not method in blocked_method else None
			values['provisor_instruction'] = "Velocidad: " + method + " " + kwargs.get("velocidad") if not method in blocked_method else None

			# update_serial_no = parsed == "00"

			if method.startswith("agregar"):
				message = "Agregado a el Aprovisionador {0}\n{1}".format(provisor, values["evento"])
			elif method.startswith("cambiar"):
				message = "Cambio de velocidad en el Aprosionador {0}\n{1}".format(provisor, values["evento"])
			elif method.startswith("remover"):
				message = "Removido del aprovisionador {0}".format(provisor)
			else:
				update_serial_no = False
				message = "Suspendido en el aprovisionador {0}".format(provisor)

			message += "\nRespuesta {0}: {1}".format(provisor, parsed)

			serial_no = frappe.get_doc("Aprovisionamiento", serial_no)
			#if update_serial_no:
			if 'eliminar' in method.lower():
				values = {k: None for k in values.keys()}
			#frappe.msgprint(method)
			#frappe.msgprint('<pre>{0}</pre>'.format(frappe.as_json(values)))
			if not int(parsed) or 'eliminar' in method.lower():
				serial_no.update(values)
				serial_no.save()
				serial_no.add_comment("Info", message)
			frappe.db.commit()
		return parsed