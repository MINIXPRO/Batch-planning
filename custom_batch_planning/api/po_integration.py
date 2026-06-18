import frappe
from frappe.utils import flt

def validate_purchase_order(doc, method):
    # 1. Group items by item_code in doc.items
    grouped_items = {}
    for item in doc.items:
        key = item.item_code
        if key not in grouped_items:
            grouped_items[key] = []
        grouped_items[key].append(item)
        
    new_items = []
    for item_code, rows in grouped_items.items():
        if len(rows) == 1:
            target = rows[0]
            if not target.get("custom_batch_planning_no") and target.get("material_request"):
                mr_bp_no = frappe.db.get_value("Material Request", target.material_request, "custom_batch_planning_no")
                if mr_bp_no:
                    target.custom_batch_planning_no = mr_bp_no
            new_items.append(target)
        else:
            target = rows[0]
            # Sum up qty
            total_qty = sum(flt(r.qty) for r in rows)
            target.qty = total_qty
            target.stock_qty = total_qty * flt(target.conversion_factor or 1)
            
            # Combine custom batch planning info
            bp_nos = []
            for r in rows:
                if r.get("custom_batch_planning_no"):
                    bp_nos.extend([x.strip() for x in r.custom_batch_planning_no.split(",") if x.strip()])
                if r.get("material_request"):
                    mr_bp_no = frappe.db.get_value("Material Request", r.material_request, "custom_batch_planning_no")
                    if mr_bp_no:
                        bp_nos.append(mr_bp_no.strip())
                    
            target.custom_batch_planning_no = ", ".join(sorted(list(set(bp_nos))))
            
            # Recalculate amount = qty * rate
            target.amount = flt(target.qty * flt(target.rate or 0))
            new_items.append(target)
            
    doc.items = new_items
    
    # 2. Update parent Purchase Order header custom_batch_planning_no
    all_bp_nos = []
    for item in doc.items:
        if item.get("custom_batch_planning_no"):
            all_bp_nos.extend([x.strip() for x in item.custom_batch_planning_no.split(",") if x.strip()])
            
    doc.custom_batch_planning_no = ", ".join(sorted(list(set(all_bp_nos))))
    
    # 3. Recalculate taxes and totals
    if hasattr(doc, "calculate_taxes_and_totals"):
        doc.calculate_taxes_and_totals()
