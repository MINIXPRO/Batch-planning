import frappe

def run():
    detail = frappe.db.sql("""
        SELECT name, batch_planning_id, to_batch_planning_id 
        FROM `tabStock Entry Detail` 
        WHERE parent = 'MAT-STE-2026-00939'
    """, as_dict=True)
    
    for d in detail:
        print(f"Detail {d.name}: bp={d.batch_planning_id}, to_bp={d.to_batch_planning_id}")
