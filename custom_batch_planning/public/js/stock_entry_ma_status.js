frappe.ui.form.on("Stock Entry", {
    on_submit: function (frm) {
        if (frm.doc.custom_material_allocation) {
            frappe.call({
                method: "custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation.on_stock_entry_submit",
                args: { stock_entry_name: frm.doc.name },
                callback: function (r) {
                    frappe.show_alert({
                        message: "✅ Material Allocation status updated to Stock Entry Done.",
                        indicator: "green"
                    });
                }
            });
        }
    }
});
