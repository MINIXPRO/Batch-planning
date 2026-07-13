import frappe
def execute():
    try:
        cf = frappe.get_doc("Custom Field", "Stock Ledger Entry-batch_planning_id")
        cf.options = "Batch Planning"
        cf.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated Custom Field options successfully.")
    except Exception as e:
        print(f"Error: {e}")
