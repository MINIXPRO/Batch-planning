import frappe

def run():
    fields = frappe.get_meta("Batch Planning Item Issue").fields
    for f in fields:
        print(f.fieldname, f.fieldtype)

run()
