import frappe

def run():
    print("=== All Item Fields ===")
    meta = frappe.get_meta("Item")
    for f in meta.fields:
        if f.fieldtype in ["Table", "Link"]:
            print(f"Fieldname: {f.fieldname}, Label: {f.label}, Fieldtype: {f.fieldtype}, Options: {f.options}")
