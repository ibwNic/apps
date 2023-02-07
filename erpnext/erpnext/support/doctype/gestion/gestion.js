// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gestion', {
	refresh: function(frm) {
	if(frm.doc.tipo_gestion === 'Cancelaciones' || frm.doc.tipo_gestion === 'Suspension Temporal' ){
        frm.toggle_display("issue", false);

    }
    else{
        frm.toggle_display("cambiar_planes", false);
        frm.toggle_display("motivo", false);

    }
	},
    workflow_state:(frm) => {
        if (frm.doc.workflow_state === "Seguimiento"){
            frm.set_value('priority', 'Alto');
        }
  }
});
frappe.ui.form.on('Gestion', 'tipo_gestion', function(frm) {
    if(frm.doc.tipo_gestion === 'Cancelaciones' || frm.doc.tipo_gestion === 'Suspension Temporal' ){
        frm.toggle_display("issue", false);

    }
    else{
        frm.toggle_display("cambiar_planes", false);
        frm.toggle_display("motivo", false);

    }
})