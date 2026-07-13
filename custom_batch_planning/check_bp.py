import frappe
def execute():
    exists = frappe.db.exists("Batch Planning", "BP-26-08-003")
    print(f"Record Exists: {exists}")
