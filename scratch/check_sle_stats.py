import frappe

def get_sle_stats():

    res = frappe.db.sql("""
        SELECT 
            SUM(CASE WHEN project IS NOT NULL AND project != '' THEN 1 ELSE 0 END) as with_project,
            SUM(CASE WHEN project IS NULL OR project = '' THEN 1 ELSE 0 END) as without_project,
            COUNT(*) as total
        FROM `tabStock Ledger Entry`
        WHERE (batch_planning_id IS NULL OR batch_planning_id = '')
        AND is_cancelled = 0

        SELECT 
            SUM(CASE WHEN employee_function IS NOT NULL AND employee_function != '' THEN 1 ELSE 0 END) as with_ef,
            SUM(CASE WHEN employee_function IS NULL OR employee_function = '' THEN 1 ELSE 0 END) as without_ef,
            COUNT(*) as total
        FROM `tabStock Ledger Entry`
        WHERE (batch_planning_id IS NULL OR batch_planning_id = '')
        AND is_cancelled = 0
    """, as_dict=True)[0]
    print(res2)
