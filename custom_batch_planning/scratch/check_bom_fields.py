import frappe

def run():
    print("=== BOM Fields ===")
    meta = frappe.get_meta("BOM")
    for f in meta.fields:
        if "project" in f.fieldname or f.fieldtype in ["Table", "Link"]:
            print(f"Fieldname: {f.fieldname}, Label: {f.label}, Fieldtype: {f.fieldtype}, Options: {f.options}")
