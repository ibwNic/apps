// // Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// // For license information, please see license.txt

frappe.ui.form.on('Feedback', {
// 	refresh: function(frm) {
// 	//
// 	//frm.trigger("respuesta");
// 	},
// 	respuesta: function(frm) {
// 		frm.doc.feedback_preguntas.forEach(p => {
// 			frappe.call({
// 				method: "erpnext.crm.doctype.feedback.feedback.respuestas",
// 				args: {'name':p.pregunta_id},
// 				callback: function(r) {
// 					console.log(r.message)
// 					cur_frm.fields_dict["feedback_preguntas"].grid.set_df_property('respuesta', 'options', r.message);			
// 				}
// 			});
// 		})
// 	}
});
// frappe.ui.form.on("Feedback", "encuesta", function(frm) {
// 	frappe.call({
// 		method: "erpnext.crm.doctype.feedback.feedback.cargar_preguntas",
// 		args: {'encuesta':frm.doc.encuesta},
// 		callback: function(r) {
// 			//console.log(r.message)
// 			var doc = frappe.model.sync(r.message)[0];
// 		    frappe.set_route("Form", doc.doctype, doc.name);
// 			frm.trigger("respuesta")
// 		}
// 	});
	
	
// });

// frappe.ui.form.on("Feedback Preguntas","pregunta", function(frm, cdt, cdn) {
// 	console.log('entra')
// 		let row = frappe.get_doc(cdt, cdn);
// 		frappe.call({
// 			method: "erpnext.crm.doctype.feedback.feedback.respuestas",
// 			args: {'name':row.pregunta_id},
// 			callback: function(r) {
// 				console.log(r.message)		
// 			}
// 		});
// 	})


