frappe.ui.form.on("Purchase Order", {
    onload: function (frm) {
        if (!frm.is_new()) return;
        
        let items = frm.doc.items || [];
        if (items.length <= 1) return;
        
        // Group items in frm.doc.items
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
                let bp_nos = [];
                
                rows.forEach(r => {
                    total_qty += parseFloat(r.qty) || 0;
                    if (r.custom_batch_planning_no) {
                        r.custom_batch_planning_no.split(",").forEach(x => {
                            if (x.trim()) bp_nos.push(x.trim());
                        });
                    }
                });
                
                target.qty = total_qty;
                target.stock_qty = total_qty * (parseFloat(target.conversion_factor) || 1);
                target.amount = target.qty * (parseFloat(target.rate) || 0);
                
                // Remove duplicates from arrays
                bp_nos = [...new Set(bp_nos)].sort();
                
                target.custom_batch_planning_no = bp_nos.join(", ");
                
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
            
            // Set parent custom_batch_planning_no
            let all_bp_nos = [];
            new_items.forEach(item => {
                if (item.custom_batch_planning_no) {
                    item.custom_batch_planning_no.split(",").forEach(x => {
                        if (x.trim()) all_bp_nos.push(x.trim());
                    });
                }
            });
            all_bp_nos = [...new Set(all_bp_nos)].sort();
            frm.set_value("custom_batch_planning_no", all_bp_nos.join(", "));
            
            frm.refresh_field("items");
        }
    }
});
