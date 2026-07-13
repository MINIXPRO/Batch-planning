import frappe
def execute():
    try:
        sle_meta = frappe.get_meta("Stock Ledger Entry")
        for f in sle_meta.fields:
            if f.fieldname == "batch_planning_id":
                print(f"SLE field: {f.fieldname}, options: {f.options}, label: {f.label}")
        pr_meta = frappe.get_meta("Purchase Receipt Item")
        for f in pr_meta.fields:
            if f.fieldname == "batch_planning_id":
                print(f"PR Item field: {f.fieldname}, options: {f.options}, label: {f.label}")
    except Exception as e:
        print(f"Error: {e}")
