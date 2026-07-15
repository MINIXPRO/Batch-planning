import frappe

def run():
    sles = frappe.db.sql("""
        SELECT name, voucher_detail_no, batch_planning_id 
        FROM `tabStock Ledger Entry` 
        WHERE voucher_no = 'MAT-STE-2026-00948'
    """, as_dict=True)
    for sle in sles:
        print(f"SLE {sle.name}: detail={sle.voucher_detail_no}, bp={sle.batch_planning_id}")
