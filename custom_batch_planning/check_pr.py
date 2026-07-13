import frappe
def execute():
    try:
        pr = frappe.get_doc("Purchase Receipt", "PR-2026-2027-00013")
        for item in pr.items:
            print(f"PR Item {item.item_code} -> batch_planning_id: {repr(item.get('batch_planning_id'))}, custom_batch_planning_no: {repr(item.get('custom_batch_planning_no'))}")
    except Exception as e:
        print(f"Could not load PR: {e}")
