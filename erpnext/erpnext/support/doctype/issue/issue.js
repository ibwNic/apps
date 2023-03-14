frappe.ui.form.on("Issue", {
	onload: function(frm) {
		frm.email_field = "raised_by";
		frm.set_query("customer", function () {
			return {
				filters: {
					"estado_cliente": "ACTIVO"
				}
			};
		});

		frappe.db.get_value("Support Settings", {name: "Support Settings"},
			["allow_resetting_service_level_agreement", "track_service_level_agreement"], (r) => {
				if (r && r.track_service_level_agreement == "0") {
					frm.set_df_property("service_level_section", "hidden", 1);
				}
				if (r && r.allow_resetting_service_level_agreement == "0") {
					frm.set_df_property("reset_service_level_agreement", "hidden", 1);
				}
			});

		// buttons
		if (frm.doc.status !== "Closed") {
			frm.add_custom_button(__("Close"), function() {
				frm.set_value("status", "Closed");
				frm.save();
			});

			frm.add_custom_button(__("Task"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.support.doctype.issue.issue.make_task",
					frm: frm
				});
			}, __("Create"));

		} else {
			frm.add_custom_button(__("Reopen"), function() {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	},

	reset_service_level_agreement: function(frm) {
		let reset_sla = new frappe.ui.Dialog({
			title: __("Reset Service Level Agreement"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "reason",
					label: __("Reason"),
					reqd: 1
				}
			],
			primary_action_label: __("Reset"),
			primary_action: (values) => {
				reset_sla.disable_primary_action();
				reset_sla.hide();
				reset_sla.clear();

				frappe.show_alert({
					indicator: "green",
					message: __("Resetting Service Level Agreement.")
				});

				frappe.call("erpnext.support.doctype.service_level_agreement.service_level_agreement.reset_service_level_agreement", {
					reason: values.reason,
					user: frappe.session.user_email
				}, () => {
					reset_sla.enable_primary_action();
					frm.refresh();
					frappe.msgprint(__("Service Level Agreement was reset."));
				});
			}
		});

		reset_sla.show();
	},
	refresh: function(frm) {
	    //console.log(frm.doc.customer);
	  // console.log(frm.doc.cambiar_equipo);
	  if(frm.doc.tipo_de_orden === 'Tramite' && frm.doc.sub_tipo === 'Oferta Comercial'){
		frm.add_custom_button(__("Solicitar Site"), function() {
			let d = frappe.model.get_new_name('service-order');
			frappe.route_options = {
				'tipo_de_orden':'SITE SURVEY',
				'tipo':'Issue',
				'tercero':frm.doc.name,
				'nombre':frm.doc.nombre,
				'descripcion':frm.doc.descripcion,
				'coordenadas':frm.doc.coordenadas,
				'latitud': frm.doc.latitud,
				'longitud':frm.doc.longitud,
				'telefonos': frm.doc.numero_de_telefono,
				'direccion':frm.doc.address_line1,
				'departamento':frm.doc.departamento,
				'municipio':frm.doc.municipio,
				'barrio':frm.doc.barrio,				
			};
			frappe.set_route(['Form', 'service-order', d]);
		})
	  }
	 

	  frm.set_query('tecnico', function(d){
			return {
				filters: {
						activo: 1
				}
			}
		})

		if(frm.doc.tipo_de_orden =='Tramite'){
			frm.toggle_display("issue_type", false);
			frm.toggle_display("sub_averia", false);
			frm.toggle_display("detalla_avaria", false);
			frm.toggle_display("cambiar_equipo", false);
			frm.toggle_display("productos", false);
			frm.toggle_display("tecnico", false);
			frm.toggle_display("detalle_solucion", false);
			frm.toggle_display("averia_masivo",false);
		}else{
			frm.toggle_display("cortesia", false);
			// frm.toggle_display("genera_débito",false);
		}	   
	   
	   	    if (frm.doc.tecnico !== undefined && frm.doc.cambiar_equipo ===1) {
	   	       
	        //console.log(frm.doc.equipos[0].modelo)
            frappe.call({
    		"method": "erpnext.support.doctype.service_order.service_order.equipos_de_almacen",
    		"args":{'portafolio': frm.doc.servicio, 'tecnico':frm.doc.tecnico},"type":"GET", callback: function(r) {
    		        console.log(r.message)
    		      frm.fields_dict.equipos.grid.get_field("equipo_nuevo").get_query = function(doc, cdt, cdn){
            			return {
            				filters: {
            					name: ["in", r.message]
            				}
            			}
            		}
    	}})
            }
            else{
                frm.set_df_property('equipos', 'read_only', frm.doc.__islocal ? 0 : 1);

            }
            
		frm.set_query('averia_masivo', function(d){
			return {
				filters: {
						workflow_state: "Abierto"
				}
			}
		})

        if (frm.doc.customer !== undefined) {
            frappe.db.get_value("Customer", {"name": frm.doc.customer},"customer_name",function(res){ 
        res.customer_name; }).then(r =>{ var rest=r.message;
        frm.set_value('nombre',rest.customer_name) })
        frappe.call({
			"method": "erpnext.support.doctype.issue.issue.get_plan_Susc_cust",
			"args": {
				"customer": frm.doc.customer
			        }
		}).then(r =>{
		            var doc=[]
		            var rest=r.message;
                    for (let i = 0; i < rest.length; i++) {
                        // get the size of the inner array
                        var innerArrayLength = rest[i].length;
                        // loop the inner array
                        for (let j = 0; j < innerArrayLength; j++) {
                            doc.push(rest[i][j]);
                        }
                    }
                    // console.log(doc);
                    // console.log(rest);
            	    frm.set_query('planes', function(d){
                    return {
                        filters: {
                            
                             name: ["in", doc]
                        }
                    }
                     }) 
    })
        } else {
                 frm.set_query('planes', function(d){
                    return {
                        filters: {
                             plan: ["in", ""]
                        }
                    }
                     }) 
        }

        if (frm.doc.issue_type !== undefined && frm.doc.sub_averia !== undefined) {
           frappe.db.get_value("Issue Type", {"name": frm.doc.sub_averia},["id_averia","id_padre"],function(res){
                res.id_averia;
                res.id_padre;
            }).then(r =>{
		            var rest=r.message;
		          //  console.log(rest);
            	    frm.set_query('detalle_solucion', function(d){
                        return {
                            filters: {
                                "idsubaveria": rest.id_averia,
                                 "idaveria": rest.id_padre
                            }
                        }
                     })
            })
        }
        
        
          if (frm.doc.workflow_state == "Finalizado"  && frm.doc.tipo_de_orden !== "Tramite" ) {
        frm.add_custom_button("Escalar a Averia", () => {
        	let d = frappe.model.get_new_name('issue');
        	frappe.route_options = {
        	    'gestion': frm.doc.gestion,
        		'subject': frm.doc.subject,
        		'customer':frm.doc.customer,
        		'planes':frm.doc.planes,
        		'servicio':frm.doc.servicio,
        		'departamento':frm.doc.departamento,
        		'municipio':frm.doc.municipio,
        		'barrio':frm.doc.barrio,
        		'address_line1':frm.doc.address_line1,
        		'longitud':frm.doc.longitud,
        		'latitud':frm.doc.latitud,
        		'priority':frm.doc.priority,
        		'issue_type':frm.doc.issue_type,
        		'sub_averia':frm.doc.sub_averia,
        		'detalla_avaria':frm.doc.detalla_avaria,
        		'averia_masivo':frm.doc.averia_masivo,
        		'tipo_de_orden': 'Averia'
        	};
        	frappe.set_route(['Form', 'issue', d]);
        }, __("Escalar ordenes"));}

        if (frm.doc.workflow_state == "Finalizado"  && frm.doc.tipo_de_orden == "Ticket" ) {
            
        frm.add_custom_button("Generar Ticket Iexpress", () => {
        	let d = frappe.model.get_new_name('issue');
        	frappe.route_options = {
        	    'gestion': frm.doc.gestion,
        		'subject': frm.doc.subject,
        		'customer':frm.doc.customer,
        		'planes':frm.doc.planes,
        		'servicio':frm.doc.servicio,
        		'departamento':frm.doc.departamento,
        		'municipio':frm.doc.municipio,
        		'barrio':frm.doc.barrio,
        		'address_line1':frm.doc.address_line1,
        		'longitud':frm.doc.longitud,
        		'latitud':frm.doc.latitud,
        		'priority':frm.doc.priority,
        		'issue_type':frm.doc.issue_type,
        		'sub_averia':frm.doc.sub_averia,
        		'detalla_avaria':frm.doc.detalla_avaria,
        		'averia_masivo':frm.doc.averia_masivo,
        		'tipo_de_orden': 'Ticket Iexpress'
        	};
        	frappe.set_route(['Form', 'issue', d]);
        }, __("Escalar ordenes"));}
	
    		frm.set_query('gestion', function(d){
                return {
                    filters: {
                         customer: frm.doc.customer,
                         estado: "Abierto"
                            }
                        }
            })
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
    	},
		coordenadas: function(frm){
			let mapdata = JSON.parse(frm.doc.coordenadas).features[0];
			if(mapdata && mapdata.geometry.type == 'Point'){
				let lat = mapdata.geometry.coordinates[1];
				let lon = mapdata.geometry.coordinates[0];
				
				frm.set_value("latitud",lat);
				frm.set_value("longitud",lon);
				
			}
		},

	timeline_refresh: function(frm) {
		if (!frm.timeline.wrapper.find(".btn-split-issue").length) {
			let split_issue_btn = $(`
				<a class="action-btn btn-split-issue" title="${__("Split Issue")}">
					${frappe.utils.icon('branch', 'sm')}
				</a>
			`);

			let communication_box = frm.timeline.wrapper.find('.timeline-item[data-doctype="Communication"]');
			communication_box.find('.actions').prepend(split_issue_btn);

			if (!frm.timeline.wrapper.data("split-issue-event-attached")) {
				frm.timeline.wrapper.on('click', '.btn-split-issue', (e) => {
					var dialog = new frappe.ui.Dialog({
						title: __("Split Issue"),
						fields: [
							{
								fieldname: "subject",
								fieldtype: "Data",
								reqd: 1,
								label: __("Subject"),
								description: __("All communications including and above this shall be moved into the new Issue")
							}
						],
						primary_action_label: __("Split"),
						primary_action: () => {
							frm.call("split_issue", {
								subject: dialog.fields_dict.subject.value,
								communication_id: e.currentTarget.closest(".timeline-item").getAttribute("data-name")
							}, (r) => {
								frappe.msgprint(`New issue created: <a href="/app/issue/${r.message}">${r.message}</a>`);
								frm.reload_doc();
								dialog.hide();
							});
						}
					});
					dialog.show();
				});
				frm.timeline.wrapper.data("split-issue-event-attached", true);
			}
		}

		// create button for "Help Article"
		// if (frappe.model.can_create("Help Article")) {
		// 	// Removing Help Article button if exists to avoid multiple occurrence
		// 	frm.timeline.wrapper.find('.action-btn .btn-add-to-kb').remove();

		// 	let help_article = $(`
		// 		<a class="action-btn btn-add-to-kb" title="${__('Help Article')}">
		// 			${frappe.utils.icon('solid-info', 'sm')}
		// 		</a>
		// 	`);

		// 	let communication_box = frm.timeline.wrapper.find('.timeline-item[data-doctype="Communication"]');
		// 	communication_box.find('.actions').prepend(help_article);
		// 	if (!frm.timeline.wrapper.data("help-article-event-attached")) {
		// 		frm.timeline.wrapper.on('click', '.btn-add-to-kb', function () {
		// 			const content = $(this).parents('.timeline-item[data-doctype="Communication"]:first').find(".content").html();
		// 			const doc = frappe.model.get_new_doc("Help Article");
		// 			doc.title = frm.doc.subject;
		// 			doc.content = content;
		// 			frappe.set_route("Form", "Help Article", doc.name);
		// 		});
		// 	}
		// 	frm.timeline.wrapper.data("help-article-event-attached", true);
		// }
	},
});


frappe.ui.form.on("Issue", "tipo_de_orden", function(frm) {
	if(frm.doc.tipo_de_orden === 'Tramite'){
		frm.toggle_display("issue_type", false);
		frm.toggle_display("sub_averia", false);
		frm.toggle_display("detalla_avaria", false);
		frm.toggle_display("cambiar_equipo", false);
		frm.toggle_display("productos", false);
		frm.toggle_display("tecnico", false);
		frm.toggle_display("detalle_solucion", false);
		frm.toggle_display("averia_masivo",false);
	}else{
		frm.toggle_display("cortesia", false);
		frm.toggle_display("genera_débito",false);
	}
});

frappe.ui.form.on("Issue", "departamento", function(frm) {
	frm.set_query('municipio', function(d){
	return {
		filters: {
			tipo_territorio: "Municipio",
			 "parent_territory": frm.doc.departamento
		}
	}
})

});

frappe.ui.form.on("Issue", "municipio", function(frm) {
frm.set_query('barrio', function(d){
	return {
		filters: {
			tipo_territorio: "Barrio",
		   "parent_territory": frm.doc.municipio
		}
	}
})
});