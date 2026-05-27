frappe.ui.form.on('Material Request', {
    refresh: function (frm) {
        if (!frm.is_new()) return;
        const raw = localStorage.getItem('mr_prefill');
        if (!raw) return;
        const data = JSON.parse(raw);
        localStorage.removeItem('mr_prefill');

        frm.set_value('material_request_type', 'Purchase');
        frm.set_value('custom_batch_no', data.batch_nos);
        frm.set_value('custom_employee_function', data.employee_function);
        frm.clear_table('items');

        data.items.forEach(item => {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Item',
                    filters: { name: item.item_code },
                    fieldname: ['is_purchase_item']
                },
                callback: function (r) {
                    if (r.message && r.message.is_purchase_item) {
                        let row = frm.add_child('items');
                        row.item_code = item.item_code;
                        row.qty = item.qty;
                        row.uom = item.uom;
                        row.schedule_date = item.schedule_date;
                        frm.refresh_field('items');
                    }
                }
            });
        });
    }
});