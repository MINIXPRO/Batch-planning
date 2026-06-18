import frappe

def run():
    print("Purchase Receipt fields:")
    meta_pr = frappe.get_meta("Purchase Receipt")
    fields_pr = sorted([f.fieldname for f in meta_pr.fields])
    print(fields_pr)

    print("\nPurchase Receipt Item fields:")
    meta_pri = frappe.get_meta("Purchase Receipt Item")
    fields_pri = sorted([f.fieldname for f in meta_pri.fields])
    print(fields_pri)

