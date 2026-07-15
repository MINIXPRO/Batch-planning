import frappe
from custom_batch_planning.api.pr_integration import map_sle_fields

def run():
    print("--- Testing map_sle_fields ---")
    se_name = "MAT-STE-2026-00947"
    sles = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": se_name}, fields=["name", "voucher_type", "voucher_detail_no", "actual_qty", "batch_planning_id", "project"])
    
    for sle in sles:
        print(f"\nSLE: {sle.name}, Qty: {sle.actual_qty}, Detail No: {sle.voucher_detail_no}")
        doc = frappe.get_doc("Stock Ledger Entry", sle.name)
        
        # Reset custom fields to test hook
        doc.batch_planning_id = None
        doc.project = None
        
        print("Before hook:", doc.batch_planning_id, doc.project)
        map_sle_fields(doc)
        print("After hook:", doc.batch_planning_id, doc.project)
        
