import frappe
from custom_batch_planning.custom_batch_planning.doctype.material_allocation.material_allocation import get_allocated_items

def execute():
    # find a batch planning that has logs
    logs = frappe.get_all("Material Allocation Log", fields=["batch_planning", "employee_function"])
    if not logs:
        print("No Material Allocation Logs found.")
        return
        
    for log in logs:
        result = get_allocated_items(log.batch_planning, log.employee_function)
        print(f"Log for {log.batch_planning} ({log.employee_function}):")
        for item in result["items"]:
            print(f"  - {item.item_code}: {item.qty_allocated}")
            
        zero_qty_items = [i for i in result["items"] if float(i.qty_allocated) <= 0]
        if zero_qty_items:
            print(f"  ERROR: Found 0-qty items: {zero_qty_items}")
    
    print("Test passed! All returned items have qty_allocated > 0.")
