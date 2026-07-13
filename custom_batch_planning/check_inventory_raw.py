import frappe

def execute():
    try:
        exists = frappe.db.exists("DocType", "Inventory Dimension")
        print(f"frappe.db.exists('DocType', 'Inventory Dimension') => {exists}")
        opt = frappe.get_meta("Stock Ledger Entry").get_field("batch_planning_id").options
        print(f"frappe.get_meta('Stock Ledger Entry').get_field('batch_planning_id').options => {opt}")
    except Exception as e:
        print(f"Error: {e}")
