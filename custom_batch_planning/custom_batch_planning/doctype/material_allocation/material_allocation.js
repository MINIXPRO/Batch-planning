// // ============================================================
// // 1. PARENT DOCTYPE EVENTS (Material Allocation)
// // ============================================================
// frappe.ui.form.on("Material Allocation", {
//     setup: function (frm) {
//         frm.set_query("batch_planning", function () {
//             return { filters: { workflow_state: "Approved" } };
//         });
//     },

//     onload: function (frm) {
//         if (frm.is_new() && !frm.doc.workflow_state) {
//             frm.doc.workflow_state = "Draft";
//         }
//     },

//     refresh: function (frm) {
//         frm.clear_custom_buttons();

//         let is_empty = !frm.doc.material_allocation || frm.doc.material_allocation.length === 0;
//         if (
//             (frm.is_new() || frm.doc.workflow_state === "Draft") &&
//             frm.doc.batch_planning &&
//             is_empty
//         ) {
//             setTimeout(() => {
//                 let current_empty =
//                     !frm.doc.material_allocation || frm.doc.material_allocation.length === 0;
//                 if (current_empty) {
//                     window.upload_bom_items(frm);
//                 }
//             }, 500);
//         }

//         // Lock grid if Allocated/Deallocated
//         if (frm.doc.allocation_status) {
//             frm.set_df_property("material_allocation", "read_only", 1);
//             frm.refresh_field("material_allocation");
//         } else {
//             // Draft or Approved without allocation — only allocate_qty and reason editable
//             frm.fields_dict["material_allocation"].grid.editable_grid = true; // ✅ force editable grid
//             frm.fields_dict["material_allocation"].grid.update_docfield_property(
//                 "allocate_qty",
//                 "read_only",
//                 0,
//             );
//             frm.fields_dict["material_allocation"].grid.update_docfield_property(
//                 "reason",
//                 "read_only",
//                 0,
//             );
//             frm.refresh_field("material_allocation");
//         }

//         if (
//             !frm.is_new() &&
//             frm.doc.employee_function &&
//             frm.doc.material_allocation &&
//             frm.doc.material_allocation.length
//         ) {
//             if (!frm.doc.allocation_status) {
//                 setTimeout(function () {
//                     window.refresh_stock_available(frm);
//                 }, 1000);
//             }
//         }


//         // ── View Allocation History Button (With Item-Level Drill Down) ──
//         if (!frm.is_new() && frm.doc.batch_planning && frm.doc.workflow_state === "Approved") {
//             frm.add_custom_button(__("📋 Allocation History"), function () {
//                 frappe.call({
//                     method: "frappe.client.get_list",
//                     args: {
//                         doctype: "Material Allocation Log",
//                         filters: { batch_planning: frm.doc.batch_planning },
//                         fields: ["name"],
//                         limit: 1,
//                     },
//                     callback: function (r) {
//                         if (!r.message || !r.message.length) {
//                             frappe.msgprint({
//                                 title: "No History",
//                                 message: "No allocation history found for this batch.",
//                                 indicator: "orange",
//                             });
//                             return;
//                         }

//                         frappe.call({
//                             method: "frappe.client.get",
//                             args: { doctype: "Material Allocation Log", name: r.message[0].name },
//                             callback: function (res) {
//                                 let ma_logs = res.message.ma_logs || [];
//                                 let history = res.message.table || [];

//                                 if (!ma_logs.length) {
//                                     frappe.msgprint({
//                                         title: "No History",
//                                         message: "No allocation history found.",
//                                         indicator: "orange",
//                                     });
//                                     return;
//                                 }

//                                 window._ma_history_data = history;

//                                 let rows = ma_logs.map((d) => {
//                                     return `
//                                 <tr style="cursor:pointer;" onclick="window._show_item_history('${d.item_code}')">
//                                     <td style="padding:8px 12px; color:#1b5e20; font-weight:bold;">${d.item_code} 🔍</td>
//                                     <td style="padding:8px 12px;">${d.item_name}</td>
//                                     <td style="padding:8px 12px;">${d.quantity_required}</td>
//                                     <td style="padding:8px 12px;">${d.qty_allocated}</td>
//                                 </tr>
//                             `;
//                                 }).join("");

//                                 let d = new frappe.ui.Dialog({
//                                     title: "📋 Allocation History",
//                                     size: "extra-large",
//                                 });

//                                 d.body.innerHTML = `
//                             <table class="table table-bordered" style="width:100%;font-size:13px;">
//                                 <thead style="background:#f1f5f9;">
//                                     <tr>
//                                         <th style="padding:8px 12px;">Item Code</th>
//                                         <th style="padding:8px 12px;">Item Name</th>
//                                         <th style="padding:8px 12px;">Qty Required</th>
//                                         <th style="padding:8px 12px;">Qty Allocated</th>
//                                     </tr>
//                                 </thead>
//                                 <tbody>${rows}</tbody>
//                             </table>
//                         `;

//                                 d.show();
//                             },
//                         });
//                     },
//                 });
//             });
//         }

//         // Action Buttons: Visibility based on allocation status
//         if (!frm.is_new() && frm.doc.workflow_state === "Approved" && frm.doc.docstatus !== 2) {
//             if (!frm.doc.allocation_status) {
//                 frm.add_custom_button(
//                     __("Auto Allocate"),
//                     function () {
//                         window.auto_allocate_all(frm);
//                     },
//                     __("Actions"),
//                 ).addClass("btn-primary");
//             } else if (frm.doc.allocation_status === "Allocated") {
//                 frm.add_custom_button(
//                     __("Deallocate"),
//                     function () {
//                         window.deallocate_all(frm);
//                     },
//                     __("Actions"),
//                 ).addClass("btn-danger");
//             } else if (frm.doc.allocation_status === "Deallocated") {
//                 frm.dashboard.add_comment(
//                     __(
//                         "⚠️ This document has been Deallocated. Create a new Material Allocation for the same Planned Batch to allocate again.",
//                     ),
//                     "orange",
//                     true,
//                 );
//             }
//         }

//         window.load_expiry_status(frm);

//         // Highlight Modified Rows
//         setTimeout(function () {
//             (frm.doc.material_allocation || []).forEach(function (row) {
//                 if (row.reason && row.allocate_qty != row.quantity_required) {
//                     let grid_row =
//                         frm.fields_dict["material_allocation"].grid.grid_rows_by_docname[row.name];
//                     if (grid_row && grid_row.row) {
//                         grid_row.row.css("background-color", "#f3e5f5");
//                     }
//                 }
//             });
//         }, 1000);
//     },

//     validate: function (frm) {
//         let stock_error = null;
//         let reason_error = null;
//         let shortage_rows = [];

//         (frm.doc.material_allocation || []).forEach(function (row) {
//             let stock = parseFloat(row.stock_available || 0);
//             let alloc = parseFloat(row.allocate_qty || 0);

//             // Rule: Cannot save if stock_available < allocate_qty (qty requested)
//             if (!stock_error && stock < alloc) {
//                 shortage_rows.push(row);
//             }

//             // Rule: Reason mandatory if Qty Requested != Quantity Required
//             if (!reason_error && row.allocate_qty != row.quantity_required && !row.reason) {
//                 reason_error = `Row ${row.idx} (${row.item_name || row.item_code}): Qty Requested differs from Quantity Required. Please fill Reason.`;
//             }
//         });

//         if (shortage_rows.length > 0) {
//             let rows_list = shortage_rows
//                 .map(
//                     (r) =>
//                         `Row ${r.idx} — <b>${r.item_code}</b>: Stock Available (${r.stock_available || 0}) < Qty Requested (${r.allocate_qty || 0})`,
//                 )
//                 .join("<br>");
//             frappe.msgprint({
//                 title: __("⚠️ Insufficient Stock"),
//                 message: __(
//                     "The following items have <b>Stock Available less than Qty Requested</b>. " +
//                     "Please adjust the Qty Requested shortages.<br><br>" +
//                     rows_list,
//                 ),
//                 indicator: "red",
//             });
//             frappe.validated = false;
//             return;
//         }

//         if (reason_error) {
//             frappe.msgprint({
//                 title: __("Validation Failed"),
//                 message: __(reason_error),
//                 indicator: "red",
//             });
//             frappe.validated = false;
//         }
//     },

//     after_save: function (frm) {
//         if (frm._allocating) return;
//         setTimeout(function () {
//             if (frm.doc.allocation_status) return;
//             if (
//                 frm.doc.employee_function &&
//                 frm.doc.material_allocation &&
//                 frm.doc.material_allocation.length
//             ) {
//                 window.refresh_stock_available(frm);
//             }
//             window.load_expiry_status(frm);
//         }, 1500);
//     },

//     employee_function: function (frm) {
//         if (
//             frm.doc.employee_function &&
//             frm.doc.material_allocation &&
//             frm.doc.material_allocation.length
//         ) {
//             window.refresh_stock_available(frm);
//         }
//     },

//     batch_planning: function (frm) {
//         if (!frm.doc.batch_planning) return;
//         frappe.db.get_value(
//             "Batches Planned",
//             frm.doc.batch_planning,
//             ["project", "project_name"],
//             function (data) {
//                 if (data) {
//                     frm.set_value("project_id", data.project);
//                     frm.set_value("project_name", data.project_name);
//                 }
//             },
//         );
//     },
// });

// // ============================================================
// // 2. CHILD TABLE EVENTS (Material Allocation Item)
// // ============================================================
// frappe.ui.form.on("Material Allocation Item", {
//     allocate_qty: function (frm, cdt, cdn) {
//         let row = locals[cdt][cdn];
//         if (row.allocate_qty != row.quantity_required && !row.reason) {
//             frappe.show_alert({
//                 message: "Row " + row.idx + ": Please fill Reason for allocation change!",
//                 indicator: "orange",
//             });
//         }
//     },
// });

// // ============================================================
// // 3. GLOBAL HELPER FUNCTIONS
// // ============================================================

// // Drill-down Target UI: Displays full sequential audit trails inside your primary history logs
// window._show_item_history = function (item_code) {
//     let filtered = (window._ma_history_data || [])
//         .filter((d) => d.item_code === item_code)
//         .sort((a, b) => (a.allocated_on > b.allocated_on ? 1 : -1));

//     if (!filtered.length) {
//         frappe.msgprint({
//             title: "No Events",
//             message: `No events found for ${item_code}`,
//             indicator: "orange",
//         });
//         return;
//     }

//     let rows = filtered
//         .map(
//             (d) => `
//         <tr>
//             <td style="padding:8px 12px;">${d.allocated_by}</td>
//             <td style="padding:8px 12px;">${d.allocated_on}</td>
//             <td style="padding:8px 12px;">${d.qty_allocated ?? "-"}</td>
//             <td style="padding:8px 12px;">${d.material_allocation_id}</td>
//         </tr>
//     `,
//         )
//         .join("");

//     let ed = new frappe.ui.Dialog({
//         title: `📦 Events for: ${item_code}`,
//         size: "extra-large",
//     });

//     ed.body.innerHTML = `
//     <table class="table table-bordered" style="width:100%;font-size:13px;">
//         <thead style="background:#f1f5f9;">
//             <tr>
//                 <th style="padding:8px 12px;">Allocated By</th>
//                 <th style="padding:8px 12px;">Date & Time</th>
//                 <th style="padding:8px 12px;">Qty Allocated</th>
//                 <th style="padding:8px 12px;">MA ID</th>
//             </tr>
//         </thead>
//         <tbody>${rows}</tbody>
//     </table>
// `;

//     ed.show();
// };

// window.refresh_stock_available = function (frm) {
//     let items = frm.doc.material_allocation || [];
//     if (!items.length) return;

//     let item_codes = items.map((r) => r.item_code);
//     fetch(
//         "/api/method/custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.get_open_pr_po",
//         {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json",
//                 "X-Frappe-CSRF-Token": frappe.csrf_token,
//             },
//             body: JSON.stringify({ item_codes: item_codes }),
//         },
//     )
//         .then((r) => r.json())
//         .then((data) => {
//             let pr_po_map = data.message || {};
//             items.forEach(function (row) {
//                 frappe.call({
//                     method: "custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.ma_get_allocated_qty",
//                     args: {
//                         item_code: row.item_code,
//                         employee_function: frm.doc.employee_function,
//                         exclude_parent: frm.doc.name,
//                         row_name: row.name,
//                     },
//                     callback: function (res) {
//                         if (res.message) {
//                             let grid_row =
//                                 frm.fields_dict["material_allocation"].grid.grid_rows_by_docname[
//                                 row.name
//                                 ];
//                             let free_stock = res.message.free_stock || 0;
//                             let qty_req = row.quantity_required || 0;
//                             let pr_po = pr_po_map[row.item_code] || {};

//                             if (grid_row) {
//                                 let allocated = grid_row.doc.qty_allocated || 0;
//                                 let display_stock = Math.max(free_stock - allocated, 0);

//                                 grid_row.doc.stock_available = display_stock;
//                                 grid_row.doc.shortage = Math.max(qty_req - display_stock, 0);
//                                 grid_row.doc.open_pr = pr_po.open_pr || 0;
//                                 grid_row.doc.open_po = pr_po.open_po || 0;

//                                 grid_row.refresh_field("stock_available");
//                                 grid_row.refresh_field("shortage");
//                                 grid_row.refresh_field("open_pr");
//                                 grid_row.refresh_field("open_po");
//                             }
//                         }
//                     },
//                 });
//             });
//         });
// };

// window.auto_allocate_all = function (frm) {
//     if (frm.is_dirty()) {
//         frappe.msgprint(__("Please save the document before allocating."));
//         return;
//     }

//     frappe.confirm(
//         "⚠️ Auto Allocation will use <b>FEFO logic</b> (earliest expiry first) to allocate batches. Continue?",
//         function () {
//             frm.call({
//                 doc: frm.doc,
//                 method: "auto_allocate",
//                 freeze: true,
//                 freeze_message: __("Allocating Batches..."),
//             }).then((r) => {
//                 if (!r.exc) {
//                     frappe.show_alert({
//                         message: __("✅ Allocated successfully!"),
//                         indicator: "green",
//                     });
//                     frm.reload_doc();
//                 }
//             });
//         },
//     );
// };

// window.deallocate_all = function (frm) {
//     frappe.confirm(
//         "⚠️ This will release all allocated quantities and clear batch details. Continue?",
//         function () {
//             frm.call("deallocate").then((r) => {
//                 if (!r.exc) {
//                     frappe.show_alert({
//                         message: __("✅ Deallocated successfully!"),
//                         indicator: "blue",
//                     });
//                     frm.reload_doc();
//                 }
//             });
//         },
//     );
// };

// window.load_expiry_status = function (frm) {
//     if (!frm.doc.material_allocation || !frm.doc.material_allocation.length) return;
//     let item_codes = frm.doc.material_allocation.map((r) => r.item_code);
//     fetch(
//         "/api/method/custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.get_item_batch_expiry",
//         {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json",
//                 "X-Frappe-CSRF-Token": frappe.csrf_token,
//             },
//             body: JSON.stringify({ item_codes: item_codes }),
//         },
//     )
//         .then((r) => r.json())
//         .then((data) => {
//             if (data.message) {
//                 setTimeout(function () {
//                     window.inject_expiry_badges(frm, data.message);
//                 }, 1500);
//             }
//         });
// };

// window.inject_expiry_badges = function (frm, expiry_map) {
//     (frm.doc.material_allocation || []).forEach(function (row) {
//         let expiry = expiry_map[row.item_code];
//         if (!expiry) return;
//         let b_color, b_bg;
//         if (expiry.status === "expired") {
//             b_color = "#c62828";
//             b_bg = "#fdecea";
//         } else if (expiry.status === "expiring_soon") {
//             b_color = "#e65100";
//             b_bg = "#fff3e0";
//         } else {
//             b_color = "#2e7d32";
//             b_bg = "#e8f5e9";
//         }

//         let badge = `<span class="expiry-badge" style="background:${b_bg};color:${b_color};padding:2px 8px;border-radius:20px;font-size:11px;font-weight:800;display:inline-block;margin-top:4px;">${expiry.label}</span>`;
//         let row_el = frm.fields_dict["material_allocation"].grid.grid_rows_by_docname[row.name];
//         if (row_el && row_el.row) {
//             let shortage_col = row_el.row.find('[data-fieldname="shortage"] .static-area');
//             if (shortage_col.find(".expiry-badge").length === 0) {
//                 shortage_col.append(badge);
//             }
//         }
//     });
// };

// window.upload_bom_items = function (frm) {
//     if (!frm.doc.batch_planning) {
//         frappe.msgprint({
//             title: "Missing",
//             message: "Please select Planned Batch first.",
//             indicator: "orange",
//         });
//         return;
//     }
//     frappe.call({
//         method: "custom_batch_planning.custom_batch_planning.doctype.batches_planned.batches_planned.get_bom_items_for_ma",
//         args: { batch_planning: frm.doc.batch_planning },
//         freeze: true,
//         freeze_message: "Loading BOM Items...",
//         callback: function (r) {
//             if (!r.message || !r.message.length) {
//                 frappe.msgprint({
//                     title: "No Items",
//                     message: "No BOM items found.",
//                     indicator: "orange",
//                 });
//                 return;
//             }
//             frm.clear_table("material_allocation");
//             r.message.forEach(function (item) {
//                 let row = frm.add_child("material_allocation");
//                 row.item_code = item.item_code;
//                 row.item_name = item.item_name;
//                 row.uom = item.uom;
//                 row.quantity_required = item.quantity_required;
//                 row.allocate_qty = item.quantity_required;
//                 row.stock_available = item.stock_available;
//             });
//             frm.refresh_field("material_allocation");
//             frappe.show_alert({
//                 message: "✅ BOM Items loaded! Please review and save.",
//                 indicator: "green",
//             });
//         },
//     });
// };



// ============================================================
// 1. PARENT DOCTYPE EVENTS (Material Allocation)
// ============================================================
frappe.ui.form.on("Material Allocation", {
    setup: function (frm) {
        frm.set_query("batch_planning", function () {
            return { filters: { workflow_state: "Approved" } };
        });
    },

    onload: function (frm) {
        if (frm.is_new() && !frm.doc.workflow_state) {
            frm.doc.workflow_state = "Draft";
        }
    },

    refresh: function (frm) {
        frm.clear_custom_buttons();

        let is_empty = !frm.doc.material_allocation || frm.doc.material_allocation.length === 0;
        if (
            (frm.is_new() || frm.doc.workflow_state === "Draft") &&
            frm.doc.batch_planning &&
            is_empty
        ) {
            setTimeout(() => {
                let current_empty =
                    !frm.doc.material_allocation || frm.doc.material_allocation.length === 0;
                if (current_empty) {
                    window.upload_bom_items(frm);
                }
            }, 500);
        }

        if (!frm.is_new()) {
            frm.set_df_property("employee_function", "read_only", 1);
            frm.set_df_property("batch_planning", "read_only", 1);
        }

        frm.set_df_property("material_allocation", "cannot_add_rows", 1);
        frm.set_df_property("material_allocation", "cannot_delete_rows", 1);

        // Lock grid if Allocated/Deallocated
        if (frm.doc.allocation_status) {
            frm.set_df_property("material_allocation", "read_only", 1);
            frm.refresh_field("material_allocation");
        } else {
            frm.fields_dict["material_allocation"].grid.editable_grid = true;
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "item_code", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "item_name", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "uom", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "quantity_required", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "stock_available", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "open_pr", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "open_po", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "grn_qty", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "qty_allocated", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "shortage", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "batch_details", "read_only", 1
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "allocate_qty", "read_only", 0
            );
            frm.fields_dict["material_allocation"].grid.update_docfield_property(
                "reason", "read_only", 0
            );
            frm.refresh_field("material_allocation");
        }

        if (
            !frm.is_new() &&
            frm.doc.employee_function &&
            frm.doc.material_allocation &&
            frm.doc.material_allocation.length
        ) {
            if (!frm.doc.allocation_status) {
                setTimeout(function () {
                    window.refresh_stock_available(frm);
                }, 1000);
            }
        }

        // ── View Allocation History Button (always visible if Planned Batch is set) ──
        if (!frm.is_new() && frm.doc.batch_planning) {
            frm.add_custom_button(__("📋 Allocation History"), function () {
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Material Allocation Log",
                        filters: { batch_planning: frm.doc.batch_planning },
                        fields: ["name"],
                        limit: 1,
                    },
                    callback: function (r) {
                        if (!r.message || !r.message.length) {
                            frappe.msgprint({
                                title: "No History",
                                message: "No allocation history found for this batch.",
                                indicator: "orange",
                            });
                            return;
                        }
                        frappe.call({
                            method: "frappe.client.get",
                            args: { doctype: "Material Allocation Log", name: r.message[0].name },
                            callback: function (res) {
                                let ma_logs = res.message.ma_logs || [];
                                let history = res.message.table || [];

                                if (!ma_logs.length) {
                                    frappe.msgprint({
                                        title: "No History",
                                        message: "No allocation history found.",
                                        indicator: "orange",
                                    });
                                    return;
                                }

                                window._ma_history_data = history;

                                let rows = ma_logs.map((d) => {
                                    return `
                                        <tr style="cursor:pointer;" onclick="window._show_item_history('${d.item_code}')">
                                            <td style="padding:8px 12px; color:#1b5e20; font-weight:bold;">${d.item_code} 🔍</td>
                                            <td style="padding:8px 12px;">${d.item_name}</td>
                                            <td style="padding:8px 12px;">${d.quantity_required}</td>
                                            <td style="padding:8px 12px;">${d.qty_allocated}</td>
                                        </tr>
                                    `;
                                }).join("");

                                let d = new frappe.ui.Dialog({
                                    title: "📋 Allocation History",
                                    size: "extra-large",
                                });
                                d.body.innerHTML = `
                                    <table class="table table-bordered" style="width:100%;font-size:13px;">
                                        <thead style="background:#f1f5f9;">
                                            <tr>
                                                <th style="padding:8px 12px;">Item Code</th>
                                                <th style="padding:8px 12px;">Item Name</th>
                                                <th style="padding:8px 12px;">Qty Required</th>
                                                <th style="padding:8px 12px;">Qty Allocated</th>
                                            </tr>
                                        </thead>
                                        <tbody>${rows}</tbody>
                                    </table>
                                `;
                                d.show();
                            },
                        });
                    },
                });
            });
        }

        // ── Action Buttons ──
        if (!frm.is_new() && frm.doc.workflow_state === "Approved" && frm.doc.docstatus !== 2) {

            if (!frm.doc.allocation_status) {
                // No allocation yet — show Auto Allocate
                frm.add_custom_button(
                    __("Auto Allocate"),
                    function () { window.auto_allocate_all(frm); },
                    __("Actions"),
                ).addClass("btn-primary");

            } else if (frm.doc.allocation_status === "Allocated") {
                // ── Check if Stock Entry already exists ──
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Stock Entry",
                        filters: {
                            custom_material_allocation: frm.doc.name,
                            docstatus: ["!=", 2],
                        },
                        fields: ["name", "docstatus"],
                        limit: 1,
                    },
                    callback: function (r) {
                        let existing_se = r.message && r.message.length ? r.message[0] : null;

                        if (existing_se) {
                            // Stock Entry exists — show Open button, block Deallocate
                            frm.add_custom_button(
                                __("📦 Open Stock Entry"),
                                function () {
                                    frappe.set_route("Form", "Stock Entry", existing_se.name);
                                },
                                __("Actions"),
                            ).addClass("btn-success");

                            // Show banner if submitted
                            if (existing_se.docstatus === 1) {
                                frm.dashboard.add_comment(
                                    __("✅ Stock Entry <b>" + existing_se.name + "</b> has been submitted. Deallocation is blocked."),
                                    "green",
                                    true,
                                );
                            } else {
                                frm.dashboard.add_comment(
                                    __("⚠️ Stock Entry <b>" + existing_se.name + "</b> is in Draft. Submit it to complete the process."),
                                    "orange",
                                    true,
                                );
                            }

                        } else {
                            // No Stock Entry — show Create Stock Entry + Deallocate
                            frm.add_custom_button(
                                __("📦 Create Stock Entry"),
                                function () {
                                    window.create_stock_entry(frm);
                                },
                                __("Actions"),
                            ).addClass("btn-primary");

                            frm.add_custom_button(
                                __("Deallocate"),
                                function () { window.deallocate_all(frm); },
                                __("Actions"),
                            ).addClass("btn-danger");
                        }
                    },
                });

            } else if (frm.doc.allocation_status === "Deallocated") {
                frm.dashboard.add_comment(
                    __("⚠️ This document has been Deallocated. Create a new Material Allocation for the same Planned Batch to allocate again."),
                    "orange",
                    true,
                );
            }
        }

        window.load_expiry_status(frm);

        // Highlight Modified Rows
        setTimeout(function () {
            (frm.doc.material_allocation || []).forEach(function (row) {
                if (row.reason && row.allocate_qty != row.quantity_required) {
                    let grid_row =
                        frm.fields_dict["material_allocation"].grid.grid_rows_by_docname[row.name];
                    if (grid_row && grid_row.row) {
                        grid_row.row.css("background-color", "#f3e5f5");
                    }
                }
            });
        }, 1000);
    },

    validate: function (frm) {
        let reason_error = null;
        let bom_error = null;

        (frm.doc.material_allocation || []).forEach(function (row) {
            let alloc = parseFloat(row.allocate_qty || 0);
            let bom_qty = parseFloat(row.quantity_required || 0);

            if (!bom_error && alloc > bom_qty) {
                bom_error = `Row ${row.idx} (${row.item_name || row.item_code}): Qty Requested (${alloc}) cannot exceed Consolidated BOM Qty (${bom_qty}).`;
            }
            if (!reason_error && alloc != bom_qty && !row.reason) {
                reason_error = `Row ${row.idx} (${row.item_name || row.item_code}): Qty Requested differs from Quantity Required. Please fill Reason.`;
            }
        });

        if (bom_error) {
            frappe.msgprint({
                title: __("Validation Failed"),
                message: __(bom_error),
                indicator: "red",
            });
            frappe.validated = false;
            return;
        }

        if (reason_error) {
            frappe.msgprint({
                title: __("Validation Failed"),
                message: __(reason_error),
                indicator: "red",
            });
            frappe.validated = false;
        }
    },

    after_save: function (frm) {
        if (frm._allocating) return;
        setTimeout(function () {
            if (frm.doc.allocation_status) return;
            if (
                frm.doc.employee_function &&
                frm.doc.material_allocation &&
                frm.doc.material_allocation.length
            ) {
                window.refresh_stock_available(frm);
            }
            window.load_expiry_status(frm);
        }, 1500);
    },

    employee_function: function (frm) {
        if (
            frm.doc.employee_function &&
            frm.doc.material_allocation &&
            frm.doc.material_allocation.length
        ) {
            window.refresh_stock_available(frm);
        }
    },

    batch_planning: function (frm) {
        if (!frm.doc.batch_planning) return;
        frappe.db.get_value(
            "Batch Planning",
            frm.doc.batch_planning,
            ["project", "project_name"],
            function (data) {
                if (data) {
                    frm.set_value("project_id", data.project);
                    frm.set_value("project_name", data.project_name);
                }
            },
        );
    },
});

// ============================================================
// 2. CHILD TABLE EVENTS (Material Allocation Item)
// ============================================================
frappe.ui.form.on("Material Allocation Item", {
    allocate_qty: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.allocate_qty != row.quantity_required && !row.reason) {
            frappe.show_alert({
                message: "Row " + row.idx + ": Please fill Reason for allocation change!",
                indicator: "orange",
            });
        }
    },
});

// ============================================================
// 3. GLOBAL HELPER FUNCTIONS
// ============================================================

window._show_item_history = function (item_code) {
    let filtered = (window._ma_history_data || [])
        .filter((d) => d.item_code === item_code)
        .sort((a, b) => (a.allocated_on > b.allocated_on ? 1 : -1));

    if (!filtered.length) {
        frappe.msgprint({
            title: "No Events",
            message: `No events found for ${item_code}`,
            indicator: "orange",
        });
        return;
    }

    let rows = filtered.map((d) => `
        <tr>
            <td style="padding:8px 12px;">${d.allocated_by}</td>
            <td style="padding:8px 12px;">${d.allocated_on}</td>
            <td style="padding:8px 12px;">${d.qty_allocated ?? "-"}</td>
            <td style="padding:8px 12px;">${d.material_allocation_id}</td>
        </tr>
    `).join("");

    let ed = new frappe.ui.Dialog({
        title: `📦 Events for: ${item_code}`,
        size: "extra-large",
    });
    ed.body.innerHTML = `
        <table class="table table-bordered" style="width:100%;font-size:13px;">
            <thead style="background:#f1f5f9;">
                <tr>
                    <th style="padding:8px 12px;">Allocated By</th>
                    <th style="padding:8px 12px;">Date & Time</th>
                    <th style="padding:8px 12px;">Qty Allocated</th>
                    <th style="padding:8px 12px;">MA ID</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
    ed.show();
};

window.refresh_stock_available = function (frm) {
    let items = frm.doc.material_allocation || [];
    if (!items.length) return;

    let item_codes = items.map((r) => r.item_code);
    fetch(
        "/api/method/custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.get_open_pr_po",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Frappe-CSRF-Token": frappe.csrf_token,
            },
            body: JSON.stringify({ item_codes: item_codes }),
        },
    )
        .then((r) => r.json())
        .then((data) => {
            let pr_po_map = data.message || {};
            items.forEach(function (row) {
                frappe.call({
                    method: "custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.ma_get_allocated_qty",
                    args: {
                        item_code: row.item_code,
                        employee_function: frm.doc.employee_function,
                        exclude_parent: frm.doc.name,
                        row_name: row.name,
                    },
                    callback: function (res) {
                        if (res.message) {
                            let grid_row =
                                frm.fields_dict["material_allocation"].grid.grid_rows_by_docname[row.name];
                            let free_stock = res.message.free_stock || 0;
                            let qty_req = row.quantity_required || 0;
                            let pr_po = pr_po_map[row.item_code] || {};

                            if (grid_row) {
                                let allocated = grid_row.doc.qty_allocated || 0;
                                let display_stock = Math.max(free_stock - allocated, 0);

                                grid_row.doc.stock_available = display_stock;
                                grid_row.doc.shortage = Math.max(qty_req - display_stock, 0);
                                grid_row.doc.open_pr = pr_po.open_pr || 0;
                                grid_row.doc.open_po = pr_po.open_po || 0;

                                grid_row.refresh_field("stock_available");
                                grid_row.refresh_field("shortage");
                                grid_row.refresh_field("open_pr");
                                grid_row.refresh_field("open_po");
                            }
                        }
                    },
                });
            });
        });
};

window.auto_allocate_all = function (frm) {
    if (frm.is_dirty()) {
        frappe.msgprint(__("Please save the document before allocating."));
        return;
    }
    frappe.confirm(
        "⚠️ Auto Allocation will use <b>FEFO logic</b> (earliest expiry first) to allocate batches. Continue?",
        function () {
            frm.call({
                doc: frm.doc,
                method: "auto_allocate",
                freeze: true,
                freeze_message: __("Allocating Batches..."),
            }).then((r) => {
                if (!r.exc) {
                    frappe.show_alert({ message: __("✅ Allocated successfully!"), indicator: "green" });
                    frm.reload_doc();
                }
            });
        },
    );
};

window.deallocate_all = function (frm) {
    // Block if Stock Entry exists and is submitted
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Stock Entry",
            filters: {
                custom_material_allocation: frm.doc.name,
                docstatus: 1,
            },
            fields: ["name"],
            limit: 1,
        },
        callback: function (r) {
            if (r.message && r.message.length) {
                frappe.msgprint({
                    title: __("⛔ Deallocation Blocked"),
                    message: __(
                        "Stock Entry <b>" + r.message[0].name + "</b> has already been submitted. " +
                        "Items have been sent for manufacturing. Deallocation is not allowed."
                    ),
                    indicator: "red",
                });
                return;
            }

            // No submitted SE — proceed with deallocation
            frappe.confirm(
                "⚠️ This will release all allocated quantities and clear batch details. Continue?",
                function () {
                    frm.call("deallocate").then((r) => {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __("✅ Deallocated successfully!"),
                                indicator: "blue",
                            });
                            frm.reload_doc();
                        }
                    });
                },
            );
        },
    });
};

window.create_stock_entry = function (frm) {
    if (frm.is_dirty()) {
        frappe.msgprint(__("Please save the document before creating Stock Entry."));
        return;
    }

    frappe.confirm(
        "⚠️ This will create a <b>Stock Entry (Manufacture)</b> with all allocated items. Continue?",
        function () {
            // Step 1: Get Employee Function warehouse
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Employee Function", name: frm.doc.employee_function },
                callback: function (ef_res) {
                    let ef = ef_res.message;
                    let from_warehouse = (ef.table_bukm || []).find(r => r.store_warehouse)?.store_warehouse;

                    if (!from_warehouse) {
                        frappe.msgprint({
                            title: "Missing Warehouse",
                            message: "No store warehouse found in Employee Function.",
                            indicator: "red",
                        });
                        return;
                    }

                    // Step 2: Get BOM from Batch Planning directly
                    frappe.call({
                        vanity: true,
                        method: "frappe.client.get",
                        args: { doctype: "Batch Planning", name: frm.doc.batch_planning },
                        callback: function (bc_res) {
                            let rows = bc_res.message.custom_batch_details || [];
                            let matched = rows.find(r => r.bom_list);
                            let bom_no = matched ? matched.bom_list : null;

                            // Step 3: Build items list from MA child table
                            let items = (frm.doc.material_allocation || []).map(row => ({
                                item_code: row.item_code,
                                item_name: row.item_name,
                                qty: row.allocate_qty,
                                uom: row.uom,
                                s_warehouse: from_warehouse,
                                conversion_factor: 1,
                                transfer_qty: row.allocate_qty,
                            }));

                            let batch_list = (frm.doc.batches_planned || "").split(",").map(s => s.trim());
                            let first_batch = batch_list[0] || "";

                            // Step 4: Open new Stock Entry with all details prefilled
                            frappe.new_doc("Stock Entry", {
                                stock_entry_type: "Material Transfer",
                                custom_batch_planning: frm.doc.batches_planned,
                                custom_batch_no: first_batch,
                                custom_batch_planning_no: frm.doc.batch_planning,
                                custom_material_allocation: frm.doc.name,
                                from_warehouse: from_warehouse,
                                project: frm.doc.project_id,
                                bom_no: bom_no || "",
                                from_bom: bom_no ? 1 : 0,
                                custom_employee_functions: frm.doc.employee_function,
                            }).then(() => {
                                if (cur_frm) {
                                    cur_frm.clear_table("items");
                                    items.forEach(item => {
                                        let row = cur_frm.add_child("items");
                                        row.item_code = item.item_code;
                                        row.item_name = item.item_name;
                                        row.qty = item.qty;
                                        row.uom = item.uom;
                                        row.s_warehouse = item.s_warehouse;
                                        row.conversion_factor = 1;
                                        row.transfer_qty = item.qty;
                                    });
                                    cur_frm.refresh_field("items");
                                    frappe.show_alert({
                                        message: __("✅ Stock Entry created. Please fill Target Warehouse and submit."),
                                        indicator: "green",
                                    });
                                }
                            });
                        },
                    });
                },
            });
        },
    );
};

window.load_expiry_status = function (frm) {
    if (!frm.doc.material_allocation || !frm.doc.material_allocation.length) return;
    let item_codes = frm.doc.material_allocation.map((r) => r.item_code);
    fetch(
        "/api/method/custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.get_item_batch_expiry",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Frappe-CSRF-Token": frappe.csrf_token,
            },
            body: JSON.stringify({ item_codes: item_codes }),
        },
    )
        .then((r) => r.json())
        .then((data) => {
            if (data.message) {
                setTimeout(function () {
                    window.inject_expiry_badges(frm, data.message);
                }, 1500);
            }
        });
};

window.inject_expiry_badges = function (frm, expiry_map) {
    (frm.doc.material_allocation || []).forEach(function (row) {
        let expiry = expiry_map[row.item_code];
        if (!expiry) return;
        let b_color, b_bg;
        if (expiry.status === "expired") {
            b_color = "#c62828"; b_bg = "#fdecea";
        } else if (expiry.status === "expiring_soon") {
            b_color = "#e65100"; b_bg = "#fff3e0";
        } else {
            b_color = "#2e7d32"; b_bg = "#e8f5e9";
        }
        let badge = `<span class="expiry-badge" style="background:${b_bg};color:${b_color};padding:2px 8px;border-radius:20px;font-size:11px;font-weight:800;display:inline-block;margin-top:4px;">${expiry.label}</span>`;
        let row_el = frm.fields_dict["material_allocation"].grid.grid_rows_by_docname[row.name];
        if (row_el && row_el.row) {
            let shortage_col = row_el.row.find('[data-fieldname="shortage"] .static-area');
            if (shortage_col.find(".expiry-badge").length === 0) {
                shortage_col.append(badge);
            }
        }
    });
};

window.upload_bom_items = function (frm) {
    if (!frm.doc.batch_planning) {
        return;
    }
    frappe.call({
        method: "custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_consolidated_bom_components",
        args: { doc_name: frm.doc.batch_planning },
        freeze: true,
        freeze_message: "Loading Consolidated BOM Items...",
        callback: function (r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint({
                    title: "No Items",
                    message: "No BOM items found.",
                    indicator: "orange",
                });
                return;
            }
            frm.clear_table("material_allocation");
            r.message.forEach(function (item) {
                let row = frm.add_child("material_allocation");
                row.item_code = item.item_code;
                row.item_name = item.item_name;
                row.uom = item.uom;
                row.quantity_required = item.qty;
                row.allocate_qty = item.qty;
                row.stock_available = 0.0;
            });
            frm.refresh_field("material_allocation");
            // Set comma-separated batches_planned
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Batches Planned",
                    filters: { batch_planning: frm.doc.batch_planning },
                    fields: ["name"]
                },
                callback: function(res) {
                    if (res.message) {
                        let names = res.message.map(b => b.name).join(", ");
                        frm.set_value("batches_planned", names);
                    }
                }
            });
            // Also refresh stock available
            setTimeout(function() {
                window.refresh_stock_available(frm);
            }, 1000);
        },
    });
};