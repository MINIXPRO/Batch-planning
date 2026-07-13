import frappe

def check_qty():
    res = frappe.db.sql("""
        SELECT actual_qty, voucher_type, voucher_no, batch_planning_id, project, employee_function, warehouse
        FROM `tabStock Ledger Entry`
        WHERE item_code = 'CN02010004'
        AND is_cancelled = 0
    """, as_dict=True)

    for r in res:
        print(r)
