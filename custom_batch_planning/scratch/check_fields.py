import frappe

def execute():
    doctypes = ["Purchase Receipt", "Purchase Receipt Item", "Purchase Order", "Purchase Order Item", "Purchase Invoice", "Purchase Invoice Item"]
    for dt in doctypes:
        meta = frappe.get_meta(dt)
        for field in meta.fields:
            if "batch" in field.fieldname.lower():
                print(f"[{dt}] {field.fieldname} (Label: {field.label}) - Type: {field.fieldtype} - Options: {field.options} - Custom: {field.is_custom_field}")
