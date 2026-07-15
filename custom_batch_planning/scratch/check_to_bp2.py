import frappe

def run():
    detail = frappe.db.sql("""
        SELECT name, parent, batch_planning_id, to_batch_planning_id 
        FROM `tabStock Entry Detail` 
        WHERE parent IN ('MAT-STE-2026-00946', 'MAT-STE-2026-00947')
    """, as_dict=True)
    
    for d in detail:
        print(f"Detail {d.name} ({d.parent}): bp={d.batch_planning_id}, to_bp={d.to_batch_planning_id}")
