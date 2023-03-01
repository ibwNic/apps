// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gestion', {
	refresh: function(frm) {
        if(frm.doc.issue.length>1){
            frm.doc.issue.forEach(item => {
                if(item.tipo_documento === 'Service Order' && item.estado === 'Finalizado'){
                    frm.add_custom_button("Generar Factura", () => {
                        msgprint("generar factura")
                    });
                }
            });
        }
    
        if(frm.doc.convertido === 0 && frm.doc.estado === 'Retenido' && !frm.doc.__islocal){
            frappe.call({					
                method: "erpnext.support.doctype.gestion.gestion.ocultar_actualizacion",
                args: {"name":frm.doc.name},
                callback: function(r) {                   
                }
            });
        }
        if(frm.doc.convertido === 0 && frm.doc.estado === 'Finalizado' && !frm.doc.__islocal){
            frappe.call({					
                method: "erpnext.support.doctype.gestion.gestion.ocultar_orden_servicio",
                args: {"name":frm.doc.name},
                callback: function(r) {                   
                }
            });
        }
	if(frm.doc.tipo_gestion === 'Cancelaciones' || frm.doc.tipo_gestion === 'Suspension Temporal' ){
        frm.toggle_display("issue", false);

    }
    else{
        frm.toggle_display("cambiar_planes", false);
        frm.toggle_display("motivo", false);

    }
	}
});
frappe.ui.form.on('Gestion', 'tipo_gestion', function(frm) {
    if(frm.doc.tipo_gestion === 'Cancelaciones' || frm.doc.tipo_gestion === 'Suspension Temporal'){
        frm.toggle_display("issue", false);
    }
    else{
        frm.toggle_display("issue", true);
        frm.toggle_display("cambiar_planes", false);
        frm.toggle_display("motivo", false);
        frm.toggle_display("estado_cancelacion",false);
        frm.toggle_display("fecha_inicio_suspension_temporal",false);

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
    if(frm.doc.customer !== undefined && frm.doc.customer.length !== 0 &&   ['Cancelaciones','Suspension Temporal'].includes(frm.doc.tipo_gestion)){
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