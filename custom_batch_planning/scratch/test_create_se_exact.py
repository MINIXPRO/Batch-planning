import frappe

def run():
    print("Creating a new Material Transfer Stock Entry to simulate JS flow...")
    
    se = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Transfer",
        "purpose": "Material Transfer",
        "custom_batch_planning_no": "BP-26-07-002",
        "items": [
            {
                "item_code": "CN02010007",
                "qty": 1.0,
                "s_warehouse": "VP-LTP-MFG-001",
                "t_warehouse": "LC01-AR01-FL01-RM028 - MCPL",
                "batch_planning_id": "BP-26-07-002",
                "project": "PLTP-2025-0001",
                # The JS did NOT pass to_batch_planning_id
            }
        ]
    })
    se.flags.ignore_mandatory = True
    se.insert()
    print(f"Created SE: {se.name}")
    
    # Do not submit yet. Check DB!
    db_items = frappe.db.get_all("Stock Entry Detail", filters={"parent": se.name}, fields=["batch_planning_id", "to_batch_planning_id"])
    print(f"DB Items: {db_items}")
