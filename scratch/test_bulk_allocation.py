import frappe
from custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning import create_bulk_material_allocations
from frappe.utils import flt

def run():
    print("Running Test for Bulk Material Allocation Creation...")
    frappe.db.begin()
    try:
        # Step 1: Find a valid BOM
        bom_list = frappe.db.get_all("BOM", filters={"docstatus": 1, "is_active": 1}, fields=["name", "item"], limit=1)
        if not bom_list:
            print("No active BOM found in DB. Exiting test.")
            return
        
        bom_name = bom_list[0].name
        finished_item = bom_list[0].item
        print(f"Found BOM: {bom_name} for Finished Item: {finished_item}")
        
        # Step 2: Find a valid Employee Function with store warehouse configured
        ef_list = frappe.db.get_all("Employee Function", limit=20)
        ef_name = None
        warehouse = None
        for ef in ef_list:
            ef_doc = frappe.get_doc("Employee Function", ef.name)
            for row in ef_doc.table_bukm or []:
                if row.store_warehouse:
                    ef_name = ef.name
                    warehouse = row.store_warehouse
                    break
            if ef_name:
                break
                
        if not ef_name:
            print("No Employee Function with Store Warehouse found. Exiting test.")
            return
            
        print(f"Using Employee Function: {ef_name} and Store Warehouse: {warehouse}")
        
        # Step 3: Get BOM items and ensure at least one has stock (to test stock eligibility)
        bom_doc = frappe.get_doc("BOM", bom_name)
        bom_items = bom_doc.exploded_items or bom_doc.items or []
        if not bom_items:
            print("Selected BOM has no items. Exiting.")
            return
            
        test_item = bom_items[0].item_code
        print(f"BOM Test Item: {test_item}")
        
        # Check if test_item has stock in target warehouse, if not, create a mock SLE to give it stock
        stock_qty = frappe.db.sql("""
            SELECT SUM(actual_qty)
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
        """, (test_item, warehouse))[0][0] or 0.0
        
        sle_inserted = False
        if flt(stock_qty) <= 0:
            print(f"No stock for {test_item} in {warehouse}. Inserting mock Stock Ledger Entry.")
            sle = frappe.get_doc({
                "doctype": "Stock Ledger Entry",
                "item_code": test_item,
                "warehouse": warehouse,
                "actual_qty": 10.0,
                "posting_date": frappe.utils.today(),
                "posting_time": "12:00:00",
                "company": frappe.db.get_single_value("Global Defaults", "default_company") or "MCPL"
            })
            sle.db_insert()
            sle_inserted = True
            print("Mock SLE inserted.")
            
        # Step 4: Create Batch Planning doc (Parent)
        bp_parent = frappe.get_doc({
            "doctype": "Batch Planning",
            "custom_employee_function": ef_name,
            "month": "June",
            "workflow_state": "Approved",
            "docstatus": 1,
            "project": "Test Project",
            "project_name": "Test Project Name",
            "custom_batch_details": [
                {
                    "batch_type": "Manufacturing",
                    "finished_item": finished_item,
                    "bom_list": bom_name,
                    "batch_planning_id": "MOCK-BATCH-1",
                    "status": "Approved"
                },
                {
                    "batch_type": "Manufacturing",
                    "finished_item": finished_item,
                    "bom_list": bom_name,
                    "batch_planning_id": "MOCK-BATCH-2",
                    "status": "Approved"
                }
            ]
        })
        bp_parent.db_insert()
        bp_parent.save()
        print(f"Mock Batch Planning parent inserted: {bp_parent.name}")
        
        # Step 5: Insert corresponding Batches Planned docs (Children)
        bp_child1 = frappe.get_doc({
            "doctype": "Batches Planned",
            "batch_planning": bp_parent.name,
            "batch_planning_id": "MOCK-BATCH-1",
            "employee_function": ef_name,
            "finished_item": finished_item,
            "workflow_state": "Approved"
        })
        bp_child1.db_insert()
        bp_child1.save()
        
        bp_child2 = frappe.get_doc({
            "doctype": "Batches Planned",
            "batch_planning": bp_parent.name,
            "batch_planning_id": "MOCK-BATCH-2",
            "employee_function": ef_name,
            "finished_item": finished_item,
            "workflow_state": "Approved"
        })
        bp_child2.db_insert()
        bp_child2.save()
        print(f"Mock Batches Planned (children) inserted: {bp_child1.name}, {bp_child2.name}")
        
        # Step 6: Test Bulk Allocation
        print("Calling create_bulk_material_allocations...")
        summary = create_bulk_material_allocations(bp_parent.name)
        print("Summary:", summary)
        
        # Verify allocations were created
        allocations = frappe.db.get_all("Material Allocation", filters={"batch_planning": bp_parent.name})
        print(f"Allocations created: {len(allocations)}")
        for alloc in allocations:
            a_doc = frappe.get_doc("Material Allocation", alloc.name)
            print(f"  MA Name: {a_doc.name} | parent_bp: {a_doc.batch_planning} | child_bp: {a_doc.batches_planned} | status: {a_doc.workflow_state}")
            
        assert len(allocations) == 2, f"Expected 2 allocations, got {len(allocations)}"
        
        # Step 7: Test silently skipping already-allocated batches
        print("Calling create_bulk_material_allocations again to verify skipping...")
        summary_skip = create_bulk_material_allocations(bp_parent.name)
        print("Summary (skip):", summary_skip)
        assert "0 Material Allocation docs created" in summary_skip, "Failed to skip already allocated batches"
        assert "2 already existed" in summary_skip, "Failed to count already existed batches"
        
        print("TEST PASSED SUCCESSFULLY!")
        
    finally:
        frappe.db.rollback()
        print("Database transaction rolled back.")
