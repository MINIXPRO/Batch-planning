// ─────────────────────────────────────────────
// SheetJS load karo (Excel ke liye)
// ─────────────────────────────────────────────
if (typeof XLSX === 'undefined') {
    let s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
    document.head.appendChild(s);
}

// ─────────────────────────────────────────────
// Batch Creation — Main Form
// ─────────────────────────────────────────────
frappe.ui.form.on('Batch Creation', {



    setup: function (frm) {
        frm.set_query('bom_list', 'custom_batch_details', function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            let filters = { docstatus: 1, is_active: 1 };
            if (row.finished_item) {
                filters['item'] = row.finished_item;
            }
            return { filters: filters };
        });

        frm.set_query('finished_item', 'custom_batch_details', function () {
            return {
                filters: { item_group: 'Finish Goods' }
            };
        });
    },

    custom_employee_function: function (frm) {
        if (frm.is_new() && !frm._emp_func_initialized) {
            frm._emp_func_initialized = true;
            if (frm.doc.slot_opening) {
                load_used_slots(frm);
                return;
            }
        }

        frm.set_value('slot_opening', '');
        frm.set_value('month', '');
        frm.clear_table('slot_opening_table');
        frm.clear_table('custom_batch_details');
        frm.refresh_field('slot_opening_table');
        frm.refresh_field('custom_batch_details');
        load_used_slots(frm);
    },

    slot_opening: function (frm) {
        if (frm.doc.slot_opening && !frm.doc.custom_employee_function) {
            frappe.msgprint({
                title: __("Missing Employee Function"),
                message: __("Please select an Employee Function first before selecting a Slot Opening."),
                indicator: "orange"
            });
            frm.set_value("slot_opening", "");
            return;
        }

        if (!frm.doc.slot_opening) {
            frm.set_value('month', '');
            frm.clear_table('slot_opening_table');
            frm.clear_table('custom_batch_details');
            frm.refresh_field('slot_opening_table');
            frm.refresh_field('custom_batch_details');
            return;
        }

        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'Slot Opening', name: frm.doc.slot_opening },
            callback: function (r) {
                if (!r.message) return;
                let rows = r.message.slot_booking || [];

                if (r.message.custom_project) {
                    frm.set_value('custom_project_id', r.message.custom_project);
                }
                if (r.message.custom_project_name) {
                    frm.set_value('custom_project_name', r.message.custom_project_name);
                }

                let future_rows = rows; // Remove past-date filter

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

                if (future_rows.length > 0 && future_rows[0].slot_booking_date) {
                    let date = new Date(future_rows[0].slot_booking_date);
                    frm.set_value('month', date.toLocaleString('en-US', { month: 'long' }));
                }

                frm.clear_table('slot_opening_table');
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

                frm.clear_table('custom_batch_details');
                future_rows.forEach(function (slot) {
                    let total = parseInt(slot.booked_slots) || 0;
                    for (let i = 0; i < total; i++) {
                        let child = frm.add_child('custom_batch_details');
                        child.slot_opening_id = frm.doc.slot_opening;
                        child.slot_booking_date = slot.slot_booking_date;
                        child.reason = slot.reason;
                    }
                });
                frm.refresh_field('custom_batch_details');

                frappe.show_alert({
                    message: `✅ Slots loaded from ${frm.doc.slot_opening}`,
                    indicator: 'green'
                }, 4);
            }
        });
    },

    refresh: function (frm) {
        load_used_slots(frm);

        if (frm.is_new() && frm.doc.slot_opening) {
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
                    "batch_creation": frm.doc.name
                };
                frappe.set_route('List', 'Batches Planned');
            });
        }

        setup_eye_buttons(frm);
    },

    after_save: function (frm) {
        // ── Fix Batch BOM Store after Edit keys after save ──
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
                method: 'custom_batch_planning.custom_batch_planning.doctype.batch_creation.batch_creation.create_batches_planned',
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
        let row = locals[cdt][cdn];
        if (!row.batch_type || !row.slot_opening_id) return;

        if (!frm._counter_queue) frm._counter_queue = Promise.resolve();

        frm._counter_queue = frm._counter_queue.then(function () {
            return new Promise(function (resolve) {
                // Collect already assigned IDs in current doc
                let assigned_ids = (frm.doc.custom_batch_details || [])
                    .filter(r => r.batch_planning_id && r.name !== row.name)
                    .map(r => r.batch_planning_id);

                frappe.call({
                    method: 'custom_batch_planning.custom_batch_planning.doctype.batch_creation.batch_creation.get_next_batch_counter',
                    args: {
                        slot_opening_id: row.slot_opening_id,
                        batch_type: row.batch_type,
                        exclude_ids: JSON.stringify(assigned_ids)
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.model.set_value(cdt, cdn, 'batch_planning_id', r.message);
                        }
                        resolve();
                    }
                });
            });
        });
    },
    finished_item: function (frm, cdt, cdn) {
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
        setup_eye_buttons(frm);
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
// existing_doc_name = name of Batch BOM Store after Edit doc if exists, else null
// ─────────────────────────────────────────────
function render_bom_dialog(frm, cdt, cdn, bom_name, batch_type, is_readonly, final_items, existing_doc_name) {

    let fields = [];

    if (!is_readonly) {
        fields.push({
            fieldtype: 'HTML',
            fieldname: 'toolbar_html',
            options: get_toolbar_html({ non_stock: false, moq: false, safety: false })
        });
    }
    else {
        let banner_html = `<div style="background:#fff8e1;border:1px solid #ffe082;
            border-radius:4px;padding:8px 12px;margin-bottom:10px;
            font-size:12px;color:#795548;">
            🔒 BOM is read-only. Items cannot be edited.
        </div>`;

        // Add checkboxes for Manufacturing
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

    // ── Checkbox handler — Manufacturing only ──
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
                method: 'custom_batch_planning.custom_batch_planning.doctype.batch_creation.batch_creation.get_item_details_for_bom',
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
        method: 'custom_batch_planning.custom_batch_planning.doctype.batch_creation.batch_creation.get_valid_slot_openings',
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
// Eye Button Setup
// ─────────────────────────────────────────────
function setup_eye_buttons(frm) {
    if (frm._bom_observer) {
        frm._bom_observer.disconnect();
        frm._bom_observer = null;
    }

    let grid = frm.fields_dict['custom_batch_details'] &&
        frm.fields_dict['custom_batch_details'].grid;

    if (!grid) return;

    grid.cannot_add_rows = true;
    grid.wrapper.find('.grid-add-row').hide();

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