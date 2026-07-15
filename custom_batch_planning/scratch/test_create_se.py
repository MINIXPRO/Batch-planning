import frappe

def run():
    print("Creating a new Material Transfer Stock Entry to test hooks...")
    
    se = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Transfer",
        "purpose": "Material Transfer",
        "items": [
            {
                "item_code": "CN02010007",
                "qty": 1.0,
                "s_warehouse": "VP-LTP-MFG-001",
                "t_warehouse": "LC01-AR01-FL01-RM028 - MCPL",
                "batch_planning_id": "BP-26-07-002",
                "project": "PLTP-2025-0001"
            }
        ]
    })
    se.flags.ignore_mandatory = True
    se.insert()
    print(f"Created SE: {se.name}")
    se.submit()
    print("Submitted.")
    
    # Check the DB for the target SLE
    sles = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": se.name}, fields=["name", "actual_qty", "warehouse", "batch_planning_id", "project"])
    for sle in sles:
        print(f"SLE: {sle.name}, Qty: {sle.actual_qty}, WH: {sle.warehouse}, BP: {sle.batch_planning_id}, Proj: {sle.project}")

    # Now check error logs to see what map_sle_fields logged
    logs = frappe.get_all("Error Log", filters={"method": "map_stock_entry_fields hook"}, fields=["error"], limit=2, order_by="creation desc")
    for log in logs:
        print("Log from map_stock_entry_fields:", log.error)
        
    logs = frappe.get_all("Error Log", filters={"method": "map_sle_fields hook executed"}, fields=["error"], limit=2, order_by="creation desc")
    for log in logs:
        print("Log from map_sle_fields:", log.error)
