// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// IBW

frappe.ui.form.on('Orden de Servicio Interno', {
	refresh: function(frm) {

		if (frm.doc.tecnico ){
			let div_boton = document.querySelector("#boton-balance");
			var boton = document.createElement("button");
			boton.className = "btn btn-success mt-3"; 

			boton.onclick =  function () { 
				let tecnico_balance = frm.doc.tecnico;
				tecnico_balance = tecnico_balance.replace(" ","%20")
				window.location.href='https://ibwni-crm.ibw.com/app/query-report/Balance%20de%20Inventario%20por%20T%C3%A9cnico?tecnico='  + tecnico_balance;
				
			}
			boton.innerText = "Ver Inventario de " + frm.doc.tecnico;
			div_boton.appendChild(boton);

		}

		frm.set_query('departamento', function(d){
			return {
				filters: {
					 tipo_territorio: "Departamento"
				}
			}
		})
		frm.set_query('municipio', function(d){
			return {
				filters: {
					 tipo_territorio: "Municipio"
				}
			}
		})
		frm.set_query('barrio', function(d){
			return {
				filters: {
					 tipo_territorio: "Barrio"
				}
			}
		})
		frm.trigger("calculate_total");
       frappe.call({
		"method": "erpnext.crm.doctype.opportunity.opportunity.get_producto_presupuesto","args":{'respuesta':'Productos' }, callback: function(r) {
        //para filtrar en una tabla secundaria:
		frm.fields_dict.bom_de_materiales.grid.get_field("item").get_query = function(doc, cdt, cdn){
        			return {
        				filters: {
        					name: ["in", r.message]
        				}
        			}
        		}
        }})
		
		frm.set_query('tecnico', function(d){
			return {
				filters: {
						activo: 1
				}
			}
		})
		
		frm.fields_dict.cuadrilla_tecnica.grid.get_field("tecnico").get_query = function(doc, cdt, cdn){
			frappe.model.set_value(cdt, cdn, "fecha_asignacion", frappe.datetime.now_datetime());

			return {
				filters: {		
					activo: 1
				}
			}
		}
		if(frm.doc.workflow_state !== 'Abierto'){
			frm.set_df_property('fecha_inicio', 'read_only', true);
		}
		let tecnico ='';	 
		 if (frm.doc.tecnico === undefined) {
		     tecnico = 'random'}
	     else{
	         tecnico = frm.doc.tecnico
	     }
	     frappe.call({
			"method": "erpnext.support.doctype.orden_de_servicio_interno.orden_de_servicio_interno.filtrar_almacen", "args":{"name":frm.doc.name},
			 callback: function(r) {

				frm.set_query('almacen_filtro', function(d){
						return {
							filters: {
								name:["in",r.message]  
					}
						}
				})
				  
			}
		});
		frm.fields_dict.materiales_detalles.grid.get_field("material").get_query = function(doc, cdt, cdn){
           
			return {
				filters: {
					item_code:["in","Primero seleccione una bodega"]  
				}
			}
		}

		if(frm.doc.almacen_filtro !== undefined){
			frappe.call({
				"method": "erpnext.support.doctype.service_order.service_order.filtrar_productos_disponibles_N", "args":{"almacen":frm.doc.almacen_filtro},
					callback: function(r) {
				   
							 frm.fields_dict.materiales_detalles.grid.get_field("material").get_query = function(doc, cdt, cdn){
							  frappe.model.set_value(cdt, cdn, "bodega", frm.doc.almacen_filtro);
								return {
									filters: {
										item_code:["in",r.message]  
									}
								}
							}
					 
					}
				})
				
			if(frm.doc.almacen_filtro !== undefined){
				 frm.fields_dict.materiales_detalles.grid.get_field("serial_no").get_query = function(doc, cdt, cdn){
				  frappe.model.set_value(cdt, cdn, "bodega", frm.doc.almacen_filtro);
					return {
						filters: {
							warehouse:frm.doc.almacen_filtro
						}
					}
				}
				
			}
			 else{
				 frm.fields_dict.materiales_detalles.grid.get_field("serial_no").get_query = function(doc, cdt, cdn){
							return {
								filters: {
									warehouse:"SELECCIONE UNA BODEGA"
								}
							}
						}
				
			}

		}

		if(frm.doc.tipo_de_orden == "GESTIÓN ADMINISTRATIVA")
		{

			if(frappe.session.user == 'Administrator' || frappe.session.user == 'jennyfer.barberena@ibw.com' ){
				set_field_options("gestion", ["RETIRO DE MATERIALES/EQUIPOS","RETIRO DE ENCOMIENDAS","TRASLADO DE PERSONAL","Consumos del Taller",
				"APOYO A INGENIERÍA","APOYO A VTA. DE EQUIPOS","APOYO AL TALLER","GESTION DE PAGO","GESTION DE VENTAS MASIVAS","Liquidacion Por Conciliacion de balance de Inventario"])

			}
			else{
				set_field_options("gestion", ["RETIRO DE MATERIALES/EQUIPOS","RETIRO DE ENCOMIENDAS","TRASLADO DE PERSONAL","Consumos del Taller",
				"APOYO A INGENIERÍA","APOYO A VTA. DE EQUIPOS","APOYO AL TALLER","GESTION DE PAGO","GESTION DE VENTAS MASIVAS"])

			}
	}
		else if(frm.doc.tipo_de_orden == "MANTENIMIENTO INTERNO")
		{
			set_field_options("gestion", ["AIRE ACONDICIONADO","PINTURA","SEGURIDAD","NOC","ELÉCTRICO","REPARACIÓN TECHO/PARED","LIMPIEZA"])
		}
		else if(frm.doc.tipo_de_orden == "VENTANA DE MANTENIMIENTO")
		{
			set_field_options("gestion", ["SERVICIOS FIBRA", "SERVICIOS GPON", "SERVICIOS HFC", "DIALUP/EMAIL", "EQUIPOS", "IMOVIL", "PUNTO A PUNTO", "PUNTO MULTIPUNTO", "LTE", "IPTV"])
		}
		else if(frm.doc.tipo_de_orden == "INSTALACIÓN DE NODO"){
			set_field_options("gestion", ["GPON INT RESIDENCIAL","GPON TV RESIDENCIAL","GPON CORPORATIVO","GPON TV CORPORATIVO","GPON INT PYME","GPON TV PYME","HFC","PUNTO A PUNTO", "PUNTO MULTIPUNTO"])
			
		}
		else if (frm.doc.tipo_de_orden == "AMPLIACION DE RED"){
			set_field_options("gestion", ["FIBRA OPTICA","GPON","HFC","PUNTO A PUNTO", "PUNTO MULTIPUNTO"])

		}
		else if (frm.doc.tipo_de_orden == "PRESUPUESTO"){
			set_field_options("gestion", ["PRESUPUESTO"])
	
		}
		else if (frm.doc.tipo_de_orden == "VENTA DE EQUIPOS"){
			set_field_options("gestion", ["INSTALACION DE EQUIPOS"])
	
		}
		else{
			set_field_options("gestion", [" "])
		}

	
	},
	calculate_total: function(frm) {
		let total = 0, base_total = 0;
		frm.doc.bom_de_materiales.forEach(item => {
			total += item.total;
			base_total += item.total_nio;
		})

		frm.set_value({
			'total_bom_usd': flt(total),
			'total_bom_nio': flt(base_total)
		});
	},
		currency: function(frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		if (company_currency != frm.doc.currency) {		
			frappe.call({
				method: "erpnext.setup.utils.get_exchange_rate",
				args: {
					from_currency: frm.doc.currency,
					to_currency: company_currency
				},
				callback: function(r) {
					if (r.message) {
						console.log('ts:' + flt(r.message))
						frm.set_value('_exchange_rate', flt(r.message));
						frm.set_df_property('_exchange_rate', 'description', '1 ' + frm.doc.currency
						+ ' = [?] ' + company_currency);
					}
				}
			});
		} else {
			frm.set_value('_exchange_rate', 1.0);
			frm.set_df_property('_exchange_rate', 'hidden', 1);
			frm.set_df_property('_exchange_rate', 'description', '');
		}
	},
});
frappe.ui.form.on("Orden de Servicio Interno", "tipo_de_orden", function(frm) {
	if(frm.doc.tipo_de_orden === 'INSTALACIÓN DE NODO' || frm.doc.tipo_de_orden === 'MANTENIMIENTO INTERNO'){
		frm.toggle_display("nodo", true);
	}
	else{
		frm.toggle_display("nodo", false);
	}
	if(frm.doc.tipo_de_orden == "GESTIÓN ADMINISTRATIVA")
	{
		if(frappe.session.user == 'Administrator' || frappe.session.user == 'jennyfer.barberena@ibw.com' ){
			set_field_options("gestion", ["RETIRO DE MATERIALES/EQUIPOS","RETIRO DE ENCOMIENDAS","TRASLADO DE PERSONAL","Consumos del Taller",
			"APOYO A INGENIERÍA","APOYO A VTA. DE EQUIPOS","APOYO AL TALLER","GESTION DE PAGO","GESTION DE VENTAS MASIVAS","Liquidacion Por Conciliacion de balance de Inventario"])

		}
		else{
			set_field_options("gestion", ["RETIRO DE MATERIALES/EQUIPOS","RETIRO DE ENCOMIENDAS","TRASLADO DE PERSONAL","Consumos del Taller",
			"APOYO A INGENIERÍA","APOYO A VTA. DE EQUIPOS","APOYO AL TALLER","GESTION DE PAGO","GESTION DE VENTAS MASIVAS"])

		}
	}
	else if(frm.doc.tipo_de_orden == "MANTENIMIENTO INTERNO")
	{
		set_field_options("gestion", ["AIRE ACONDICIONADO","PINTURA","SEGURIDAD","NOC","ELÉCTRICO","REPARACIÓN TECHO/PARED","LIMPIEZA"])
	}
	else if(frm.doc.tipo_de_orden == "VENTANA DE MANTENIMIENTO")
	{
		set_field_options("gestion", ["SERVICIOS FIBRA", "SERVICIOS GPON", "SERVICIOS HFC", "DIALUP/EMAIL", "EQUIPOS", "IMOVIL", "PUNTO A PUNTO", "PUNTO MULTIPUNTO", "LTE", "IPTV"])
	}
	else if(frm.doc.tipo_de_orden == "INSTALACIÓN DE NODO"){
		set_field_options("gestion", ["GPON INT RESIDENCIAL","GPON TV RESIDENCIAL","GPON CORPORATIVO","GPON TV CORPORATIVO","GPON INT PYME","GPON TV PYME","HFC","PUNTO A PUNTO", "PUNTO MULTIPUNTO"])
	}
	else if (frm.doc.tipo_de_orden == "AMPLIACION DE RED"){
		set_field_options("gestion", ["FIBRA OPTICA","GPON","HFC","PUNTO A PUNTO", "PUNTO MULTIPUNTO"])

	}
	else if (frm.doc.tipo_de_orden == "PRESUPUESTO"){
		set_field_options("gestion", ["PRESUPUESTO"])

	}
	else if (frm.doc.tipo_de_orden == "VENTA DE EQUIPOS"){
		set_field_options("gestion", ["INSTALACION DE EQUIPOS"])

	}
	else{
		set_field_options("gestion", [" "])
	}
});

frappe.ui.form.on("Orden de Servicio Interno", "almacen_filtro", function(frm) {    
	frappe.call({
    		"method": "erpnext.support.doctype.service_order.service_order.filtrar_productos_disponibles_N", "args":{"almacen":frm.doc.almacen_filtro},
				callback: function(r) {
               
       		          frm.fields_dict.materiales_detalles.grid.get_field("material").get_query = function(doc, cdt, cdn){
        		          frappe.model.set_value(cdt, cdn, "bodega", frm.doc.almacen_filtro);
                			return {
                				filters: {
                					item_code:["in",r.message]  
                				}
                			}
                		}               
				}
			})
			
	    if(frm.doc.almacen_filtro !== undefined){
             frm.fields_dict.materiales_detalles.grid.get_field("serial_no").get_query = function(doc, cdt, cdn){
	          frappe.model.set_value(cdt, cdn, "bodega", frm.doc.almacen_filtro);
    			return {
    				filters: {
    					warehouse:frm.doc.almacen_filtro
    				}
    			}
    		}
    		
	    }
	     else{
	         frm.fields_dict.materiales_detalles.grid.get_field("serial_no").get_query = function(doc, cdt, cdn){
            			return {
            				filters: {
            					warehouse:"SELECCIONE UNA BODEGA"
            				}
            			}
            		}	        
	    }
		      
        });

frappe.ui.form.on('Equipos BOM', {

	calculate: function(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	frappe.model.set_value(cdt, cdn, "total", flt(row.precio)*flt(row.qty));
	frappe.model.set_value(cdt, cdn, "total_nio", flt(row.precio_nio)*flt(row.qty));
	frm.trigger("calculate_total");
	},
	get_price: function(frm,cdt,cdn){
		let item = frappe.get_doc(cdt,cdn);
			if (item.item) {
			frappe.call({
				'method': "erpnext.support.doctype.service_order.service_order.obtener_tasa_de_valoracion_por_item",
				'args': {
					'item_code':item.item,
				},
				callback: function(r) {
					console.log('x:' + r.message)
					let precio = flt(r.message) || 0.0;
					frappe.model.set_value(cdt, cdn, 'precio_nio', precio);
					let precio_usd = precio / flt(frm.doc._exchange_rate);
					frappe.model.set_value(cdt, cdn, 'precio', precio_usd);
					console.log(frappe.model.get_value(cdt, cdn, 'precio_nio'))
					console.log(frappe.model.get_value(cdt, cdn, 'precio'))
				}
			});
			frm.trigger("calculate", cdt, cdn);
		}
	},
	item: function(frm, cdt, cdn) {
		frm.trigger("get_price", cdt, cdn);
		frm.trigger("calculate_total");
		frm.trigger("currency");

	},
	qty: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
		frm.trigger("calculate_total");
		frm.trigger("currency");

	},
	precio: function(frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
		frm.trigger("calculate_total");
	},
	precio_nio: function(frm,cdt,cdn) {
			frm.trigger("calculate", cdt, cdn);
		frm.trigger("calculate_total");
	}
	
});

frappe.ui.form.on("Orden de Servicio Interno", "departamento", function(frm) {
	frm.set_query('municipio', function(d){
		return {
			filters: {
				tipo_territorio: "Municipio",
				"parent_territory": frm.doc.departamento
			}
		}
	})

});
frappe.ui.form.on("Orden de Servicio Interno", "municipio", function(frm) {
	frm.set_query('barrio', function(d){
		return {
			filters: {
				tipo_territorio: "Barrio",
			"parent_territory": frm.doc.municipio
			}
		}
	})
});

frappe.ui.form.on('Materiales detalles', {
    serial_no: function(frm,cdt,cdn){
        let item = frappe.get_doc(cdt,cdn);
    	if (item.serial_no.length > 8) {     
            frappe.call({
				'method': "erpnext.support.doctype.service_order.service_order.obtener_item_code",
				'args': {
					'serial_no':item.serial_no,
				},
				callback: function(r) {
				    frappe.model.set_value(cdt, cdn, 'material', r.message);
				}
			});
        }
    } 
});
