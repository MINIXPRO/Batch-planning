import frappe

def run():
    po_list = frappe.get_all(
        "Purchase Order",
        order_by="creation desc",
        limit=1
    )
    
    if not po_list:
        print("No POs found in the system.")
        return
        
    po_name = po_list[0].name
    print(f"Found Latest PO: {po_name}")
    
    po = frappe.get_doc("Purchase Order", po_name)
    print(f"PO linked to MR? {po.items[0].material_request if po.items else 'No items'}")
    for item in po.items:
        print(f"Item Code: {item.item_code}, Batch Planning ID: {item.batch_planning_id}")
