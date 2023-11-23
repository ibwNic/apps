# Copyright (c) 2022, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from zeep import client
import frappe
import pymysql
from collections import deque
import subprocess
miConexion = pymysql.connect( host='192.168.150.196', user= 'it_access', passwd='offiCiAlLy_570_coriAnDer', db='db_gpon' )

class Aprovisionamiento(Document):
	pass

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

def	generar_velocidades_yota():
	cliente = get_aprovisionador()
	velocidadesYota = cliente.velocidadesYota()
	return parse_nested_dict_list(velocidadesYota, 'velocidadesYotaResponse.velocidadesYotaResult.diffgr:diffgram.NewDataSet.tblTemp', 'perfilyota', 'Velocidad')

def get_velocidades_yota():
	return frappe.cache().get_value('velocidadesYota', generar_velocidades_yota)

def generar_velocidades_netspan():
	cliente = get_aprovisionador()
	velocidadesNetspan = cliente.velocidadesNetSpan()
	return parse_nested_dict_list(velocidadesNetspan, 'velocidadesNetSpanResponse.velocidadesNetSpanResult.diffgr:diffgram.NewDataSet.velocidadesNetSpan', 'Name', 'Velocidad')

def get_velocidades_netspan():
	return frappe.cache().get_value('velocidadesNetSpan', generar_velocidades_netspan)

def generar_velocidades_hfc():
	client = get_aprovisionador()
	velocidades = parse_nested_dict_list(client.cmtsHfc(), 'cmtsHfcResponse.cmtsHfcResult.diffgr:diffgram.NewDataSet.tblTemp', 'IDCMTS', 'Nombre' , is_group=True)
	ret = []
	for velocidad in velocidades:
		ret.append(velocidad)
		ret += parse_nested_dict_list(client.velocidadesHfc(idCmts=velocidad['value']), 
			'velocidadesHfcResponse.velocidadesHfcResult.diffgr:diffgram.NewDataSet.tblTemp', 'IDClase', 'Nombre', group=velocidad['value']
		)
	return ret

def get_velocidades_hfc():
	return frappe.cache().get_value('velocidadesHfc', generar_velocidades_hfc)

def build_provisioning_details(provisor, provisor_speed_id):
	group = None
	if provisor.lower() == "yota":
		speed = filter(lambda s, _id=provisor_speed_id: str(_id) in s.values()[0], get_velocidades_yota())[0]
	elif provisor.lower() in ("netspan", 'netspam'):
		speed = filter(lambda s, _id=provisor_speed_id: str(_id) in s.values()[0], get_velocidades_netspan())[0]
	elif provisor.lower() == "hfc":
		for speed in get_velocidades_hfc():
			if speed.get('is_group', False):
				group = speed
				continue
			if provisor_speed_id == speed['value']:
				break

	details = ""
	if group:
		details += "CMTS: {0}\n".format(group.get("label"))
	details += "Velocidad: {0}".format(speed.get("label"))
	return details

@frappe.whitelist()
def call_soap_method(method, **kwargs):
	return method
	if method.lower() == "velocidadeshfc":
		return get_velocidades_hfc()
	elif method.lower() == "velocidadesnetspan":
		return get_velocidades_netspan()
	elif method.lower() == "velocidadesyota":
		return get_velocidades_yota()
	elif method.lower() == "idvelocidad":
		return get_speed_code(**kwargs)
	else:
		serial_no = kwargs.pop("serial_no", None)
		provisor = kwargs.pop("provisor", None)
		client = get_aprovisionador()
		method = method.replace('Spa', 'spa').replace('spam', 'span')
		if method == 'velocidadesNetspan':
			method = 'velocidadesNetSpan'
			provisor = 'NetSpan'
		if not method in client.operations:
			frappe.throw("Unknown method {0}".format(method))
		fn = getattr(client, method)
	
		response =  fn(**kwargs)
		parsed = parse_nested_dict_str(response, "{0}Response.{0}Result".format(method))
		blocked_method = ["eliminar"+provisor, "suspender"+provisor, 'eliminar'+provisor.upper(), 'suspender'+provisor.upper()]
	
		if serial_no:
			values = {}
			
			values['provisor'] = provisor if not method.startswith("eliminar") else None
			values['provisor_speed_id'] = kwargs.get("velocidad") if not method.startswith("eliminar") else None
			values['provisor_instruction'] = build_provisioning_details(**values) if not method in blocked_method else None

			update_serial_no = parsed == "00"

			if method.startswith("agregar"):
				message = "Agregado a el Aprovisionador {0}\n{1}".format(provisor, values["provisor_instruction"])
			elif method.startswith("cambiar"):
				message = "Cambio de velocidad en el Aprosionador {0}\n{1}".format(provisor, values["provisor_instruction"])
			elif method.startswith("remover"):
				message = "Removido del aprovisionador {0}".format(provisor)
			else:
				update_serial_no = False
				message = "Suspendido en el aprovisionador {0}".format(provisor)

			message += "\nRespuesta {0}: {1}".format(provisor, parsed)

			serial_no = frappe.get_doc("Serial No", serial_no)
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

@frappe.whitelist()
def get_all_serial_no():
	return [sn[0] for sn in frappe.db.sql(""" select name from `tabSerial No`; """)]

# @frappe.whitelist()
# def validar_all_serial_no(mac):
# 	# return [sn[0] for sn in frappe.db.sql(""" select name from `tabSerial No`; """)]
# 	if len(mac)>1:
# 		no_serie = frappe.db.sql(""" select name from `tabSerial No` where name = %(mac)s """, {"mac": mac})
		
# 		try:
# 			if len(no_serie)>0:		
# 				return no_serie
				
# 		except:
# 			frappe.msgprint("Mac no Esta Registrado en CRM")"
# 				return True

@frappe.whitelist()
def velocidad_hfc(provisor_speed_id):
	velocidad = frappe.db.get_value("Velocidades HFC",provisor_speed_id,"velocidad")
	cmts = frappe.db.get_value("Velocidades HFC",provisor_speed_id,"cmts")
	return velocidad, cmts

@frappe.whitelist()
def vlan_masivo(equipo):

	cur = miConexion.cursor()
	vlan = []
	try:
		
		query = """select un.value,v.value,v.name,g.ip from  dbgp_gpon_uncfg un
					inner join dbgp_vlan v on v.gpon=un.gpon 
					inner join dbgp_gpon g on g.id=v.gpon
					where un.value= '"""
		query = query + equipo + """' limit 5000; """
		cur.execute(query)
		for e in cur.fetchall(): 
			vlan.append([e[2],e[1]])		
	except (pymysql.err.OperationalError, err.InterfaceError) as e:
		if isinstance(e, pymysql.err.OperationalError) and e.args[0] == 2006:
			print("Reconectando...")
			miConexion.ping(reconnect=True)
		else:
			# Manejar otros errores
			print(f"Error: {e}")
	finally:
		miConexion.close()

	# print(vlan)
	return vlan

@frappe.whitelist()
def obtener_script(Vlan=None,Velocidad=None,id=None,mac=None):

	# # Definir los parámetros del comando SSH y del programa Python en el servidor remoto
	# usuario = "tu_usuario_ssh"
	# servidor_remoto = "tu_servidor_remoto"
	# ruta_programa_remoto = "/ruta/del/programa.py"

	# # Comando SSH para ejecutar el programa Python en el servidor remoto
	# comando_ssh = f"ssh it_access@192.168.150.196  python3 prueba_ssh.py"

	# # Ejecutar el comando SSH utilizando subprocess
	# try:
	# 	resultado = subprocess.run(comando_ssh, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	# 	print("Salida estándar:", resultado.stdout.decode())
	# 	print("Error estándar:", resultado.stderr.decode())
	# except subprocess.CalledProcessError as e:
	# 	print(f"Error al ejecutar el comando SSH: {e}")


	# Ejecutar el script expect mediante subprocess
	

	# Parámetros it_access@192.168.150.196
	usuario_remoto = "it_access"
	servidor_remoto = "192.168.150.196"
	numero_a_ingresar = "21"  # Puedes cambiar esto al número que desees
	script_expect_path = "apps/frappe/frappe/custom/doctype/aprovisionamiento/conexion_ssh"
	# Guarda el script Expect en un archivo temporal
	with open(script_expect_path, "w") as script_file:
		script_file.write(f"#!/usr/bin/expect\n\nset numero_a_ingresar {numero_a_ingresar}\n\nspawn python3 programa.py\nexpect \"Ingresa un número:\"\nsend \"$numero_a_ingresar\\n\"\nexpect eof")

	# Comando SSH para ejecutar el script Expect en el servidor remoto
	comando_ssh = f"ssh {usuario_remoto}@{servidor_remoto} 'expect {script_expect_path} {numero_a_ingresar}'"

	# Ejecutar el comando SSH mediante subprocess
	try:
		resultado = subprocess.run(comando_ssh, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		print("Salida estándar:", resultado.stdout.decode())
		print("Error estándar:", resultado.stderr.decode())
	except subprocess.CalledProcessError as e:
		print(f"Error al ejecutar el comando SSH: {e}")
	
    # r=resultado
	# modelo = frappe.db.get_value("Serial No",mac,"item_code")
	# cur = miConexion.cursor()
	# query = f""" select un.id,s.Script from dbgp_gpon un 
	# 	inner join dbgp_vlan v on v.gpon=un.id
	# 	inner join tbScript s on s.IdOlt=un.id
	# 	where v.value='{id}' and s.modelo='{modelo}' """
	# cur.execute(query)
	# script = ''
	# for e in cur.fetchall():
	# 	script = e[1]
	
	# script = script.replace("identificador",mac).replace("velocidad",Velocidad).replace("ident_vlan",id)
	# frappe.msgprint(script)
	#return script

# ITPTV
@frappe.whitelist()
def Registrar_cliente(country, message, message_format, mobile):
	url = "https://apitellit.aldeamo.com/SmsiWS/smsSendPost"

	payload = build_jason(country, message, message_format, mobile)

	usrPass = "rene.gomez:c1ODE4NQ=="
	b64Val = base64.b64encode(usrPass.encode()).decode()

	headers = {'Content-Type': 'application/json', 'Authorization': 'Basic %s' % b64Val}

	response = requests.request("POST", url, headers=headers, data=payload)

	return response

@frappe.whitelist()
def Registrar_cliente(country, message, message_format, mobile):
	url = "https://apitellit.aldeamo.com/SmsiWS/smsSendPost"

	payload = build_jason(country, message, message_format, mobile)

	usrPass = "rene.gomez:c1ODE4NQ=="
	b64Val = base64.b64encode(usrPass.encode()).decode()

	headers = {'Content-Type': 'application/json', 'Authorization': 'Basic %s' % b64Val}

	response = requests.request("POST", url, headers=headers, data=payload)

	return response


def deshabilitar_activacion_forsoza():
	frappe.db.sql(""" update `tabAprovisionamiento` set activacion_forzosa = 0 where mac in (
       select mac from `tabAprovisionamiento`  where activacion_forzosa=1 and TIMESTAMPDIFF(HOUR, fecha_activacion_forzosa,now())>=24);""")