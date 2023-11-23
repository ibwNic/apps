// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gestion', {
	refresh: function(frm) {
        if(!frm.doc.__islocal){
            if(frm.doc.tipo_gestion == "Clientes Terminados" && frm.doc.subgestion == "Reactivacion" && frm.doc.workflow_state == "En Proceso"){
                frm.set_intro('ESCALAR para solicitar una orden de reactivación de los planes terminados que están en la tabla, FINALIZAR si no se hará la solicitud. Solicitar apoyo de IT solo en caso de no cargarse los planes terminados del cliente en la tabla.', 'blue');
            }
            if(frm.doc.tipo_gestion === 'Cancelaciones' && frm.doc.estado_cancelacion === 'Retenida' && frm.doc.workflow_state === 'En Proceso'){
                frm.set_intro('Si la cancelación ha sido retenida, la siguiente acción debe ser "Escalar gestión a BO"', 'blue');
            }
            if(frm.doc.tipo_gestion === 'Cancelaciones' && frm.doc.estado_cancelacion === 'Aceptada' && frm.doc.workflow_state === 'En Proceso'){
                frm.set_intro('Si la cancelación ha sido aceptada, la siguiente acción debe ser "Finalizar Gestión"', 'blue');
            }
            if(frm.doc.tipo_gestion === 'Tramites' && (frm.doc.subgestion === 'Oferta Comercial' || frm.doc.subgestion=='Nueva Venta' ) && frm.doc.workflow_state === 'En Proceso'){
                frm.set_intro('Escalar gestión a BO si desea hacer una actualización de contrato', 'blue');
            }
            if(frm.doc.tipo_gestion === 'Tramites' || frm.doc.tipo_gestion === 'Venta' || frm.doc.tipo_gestion === 'Reclamos'){
                // frm.add_custom_button(__("Site Survey"), function() {
                //     let d = frappe.model.get_new_name('service-order');
                //     frappe.route_options = {
                //         'tipo_de_orden':'SITE SURVEY',
                //         'tipo':'Customer',
                //         'tercero':frm.doc.customer,
                //         'nombre':frm.doc.nombre,
                //         'descripcion':frm.doc.detalle_gestion,
                //         'departamento':frm.doc.departamento,
                //         'municipio': frm.doc.municipio,
                //         'barrio':frm.doc.barrio,
                //         'tipo_de_origen': frm.doc.doctype,
                //         'nombre_de_origen':frm.doc.name,	
                //         'portafolio': '',
                //         'proveedor': 'IBW'			
                //     };
                //     frappe.set_route(['Form', 'service-order', d]);
                // }, __('Crear...'));
                // || frm.doc.subgestion === 'Oferta Comercial' 
                if((frm.doc.subgestion === 'Oferta Comercial' ||  frm.doc.subgestion=='Nueva Venta' )&& frm.doc.workflow_state === 'Escalado' && frm.doc.convertido === 0){
                    frm.add_custom_button(__("Actualización de Contrato"), function() {
                        let d = frappe.model.get_new_name('subscription-update');
                        frappe.route_options = {
                            'customer':frm.doc.customer,
                            'gestion':frm.doc.name,                           				
                        };
                        frappe.set_route(['Form', 'subscription-update', d]);
                    }, __('Crear...'));
                }
                if(frm.doc.subgestion === 'Cambio Razón Social' && frm.doc.workflow_state === 'Escalado' && frm.doc.convertido === 0){
                    frm.add_custom_button(__("Cambio Razón Social"), function() {
                        let d = frappe.model.get_new_name('cambio-de-razon-social');
                        frappe.route_options = {
                            'cliente':frm.doc.customer,
                            'gestion':frm.doc.name,                           				
                        };
                        frappe.set_route(['Form', 'cambio-de-razon-social', d]);
                    }, __('Crear...'));
                }
            }
            if(frm.doc.tipo_gestion == "Clientes Terminados" && frm.doc.subgestion == "Reactivacion" && frm.doc.workflow_state == "Escalado")
            {
                frm.add_custom_button("Crear Orden de Reactivación", () => {
                    frm.doc.cambiar_planes.forEach(item => {
                        frappe.call({
                            "method": "erpnext.support.doctype.gestion.gestion.generar_orden_de_reactivacion","args":{"plan": item.plan,"gestion":frm.doc.name},
                                callback: function(r){
                                frm.reload_doc()                   
                            }
                        });                 
                        
                    });
                    
                }, __('Reactivación'));
                frm.add_custom_button("No Reactivar", () => {
                    frappe.call({
                        "method": "erpnext.support.doctype.gestion.gestion.finalizar_gestion","args":{"gestion":frm.doc.name},
                            callback: function(r){
                            frm.reload_doc()                   
                        }
                    });
                    
                }, __('Reactivación'));
            }

        }
        if(frm.doc.convertido === 1 && frm.doc.facturado === 1 && frm.doc.issue.length > 1 && frm.doc.workflow_state === "Atendido" && ["TV Adicional","Cableado","Traslado de Servicio", "Instalacion OTC"].includes(frm.doc.subgestion)){
            let abiertas   = false;
            frm.doc.issue.forEach(item => {
                if(item.estado !=='Finalizado' && item.estado !== 'Cancelado'){
                    abiertas = true;
                }
                if(item.tipo_documento === 'Service Order' && (item.estado === 'Finalizado' || item.estado === 'Cancelado')){
                    frm.add_custom_button("Generar Factura de Débito", () => {
                    if (abiertas){
                        msgprint("todavía hay ordenes sin finalizar");
                    }
                    var d = new frappe.ui.Dialog({
                        title: __("Generar Factura de Débito"),
                        fields: [
                            {"fieldname":"costo", "fieldtype":"Data", "label":__("Ingrese costo OTC en dólares"),"reqd": "1",		},
                            {"fieldname":"fetch", "label":__("Crear Factura de " + frm.doc.subgestion ), "fieldtype":"Button"}
                        ]
                    });

                    d.get_input("fetch").on("click", function() {
                        var values = d.get_values();
                        if(!values) return;
                        //console.log(values)
                        frappe.call({
                            "method": "erpnext.accounts.doctype.subscription.subscription.gestion_generar_factura","args":{"costo": values.costo,"gestion":frm.doc.name},
                                callback: function(r){
                                frm.reload_doc()
                            
                            }
                        });
                
                    });
                    d.show();
                    });
                }
            });
        }
    
        // if(frm.doc.convertido === 0 && frm.doc.estado === 'Retenida' && !frm.doc.__islocal){
        //     frappe.call({					
        //         method: "erpnext.support.doctype.gestion.gestion.ocultar_actualizacion",
        //         args: {"name":frm.doc.name},
        //         callback: function(r) {                   
        //         }
        //     });
        // }
       
        if(frm.doc.tipo_gestion === 'Cancelaciones' || frm.doc.tipo_gestion === 'Suspensiones'){
                frm.toggle_display("issue", false);

        }
        else{
            frm.toggle_display("cambiar_planes", false);
            frm.toggle_display("motivo", false);
            if (frm.doc.tipo_gestion === 'Clientes Terminados'){
                if(frm.doc.subgestion === "Reactivacion"){
                    frm.toggle_display("cambiar_planes", true);
                    frm.toggle_display("facturas_pendientes", false);
        
                }
                else if (frm.doc.subgestion === 'Borra Saldo'){
                    frm.toggle_display("facturas_pendientes", true);
                    frm.toggle_display("cambiar_planes", false);
        
                }
            }
            else{
                frm.toggle_display("facturas_pendientes", false);
            }

        }
      
      

	},
});
frappe.ui.form.on('Gestion', 'tipo_gestion', function(frm) {
    if(frm.doc.tipo_gestion === 'Cancelaciones' || frm.doc.tipo_gestion === 'Suspensiones'){
        frm.toggle_display("issue", false);
    }
    else{
        frm.toggle_display("issue", true);
        frm.toggle_display("cambiar_planes", false);
        frm.toggle_display("motivo", false);
        frm.toggle_display("estado_cancelacion",false);
       // frm.toggle_display("fecha_inicio_suspension_temporal",false);

    }
    if(frm.doc.tipo_gestion.length > 0 && frm.doc.customer){
        frappe.call({
            "method": "erpnext.support.doctype.gestion.gestion.validar_cliente",
            "args": {
                "customer": frm.doc.customer,
                "tipo_gestion":frm.doc.tipo_gestion
            }
            ,callback:function(r){
                console.log(r.message)
                if(r.message!==undefined){
                    frappe.set_route(['Form', 'gestion',r.message]);	
                }
            }
        });
    if(frm.doc.customer !== undefined && frm.doc.customer.length !== 0 &&   ['Cancelaciones','Suspensiones'].includes(frm.doc.tipo_gestion)){
        frappe.call({					
            method: "erpnext.support.doctype.gestion.gestion.obtener_planes_de_cliente",
            args: {"customer":frm.doc.customer, "tipo_gestion": frm.doc.tipo_gestion},
            callback: function(r) {            
            var doc = frappe.model.sync(r.message)[0];
            frappe.set_route("Form", doc.doctype, doc.name);
            }
        });
    }
    }
})

frappe.ui.form.on('Gestion', 'subgestion', function(frm) {
    if(frm.doc.customer !== undefined && frm.doc.customer.length !== 0 &&   ['Clientes Terminados'].includes(frm.doc.tipo_gestion) && frm.doc.subgestion == "Reactivacion"){
        frappe.call({					
            method: "erpnext.support.doctype.gestion.gestion.obtener_planes_de_cliente_Terminados",
            args: {"customer":frm.doc.customer, "tipo_gestion": frm.doc.tipo_gestion, "subgestion":frm.doc.subgestion},
            callback: function(r) {            
            var doc = frappe.model.sync(r.message)[0];
            frappe.set_route("Form", doc.doctype, doc.name);
            }
        });
    }
    if(frm.doc.customer !== undefined && frm.doc.customer.length !== 0 &&   ['Clientes Terminados'].includes(frm.doc.tipo_gestion) && frm.doc.subgestion == "Borra Saldo"){
        frappe.call({					
            method: "erpnext.support.doctype.gestion.gestion.obtener_facturas_pendientes",
            args: {"customer":frm.doc.customer, "tipo_gestion": frm.doc.tipo_gestion, "subgestion":frm.doc.subgestion},
            callback: function(r) {            
            var doc = frappe.model.sync(r.message)[0];
            frappe.set_route("Form", doc.doctype, doc.name);
            }
        });
    }
})

