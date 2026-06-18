import frappe

def run():
    print("=== BOMs with Projects ===")
    boms = frappe.db.get_list(
        "BOM",
        filters={"project": ["!=", ""]},
        fields=["name", "item", "project", "docstatus", "is_active"],
        limit=15
    )
    for bom in boms:
        print(bom)
