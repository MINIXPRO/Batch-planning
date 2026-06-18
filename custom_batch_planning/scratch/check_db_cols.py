import frappe

def run():
    print("Columns in tabMaterial Allocation:")
    cols = frappe.db.sql("DESC `tabMaterial Allocation`", as_dict=True)
    for c in cols:
        print(f"{c.Field} | {c.Type}")

    print("\nColumns in tabMaterial Allocation Item:")
    cols_item = frappe.db.sql("DESC `tabMaterial Allocation Item`", as_dict=True)
    for c in cols_item:
        print(f"{c.Field} | {c.Type}")
