import frappe
def execute():
    entries = frappe.db.get_all("Stock Ledger Entry", filters={"voucher_no": "PR-2026-2027-00010"}, fields=["name", "item_code", "batch_planning_id", "project", "actual_qty", "warehouse", "voucher_type"])
    for entry in entries:
        print(entry)
