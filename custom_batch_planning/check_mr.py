import frappe

def execute():
    mr_items = frappe.db.sql("""
        SELECT mri.parent, mri.item_code, mri.batch_planning_id, mri.qty, mri.ordered_qty,
               mr.project, mr.docstatus, mr.status, mr.material_request_type, mr.custom_batch_planning_no
        FROM `tabMaterial Request Item` mri
        JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE mri.batch_planning_id = 'BP-26-07-001' OR mr.custom_batch_planning_no = 'BP-26-07-001'
    """, as_dict=True)

    print(f"Total MR Items found: {len(mr_items)}")
    for row in mr_items:
        print(row)
