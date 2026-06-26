import frappe
from custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning import create_bulk_material_allocations

def run_tests():
    print("\n=== Step 1: Batch Planning ===")
    try:
        bp = frappe.get_doc("Batch Planning", "BP-26-11-001")
        print("workflow_state:", bp.workflow_state)
        print("docstatus:", bp.docstatus)
        print("custom_batch_details len:", len(bp.custom_batch_details))
    except Exception as e:
        print("Error in Step 1:", e)

    print("\n=== Step 2: Net Requirement ===")
    try:
        result = frappe.call(
            "custom_batch_planning.custom_batch_planning.doctype.batches_planned.batches_planned.get_material_planning_data",
            items=[{"item_code": "CN02010007", "qty_required": 4, "item_name": "Test"}],
            warehouse="VP-LTP-MFG-001",
            batch_planning="BP-26-11-001",
            employee_function="VP-LTP-MFG-001"
        )
        for r in result:
            print(r["item_code"], "net_req:", r["net_requirement"], "bp_mr:", r["bp_mr_qty"], "free:", r["free_stock"])
    except Exception as e:
        print("Error in Step 2:", e)

    print("\n=== Step 3: MR batch_planning_id ===")
    try:
        mr = frappe.get_doc("Material Request", "MAT-MR-2026-01170")
        for item in mr.items:
            print(item.item_code, getattr(item, "batch_planning_id", None))
    except Exception as e:
        print("Error in Step 3:", e)

    print("\n=== Step 4: PO batch_planning_id ===")
    try:
        po = frappe.get_doc("Purchase Order", "1205001270")
        for item in po.items:
            print(item.item_code, getattr(item, "batch_planning_id", None))
    except Exception as e:
        print("Error in Step 4:", e)

    print("\n=== Step 5: Stock Available in MA ===")
    try:
        result = create_bulk_material_allocations("BP-26-11-001")
        for item in result.get("material_allocation", []):
            print(item["item_code"], "stock_available:", item["stock_available"])
    except Exception as e:
        print("Error in Step 5:", e)

    print("\n=== Step 6: Stock Entry / Item Issue tabs ===")
    try:
        bp = frappe.get_doc("Batch Planning", "BP-26-11-001")
        print("Stock Entry Log:", len(bp.stock_entry_log))
        print("Item Issue Log:", len(bp.item_issue_log))
    except Exception as e:
        print("Error in Step 6:", e)
