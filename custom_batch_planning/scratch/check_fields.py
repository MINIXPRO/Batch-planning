import frappe

def run():
    fields = [f.fieldname for f in frappe.get_meta("Stock Entry Detail").fields if "project" in f.fieldname or "batch_planning" in f.fieldname]
    print(fields)
