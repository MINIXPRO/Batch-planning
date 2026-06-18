import frappe
from custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning import create_bulk_material_allocations
from frappe.utils import flt

def run():
    print("Running Test for Consolidated Material Allocation Flow (Dictionary Return)...")
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
        
        # Step 3: Get BOM items and ensure we have stock for them
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
        
        # Insert enough mock stock so that both batches can be allocated
        if flt(stock_qty) < 100.0:
            print(f"Not enough stock ({stock_qty}) for {test_item} in {warehouse}. Inserting mock Stock Ledger Entry.")
            sle = frappe.get_doc({
                "doctype": "Stock Ledger Entry",
                "item_code": test_item,
                "warehouse": warehouse,
                "actual_qty": 100.0,
                "posting_date": frappe.utils.today(),
                "posting_time": "12:00:00",
                "company": frappe.db.get_single_value("Global Defaults", "default_company") or "MCPL"
            })
            sle.db_insert()
            print("Mock SLE inserted.")
            
        # Get a valid Project if available
        project_id = frappe.db.get_value("Project", {}, "name") or ""
        project_name = frappe.db.get_value("Project", project_id, "project_name") if project_id else ""

        # Generate unique batch IDs
        batch_id_1 = f"TB-1-{frappe.generate_hash(length=6)}"
        batch_id_2 = f"TB-2-{frappe.generate_hash(length=6)}"

        # Step 4: Create Batch Planning doc (Parent)
        bp_parent = frappe.get_doc({
            "doctype": "Batch Planning",
            "custom_employee_function": ef_name,
            "month": "June",
            "workflow_state": "Draft",
            "docstatus": 0,
            "project": project_id,
            "project_name": project_name,
            "custom_batch_details": [
                {
                    "batch_type": "Manufacturing",
                    "finished_item": finished_item,
                    "bom_list": bom_name,
                    "batch_planning_id": batch_id_1,
                    "status": "Approved"
                },
                {
                    "batch_type": "Manufacturing",
                    "finished_item": finished_item,
                    "bom_list": bom_name,
                    "batch_planning_id": batch_id_2,
                    "status": "Approved"
                }
            ]
        })
        bp_parent.flags.ignore_validate = True
        bp_parent.insert(ignore_permissions=True)
        
        # Manually force Approved and Submitted states via db_update
        bp_parent.workflow_state = "Approved"
        bp_parent.docstatus = 1
        bp_parent.db_update()
        for d in bp_parent.custom_batch_details:
            d.db_update()
            
        print(f"Mock Batch Planning parent inserted: {bp_parent.name}")
        
        # Step 5: Insert corresponding Batches Planned docs (Children)
        bp_child1 = frappe.get_doc({
            "doctype": "Batches Planned",
            "name": batch_id_1,
            "batch_planning": bp_parent.name,
            "batch_planning_id": batch_id_1,
            "employee_function": ef_name,
            "finished_item": finished_item,
            "workflow_state": "Approved"
        })
        bp_child1.db_insert()
        
        bp_child2 = frappe.get_doc({
            "doctype": "Batches Planned",
            "name": batch_id_2,
            "batch_planning": bp_parent.name,
            "batch_planning_id": batch_id_2,
            "employee_function": ef_name,
            "finished_item": finished_item,
            "workflow_state": "Approved"
        })
        bp_child2.db_insert()
        
        print(f"Mock Batches Planned children inserted: {bp_child1.name}, {bp_child2.name}")

        # Step 6: Test Consolidated Allocation dict return
        print("Calling create_bulk_material_allocations...")
        ma_data = create_bulk_material_allocations(bp_parent.name)
        
        # Verify it is a dict and has expected keys
        assert isinstance(ma_data, dict), f"Expected dict, got {type(ma_data)}"
        assert ma_data.get("doctype") == "Material Allocation", "Expected doctype to be Material Allocation"
        assert ma_data.get("batch_planning") == bp_parent.name, "Batch planning link mismatch"
        
        batch_names_got = sorted([x.strip() for x in ma_data.get("batches_planned", "").split(",")])
        batch_names_expected = sorted([batch_id_1, batch_id_2])
        assert batch_names_got == batch_names_expected, f"Expected batches list {batch_names_expected}, got {batch_names_got}"

        # Verify quantities are consolidated (BOM component qty is summed)
        items = ma_data.get("material_allocation", [])
        test_item_rows = [r for r in items if r.get("item_code") == test_item]
        assert len(test_item_rows) == 1, f"Expected exactly 1 consolidated row for {test_item}, got {len(test_item_rows)}"
        test_row = test_item_rows[0]
        
        # Calculate expected qty (summed from both batches custom_batch_details)
        single_batch_bom_qty = flt(bom_items[0].qty_consumed_per_unit or bom_items[0].stock_qty or bom_items[0].qty)
        expected_consolidated_qty = single_batch_bom_qty * 2.0
        print(f"Single batch BOM qty: {single_batch_bom_qty}, Expected Consolidated: {expected_consolidated_qty}, Actual: {test_row.get('quantity_required')}")
        assert flt(test_row.get("quantity_required")) == expected_consolidated_qty, f"Consolidation quantity mismatch. Expected {expected_consolidated_qty}, got {test_row.get('quantity_required')}"
        assert flt(test_row.get("allocate_qty")) == expected_consolidated_qty, f"Default allocate_qty should equal quantity_required. Got {test_row.get('allocate_qty')}"

        # Create document locally (simulate frappe.new_doc in JS)
        ma_doc = frappe.get_doc(ma_data)
        ma_doc.flags.ignore_validate = True
        ma_doc.insert(ignore_permissions=True)
        print(f"Inserted Draft MA document: {ma_doc.name}")

        # Step 7: Test python validations on save
        print("Testing validation: stock_available >= allocate_qty...")
        doc = frappe.get_doc("Material Allocation", ma_doc.name)
        row = [r for r in doc.material_allocation if r.item_code == test_item][0]
        row.stock_available = 5.0
        row.allocate_qty = 10.0
        try:
            doc.save()
            assert False, "Should have thrown stock validation error"
        except frappe.ValidationError as e:
            print("Successfully caught expected validation error:", str(e))
        
        print("Testing validation: allocate_qty <= quantity_required...")
        doc = frappe.get_doc("Material Allocation", ma_doc.name)
        row = [r for r in doc.material_allocation if r.item_code == test_item][0]
        row.stock_available = 100.0
        row.allocate_qty = expected_consolidated_qty + 5.0
        try:
            doc.save()
            assert False, "Should have thrown BOM qty ceiling validation error"
        except frappe.ValidationError as e:
            print("Successfully caught expected validation error:", str(e))

        print("Testing validation: reason mandatory if allocate_qty != quantity_required...")
        doc = frappe.get_doc("Material Allocation", ma_doc.name)
        row = [r for r in doc.material_allocation if r.item_code == test_item][0]
        row.allocate_qty = expected_consolidated_qty - 1.0
        row.reason = ""
        try:
            doc.save()
            assert False, "Should have thrown reason mandatory validation error"
        except frappe.ValidationError as e:
            print("Successfully caught expected validation error:", str(e))

        print("Testing validation: successful save when parameters are valid...")
        doc = frappe.get_doc("Material Allocation", ma_doc.name)
        for r in doc.material_allocation:
            r.stock_available = 1000.0  # bypass stock validation for other items
            if r.item_code == test_item:
                r.allocate_qty = expected_consolidated_qty - 1.0
                r.reason = "Reduced requirement because of lower batch size"
        doc.save()
        print("Successfully saved after correcting parameters.")

        print("CONSOLIDATED MATERIAL ALLOCATION TEST PASSED SUCCESSFULLY!")
        
    finally:
        frappe.db.rollback()
        print("Database transaction rolled back.")
