import frappe
from frappe.utils import today

def run():
    pr = frappe.new_doc("Purchase Receipt")
    pr.supplier = frappe.db.get_value("Supplier", {"disabled": 0})
    if not pr.supplier:
        pr.supplier = "Test Supplier"
        if not frappe.db.exists("Supplier", pr.supplier):
            frappe.get_doc({"doctype": "Supplier", "supplier_name": pr.supplier, "supplier_group": "All Supplier Groups"}).insert(ignore_permissions=True)
    
    pr.company = frappe.db.get_value("Company", None, "name")
    
    pr.append("items", {
        "item_code": "CN05010006",
        "qty": 5,
        "rate": 100,
        "warehouse": frappe.db.get_value("Warehouse", {"is_group": 0}),
        "use_serial_batch_fields": 1
    })
    
    pr.insert(ignore_permissions=True)
    pr.submit()
    
    print("PR Created:", pr.name)
    for d in pr.items:
        print("Item:", d.item_code, "Batch:", d.batch_no)
        print("Bundle:", d.serial_and_batch_bundle)
