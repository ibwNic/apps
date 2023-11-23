# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import time
from frappe.core.doctype.communication.email import make

class EnvioFacturasElectronicas(Document):
	pass

@frappe.whitelist()
def generar_vista_previa(name):
	envio = frappe.get_doc("Envio Facturas Electronicas", name)

	query = " select c.name as regnumber, c.customer_name as nombre, si.name as factura, e.email_id "
	query = query + " from `tabCustomer` c inner join `tabDynamic Link` dl on c.name=dl.link_name inner join `tabContact Email` e on dl.parent=e.parent inner join `tabSales Invoice` si on c.name=si.customer"
	query = query +  " where si.docstatus = 1 and si.naming_series='" + str(envio.envio_factura) + "' and posting_date>='" + str(envio.fecha_inicio) + "' and posting_date<='" + str(envio.fecha_fin) + "'"

	resultado = frappe.db.sql(query + " LIMIT 20000;")
	time.sleep(1)
	
	try:
		for res in resultado:
			
			child = frappe.new_doc("Detalle Envio de Factura")
			child.update(
				{
					"parent": name,
					"parentfield": "envios",
					"parenttype": "Envio Facturas Electronicas",
					"regnumber": res[0],
					"nombre": res[1],
					"factura": res[2],
					"correo": res[3]
				}
			)
			envio.envios.append(child)	
		envio.save()

	except Exception as e:
			frappe.msgprint(frappe._('Fatality Error Project {0} ').format(e))	

	return query

@frappe.whitelist()
def enviar_facturas(name):
	enviar = frappe.get_doc("Envio Facturas Electronicas", name)
	respuesta=None

	for e in range(0, len(enviar.envios)):
		if enviar.envios[e].envio == None:

			try:
				respuesta = make('Sales Invoice', enviar.envios[e].factura, plantilla(), 'IBW Factura: ' + str(enviar.envios[e].factura), 'Sent', 'relay@cobranza.ibw.com.ni', 'Cobranza IBW', enviar.envios[e].correo, 'Email', True, None, 'FORMATO FACTURA A', [], False, None, None, False, True, None, None)

				correos = enviar.get('envios', {'name': enviar.envios[e].name})

				correos[0].envio = respuesta["name"]
			except:
				frappe.msgprint("Mensajes Enviados")
			
			respuesta = None
		
		# time.sleep(1)

	enviar.save(ignore_permissions=True)
	frappe.db.commit()

	enviar.submit()

	frappe.msgprint("Mensajes Enviados")

def plantilla():
    htmlCode = '<div class="ql-editor read-mode"><h1>IBW Comunicaciones</h1><p><br></p><p>Estimado Cliente: </p><p><br></p><p>Por este medio remitimos a usted la factura adjunta, &nbsp;por el servicio que le brinda IBW.</p><p>A la vez aprovechamos para indicarle que su pago lo puede hacer efectivo:</p><p><br></p><p>1- En la Institucion Bancaria de su preferencia:</p><table class="table table-bordered"><tbody><tr><td data-row="row-3vvl">BANCO</td><td data-row="row-3vvl">CUENTA CORDOBAS</td><td data-row="row-3vvl">CUENTA DOLARES</td></tr><tr><td data-row="insert-row-above">BANCENTRO</td><td data-row="insert-row-above">100-208-377</td><td data-row="insert-row-above">101-209-210</td></tr><tr><td data-row="insert-column-right">BAC</td><td data-row="insert-column-right">351-000-488</td><td data-row="insert-column-right">360-871-727</td></tr><tr><td data-row="row-bwm9">BDF</td><td data-row="row-bwm9">100-000-8725</td><td data-row="row-bwm9"><br></td></tr><tr><td data-row="insert-column-right">BANPRO</td><td data-row="insert-column-right">10010009326724</td><td data-row="insert-column-right">10010019326730</td></tr></tbody></table><p>2. Usted puede hacer uso de nuestro sistema de pago con tarjeta de credito o debito, con cualquiera de las siguientes opciones:</p><p><br></p><p>	a) Entrando a nuestra caja electronica</p><p>	b) Realizando un Telepago llamando a nuestro departamento de Cobranza al 2278-6328.</p><p>	c) En Bancanet de Bancentro, pagando en linea desde la pagina del Banco</p><p>	d) Llamando al 1800-1524, Central de pagos Credomatic, Central de Pagos de Bancentro 1800-8472</p><p>	e) En Western Union/Airpak, Agentes Banpro y RapiBac</p><p>	f) En Punto Facil de Gallo mas Gallo y el Verdugo</p><p>	g) En sucursales de IBW, Tipitapa, Matagalpa, Leon, Masaya, Jinotepe y Managua</p><p><br></p><p>Nota Aclaratoria: Si usted paga su factura por &nbsp;Cargo Automatico favor ignorar el presente mensaje.</p><p><br></p><p>Agradecemos su atencion,</p><p><br></p><p>Atentamente,</p><p><br></p><p>Comunicaciones IBW.</p></div>'

    fn_return_value = htmlCode
    return fn_return_value