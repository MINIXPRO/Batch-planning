import frappe
def execute():
    try:
        exists = frappe.db.exists("DocType", "Inventory Dimension")
        print(f"Inventory Dimension DocType exists: {exists}")
        if exists:
            meta = frappe.get_meta("Inventory Dimension")
            print(f"Number of fields: {len(meta.fields)}")
            for f in meta.fields[:10]:
                print(f"- {f.fieldname}: {f.fieldtype}")
        else:
            print("The Inventory Dimension DocType is not present in this ERPNext version.")
    except Exception as e:
        print(f"Error while checking: {e}")
