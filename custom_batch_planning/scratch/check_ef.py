import frappe

def run():
    meta = frappe.get_meta("Employee Function")
    for f in meta.fields:
        if f.fieldtype == "Table":
            print(f"Table Fieldname: {f.fieldname} | Options: {f.options}")
