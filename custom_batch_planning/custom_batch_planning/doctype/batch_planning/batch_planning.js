// ─────────────────────────────────────────────
// SheetJS load karo (Excel ke liye)
// ─────────────────────────────────────────────
if (typeof XLSX === 'undefined') {
    let s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
    document.head.appendChild(s);
}

// ─────────────────────────────────────────────
// Batch Planning — Main Form
// ─────────────────────────────────────────────
frappe.ui.form.on('Batch Planning', {



    refresh: function (frm) {
        if (frm.fields_dict['custom_batch_details']) {
            let grid = frm.fields_dict['custom_batch_details'].grid;
            grid.cannot_add_rows = true;
            grid.cannot_delete_rows = true;
        }
        set_project_filter(frm);
        // ✅ set_query yahan move kiya — setup se hataya
        frm.set_query('bom_list', 'custom_batch_details', function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            let filters = { docstatus: 1, is_active: 1 };
            if (row.finished_item) {
                filters['item'] = row.finished_item;
            }
            return { filters: filters };
        });

        frm.set_query('finished_item', 'custom_batch_details', function (doc) {
            return {
                query: 'custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_project_finished_items',
                filters: {
                    project: doc.project || ''
                }
            };
        });

        frm.set_query('finished_item', function (doc) {
            return {
                query: 'custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_project_finished_items',
                filters: {
                    project: doc.project || ''
                }
            };
        });

        frm.set_query('bom_list', function (doc) {
            let filters = { docstatus: 1, is_active: 1 };
            if (doc.finished_item) {
                filters['item'] = doc.finished_item;
            }
            return { filters: filters };
        });

        load_used_slots(frm);

        if (frm.is_new() && frm.doc.slot_opening && !frm._slot_loaded) {
            frm._slot_loaded = true;
            frm.trigger('slot_opening');
        }

        if (frm.doc.workflow_state === 'Submitted' && !frm.is_new()) {
            frm.add_custom_button('Send For Approval', function () {
                // future use
            }, 'Action');
        }

        if (!frm.is_new()) {
            frm.add_custom_button(__('View Batches Planned'), function () {
                frappe.route_options = {
                    "batch_planning": frm.doc.name
                };
                frappe.set_route('List', 'Batches Planned');
            });
        }

        setup_eye_buttons(frm);

        if (frm.doc.docstatus === 1 || frm.doc.workflow_state === 'Approved') {
            render_bom_components_tab(frm);
            // Load persisted data from localStorage if not already in memory
            if (!frm._mp_data) {
                const stored = localStorage.getItem('mp_' + frm.doc.name);
                if (stored) {
                    try { frm._mp_data = JSON.parse(stored); } catch(e) { console.error('Failed to parse stored material planning data', e); }
                }
            }
            // Render material planning based on available data
            if (frm._mp_data && frm._mp_data.length) {
                render_material_planning_tab(frm);
            } else {
                render_material_planning_placeholder(frm);
            }
            render_stock_entry_tab(frm);
            render_item_issue_tab(frm);

            frm.remove_custom_button(__("Run Material Planning"));
            frm.add_custom_button(__("Run Material Planning"), function () {
                render_material_planning_tab(frm);
            }).addClass("btn-primary");

            // Material Allocation button
            frm.remove_custom_button(__("Material Allocation"), __("Create"));
            frm.add_custom_button(__("Material Allocation"), function () {
                frappe.call({
                    method: "custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.create_bulk_material_allocations",
                    args: { batch_planning_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Preparing Material Allocation..."),
                    callback: function (r) {
                        if (r.message) {
                            if (typeof r.message === "string" && r.message.indexOf("already exists") !== -1) {
                                frappe.msgprint({
                                    title: __("Material Allocation"),
                                    message: r.message,
                                    indicator: "orange"
                                });
                            } else {
                                frappe.new_doc("Material Allocation", r.message);
                            }
                        }
                    }
                });
            }, __("Create"));

            // Material Request button
            frm.remove_custom_button(__("Material Request"), __("Create"));
            frm.add_custom_button(__("Material Request"), function () {
                frappe.call({
                    method: "custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_batch_wise_shortages",
                    args: { doc_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Calculating batch-wise shortages..."),
                    callback: function (r) {
                        let shortages = r.message || [];
                        if (!shortages.length) {
                            frappe.msgprint({
                                title: __("No Shortage"),
                                message: __("All items have sufficient stock. No Material Request needed."),
                                indicator: "green",
                            });
                            return;
                        }

                        frappe.new_doc("Material Request", {
                            material_request_type: "Manufacture",
                            custom_employee_function: frm.doc.custom_employee_function,
                            project: frm.doc.project,
                            custom_batch_planning_no: frm.doc.name,
                        }).then(() => {
                            if (cur_frm) {
                                cur_frm.set_value("project", frm.doc.project);
                                cur_frm.set_value("custom_batch_planning_no", frm.doc.name);
                                cur_frm.clear_table("items");
                                shortages.forEach((item) => {
                                    let row = cur_frm.add_child("items");
                                    row.item_code = item.item_code;
                                    row.qty = item.qty;
                                    row.uom = item.uom;
                                    row.conversion_factor = 1;
                                    row.schedule_date = item.schedule_date;
                                    row.custom_batch_planning_no = item.custom_batch_planning_no;
                                    row.project = frm.doc.project;
                                });
                                cur_frm.refresh_field("items");
                            }
                        });
                    }
                });
            }, __("Create"));

        } else {
            frm.remove_custom_button(__("Run Material Planning"));
            frm.remove_custom_button(__("Material Allocation"), __("Create"));
            frm.remove_custom_button(__("Material Request"), __("Create"));
        }
    },

    finished_item: function (frm) {
        if (frm._bulk_populating) return;
        if (!frm.doc.finished_item && frm.doc.bom_list) {
            frm.set_value('bom_list', '');
        }
        frm._bulk_populating = true;
        let promises = [];
        (frm.doc.custom_batch_details || []).forEach(row => {
            promises.push(frappe.model.set_value(row.doctype, row.name, 'finished_item', frm.doc.finished_item || ''));
            promises.push(frappe.model.set_value(row.doctype, row.name, 'bom_list', ''));
        });
        Promise.all(promises).then(() => {
            frm._bulk_populating = false;
            frm.refresh_field('custom_batch_details');
        });
    },

    bom_list: function (frm) {
        if (frm._bulk_populating) return;
        frm._bulk_populating = true;
        let promises = [];
        (frm.doc.custom_batch_details || []).forEach(row => {
            if (row.finished_item === frm.doc.finished_item) {
                promises.push(frappe.model.set_value(row.doctype, row.name, 'bom_list', frm.doc.bom_list || ''));
            }
        });
        Promise.all(promises).then(() => {
            frm._bulk_populating = false;
            frm.refresh_field('custom_batch_details');
        });
    },

    custom_employee_function: function (frm) {
        if (frm._setting_from_slot_opening) {
            return;
        }

        if (frm.is_new() && !frm._emp_func_initialized) {
            frm._emp_func_initialized = true;
            if (frm.doc.slot_opening) {
                load_used_slots(frm);
                return;
            }
        }

        frm.set_value('slot_opening', '');
        frm.set_value('custom_slot_master', '');
        frm.set_value('project', '');
        set_project_filter(frm);
        frm.set_value('month', '');
        frm.clear_table('slot_opening_table');
        frm.clear_table('custom_batch_details');

        if (frm.doc.custom_employee_function) {
            frappe.db.get_value('Employee Function', frm.doc.custom_employee_function, 'function_head_name')
                .then(r => {
                    if (r && r.message) {
                        frm.set_value('custom_employee_headname', r.message.function_head_name);
                    }
                });
        } else {
            frm.set_value('custom_employee_headname', '');
        }

        load_used_slots(frm);
    },

    custom_slot_master: function (frm) {
        if (frm._setting_from_slot_opening) {
            return;
        }

        if (!frm.doc.custom_slot_master) {
            return;
        }

        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'Slot Master List', name: frm.doc.custom_slot_master },
            callback: function (r) {
                if (!r.message) return;

                frm._setting_from_slot_opening = true;
                let promises = [];
                if (r.message.employee_function) {
                    promises.push(frm.set_value('custom_employee_function', r.message.employee_function));
                }
                if (r.message.employee_function_head_name) {
                    promises.push(frm.set_value('custom_employee_headname', r.message.employee_function_head_name));
                }
                if (r.message.project) {
                    promises.push(frm.set_value('project', r.message.project));
                }

                Promise.all(promises).then(() => {
                    frm._setting_from_slot_opening = false;
                    load_used_slots(frm);
                });
            }
        });
    },

    slot_opening: function (frm) {
        // 1. Clear fields and tables if the slot_opening field is emptied
        if (!frm.doc.slot_opening) {
            frm.set_value('month', '');
            frm.set_value('custom_slot_master', '');
            frm.set_value('project', '');
            frm.clear_table('slot_opening_table');
            frm.clear_table('custom_batch_details');
            frm.refresh_field('slot_opening_table');
            frm.refresh_field('custom_batch_details');
            return;
        }

        // Clear tables immediately to prevent duplicate stacking while loading
        frm.clear_table('slot_opening_table');
        frm.clear_table('custom_batch_details');

        // 2. Fetch data from Slot Opening Doctype
        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'Slot Opening', name: frm.doc.slot_opening },
            callback: function (r) {
                if (!r.message) return;

                frm._setting_from_slot_opening = true;
                let promises = [];

                if (r.message.employee_function) {
                    promises.push(frm.set_value('custom_employee_function', r.message.employee_function));
                }
                if (r.message.function_head_name) {
                    promises.push(frm.set_value('custom_employee_headname', r.message.function_head_name));
                }
                if (r.message.slot_master) {
                    promises.push(frm.set_value('custom_slot_master', r.message.slot_master));
                }
                if (r.message.project) {
                    promises.push(frm.set_value('project', r.message.project));
                }

                // WE WAIT until all parent fields are set before touching child tables
                Promise.all(promises).then(() => {
                    frm._setting_from_slot_opening = false;

                    let future_rows = r.message.slot_booking || [];

                    // 3. Handle Empty Bookings Case
                    if (future_rows.length === 0) {
                        frappe.msgprint({
                            title: '⛔ No Slots Found',
                            message: `The selected slot <b>${frm.doc.slot_opening}</b> has no booking dates.`,
                            indicator: 'red'
                        });
                        frm.set_value('slot_opening', '');
                        frm.set_value('month', '');
                        frm.clear_table('slot_opening_table');
                        frm.clear_table('custom_batch_details');
                        frm.refresh_field('slot_opening_table');
                        frm.refresh_field('custom_batch_details');
                        return;
                    }

                    // 4. Set month field from first booking date
                    if (future_rows[0].slot_booking_date) {
                        let date = new Date(future_rows[0].slot_booking_date);
                        frm.set_value('month', date.toLocaleString('en-US', { month: 'long' }));
                    }

                    // 5. Populate Main Slot Table
                    future_rows.forEach(function (row) {
                        let nr = frm.add_child('slot_opening_table');
                        nr.slot_booking_date = row.slot_booking_date;
                        nr.how_many_slots_per_day = row.how_many_slots_per_day;
                        nr.total_slots = row.total_slots;
                        nr.booked_slots = row.booked_slots;
                        nr.availabe_capacity = row.availabe_capacity;
                        nr.reason = row.reason;
                    });
                    frm.refresh_field('slot_opening_table');

                    // 6. Fetch Planned Batches Details
                    frappe.call({
                        method: 'custom_batch_planning.custom_batch_planning.doctype.slot_opening.slot_opening.get_sct_details',
                        args: { slot_master: r.message.slot_master },
                        callback: function (sct_r) {
                            console.log("sct_r.message", sct_r.message);

                            if (!frm.fields_dict['custom_batch_details'] || !frm.fields_dict['custom_batch_details'].grid) {
                                return;
                            }

                            let sct_map = {};
                            (sct_r.message || []).forEach(function (d) {
                                sct_map[d.date] = parseInt(d.batches_planned) || 0;
                            });

                            // Populate Custom Batch Details Table
                            future_rows.forEach(function (slot) {
                                let booked = parseInt(slot.booked_slots) || 0;
                                let planned = sct_map[slot.slot_booking_date] || 0;
                                let remaining = booked - planned;

                                if (remaining <= 0) return;

                                for (let i = 0; i < remaining; i++) {
                                    let child = frm.add_child('custom_batch_details');
                                    child.slot_opening_id = frm.doc.slot_opening;
                                    child.slot_booking_date = slot.slot_booking_date;
                                    child.reason = slot.reason;
                                    child.status = "Approved";
                                }
                            });

                            // Force layout rendering refresh
                            frm.refresh_field('custom_batch_details');

                            frappe.show_alert({
                                message: `✅ Slots successfully loaded!`,
                                indicator: 'green'
                            }, 4);
                        }
                    });
                });
            }
        });
    },

    after_save: function (frm) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Batch BOM Store after Edit',
                filters: [
                    ['batch_id', 'like', 'new-batch-creation-%']
                ],
                fields: ['name', 'batch_id'],
                limit: 20
            },
            callback: function (r) {
                if (!r.message || !r.message.length) return;
                r.message.forEach(function (doc) {
                    let parts = doc.batch_id.split('-');
                    let idx = parts[parts.length - 1];
                    let new_key = `${frm.doc.name}-${idx}`;
                    frappe.call({
                        method: 'frappe.client.set_value',
                        args: {
                            doctype: 'Batch BOM Store after Edit',
                            name: doc.name,
                            fieldname: {
                                'batch_id': new_key,
                                'custom_batch_creation_id': frm.doc.name
                            }
                        }
                    });
                });
            }
        });
    },

    after_workflow_action: function (frm) {
        console.log("Workflow state:", frm.doc.workflow_state);
        console.log("Docstatus:", frm.doc.docstatus);

        if (frm.doc.workflow_state === 'Approved' && frm.doc.docstatus === 1) {
            frappe.call({
                method: 'custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.create_batches_planned',
                args: {
                    doc_name: frm.doc.name
                },
                freeze: true,
                freeze_message: 'Creating Batches Planned records...',
                callback: function (r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: 'Success',
                            message: 'Batches Planned created successfully.',
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                },
                error: function (r) {
                    console.error("Error:", r);
                    frappe.msgprint({
                        title: 'Error',
                        message: JSON.stringify(r),
                        indicator: 'red'
                    });
                }
            });
        }
    }

});

// ─────────────────────────────────────────────
// Batch Planning Detail CT — ALL triggers
// ─────────────────────────────────────────────
frappe.ui.form.on('Batch Planning Detail', {

    batch_type: function (frm, cdt, cdn) {
        if (frm._bulk_populating) return;
        let row = locals[cdt][cdn];
        if (!row.batch_type || !row.slot_opening_id) return;

        if (!frm._counter_queue) frm._counter_queue = Promise.resolve();

        frm._counter_queue = frm._counter_queue.then(function () {
            return new Promise(function (resolve) {
                let assigned_ids = (frm.doc.custom_batch_details || [])
                    .filter(r => r.batch_planning_id && r.name !== row.name)
                    .map(r => r.batch_planning_id);

                frappe.call({
                    method: 'custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_next_batch_counter',
                    args: {
                        slot_opening_id: row.slot_opening_id,
                        batch_type: row.batch_type,
                        exclude_ids: JSON.stringify(assigned_ids)
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.model.set_value(cdt, cdn, 'batch_planning_id', r.message);
                        }
                        if (frm.doc.finished_item) {
                            frappe.model.set_value(cdt, cdn, 'finished_item', frm.doc.finished_item);
                            if (frm.doc.bom_list) {
                                frappe.model.set_value(cdt, cdn, 'bom_list', frm.doc.bom_list);
                            }
                        }
                        resolve();
                    }
                });
            });
        });
    },

    finished_item: function (frm, cdt, cdn) {
        if (frm._bulk_populating) return;
        let row = locals[cdt][cdn];

        if (row.finished_item && !row.batch_type) {
            frappe.msgprint({
                title: __("Missing Batch Type"),
                message: __("Please select a Batch Type first before selecting a Finished Item."),
                indicator: "orange"
            });
            frappe.model.set_value(cdt, cdn, 'finished_item', '');
            return;
        }

        frappe.model.set_value(cdt, cdn, 'bom_list', '');
    },

    bom_list: function (frm, cdt, cdn) {
        if (frm._bulk_populating) return;
        let row = locals[cdt][cdn];

        if (row.bom_list && !row.finished_item) {
            frappe.msgprint({
                title: __("Missing Finished Item"),
                message: __("Please select a Finished Item first before selecting a BOM."),
                indicator: "orange"
            });
            frappe.model.set_value(cdt, cdn, 'bom_list', '');
            return;
        }

        if (!row.bom_list) return;

        open_bom_dialog(frm, cdt, cdn, row.bom_list, row.batch_type);

        // ✅ Delay diya taaki grid pehle render ho jaye
        setTimeout(function () {
            setup_eye_buttons(frm);
        }, 500);
    }
});

// ─────────────────────────────────────────────
// BOM Items Dialog — checks store first, fallback to BOM
// ─────────────────────────────────────────────
function open_bom_dialog(frm, cdt, cdn, bom_name, batch_type) {
    let locked_states = ['Pending Approval', 'Approved', 'Rejected'];
    let is_readonly = (batch_type === 'Manufacturing') ||
        locked_states.includes(frm.doc.workflow_state);

    let row_data = locals[cdt] && locals[cdt][cdn];

    let batch_key = (frm.doc.name && row_data && row_data.idx)
        ? `${frm.doc.name}-${row_data.idx}`
        : '';

    if (!batch_key) {
        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'BOM', name: bom_name },
            freeze: true,
            freeze_message: 'Loading BOM Items...',
            callback: function (r) {
                if (!r.message) {
                    frappe.msgprint({ title: 'Error', message: 'BOM not found!', indicator: 'red' });
                    return;
                }
                let bom_items = (r.message.exploded_items || r.message.items || []).map(function (item) {
                    return {
                        item_code: item.item_code || '',
                        item_name: item.item_name || '',
                        uom: item.stock_uom || item.uom || '',
                        qty: item.stock_qty || item.qty || 0
                    };
                });
                render_bom_dialog(frm, cdt, cdn, bom_name, batch_type, is_readonly, bom_items, null);
            }
        });
        return;
    }

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Batch BOM Store after Edit',
            filters: { batch_id: batch_key },
            fields: ['name'],
            limit: 1
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Batch BOM Store after Edit',
                        name: r.message[0].name
                    },
                    callback: function (res) {
                        if (!res.message) return;
                        let items = (res.message.bom_components || []).map(function (row) {
                            return {
                                item_code: row.item_code,
                                item_name: row.item_name,
                                uom: row.uom,
                                qty: row.qty
                            };
                        });
                        render_bom_dialog(frm, cdt, cdn, bom_name, batch_type, is_readonly, items, r.message[0].name);
                    }
                });
            } else {
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'BOM', name: bom_name },
                    freeze: true,
                    freeze_message: 'Loading BOM Items...',
                    callback: function (r) {
                        if (!r.message) {
                            frappe.msgprint({ title: 'Error', message: 'BOM not found!', indicator: 'red' });
                            return;
                        }
                        let bom_items = (r.message.exploded_items || r.message.items || []).map(function (item) {
                            return {
                                item_code: item.item_code || '',
                                item_name: item.item_name || '',
                                uom: item.stock_uom || item.uom || '',
                                qty: item.stock_qty || item.qty || 0
                            };
                        });
                        render_bom_dialog(frm, cdt, cdn, bom_name, batch_type, is_readonly, bom_items, null);
                    }
                });
            }
        }
    });
}

// ─────────────────────────────────────────────
// Render Dialog
// ─────────────────────────────────────────────
function render_bom_dialog(frm, cdt, cdn, bom_name, batch_type, is_readonly, final_items, existing_doc_name) {

    let fields = [];

    if (!is_readonly) {
        fields.push({
            fieldtype: 'HTML',
            fieldname: 'toolbar_html',
            options: get_toolbar_html({ non_stock: false, moq: false, safety: false })
        });
    } else {
        let banner_html = `<div style="background:#fff8e1;border:1px solid #ffe082;
            border-radius:4px;padding:8px 12px;margin-bottom:10px;
            font-size:12px;color:#795548;">
            🔒 BOM is read-only. Items cannot be edited.
        </div>`;

        if (batch_type === 'Manufacturing') {
            let locked_states = ['Pending Approval', 'Approved', 'Rejected'];
            let dis = locked_states.includes(frm.doc.workflow_state) ? 'disabled' : '';
            let cur = dis ? 'not-allowed' : 'pointer';
            let opa = dis ? '0.6' : '1';

            banner_html += `
            <div style="display:flex;gap:16px;margin-bottom:10px;padding:8px 10px;
                background:#f7f9fc;border:1px solid #e0e0e0;border-radius:4px;flex-wrap:wrap;">
                <label style="font-size:12px;cursor:${cur};display:flex;align-items:center;gap:5px;opacity:${opa};">
                    <input type="checkbox" id="chk_non_stock" ${dis}> Exclude Non-Stock Items
                </label>
                <label style="font-size:12px;cursor:${cur};display:flex;align-items:center;gap:5px;opacity:${opa};">
                    <input type="checkbox" id="chk_subcontracted" disabled> Exclude Subcontracted Items
                </label>
                <label style="font-size:12px;cursor:${cur};display:flex;align-items:center;gap:5px;opacity:${opa};">
                    <input type="checkbox" id="chk_moq" ${dis}> Consider Minimum Order Qty
                </label>
                <label style="font-size:12px;cursor:${cur};display:flex;align-items:center;gap:5px;opacity:${opa};">
                    <input type="checkbox" id="chk_safety" ${dis}> Include Safety Stock in Qty
                </label>
                <label style="font-size:12px;cursor:not-allowed;display:flex;align-items:center;gap:5px;opacity:0.5;">
                    <input type="checkbox" id="chk_ignore_stock" disabled> Ignore Available Stock
                </label>
            </div>`;
        }

        fields.push({
            fieldtype: 'HTML',
            fieldname: 'readonly_banner',
            options: banner_html
        });
    }

    fields.push({
        fieldtype: 'HTML',
        fieldname: 'table_html',
        options: get_table_html(final_items, is_readonly)
    });

    var d = new frappe.ui.Dialog({
        title: `📋 BOM Items — ${bom_name}` + (is_readonly ? ' (Read Only)' : ''),
        size: 'extra-large',
        fields: fields,
        primary_action_label: is_readonly ? null : '💾 Save',
        primary_action: is_readonly ? null : function () {
            let items = collect_table_data(d);
            if (!items) return;

            if (items.length === 0) {
                frappe.msgprint({
                    title: '⚠️ Cannot Save',
                    message: 'BOM table must have at least <b>one item</b> before saving.',
                    indicator: 'red'
                });
                return;
            }

            let row_data = locals[cdt] && locals[cdt][cdn];
            let batch_key = (frm.doc.name && row_data && row_data.idx)
                ? `${frm.doc.name}-${row_data.idx}`
                : '';

            if (!batch_key) {
                frappe.msgprint({
                    title: '⚠️ Cannot Save',
                    message: 'Form not saved yet. Please save the form first.',
                    indicator: 'red'
                });
                return;
            }

            let bom_components = items.map(function (item) {
                return {
                    item_code: item.item_code,
                    item_name: item.item_name,
                    uom: item.uom,
                    qty: item.qty
                };
            });

            if (existing_doc_name) {
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Batch BOM Store after Edit',
                        name: existing_doc_name
                    },
                    callback: function (res) {
                        if (!res.message) return;
                        let doc = res.message;
                        doc.bom_components = bom_components;

                        frappe.call({
                            method: 'frappe.client.save',
                            args: { doc: doc },
                            callback: function (saved) {
                                if (saved.message) {
                                    frappe.show_alert({
                                        message: `✅ BOM <b>${bom_name}</b> updated — ${items.length} items saved.`,
                                        indicator: 'green'
                                    }, 5);
                                    existing_doc_name = saved.message.name;
                                    d.hide();
                                }
                            }
                        });
                    }
                });
            } else {
                frappe.call({
                    method: 'frappe.client.insert',
                    args: {
                        doc: {
                            doctype: 'Batch BOM Store after Edit',
                            batch_id: batch_key,
                            custom_batch_creation_id: frm.doc.name,
                            bom_name: bom_name,
                            bom_components: bom_components
                        }
                    },
                    callback: function (res) {
                        if (res.message) {
                            frappe.show_alert({
                                message: `✅ BOM <b>${bom_name}</b> saved — ${items.length} items stored.`,
                                indicator: 'green'
                            }, 5);
                            existing_doc_name = res.message.name;
                            d.hide();
                        }
                    }
                });
            }
        },
        secondary_action_label: is_readonly ? 'Close' : 'Cancel',
        secondary_action: function () { d.hide(); }
    });

    d.show();

    if (!is_readonly) {
        bind_dialog_events(d);
    }

    if (batch_type === 'Manufacturing') {
        let original_items = final_items.map(function (i) {
            return { item_code: i.item_code, item_name: i.item_name, uom: i.uom, qty: i.qty };
        });

        d.$wrapper.on('change', '#chk_non_stock, #chk_moq, #chk_safety', function () {
            let non_stock = d.$wrapper.find('#chk_non_stock').is(':checked');
            let moq = d.$wrapper.find('#chk_moq').is(':checked');
            let safety = d.$wrapper.find('#chk_safety').is(':checked');

            if (!non_stock && !moq && !safety) {
                let $tbody = d.$wrapper.find('#bom_edit_tbody');
                $tbody.empty();
                original_items.forEach(function (item, i) {
                    $tbody.append(make_row(i + 1, item.item_code, item.item_name, item.qty, item.uom, true));
                });
                update_row_count(d.$wrapper);
                return;
            }

            let item_codes = original_items.map(function (i) { return i.item_code; });
            frappe.call({
                method: 'custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_item_details_for_bom',
                args: { item_codes: JSON.stringify(item_codes) },
                callback: function (r) {
                    if (!r.message) return;
                    let item_map = {};
                    r.message.forEach(function (i) { item_map[i.name] = i; });

                    let filtered = [];
                    original_items.forEach(function (bom_item) {
                        let detail = item_map[bom_item.item_code];
                        if (!detail) { filtered.push(bom_item); return; }

                        if (non_stock && detail.item_group === 'Service') return;

                        let qty = bom_item.qty;
                        if (moq && detail.min_order_qty > 0 && qty < detail.min_order_qty)
                            qty = detail.min_order_qty;
                        if (safety && detail.safety_stock > 0 && qty < detail.safety_stock)
                            qty = detail.safety_stock;

                        filtered.push({ item_code: bom_item.item_code, item_name: bom_item.item_name, uom: bom_item.uom, qty: qty });
                    });

                    let $tbody = d.$wrapper.find('#bom_edit_tbody');
                    $tbody.empty();
                    filtered.forEach(function (item, i) {
                        $tbody.append(make_row(i + 1, item.item_code, item.item_name, item.qty, item.uom, true));
                    });
                    update_row_count(d.$wrapper);
                }
            });
        });
    }
}

// ─────────────────────────────────────────────
// Toolbar HTML
// ─────────────────────────────────────────────
function get_toolbar_html(checkbox_state) {
    checkbox_state = checkbox_state || {};
    return `
        <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center;">
            <button class="btn btn-sm btn-default" id="btn_download_template">
                ⬇️ Download Template
            </button>
            <label class="btn btn-sm btn-primary" style="margin:0;cursor:pointer;">
                ⬆️ Upload Excel
                <input type="file" id="excel_file_input" accept=".xlsx,.xls" style="display:none;">
            </label>
            <span id="upload_status" style="font-size:12px;color:#888;"></span>
        </div>
        <div style="display:flex;gap:16px;margin-bottom:10px;padding:8px 10px;
            background:#f7f9fc;border:1px solid #e0e0e0;border-radius:4px;flex-wrap:wrap;">
            <label style="font-size:12px;cursor:pointer;display:flex;align-items:center;gap:5px;">
                <input type="checkbox" id="chk_non_stock" ${checkbox_state.non_stock ? 'checked' : ''}>
                Exclude Non-Stock Items
            </label>
            <label style="font-size:12px;cursor:pointer;display:flex;align-items:center;gap:5px;">
                <input type="checkbox" id="chk_moq" ${checkbox_state.moq ? 'checked' : ''}>
                Consider Minimum Order Qty
            </label>
            <label style="font-size:12px;cursor:pointer;display:flex;align-items:center;gap:5px;">
                <input type="checkbox" id="chk_safety" ${checkbox_state.safety ? 'checked' : ''}>
                Include Safety Stock in Qty
            </label>
        </div>
    `;
}

// ─────────────────────────────────────────────
// Table HTML
// ─────────────────────────────────────────────
function get_table_html(items, is_readonly) {
    let rows = '';

    if (!items || items.length === 0) {
        rows = `<tr id="empty_row">
                    <td colspan="${is_readonly ? 5 : 6}"
                        style="text-align:center;color:#aaa;padding:20px;">
                        No items found.
                    </td>
                </tr>`;
    } else {
        items.forEach(function (item, i) {
            rows += make_row(i + 1, item.item_code, item.item_name, item.qty, item.uom, is_readonly);
        });
    }

    let del_header = is_readonly ? '' : '<th style="width:40px;"></th>';

    return `
        <div style="max-height:420px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;">
            <table class="table table-bordered" id="bom_edit_table"
                style="margin:0;font-size:13px;width:100%;">
                <thead style="background:#f7f7f7;position:sticky;top:0;z-index:1;">
                    <tr>
                        <th style="width:40px;text-align:center;">#</th>
                        <th style="width:160px;">Item Code</th>
                        <th>Item Name</th>
                        <th style="width:90px;">UOM</th>
                        <th style="width:90px;">Qty</th>
                        ${del_header}
                    </tr>
                </thead>
                <tbody id="bom_edit_tbody">
                    ${rows}
                </tbody>
            </table>
        </div>
        ${!is_readonly ? `
        <div style="margin-top:10px;">
            <button class="btn btn-sm btn-success" id="btn_add_row">+ Add Row</button>
            <span style="float:right;font-size:12px;color:#888;" id="row_count">
                ${items ? items.length : 0} rows
            </span>
        </div>` : `
        <div style="margin-top:8px;text-align:right;">
            <span style="font-size:12px;color:#888;">${items ? items.length : 0} rows</span>
        </div>`}
    `;
}

// ─────────────────────────────────────────────
// Single Row HTML
// ─────────────────────────────────────────────
function make_row(idx, item_code, item_name, qty, uom, is_readonly) {
    if (is_readonly) {
        return `
            <tr>
                <td style="text-align:center;color:#888;padding:6px;">${idx}</td>
                <td style="padding:6px;">${item_code || ''}</td>
                <td style="padding:6px;">${item_name || ''}</td>
                <td style="padding:6px;">${uom || ''}</td>
                <td style="padding:6px;">${qty || 0}</td>
            </tr>`;
    }
    return `
        <tr>
            <td style="text-align:center;vertical-align:middle;color:#888;">${idx}</td>
            <td style="padding:3px;">
                <input type="text" class="form-control form-control-sm r-item-code"
                    value="${item_code || ''}" placeholder="Item Code" style="width:100%;">
            </td>
            <td style="padding:3px;">
                <input type="text" class="form-control form-control-sm r-item-name"
                    value="${item_name || ''}" placeholder="Auto-filled"
                    readonly style="width:100%;background:#f9f9f9;color:#555;">
            </td>
            <td style="padding:3px;">
                <input type="text" class="form-control form-control-sm r-uom"
                    value="${uom || ''}" placeholder="UOM" style="width:100%;">
            </td>
            <td style="padding:3px;">
                <input type="number" class="form-control form-control-sm r-qty"
                    value="${qty || ''}" placeholder="0" min="0" style="width:100%;">
            </td>
            <td style="text-align:center;vertical-align:middle;">
                <button class="btn btn-xs btn-danger btn-del-row"
                    style="padding:1px 7px;font-size:11px;">✕</button>
            </td>
        </tr>`;
}

// ─────────────────────────────────────────────
// Bind Dialog Events
// ─────────────────────────────────────────────
function bind_dialog_events(d) {
    let $w = d.$wrapper;

    $w.on('click', '#btn_add_row', function () {
        let $tbody = $w.find('#bom_edit_tbody');
        $tbody.find('#empty_row').remove();
        let idx = $tbody.find('tr').length + 1;
        $tbody.append(make_row(idx, '', '', '', '', false));
        update_row_count($w);
    });

    $w.on('click', '.btn-del-row', function () {
        $(this).closest('tr').remove();
        renumber_rows($w);
        update_row_count($w);
    });

    $w.on('blur', '.r-item-code', function () {
        let $input = $(this);
        let item_code = $input.val().trim();
        let $row = $input.closest('tr');
        if (!item_code) return;

        frappe.db.get_value('Item', item_code, ['item_name', 'stock_uom'])
            .then(function (r) {
                if (r && r.message) {
                    $row.find('.r-item-name').val(r.message.item_name || '');
                    if (!$row.find('.r-uom').val()) {
                        $row.find('.r-uom').val(r.message.stock_uom || '');
                    }
                } else {
                    frappe.show_alert({
                        message: `Item "${item_code}" not found`,
                        indicator: 'orange'
                    });
                    $row.find('.r-item-name').val('');
                }
            });
    });

    $w.on('click', '#btn_download_template', function () {
        download_template();
    });

    $w.on('change', '#excel_file_input', function (e) {
        let file = e.target.files[0];
        if (!file) return;
        $w.find('#upload_status').text('Reading file...');
        handle_excel_upload(file, $w, function (count) {
            $w.find('#upload_status').text(`✅ ${count} rows loaded`);
            update_row_count($w);
            $w.find('#excel_file_input').val('');
        });
    });
}

// ─────────────────────────────────────────────
// Collect Table Data
// ─────────────────────────────────────────────
function collect_table_data(d) {
    let items = [];
    let error = null;

    d.$wrapper.find('#bom_edit_tbody tr:not(#empty_row)').each(function (i) {
        let item_code = $(this).find('.r-item-code').val().trim();
        let item_name = $(this).find('.r-item-name').val().trim();
        let qty = parseFloat($(this).find('.r-qty').val()) || 0;
        let uom = $(this).find('.r-uom').val().trim();

        if (!item_code) {
            error = `Row ${i + 1}: Item Code cannot be empty!`;
            return false;
        }
        if (qty <= 0) {
            error = `Row ${i + 1} (${item_code}): Qty must be greater than 0!`;
            return false;
        }
        items.push({ item_code, item_name, qty, uom });
    });

    if (error) {
        frappe.msgprint({ title: '⚠️ Validation Error', message: error, indicator: 'red' });
        return null;
    }
    return items;
}

// ─────────────────────────────────────────────
// Renumber + Row Count
// ─────────────────────────────────────────────
function renumber_rows($w) {
    $w.find('#bom_edit_tbody tr:not(#empty_row)').each(function (i) {
        $(this).find('td:first').text(i + 1);
    });
}

function update_row_count($w) {
    let count = $w.find('#bom_edit_tbody tr:not(#empty_row)').length;
    $w.find('#row_count').text(count + ' rows');
}

// ─────────────────────────────────────────────
// Excel Upload
// ─────────────────────────────────────────────
function handle_excel_upload(file, $w, callback) {
    if (typeof XLSX === 'undefined') {
        frappe.msgprint('⚠️ Excel library not loaded yet. Please try again in a moment.');
        return;
    }

    const REQUIRED = ['Item Code', 'Item Name', 'UOM', 'Qty'];

    let reader = new FileReader();
    reader.onload = function (e) {
        try {
            let wb = XLSX.read(new Uint8Array(e.target.result), { type: 'array' });
            let ws = wb.Sheets[wb.SheetNames[0]];

            let raw = XLSX.utils.sheet_to_json(ws, { header: 1 });
            let headers = (raw[0] || []).map(h => h.toString().trim());

            let format_ok = REQUIRED.every((col, idx) => headers[idx] === col);
            if (!format_ok) {
                frappe.msgprint({
                    title: '⚠️ Invalid Excel Format',
                    message: `Expected columns in order:<br><b>Item Code | Item Name | UOM | Qty</b><br><br>
                        Found: <b>${headers.join(' | ')}</b><br><br>
                        Please download the template first.`,
                    indicator: 'red'
                });
                return;
            }

            let data = XLSX.utils.sheet_to_json(ws, { defval: '' });

            if (!data.length) {
                frappe.msgprint('⚠️ Excel file is empty!');
                return;
            }

            let $tbody = $w.find('#bom_edit_tbody');
            $tbody.empty();

            data.forEach(function (row, i) {
                let item_code = (row['Item Code'] || '').toString().trim();
                let item_name = (row['Item Name'] || '').toString().trim();
                let uom = (row['UOM'] || '').toString().trim();
                let qty = parseFloat(row['Qty']) || 0;
                $tbody.append(make_row(i + 1, item_code, item_name, qty, uom, false));
            });

            if (typeof callback === 'function') callback(data.length);

        } catch (err) {
            frappe.msgprint('⚠️ Error reading Excel: ' + err.message);
        }
    };
    reader.readAsArrayBuffer(file);
}

// ─────────────────────────────────────────────
// Download Excel Template
// ─────────────────────────────────────────────
function download_template() {
    if (typeof XLSX === 'undefined') {
        frappe.msgprint('⚠️ Excel library not loaded yet. Please try again.');
        return;
    }
    let ws = XLSX.utils.aoa_to_sheet([
        ['Item Code', 'Item Name', 'UOM', 'Qty'],
        ['ITEM-001', 'Sample Item', 'Nos', 1]
    ]);
    ws['!cols'] = [{ wch: 20 }, { wch: 30 }, { wch: 10 }, { wch: 10 }];

    let wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'BOM Items');
    XLSX.writeFile(wb, 'BOM_Items_Template.xlsx');
}

// ─────────────────────────────────────────────
// Load Valid Slots & re-apply set_query
// ─────────────────────────────────────────────
function load_used_slots(frm) {
    if (!frm.doc.custom_employee_function) return;

    frappe.call({
        method: 'custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_valid_slot_openings',
        args: {
            employee_function: frm.doc.custom_employee_function,
            current_doc: frm.doc.name || ''
        },
        callback: function (r) {
            let valid = r.message || [];
            frm.set_query('slot_opening', function () {
                return {
                    filters: [
                        ['Slot Opening', 'name', 'in', valid.length ? valid : ['']]
                    ]
                };
            });
        }
    });
}

// ─────────────────────────────────────────────
// Eye Button Setup — with all guards
// ─────────────────────────────────────────────
function setup_eye_buttons(frm) {
    // ✅ Observer pehle disconnect karo
    if (frm._bom_observer) {
        frm._bom_observer.disconnect();
        frm._bom_observer = null;
    }

    // ✅ Guard 1: fields_dict ready nahi hai
    if (!frm.fields_dict || !frm.fields_dict['custom_batch_details']) return;

    let grid = frm.fields_dict['custom_batch_details'].grid;

    // ✅ Guard 2: grid ya wrapper ready nahi hai
    if (!grid || !grid.wrapper) return;

    // ✅ Guard 3: doc ya rows ready nahi hain
    if (!frm.doc || !frm.doc.custom_batch_details) return;

    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;
    grid.wrapper.find('.grid-add-row').hide();
    grid.wrapper.find('.grid-remove-rows').hide();
    grid.wrapper.find('.grid-remove-all-rows').hide();

    let $grid_wrapper = grid.wrapper;

    inject_eye_buttons_once(frm, $grid_wrapper);

    frm._bom_observer = new MutationObserver(function () {
        clearTimeout(frm._bom_observer_timer);
        frm._bom_observer_timer = setTimeout(function () {
            inject_eye_buttons_once(frm, $grid_wrapper);
        }, 300);
    });

    frm._bom_observer.observe($grid_wrapper[0], { childList: true, subtree: true });
}

// ─────────────────────────────────────────────
// Inject Eye Button — ONE per row, no duplicates
// ─────────────────────────────────────────────
function inject_eye_buttons_once(frm, $grid_wrapper) {
    $grid_wrapper.find('.grid-row').each(function () {
        let $row = $(this);
        let row_name = $row.attr('data-name');
        if (!row_name) return;

        let rd = locals['Batch Planning Detail'] &&
            locals['Batch Planning Detail'][row_name];

        let bom_val = (rd && rd.bom_list) || '';

        if (!bom_val) {
            bom_val = $row.find('[data-fieldname="bom_list"] .static-area').text().trim() ||
                $row.find('[data-fieldname="bom_list"] .ellipsis').text().trim() ||
                $row.find('[data-fieldname="bom_list"]').attr('data-value') || '';
        }

        bom_val = bom_val.trim();

        let $bom_cell = $row.find('[data-fieldname="bom_list"]');
        if (!$bom_cell.length) return;

        $bom_cell.find('.bom-eye-btn').remove();

        if (!bom_val) return;

        $bom_cell.css({
            'display': 'flex',
            'align-items': 'center',
            'gap': '4px',
            'white-space': 'nowrap'
        });

        let $btn = $(`<button class="btn btn-xs bom-eye-btn"
            data-bom="${bom_val}"
            data-row="${row_name}"
            title="View / Edit BOM Items"
            style="padding:1px 5px;font-size:11px;background:transparent;
            border:1px solid #d1d8dd;border-radius:4px;cursor:pointer;
            color:#5e64ff;flex-shrink:0;line-height:1.5;">👁</button>`);

        $btn.on('click', function (e) {
            e.stopPropagation();
            e.preventDefault();

            let fresh_rd = locals['Batch Planning Detail'] &&
                locals['Batch Planning Detail'][row_name];
            let fresh_bom = (fresh_rd && fresh_rd.bom_list) || bom_val;
            let fresh_type = (fresh_rd && fresh_rd.batch_type) || '';

            if (!fresh_bom) {
                frappe.show_alert({ message: 'No BOM selected', indicator: 'orange' });
                return;
            }

            open_bom_dialog(frm, 'Batch Planning Detail', row_name, fresh_bom, fresh_type);
        });

        $bom_cell.append($btn);
    });
}

function empty_state(icon, msg) {
    return `<div style="padding:48px; text-align:center; color:#6b7280; border:2px dashed #d1fae5; border-radius:12px; background:#f0fdf4;"><div style="font-size:36px;">${icon}</div><div style="font-size:13px;">${msg}</div></div>`;
}

function render_bom_components_tab(frm) {
    let $field = frm.fields_dict["bom_component_html"];
    if (!$field) return;

    frappe.call({
        method: "custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_consolidated_bom_components",
        args: { doc_name: frm.doc.name },
        callback: function (r) {
            let items = r.message || [];
            if (!items.length) {
                $field.$wrapper.html(empty_state("📦", "No BOM components found."));
                return;
            }

            let rows_html = items.map(function (item, i) {
                let bg = i % 2 === 0 ? "#f9fafb" : "#ffffff";
                return `
                    <tr style="background:${bg}; border-bottom: 1px solid #e5e7eb;">
                        <td style="padding:12px 16px; text-align:center; color:#6b7280; font-weight:600; font-size:13px;">${i + 1}</td>
                        <td style="padding:12px 16px;">
                            <span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:5px;
                                font-size:11px; font-weight:700; letter-spacing:0.3px; white-space:nowrap;">
                                ${item.item_code || ""}
                            </span>
                        </td>
                        <td style="padding:12px 16px; color:#1f2937; font-size:13px; font-weight:500;">${item.item_name || ""}</td>
                        <td style="padding:12px 16px; text-align:center; color:#4b5563; font-size:12px;
                            font-family:monospace;">${item.uom || ""}</td>
                        <td style="padding:12px 16px; text-align:center; font-weight:700; color:#15803d;
                            font-size:13px;">${parseFloat(item.qty || 0).toFixed(4)}</td>
                    </tr>`;
            }).join("");

            let html = `
                <div style="width:100%; box-sizing:border-box; font-family:inherit; margin-top: 15px;">
                    <div style="background:linear-gradient(135deg, #16a34a 0%, #14532d 100%);
                        color:#fff; padding:16px 20px; border-radius:10px 10px 0 0;
                        display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
                        <div>
                            <span style="font-size:16px; font-weight:700; letter-spacing:0.5px;">Consolidated BOM Components</span>
                            <div style="font-size:11px; opacity:0.85; margin-top:2px;">Consolidated raw materials for all batches in this plan</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.15); padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600;">
                            ${items.length} Unique Items
                        </div>
                    </div>
                    <div style="border:1px solid #e5e7eb; border-top:none; border-radius:0 0 10px 10px; overflow:hidden; background:#fff;">
                        <table style="width:100%; border-collapse:collapse; text-align:left;">
                            <thead>
                                <tr style="background:#f3f4f6; border-bottom:1px solid #e5e7eb;">
                                    <th style="padding:12px 16px; text-align:center; color:#374151; font-weight:600; font-size:12px; text-transform:uppercase;">#</th>
                                    <th style="padding:12px 16px; color:#374151; font-weight:600; font-size:12px; text-transform:uppercase;">Item Code</th>
                                    <th style="padding:12px 16px; color:#374151; font-weight:600; font-size:12px; text-transform:uppercase;">Item Name</th>
                                    <th style="padding:12px 16px; text-align:center; color:#374151; font-weight:600; font-size:12px; text-transform:uppercase;">UOM</th>
                                    <th style="padding:12px 16px; text-align:center; color:#374151; font-weight:600; font-size:12px; text-transform:uppercase;">Total Qty</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>`;
            $field.$wrapper.html(html);
        }
    });
}

function render_material_planning_tab(frm) {
    let $field = frm.fields_dict["material_planning_html"];
    if (!$field) return;

    $field.$wrapper.html(`
        <div style="padding:48px; text-align:center; color:#6b7280;">
            <div style="width:36px; height:36px; border:3px solid #d1fae5; border-top-color:#16a34a; border-radius:50%; animation:mp-spin-bp 0.8s linear infinite; margin:0 auto 14px;"></div>
            <style>@keyframes mp-spin-bp { to { transform:rotate(360deg); } }</style>
            <div style="font-size:13px; color:#4b5563;">Fetching consolidated material planning data...</div>
        </div>
    `);

    frappe.call({
        method: "custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning.get_material_planning_data",
        args: { doc_name: frm.doc.name },
        callback: function (r) {
            if (!r.message) {
                $field.$wrapper.html(empty_state("❌", "Could not fetch material planning data."));
                return;
            }

            let warehouse = r.message.warehouse;
            let data = r.message.results || [];
            frm._mp_data = data;

            if (!data.length) {
                $field.$wrapper.html(empty_state("📦", "No items to display for material planning."));
                return;
            }

            let th_style = function (align = "center") {
                return `padding:11px 10px; text-align:${align}; color:#166534; font-weight:700; font-size:10px; text-transform:uppercase; white-space:nowrap; border-bottom:2px solid #86efac;`;
            };

            let format_qty_val = function (val) {
                if (val === null || val === undefined || val === "") return "-";
                let num = parseFloat(val);
                if (isNaN(num)) return "-";
                return num % 1 === 0 ? num.toString() : num.toFixed(2);
            };

            let rows_html = data.map((row, i) => {
                let bg = i % 2 === 0 ? "#f9fafb" : "#ffffff";
                
                let mr_qty_sum = parseFloat(row.global_mr_qty || 0) + parseFloat(row.bp_mr_qty || 0);
                let po_qty_sum = parseFloat(row.global_po_qty || 0) + parseFloat(row.bp_po_qty || 0);
                let grn_qty_sum = parseFloat(row.global_grn_qty || 0) + parseFloat(row.bp_grn_qty || 0);

                let mr_td = "";
                if (mr_qty_sum > 0) {
                    mr_td = `
                        <td style="padding:9px 10px; text-align:center; font-weight:700; cursor:pointer; color:#1f2937;"
                            onclick="frappe.set_route('List', 'Material Request', {
                                'custom_employee_function': '${frm.doc.custom_employee_function || ""}',
                                'docstatus': 1,
                                'Material Request Item.item_code': '${row.item_code}'
                            })">
                            <span>${format_qty_val(row.global_mr_qty)}</span> <span style="color:#16a34a;">(${format_qty_val(row.bp_mr_qty)})</span>
                        </td>
                    `;
                } else {
                    mr_td = `
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#9ca3af;">
                            <span>${format_qty_val(row.global_mr_qty)}</span> <span style="color:#d1d5db;">(${format_qty_val(row.bp_mr_qty)})</span>
                        </td>
                    `;
                }

                let po_td = "";
                if (po_qty_sum > 0) {
                    po_td = `
                        <td style="padding:9px 10px; text-align:center; font-weight:700; cursor:pointer; color:#1f2937;"
                            onclick="frappe.set_route('List', 'Purchase Order', {
                                'employee_function': '${frm.doc.custom_employee_function || ""}',
                                'docstatus': 1,
                                'Purchase Order Item.item_code': '${row.item_code}'
                            })">
                            <span>${format_qty_val(row.global_po_qty)}</span> <span style="color:#16a34a;">(${format_qty_val(row.bp_po_qty)})</span>
                        </td>
                    `;
                } else {
                    po_td = `
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#9ca3af;">
                            <span>${format_qty_val(row.global_po_qty)}</span> <span style="color:#d1d5db;">(${format_qty_val(row.bp_po_qty)})</span>
                        </td>
                    `;
                }

                let grn_td = "";
                if (grn_qty_sum > 0) {
                    grn_td = `
                        <td style="padding:9px 10px; text-align:center; font-weight:700; cursor:pointer; color:#1f2937;"
                            onclick="frappe.set_route('List', 'Purchase Receipt', {
                                'employee_function': '${frm.doc.custom_employee_function || ""}',
                                'docstatus': 1,
                                'Purchase Receipt Item.item_code': '${row.item_code}'
                            })">
                            <span>${format_qty_val(row.global_grn_qty)}</span> <span style="color:#16a34a;">(${format_qty_val(row.bp_grn_qty)})</span>
                        </td>
                    `;
                } else {
                    grn_td = `
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#9ca3af;">
                            <span>${format_qty_val(row.global_grn_qty)}</span> <span style="color:#d1d5db;">(${format_qty_val(row.bp_grn_qty)})</span>
                        </td>
                    `;
                }

                return `
                    <tr style="background:${bg}; border-bottom: 1px solid #e5e7eb;">
                        <td style="padding:9px 10px; text-align:center; color:#9ca3af; font-size:12px; font-weight:600;">${i + 1}</td>
                        <td style="padding:9px 10px;"><span style="background:#16a34a; color:#fff; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; white-space:nowrap;">${row.item_code}</span></td>
                        <td style="padding:9px 10px; color:#1f2937; font-size:12px; font-weight:500;">${row.item_name || ""}</td>
                        <td style="padding:9px 10px; text-align:center; color:#4b5563; font-size:12px; font-family:monospace;">${row.uom || ""}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#d97706; font-size:12px;">${format_qty_val(row.qty_required)}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#15803d; font-size:12px;">${format_qty_val(row.total_stock)}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#1d4ed8; font-size:12px;">${format_qty_val(row.main_stock)}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#d97706; font-size:12px;">${format_qty_val(row.allocated_qty)}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; font-size:12px; color:${parseFloat(row.free_stock || 0) > 0 ? "#15803d" : "#dc2626"};">${format_qty_val(row.free_stock)}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#7c3aed; font-size:12px;">${format_qty_val(row.lab_stock)}</td>
                        ${mr_td}
                        ${po_td}
                        ${grn_td}
                        <td style="padding:9px 10px; text-align:center; font-weight:700; font-size:12px; color:${parseFloat(row.net_requirement || 0) > 0 ? "#dc2626" : "#15803d"};">${format_qty_val(row.net_requirement)}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#15803d; font-size:12px;">${format_qty_val(row.usable_qty)}</td>
                        <td style="padding:9px 10px; text-align:center; font-weight:700; color:#dc2626; font-size:12px;">${format_qty_val(row.expired_qty)}</td>
                    </tr>`;
            }).join("");

            let html = `
                <div id="mp-table-container-bp" style="width:100%; font-family:inherit; margin-top: 15px;">
                    <div style="background:linear-gradient(135deg, #16a34a 0%, #14532d 100%); color:#fff; padding:16px 20px; border-radius:10px 10px 0 0; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:15px; font-weight:700;">🏭 Consolidated Material Planning — Stock vs Requirement</div>
                            <div style="font-size:12px; opacity:0.85; margin-top:2px;">Warehouse: <b>${warehouse}</b></div>
                        </div>
                        <div style="background:rgba(255,255,255,0.15); padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600;">
                            ${data.length} Items
                        </div>
                    </div>
                    <div style="overflow-x:auto; border:1px solid #d1fae5; border-top:none; border-radius:0 0 10px 10px; background:#fff;">
                        <table style="width:100%; border-collapse:collapse; min-width:1350px; text-align:left;">
                            <thead>
                                <tr style="background:#f3f4f6;">
                                    <th style="${th_style()}">#</th>
                                    <th style="${th_style("left")}">Item Code</th>
                                    <th style="${th_style("left")}">Item Name</th>
                                    <th style="${th_style()}">UOM</th>
                                    <th style="${th_style()}">Qty Req</th>
                                    <th style="${th_style()}">Total Stock</th>
                                    <th style="${th_style()}">Main Wh</th>
                                    <th style="${th_style()}">Allocated</th>
                                    <th style="${th_style()}">Free Qty</th>
                                    <th style="${th_style()}">Lab Wise</th>
                                    <th style="${th_style()}">Open MR</th>
                                    <th style="${th_style()}">Open PO</th>
                                    <th style="${th_style()}">Open PR</th>
                                    <th style="${th_style()}">Net Req</th>
                                    <th style="${th_style()}">Usable</th>
                                    <th style="${th_style()}">Expired Qty</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>`;
            $field.$wrapper.html(html);
        }
    });
}

function render_material_planning_placeholder(frm) {
    let $field = frm.fields_dict["material_planning_html"];
    if (!$field) return;

    $field.$wrapper.html(`
        <div style="padding:48px; text-align:center; color:#6b7280; border:2px dashed #d1fae5; border-radius:12px; margin:4px 0; background:#f0fdf4;">
            <div style="font-size:36px; margin-bottom:12px;">🏭</div>
            <div style="font-size:15px; font-weight:700; color:#166534; margin-bottom:6px;">Material Planning</div>
            <div style="font-size:13px; color:#4b5563;">Click <b style="color:#16a34a;">Run Material Planning</b> above to load stock data.</div>
        </div>
    `);
}

function set_project_filter(frm) {
    if (!frm.doc.custom_employee_function) {
        frm.set_query('project', function () {
            return {
                filters: [['name', '=', '']]
            };
        });
        return;
    }

    frappe.call({
        method: 'custom_batch_planning.custom_batch_planning.doctype.slot_master_list.slot_master_list.get_employee_function_projects',
        args: {
            employee_function: frm.doc.custom_employee_function
        },
        callback: function (r) {
            let projects = r.message || [];
            frm.set_query('project', function () {
                return {
                    filters: [['name', 'in', projects.length ? projects : ['']]]
                };
            });
        }
    });
}

function render_stock_entry_tab(frm) {
    let rows = frm.doc.stock_entry_log || [];
    let html = '';
    if (!rows.length) {
        html = '<p style="padding: 20px; text-align: center; color: #6b7280; border: 2px dashed #e5e7eb; border-radius: 8px; margin-top: 15px;">No Stock Entries Yet</p>';
    } else {
        html = `<table class="table table-bordered">
            <thead><tr>
                <th>#</th>
                <th>Stock Entry</th>
                <th>Date</th>
                <th>From Warehouse</th>
                <th>To Warehouse</th>
                <th>Status</th>
            </tr></thead><tbody>`;
        rows.forEach((r, i) => {
            html += `<tr>
                <td>${i + 1}</td>
                <td><a href="/app/stock-entry/${r.stock_entry}">${r.stock_entry}</a></td>
                <td>${r.date || ''}</td>
                <td>${r.from_warehouse || ''}</td>
                <td>${r.to_warehouse || ''}</td>
                <td>${r.status || ''}</td>
            </tr>`;
        });
        html += '</tbody></table>';
    }
    if (frm.fields_dict["stock_entry_details"] && frm.fields_dict["stock_entry_details"].$wrapper) {
        frm.fields_dict["stock_entry_details"].$wrapper.html(html);
    }
}

function render_item_issue_tab(frm) {
    let rows = frm.doc.item_issue_log || [];
    let html = '';
    if (!rows.length) {
        html = '<p style="padding: 20px; text-align: center; color: #6b7280; border: 2px dashed #e5e7eb; border-radius: 8px; margin-top: 15px;">No Items Issued Yet</p>';
    } else {
        html = `<table class="table table-bordered">
            <thead><tr>
                <th>#</th>
                <th>Item Code</th>
                <th>Item Name</th>
                <th>Qty</th>
                <th>UOM</th>
                <th>From Warehouse</th>
                <th>To Warehouse</th>
                <th>Stock Entry</th>
            </tr></thead><tbody>`;
        rows.forEach((r, i) => {
            html += `<tr>
                <td>${i + 1}</td>
                <td>${r.item_code || ''}</td>
                <td>${r.item_name || ''}</td>
                <td>${r.qty || 0}</td>
                <td>${r.uom || ''}</td>
                <td>${r.from_warehouse || ''}</td>
                <td>${r.to_warehouse || ''}</td>
                <td><a href="/app/stock-entry/${r.stock_entry}">${r.stock_entry}</a></td>
            </tr>`;
        });
        html += '</tbody></table>';
    }
    if (frm.fields_dict["item_issue_details"] && frm.fields_dict["item_issue_details"].$wrapper) {
        frm.fields_dict["item_issue_details"].$wrapper.html(html);
    }
}