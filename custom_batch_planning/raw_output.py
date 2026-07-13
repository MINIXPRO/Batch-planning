import frappe

def execute():
    # Direct raw output, no extra text
    print(frappe.db.exists("DocType", "Inventory Dimension"))
    print(frappe.get_meta("Stock Ledger Entry").get_field("batch_planning_id").options)
