import frappe

def run():
    print("Stock Entry fields:")
    meta = frappe.get_meta("Stock Entry")
    print(sorted([f.fieldname for f in meta.fields]))

    print("\nStock Entry Detail fields:")
    meta_detail = frappe.get_meta("Stock Entry Detail")
    print(sorted([f.fieldname for f in meta_detail.fields]))

