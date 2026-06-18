import frappe

def run():
    print("=== Batch Planning Fields ===")
    meta = frappe.get_meta("Batch Planning")
    fields = [f.fieldname for f in meta.fields if "project" in f.fieldname]
    print("Batch Planning project fields:", fields)

    print("\n=== Batch Planning Detail Fields ===")
    meta_detail = frappe.get_meta("Batch Planning Detail")
    fields_detail = [f.fieldname for f in meta_detail.fields if "project" in f.fieldname]
    print("Batch Planning Detail project fields:", fields_detail)
