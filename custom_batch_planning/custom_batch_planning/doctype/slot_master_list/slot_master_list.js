frappe.ui.form.on('Slot Master List', {

    onload: function (frm) {
        if (frm.is_new()) {
            frm.set_value('created_by', frappe.session.user);
            frm.set_value('naming_series', 'SM-.YY.-.MM.-.#####');
        }
    },

    employee_function: function (frm) {
        frm.set_value('custom_project', '');

        if (!frm.doc.employee_function) return;

        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Employee Function',
                name: frm.doc.employee_function
            },
            callback: function (r) {
                if (r.message && r.message.project_list) {
                    let allowed_ids = r.message.project_list.map(p => p.projects.trim());

                    frm.set_query('custom_project', function () {
                        return {
                            filters: [['name', 'in', allowed_ids]]
                        };
                    });
                }
            }
        });
    },

    batch_start_date: function (frm) { calculate_totals(frm); },
    batch_end_date: function (frm) { calculate_totals(frm); },
    batch_capacity: function (frm) { calculate_totals(frm); },

    refresh: function (frm) {
        if (frm.doc.employee_function) {
            frappe.call({
                method: 'frappe.client.get',
                args: { doctype: 'Employee Function', name: frm.doc.employee_function },
                callback: function (r) {
                    if (r.message && r.message.project_list) {
                        let allowed_ids = r.message.project_list.map(p => p.projects.trim());
                        frm.set_query('custom_project', function () {
                            return { filters: [['name', 'in', allowed_ids]] };
                        });
                    }
                }
            });
        }

        if (!frm.is_new() && frm.doc.docstatus === 1) {
            frm.add_custom_button('📋 Create Slot Opening', function () {
                frappe.model.with_doctype('Slot Opening', function () {
                    let new_doc = frappe.model.get_new_doc('Slot Opening');

                    new_doc.slot_master = frm.doc.name;         // ✅ keep this
                    new_doc.employee_function = frm.doc.employee_function;
                    new_doc.custom_project = frm.doc.custom_project;
                    new_doc.batch_start_date = frm.doc.batch_start_date;
                    new_doc.batch_end_date = frm.doc.batch_end_date;
                    new_doc.total_batch_capacity = frm.doc.custom_total_capacity;

                    let start = frappe.datetime.str_to_obj(frm.doc.batch_start_date);
                    let end = frappe.datetime.str_to_obj(frm.doc.batch_end_date);
                    let current = new Date(start);
                    new_doc.slot_booking = [];

                    while (current <= end) {
                        let row = frappe.model.add_child(new_doc, 'Slot Booking CT', 'slot_booking');
                        row.slot_booking_date = frappe.datetime.obj_to_str(current);
                        row.batch_capacity = frm.doc.batch_capacity;
                        current.setDate(current.getDate() + 1);
                    }

                    // ✅ This ensures slot_master is applied after the form loads
                    frappe.route_options = {
                        slot_master: frm.doc.name
                    };

                    frappe.set_route('Form', 'Slot Opening', new_doc.name);
                });
            });
        }
    },

    before_save: function (frm) {
        if (!frm.doc.naming_series) {
            frm.set_value('naming_series', 'SM-.YY.-.MM.-.#####');
        }
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    const start = frm.doc.batch_start_date;
    const end = frm.doc.batch_end_date;
    const capacity_per_day = frm.doc.batch_capacity;

    if (start && end) {
        const start_date = frappe.datetime.str_to_obj(start);
        const end_date = frappe.datetime.str_to_obj(end);
        const total_days = frappe.datetime.get_day_diff(end_date, start_date) + 1;

        if (total_days < 0) {
            frappe.msgprint(__('Batch End Date cannot be earlier than Start Date.'));
            frm.set_value('custom_total_days', 0);
            frm.set_value('custom_total_capacity', 0);
            return;
        }

        frm.set_value('custom_total_days', total_days);
        frm.set_value('custom_total_capacity', capacity_per_day ? total_days * capacity_per_day : 0);
    }
}