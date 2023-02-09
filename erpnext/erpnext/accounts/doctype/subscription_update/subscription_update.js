// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subscription Update', {
	refresh: function(frm) {
		// if(frm.doc.name==='new-subscription-update-1'){
		// 	frm.toggle_display("actualizar_planes_de_contrato", false);
		// }
		// if(!(frm.doc.name.includes("SU"))){
		// 	frm.toggle_display("actualizar_planes_de_contrato", false);
		// }

		if(!frm.doc.__islocal){
			frm.set_df_property('actualizar_planes_de_contrato', 'read_only', false);
		}
		else{
			frm.set_df_property('actualizar_planes_de_contrato', 'read_only', true);
		}
		if(frm.doc.contrato !== undefined && frm.doc.customer!== undefined){
			frappe.call({
			"method": "erpnext.accounts.doctype.subscription_update.subscription_update.filtrar_planes_de_usuario",
			"args":{
				'contrato': frm.doc.contrato,
				'customer': frm.doc.customer 
				}}).then(r=>{
					//console.log(r.message)
				  frm.fields_dict.actualizar_planes_de_contrato.grid.get_field("plan").get_query = function(doc, cdt, cdn){
						return {
							filters: {
								name: ["in", r.message]
							}
						}
					}
				}) 
			} 
			if(frm.doc.customer !== undefined && frm.doc.customer.length !== 0){
				// console.log(rest.name)
				frm.set_query('contrato', function(d){
					return {
						filters: {
							workflow_state: "Activo",
							party:frm.doc.customer
						}
					}
					})
			}
			frm.fields_dict.actualizar_planes_de_contrato.grid.get_field("nuevo_plan").get_query = function(doc, cdt, cdn){
				let row = frappe.get_doc(cdt, cdn);
				let plan = row.name_old_plan;
				
				frappe.call({
					"method": "erpnext.accounts.doctype.subscription_update.subscription_update.filtrar_planes_nuevos",
					"args":{
						'contrato': frm.doc.contrato,
						'customer': frm.doc.customer 
						}}).then(r=>{
							if(r.message){
								localStorage.setItem("planes",r.message)
							}
							else{
								localStorage.removeItem("planes")
							}
						}) 
				
				//console.log(localStorage.getItem("planes"))
				if (plan && !(localStorage.getItem("planes"))) {
					if(plan.includes("+ TV")){
						return {
							filters: {
								activo: 1,
								es_combo : 1
							}
						}
					}
					else if(plan === 'TV Combo GPON' || plan === 'TV Combo HFC' || plan.includes('GPON-TV-RESIDENCIAL SIN VELOCIDAD')){
						return {
							filters: {
								name: ['in',['TV Combo GPON','TV Combo HFC']]
							}
						}
					}
					else{
						return {
							filters: {
								activo: 1,
								es_corporativo:0,
								tarifa_ibw:1
							}
						}
					}
				}
				else if(plan && localStorage.getItem("planes")){
					return {
						filters: {
							name: ['in', localStorage.getItem("planes").split(",")]
						}
					}
				}
				else{
					return {
						filters: {
							activo: 1,
							tarifa_ibw:1
						}
					}
				}
			}
			// frappe.call({
			// 	"method": "erpnext.accounts.doctype.subscription_update.subscription_update.filtrar_planes_ibw",
			// 	}).then(r=>{
			// 			//console.log(r.message)
			// 		  frm.fields_dict.actualizar_planes_de_contrato.grid.get_field("nuevo_plan").get_query = function(doc, cdt, cdn){
			// 				return {
			// 					filters: {
			// 						name: ["in", r.message]
			// 					}
			// 				}
			// 			}
			// 		}) 
	},
	after_save(frm) {
		console.log(frm.doc.actualizar_planes_de_contrato)
		if(frm.doc.actualizar_planes_de_contrato.length === 0){
			console.log(frm.doc.actualizar_planes_de_contrato)
			frappe.call({					
				method: "erpnext.accounts.doctype.subscription_update.subscription_update.obtener_planes_de_contrato",
				args: {"name":frm.doc.name, "contrato":frm.doc.contrato, "customer":frm.doc.customer},
				callback: function(r) {
				//console.log(r.message)
				frm.reload_doc();	
				}
			});
			
		}
		frm.set_df_property('customer', 'read_only', frm.doc.__islocal ? 0 : 1);
	}
	 
});

frappe.ui.form.on("Subscription Update", "contrato", function(frm) {
	if(frm.doc.contrato !== undefined && frm.doc.contrato.length !== 0){
		frappe.call({					
			method: "erpnext.accounts.doctype.subscription_update.subscription_update.obtener_planes_de_contrato",
			args: {"name":frm.doc.name, "contrato":frm.doc.contrato, "customer":frm.doc.customer},
			callback: function(r) {
			//console.log(r.message)	
			frm.reload_doc();
			}
		});
		frappe.call({
			"method": "erpnext.accounts.doctype.subscription_update.subscription_update.filtrar_planes_de_usuario",
			"args":{
				'contrato': frm.doc.contrato, 
				}}).then(r=>{
					console.log(r.message)
				  frm.fields_dict.actualizar_planes_de_contrato.grid.get_field("plan").get_query = function(doc, cdt, cdn){
						return {
							filters: {
								name: ["in", r.message]
							}
						}
					}
				}) 
	}
});

frappe.ui.form.on("Subscription Update", "customer", function(frm) {
	if(frm.doc.customer !== undefined && frm.doc.customer.length !== 0){

		frm.set_query('contrato', function(d){
			return {
				filters: {
					workflow_state: "Activo",
					party:frm.doc.customer
				}
			}
			})

		}		
});

frappe.ui.form.on("Subscription Update Planes", {
	calculate: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		let costo = row.coston;
		let descuento = row.descuento;
		frappe.model.set_value(cdt, cdn, "coston", costo-costo*(descuento/100));
	},
	descuento: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frm.trigger("calculate", cdt, cdn);
		if(row.descuento==0 || !row.descuento){
			frappe.db.get_value("Subscription Plan", {"name": row.nuevo_plan},"cost",function(res){
				res.cost;
			}).then(r =>{
					var rest=r.message;
					frappe.model.set_value(cdt, cdn, "coston", rest.cost);
			})
		}
	},
	nuevo_plan: function(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.db.get_value("Subscription Plan", {"name": row.nuevo_plan},"cost",function(res){
			res.cost;
		}).then(r =>{
				var rest=r.message;
				frappe.model.set_value(cdt, cdn, "coston", rest.cost);
				frm.trigger("calculate", cdt, cdn);
		})
		
	},
})
