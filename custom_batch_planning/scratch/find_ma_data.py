import frappe

def run():
    print("=== Material Allocation documents ===")
    docs = frappe.get_all("Material Allocation", fields=["*"], limit=5)
    for d in docs:
        print(dict(d))
        print("--- Child items ---")
        items = frappe.get_all("Material Allocation Item", filters={"parent": d.name}, fields=["*"])
        for item in items:
            print(dict(item))
