import frappe

def run():
    print(frappe.db.get_value("Stock Entry", "MAT-STE-2026-00947", "creation"))
