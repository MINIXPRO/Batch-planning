import frappe

def run():
    print("Testing map_sle_fields hook fallback...")
    
    # Temporarily disable map_stock_entry_fields to ensure to_batch_planning_id remains None
    frappe.get_hooks()["doc_events"]["Stock Entry"]["before_save"].remove("custom_batch_planning.api.pr_integration.map_stock_entry_fields")
    
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
    se.submit()
    
    # Check DB for to_batch_planning_id
    detail = frappe.db.get_value("Stock Entry Detail", {"parent": se.name}, "to_batch_planning_id")
    print(f"SE Detail to_bp: {detail}")
    
    # Check SLEs
    sles = frappe.db.sql("""
        SELECT name, warehouse, actual_qty, batch_planning_id 
        FROM `tabStock Ledger Entry` 
        WHERE voucher_no = %s
    """, se.name, as_dict=True)
    
    for sle in sles:
        print(f"SLE {sle.name}, WH {sle.warehouse}, Qty {sle.actual_qty}, BP {sle.batch_planning_id}")
        
    # Check Logs
    logs = frappe.get_all("Error Log", filters={"method": "map_sle_fields hook executed"}, fields=["error"], limit=2, order_by="creation desc")
    for log in logs:
        print("Log:", log.error)
