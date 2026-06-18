import frappe
from custom_batch_planning.api.pr_integration import map_purchase_receipt_fields, map_stock_entry_fields, map_purchase_invoice_fields

def run():
    print("Starting PR Integration Tests...")
    
    frappe.db.begin()
    
    try:
        # 1. Fetch setup data
        suppliers = frappe.db.get_all("Supplier", limit=5)
        supplier_name = suppliers[0].name if suppliers else None
        if not supplier_name:
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
                }
            ]
        })
        bp_doc.insert(ignore_permissions=True)
        print("Batch Planning created:", bp_doc.name)
        
        # Create Batches Planned document to match the Link field option exists check
        bp_planned = frappe.get_doc({
            "doctype": "Batches Planned",
            "batch_planning_id": "BATCH-REF-TEST-1",
            "batch_planning": bp_doc.name,
            "employee_function": "VP-LTP-POC-003",
            "month": "June",
            "batch_type": "Manufacturing",
            "finished_item": "FG01010004"
        })
        bp_planned.insert(ignore_permissions=True)
        # We override the name to be exactly 'BATCH-REF-TEST-1'
        frappe.db.sql("update `tabBatches Planned` set name=%s where name=%s", ("BATCH-REF-TEST-1", bp_planned.name))
        print("Batches Planned created with name: BATCH-REF-TEST-1")
        
        # 3. Create a Material Request with linked fields
        print("Creating test Material Request...")
        mr_doc = frappe.get_doc({
            "doctype": "Material Request",
            "material_request_type": "Purchase",
            "transaction_date": frappe.utils.today(),
            "custom_batch_planning_no": bp_doc.name,
            "items": [
                {
                    "item_code": "RM/000701",
                    "qty": 10.0,
                    "uom": "Nos",
                    "warehouse": "LC01-AR11-FL07-RM078 - MCPL",
                    "schedule_date": frappe.utils.today(),
                    "custom_batch_planning_no": bp_doc.name,
                    "custom_batch_reference": "BATCH-REF-TEST-1"
                }
            ]
        })
        mr_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        print("Material Request created:", mr_doc.name)
        
        # 4. Create a Purchase Order referencing the Material Request Item
        print("Creating test Purchase Order...")
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
                    "warehouse": "LC01-AR11-FL07-RM078 - MCPL",
                    "schedule_date": frappe.utils.today(),
                    "material_request": mr_doc.name,
                    "material_request_item": mr_doc.items[0].name,
                    "custom_batch_planning_no": bp_doc.name
                }
            ]
        })
        po_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        print("Purchase Order created:", po_doc.name)
        
        # 5. Create a Purchase Receipt (GRN) from PO
        print("Creating test Purchase Receipt...")
        pr_doc = frappe.get_doc({
            "doctype": "Purchase Receipt",
            "supplier": supplier_name,
            "company": frappe.db.get_single_value("Global Defaults", "default_company") or "MCPL",
            "items": [
                {
                    "item_code": "RM/000701",
                    "qty": 10.0,
                    "uom": "Nos",
                    "warehouse": "LC01-AR11-FL07-RM078 - MCPL",
                    "purchase_order": po_doc.name,
                    "purchase_order_item": po_doc.items[0].name,
                    "material_request": mr_doc.name,
                    "material_request_item": mr_doc.items[0].name
                }
            ]
        })
        
        # Trigger fields mapping
        map_purchase_receipt_fields(pr_doc)
        
        # Verify mapping output
        print("PR Header Batch Planning No:", pr_doc.custom_batch_planning_no)
        print("PR Header Batch No:", pr_doc.custom_batch_no)
        
        assert pr_doc.custom_batch_planning_no == bp_doc.name, "Parent Batch Planning No mapping failed"
        assert pr_doc.custom_batch_no == "BATCH-REF-TEST-1", "Parent Batch No mapping failed"
        
        # Insert Purchase Receipt to allow Stock Entry to fetch from it
        pr_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        print("Purchase Receipt created:", pr_doc.name)
        
        # 6. Create a Stock Entry linked to Purchase Receipt
        print("Creating test Stock Entry...")
        se_doc = frappe.get_doc({
            "doctype": "Stock Entry",
            "purpose": "Material Issue",
            "purchase_receipt_no": pr_doc.name,
            "company": pr_doc.company,
            "items": [
                {
                    "item_code": "RM/000701",
                    "qty": 10.0,
                    "uom": "Nos",
                    "s_warehouse": "LC01-AR11-FL07-RM078 - MCPL"
                }
            ]
        })
        
        # Trigger Stock Entry mapping
        map_stock_entry_fields(se_doc)
        
        # Verify Stock Entry mapping output
        print("Stock Entry Batch Planning No:", se_doc.custom_batch_planning_no)
        print("Stock Entry Batch No:", se_doc.custom_batch_no)
        print("Stock Entry Batch Planning (compatibility):", se_doc.custom_batch_planning)
        
        assert se_doc.custom_batch_planning_no == bp_doc.name, "Stock Entry Batch Planning No mapping failed"
        assert se_doc.custom_batch_no == "BATCH-REF-TEST-1", "Stock Entry Batch No mapping failed"
        assert se_doc.custom_batch_planning == "BATCH-REF-TEST-1", "Stock Entry Batch Planning compatibility mapping failed"
        
        # 7. Create a Purchase Invoice linked to Purchase Receipt
        print("Creating test Purchase Invoice...")
        pi_doc = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": supplier_name,
            "company": pr_doc.company,
            "items": [
                {
                    "item_code": "RM/000701",
                    "qty": 10.0,
                    "uom": "Nos",
                    "purchase_receipt": pr_doc.name,
                    "purchase_order": po_doc.name
                }
            ]
        })
        
        # Trigger Purchase Invoice mapping
        map_purchase_invoice_fields(pi_doc)
        
        # Verify Purchase Invoice mapping output
        print("Purchase Invoice Batch Planning No:", pi_doc.custom_batch_planning_no)
        
        assert pi_doc.custom_batch_planning_no == bp_doc.name, "Purchase Invoice Batch Planning No mapping failed"
        
        print("ALL TESTS PASSED SUCCESSFULLY!")
        
    finally:
        frappe.db.rollback()
        print("Database transaction rolled back.")
