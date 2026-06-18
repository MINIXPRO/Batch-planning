import frappe

def run():
    doc = frappe.get_doc("Material Allocation", "MA-SO-26-08-002-MFG-01-01")
    print("Document keys:")
    for k in sorted(doc.as_dict().keys()):
        print(f"{k}: {doc.get(k)}")
