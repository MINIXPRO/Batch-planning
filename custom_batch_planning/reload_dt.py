import frappe

def run():
    frappe.reload_doc("custom_batch_planning", "doctype", "batch_planning_item_issue")
    frappe.db.commit()
    print("DocType reloaded")
