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
        console.log("🔄 Material Allocation refreshed for:", frm.doc.name);
        
        frm.clear_custom_buttons();

        // ── Auto-load BOM items if new/draft and table is empty ──
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

        // ── Lock header fields outside Draft ──
        if (!frm.is_new() && frm.doc.workflow_state !== "Draft") {
            frm.set_df_property("employee_function", "read_only", 1);
            frm.set_df_property("batch_planning", "read_only", 1);
        }

        // ── Grid: allow add rows; allow delete but enforce min 1 row ──
        frm.set_df_property("material_allocation", "cannot_add_rows", false);
        frm.set_df_property("material_allocation", "cannot_delete_rows", false);
        if (frm.fields_dict["material_allocation"] && frm.fields_dict["material_allocation"].grid) {
            frm.fields_dict["material_allocation"].grid.cannot_delete_rows = false;
            frm.fields_dict["material_allocation"].grid.df.cannot_delete_rows = false;
        }

        // ── Grid: lock all cols, only allocate_qty + reason editable ──
        if (frm.doc.allocation_status) {
            // Fully locked once allocated/deallocated
            frm.set_df_property("material_allocation", "read_only", 1);
            frm.refresh_field("material_allocation");
        } else {
            let read_only_cols = [
                "item_code", "item_name", "uom", "quantity_required",
                "stock_available", "open_pr", "open_po", "grn_qty",
                "qty_allocated", "shortage", "batch_details"
            ];
            read_only_cols.forEach(function (fieldname) {
                try {
                    frm.fields_dict["material_allocation"].grid.update_docfield_property(
                        fieldname, "read_only", 1
                    );
                } catch (e) {
                    // Ignore missing fields like batch_details
                }
            });
            try {
                frm.fields_dict["material_allocation"].grid.update_docfield_property(
                    "allocate_qty", "read_only", 0
                );
                frm.fields_dict["material_allocation"].grid.update_docfield_property(
                    "reason", "read_only", 0
                );
            } catch (e) {}
            
            frm.refresh_field("material_allocation");
        }

        // ── Refresh stock available for non-allocated docs ──
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

        // ── View Allocations Button (visible on any doc with batch_planning) ──
        if (frm.doc.batch_planning) {
            setTimeout(function () {
                frm.add_custom_button(__("View Allocations"), function () {
                    frappe.call({
                        method: "custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.get_allocated_items",
                        args: {
                            batch_planning: frm.doc.batch_planning,
                            employee_function: frm.doc.employee_function
                        },
                        callback: function(r) {
                            let data = r.message || {};
                            let items = data.items || [];
                            let ma_count = data.ma_count || 0;
                            
                            if (!items.length) {
                                frappe.msgprint({
                                    title: "No Allocations",
                                    message: __("No allocated items found for this batch planning."),
                                    indicator: "orange"
                                });
                                return;
                            }
                            
                            let rows = items.map(d => {
                                let row_style = "";
                                if (d.qty_allocated > d.quantity_required) {
                                    row_style = "background-color: #ffebee; color: #c62828;";
                                }
                                return `
                                <tr style="${row_style}">
                                    <td style="padding:8px 12px; font-weight:bold;">${d.item_code}</td>
                                    <td style="padding:8px 12px;">${d.item_name}</td>
                                    <td style="padding:8px 12px;">${d.uom}</td>
                                    <td style="padding:8px 12px;">${d.quantity_required}</td>
                                    <td style="padding:8px 12px; font-weight:bold;">${d.qty_allocated}</td>
                                </tr>
                                `;
                            }).join("");
                            
                            let d_dialog = new frappe.ui.Dialog({
                                title: "Allocated Items",
                                size: "large",
                            });
                            d_dialog.body.innerHTML = `
                                <p style="margin-bottom: 15px; font-size: 14px;">
                                    <b>${ma_count} Material Allocation(s) have been done against this Batch Planning.</b>
                                </p>
                                <table class="table table-bordered" style="width:100%;font-size:13px;">
                                    <thead style="background:#f1f5f9; color:#333;">
                                        <tr>
                                            <th style="padding:8px 12px;">Item Code</th>
                                            <th style="padding:8px 12px;">Item Name</th>
                                            <th style="padding:8px 12px;">UOM</th>
                                            <th style="padding:8px 12px;">Qty Required</th>
                                            <th style="padding:8px 12px;">Qty Allocated</th>
                                        </tr>
                                    </thead>
                                    <tbody>${rows}</tbody>
                                </table>
                            `;
                            d_dialog.show();
                        }
                    });
                });
            }, 100);
        }

        // ── Action Buttons ──
        setTimeout(function () {
            if (!frm.is_new() && frm.doc.workflow_state === "Approved" && frm.doc.docstatus !== 2) {
                if (!frm.doc.allocation_status) {
                    frm.add_custom_button(
                        __("Allocate"),
                        function () { window.auto_allocate_all(frm); }
                    ).addClass("btn-primary");

                } else if (frm.doc.allocation_status === "Allocated") {
                    // Check if Stock Entry exists
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
                            if (r.message && r.message.length > 0) {
                                let se = r.message[0];
                                frm.add_custom_button(
                                    __("📦 Open Stock Entry"),
                                    function () {
                                        frappe.set_route("Form", "Stock Entry", se.name);
                                    }
                                ).addClass("btn-success");

                                if (se.docstatus === 1) {
                                    frm.dashboard.add_comment(
                                        __("✅ Stock Entry <b>" + se.name + "</b> has been submitted. Deallocation is blocked."),
                                        "green", true
                                    );
                                } else {
                                    frm.dashboard.add_comment(
                                        __("⚠️ Stock Entry <b>" + se.name + "</b> is in Draft. Submit it to complete the process."),
                                        "orange", true
                                    );
                                }
                            } else {
                                frm.add_custom_button(
                                    __("📦 Create Stock Entry"),
                                    function () { window.create_stock_entry(frm); }
                                ).addClass("btn-primary");

                                frm.add_custom_button(
                                    __("Deallocate"),
                                    function () { window.deallocate_all(frm); }
                                ).addClass("btn-danger");
                            }
                        },
                    });
                }
            } else if (frm.doc.allocation_status === "Deallocated") {
                frm.dashboard.add_comment(
                    __("⚠️ This document has been Deallocated. Create a new Material Allocation for the same Planned Batch to allocate again."),
                    "orange", true
                );
            }
        }, 100);

        window.load_expiry_status(frm);

        // ── Highlight rows where allocate_qty differs from quantity_required ──
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

    // ── No validate on client side — handled by server script ──

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

    // ── No batch_planning trigger — MA is created only via batch_planning ──
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

    before_material_allocation_remove: function (frm, cdt, cdn) {
        // Enforce minimum 1 row
        if ((frm.doc.material_allocation || []).length <= 1) {
            frappe.msgprint({
                title: __("Cannot Delete"),
                message: __("At least one item must remain in the allocation table."),
                indicator: "red",
            });
            frappe.validated = false;
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
    // Block if submitted Stock Entry exists
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

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Stock Entry",
            filters: {
                custom_material_allocation: frm.doc.name,
                docstatus: ["!=", 2],
            },
            fields: ["name"],
            limit: 1,
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                frappe.msgprint({
                    title: __("Not Allowed"),
                    message: __("A Stock Entry (<b>" + r.message[0].name + "</b>) already exists for this Material Allocation. Only one Stock Entry is allowed."),
                    indicator: "red"
                });
                return;
            }

            frappe.confirm(
                "⚠️ This will create a <b>Stock Entry (Material Transfer)</b> with all allocated items. Continue?",
                function () {
                    // Step 1: Get Employee Function warehouse
                    frappe.call({
                        method: "frappe.client.get",
                        args: { doctype: "Employee Function", name: frm.doc.employee_function },
                        callback: function (ef_res) {
                            let ef = ef_res.message;
                            let store_row = (ef.table_bukm || []).find(r => r.store_warehouse);
                            let from_warehouse = store_row ? store_row.store_warehouse : null;

                    if (!from_warehouse) {
                        frappe.msgprint({
                            title: "Missing Warehouse",
                            message: "No store warehouse found in Employee Function.",
                            indicator: "red",
                        });
                        return;
                    }

                    // Step 2: Get BOM from Batch Planning
                    frappe.call({
                        method: "frappe.client.get",
                        args: { doctype: "Batch Planning", name: frm.doc.batch_planning },
                        callback: function (bc_res) {
                            let rows = bc_res.message.custom_batch_details || [];
                            let matched = rows.find(r => r.bom_list);
                            let bom_no = matched ? matched.bom_list : null;

                            // Step 3: Build items from MA child table
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

                            // Step 4: Open new Stock Entry prefilled
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

                        } // end callback bc_res
                    }); // end call bc_res
                } // end callback ef_res
            }); // end call ef_res
        } // end confirm callback
    ); // end confirm
        } // end callback r
    }); // end call r
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
    if (!frm.doc.batch_planning) return;

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

            // Set batches_planned field
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Batches Planned",
                    filters: { batch_planning: frm.doc.batch_planning },
                    fields: ["name"],
                },
                callback: function (res) {
                    if (res.message) {
                        let names = res.message.map(b => b.name).join(", ");
                        frm.set_value("batches_planned", names);
                    }
                },
            });

            // Refresh stock available after BOM load
            setTimeout(function () {
                window.refresh_stock_available(frm);
            }, 1000);
        },
    });
};