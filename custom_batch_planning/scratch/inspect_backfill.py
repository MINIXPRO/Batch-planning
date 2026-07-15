import frappe

def run():
    print("--- 1. Inspecting BP-29-08-001 ---")
    bp = frappe.db.get_value("Batch Planning", "BP-29-08-001", ["name", "workflow_state", "project", "custom_employee_function", "creation"], as_dict=True)
    if bp:
        print(bp)
    else:
        print("BP-29-08-001 not found.")

    print("\n--- 2. Inspecting Asymmetric Stock Entries (00939 to 00942) ---")
    se_names = ["MAT-STE-2026-00939", "MAT-STE-2026-00940", "MAT-STE-2026-00941", "MAT-STE-2026-00942"]
    
    for se_name in se_names:
        print(f"\nStock Entry: {se_name}")
        se = frappe.db.get_value("Stock Entry", se_name, ["stock_entry_type", "purpose", "custom_material_allocation"], as_dict=True)
        print(se)
        
        details = frappe.db.sql("""
            SELECT name, item_code, batch_planning_id, project, s_warehouse, t_warehouse, qty, transfer_qty 
            FROM `tabStock Entry Detail` 
            WHERE parent = %s 
        """, (se_name,), as_dict=True)
        print("Details:")
        for d in details:
            print(f"  {d.name}: Item {d.item_code}, s_wh: {d.s_warehouse}, t_wh: {d.t_warehouse}, qty: {d.qty}, bp: {d.batch_planning_id}, proj: {d.project}")
            
        sles = frappe.db.sql("""
            SELECT name, item_code, batch_planning_id, project, warehouse, actual_qty
            FROM `tabStock Ledger Entry` 
            WHERE voucher_type = 'Stock Entry' 
            AND voucher_no = %s 
        """, (se_name,), as_dict=True)
        print("SLEs:")
        for sle in sles:
            print(f"  {sle.name}: Item {sle.item_code}, wh: {sle.warehouse}, qty: {sle.actual_qty}, bp: {sle.batch_planning_id}, proj: {sle.project}")
