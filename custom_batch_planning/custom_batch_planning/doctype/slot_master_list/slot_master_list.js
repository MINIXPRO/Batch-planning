frappe.ui.form.on('Slot Master List', {

    onload: function (frm) {
        if (frm.is_new()) {
            frm.set_value('created_by', frappe.session.user);
            frm.set_value('naming_series', 'SM-.YY.MM.-.####');
        }
    },

    employee_function: function (frm) {
        frm.set_value('custom_project', '');

        if (!frm.doc.employee_function) return;

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
    },

    custom_project: function (frm) {
        if (!frm.doc.employee_function) {
            frappe.msgprint({ title: '⚠️ Required', message: 'Please select Employee Function first.', indicator: 'orange' });
            frm.set_value('custom_project', '');
            return;
        }
    },


    batch_end_date: function (frm) {

        if (!frm.doc.batch_start_date) {
            frappe.msgprint({ title: '⚠️ Required', message: 'Please select Batch Start Date first.', indicator: 'orange' });
            frm.set_value('batch_end_date', '');
            return;
        }
        calculate_totals(frm);
    },

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

        let today = frappe.datetime.nowdate();

        if (!frm.is_new() && frm.doc.docstatus === 1
            && frm.doc.batch_end_date && frm.doc.batch_end_date >= today) {

            frm.add_custom_button('📋 Create Slot Opening', function () {
                frappe.model.with_doctype('Slot Opening', function () {
                    let new_doc = frappe.model.get_new_doc('Slot Opening');
                    new_doc.employee_function = frm.doc.employee_function;
                    new_doc.slot_master = frm.doc.name;
                    new_doc.batch_capacity = frm.doc.batch_capacity;
                    frappe.set_route('Form', 'Slot Opening', new_doc.name);
                });
            });
        }
    },

    before_save: function (frm) {
        if (!frm.doc.naming_series) {
            frm.set_value('naming_series', 'SM-.YY.MM.-.####');
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