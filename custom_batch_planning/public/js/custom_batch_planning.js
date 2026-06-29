// Global Client Script for Custom Batch Planning App
// This prevents negative values in all numeric fields for any doctype belonging to this app.

frappe.ui.form.on("*", {
    refresh: function(frm) {
        // Only apply to this app's doctypes
        if (frm.meta.module !== "Custom Batch Planning" && frm.meta.module !== "custom_batch_planning") {
            return;
        }
        
        frm.meta.fields.forEach(function(df) {
            if (["Int", "Float", "Currency", "Percent"].includes(df.fieldtype)) {
                // Attach onchange handler directly to the input element if it exists
                if (frm.fields_dict[df.fieldname] && frm.fields_dict[df.fieldname].input) {
                    $(frm.fields_dict[df.fieldname].input).on("change", function() {
                        if (frm.doc[df.fieldname] < 0) {
                            frm.set_value(df.fieldname, 0);
                            frappe.show_alert({
                                message: df.label + " cannot be negative.", 
                                indicator: "red"
                            });
                        }
                    });
                }
            }
        });
    },
    validate: function(frm) {
        // Only apply to this app's doctypes
        if (frm.meta.module !== "Custom Batch Planning" && frm.meta.module !== "custom_batch_planning") {
            return;
        }

        frm.meta.fields.forEach(function(df) {
            if (["Int", "Float", "Currency", "Percent"].includes(df.fieldtype)) {
                if (frm.doc[df.fieldname] < 0) {
                    frappe.throw(df.label + " cannot be negative.");
                }
            }
        });
    }
});
