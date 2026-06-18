import frappe
from frappe.utils import flt
from custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning import get_batch_wise_shortages
from custom_batch_planning.api.po_integration import validate_purchase_order

def run():
    print("Starting Integration Tests...")
    
    # Start transaction
    frappe.db.begin()
    
    try:
        # 1. Fetch some setup data
        suppliers = frappe.db.get_all("Supplier", limit=5)
        print("Existing Suppliers:", [s.name for s in suppliers])
        
        items = frappe.db.get_all("Item", limit=5)
        print("Existing Items:", [i.name for i in items])
        
        # Make sure default supplier exists or create/update one to avoid currency error
        supplier_name = None
        if suppliers:
            supplier_name = suppliers[0].name
            # Ensure it has default_currency set
            frappe.db.set_value("Supplier", supplier_name, "default_currency", "INR")
        else:
            supplier = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": "Test Supplier",
                "supplier_group": "All Supplier Groups",
                "default_currency": "INR"
            })
            supplier.insert(ignore_permissions=True)
            supplier_name = supplier.name
            
        print("Selected Supplier:", supplier_name)

        # 2. Create Batch Planning Document
        print("Creating test Batch Planning...")
        bp_doc = frappe.get_doc({
            "doctype": "Batch Planning",
            "custom_employee_function": "VP-LTP-POC-003",
            "month": "June",
            "custom_batch_details": [
                {
                    "batch_type": "Manufacturing",
                    "finished_item": "FG01010004",
                    "bom_list": "BOM-FG01010004-001",
                    "batch_planning_id": "BATCH-REF-TEST-1",
                    "status": "Approved"
                },
                {
                    "batch_type": "Manufacturing",
                    "finished_item": "FG01010004",
                    "bom_list": "BOM-FG01010004-001",
                    "batch_planning_id": "BATCH-REF-TEST-2",
                    "status": "Approved"
                }
            ]
        })
        bp_doc.insert(ignore_permissions=True)
        print("Batch Planning created:", bp_doc.name)
        
        # 3. Test shortages calculation
        print("Running get_batch_wise_shortages...")
        shortages = get_batch_wise_shortages(bp_doc.name)
        print(f"Calculated shortages (count={len(shortages)}):")
        for s in shortages:
            print(f"  Item: {s['item_code']}, Qty: {s['qty']}, BP: {s['custom_batch_planning_no']}, Ref: {s['custom_batch_reference']}")
            assert s["custom_batch_planning_no"] == bp_doc.name, "Batch Planning name mismatch"
            assert s["custom_batch_reference"] in ["BATCH-REF-TEST-1", "BATCH-REF-TEST-2"], "Batch Reference mismatch"
            
        # 4. Test Purchase Order Consolidation logic
        print("Testing Purchase Order Consolidation...")
        po_doc = frappe.get_doc({
            "doctype": "Purchase Order",
            "supplier": supplier_name,
            "transaction_date": frappe.utils.today(),
            "schedule_date": frappe.utils.today(),
            "company": frappe.db.get_single_value("Global Defaults", "default_company") or "MCPL",
            "items": [
                {
                    "item_code": "RM/000701",
                    "qty": 10.0,
                    "rate": 100.0,
                    "uom": "Nos",
                    "warehouse": "Stores - MCPL",
                    "custom_batch_planning_no": bp_doc.name
                },
                {
                    "item_code": "RM/000701",
                    "qty": 20.0,
                    "rate": 100.0,
                    "uom": "Nos",
                    "warehouse": "Stores - MCPL",
                    "custom_batch_planning_no": bp_doc.name
                },
                {
                    "item_code": "RM/000702",
                    "qty": 5.0,
                    "rate": 50.0,
                    "uom": "Nos",
                    "warehouse": "Stores - MCPL",
                    "custom_batch_planning_no": "OTHER-BP-001"
                }
            ]
        })
        
        # Trigger validation
        validate_purchase_order(po_doc, None)
        
        # Check consolidated items
        print("PO Items after consolidation:")
        for item in po_doc.items:
            print(f"  Item: {item.item_code}, Qty: {item.qty}, Rate: {item.rate}, Amount: {item.amount}, BP: {item.custom_batch_planning_no}")
            
        assert len(po_doc.items) == 2, f"Expected 2 items, got {len(po_doc.items)}"
        
        item1 = next(item for item in po_doc.items if item.item_code == "RM/000701")
        assert item1.qty == 30.0, f"Expected Qty 30.0 for RM/000701, got {item1.qty}"
        assert item1.amount == 3000.0, f"Expected Amount 3000.0, got {item1.amount}"
        assert item1.custom_batch_planning_no == bp_doc.name, f"Expected BP no {bp_doc.name}, got {item1.custom_batch_planning_no}"
        
        # Header Batch Planning No should list unique non-empty bp_nos
        expected_header_bp = f"{bp_doc.name}, OTHER-BP-001"
        assert po_doc.custom_batch_planning_no == expected_header_bp, f"Expected header BP '{expected_header_bp}', got '{po_doc.custom_batch_planning_no}'"
        
        print("ALL TESTS PASSED SUCCESSFULLY!")
        
    finally:
        # Rollback so no test data remains in the database
        frappe.db.rollback()
        print("Database transaction rolled back.")
