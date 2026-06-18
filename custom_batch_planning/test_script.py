import frappe

def run():
    frappe.init(site="site_local")
    frappe.connect()
    
    print("Batches Planned fields:")
    meta = frappe.get_meta("Batches Planned")
    for f in meta.fields:
        if f.fieldtype == "Link":
            print(f"- {f.fieldname} -> {f.options}")
