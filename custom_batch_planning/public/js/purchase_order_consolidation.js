frappe.ui.form.on("Purchase Order", {
    onload: function (frm) {
        if (!frm.is_new()) return;

        let items = frm.doc.items || [];
        if (items.length <= 1) return;

        let grouped = {};
        items.forEach(item => {
            let key = item.item_code;
            if (!grouped[key]) {
                grouped[key] = [];
            }
            grouped[key].push(item);
        });

        let new_items = [];
        let modified = false;

        for (let item_code in grouped) {
            let rows = grouped[item_code];
            if (rows.length === 1) {
                new_items.push(rows[0]);
            } else {
                modified = true;
                let target = rows[0];
                let total_qty = 0;

                rows.forEach(r => {
                    total_qty += parseFloat(r.qty) || 0;
                });

                target.qty = total_qty;
                target.stock_qty = total_qty * (parseFloat(target.conversion_factor) || 1);
                target.amount = target.qty * (parseFloat(target.rate) || 0);

                new_items.push(target);
            }
        }

        if (modified) {
            frm.clear_table("items");
            new_items.forEach(d => {
                let row = frm.add_child("items");
                let row_name = row.name;
                let row_idx = row.idx;
                Object.assign(row, d);
                row.name = row_name;
                row.idx = row_idx;
            });
            frm.refresh_field("items");
        }

        if (!frm.doc.custom_batch_planning_no) {
            for (let item of frm.doc.items || []) {
                if (item.material_request) {
                    frappe.db.get_value("Material Request", item.material_request, "custom_batch_planning_no")
                        .then(r => {
                            if (r && r.message && r.message.custom_batch_planning_no && !frm.doc.custom_batch_planning_no) {
                                frm.set_value("custom_batch_planning_no", r.message.custom_batch_planning_no);
                            }
                        });
                    break;
                }
            }
        }
    }
});
