import frappe

def run():
    efs = frappe.db.get_all("Employee Function")
    for ef in efs:
        doc = frappe.get_doc("Employee Function", ef.name)
        stores = [r.store_warehouse for r in doc.table_bukm or [] if r.store_warehouse]
        labs = [r.lab_warehouse for r in doc.table_szrn or [] if r.lab_warehouse]
        if stores or labs:
            print(f"EF: {doc.name} | Stores: {stores} | Labs: {labs}")
