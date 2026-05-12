# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import frappe


# ═══════════════════════════════════════════════
# API — Get All Material Allocations
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_all_material_allocations(employee_function=None):

    filters = "WHERE ma.docstatus IN (0, 1, 2)"
    values = []

    if employee_function:
        filters += " AND bp.employee_function = %s"
        values.append(employee_function)

    result = frappe.db.sql(f"""
        SELECT
            ma.name,
            ma.batch_planning,
            ma.warehouse,
            ma.workflow_state,
            ma.docstatus,
            ma.custom_allocation_status,
            ma.modified
        FROM `tabMaterial Allocation` ma
        LEFT JOIN `tabBatches Planned` bp ON bp.name = ma.batch_planning
        {filters}
        ORDER BY ma.modified DESC
        LIMIT 99999
    """, values, as_dict=True)

    return result


# ═══════════════════════════════════════════════
# API — Get Material Allocation Items By Parent
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_ma_items(ma_names=None):
    if not ma_names:
        return []
    if isinstance(ma_names, str):
        import json
        try:
            ma_names = json.loads(ma_names)
        except Exception:
            ma_names = [ma_names]
    fmt = ",".join(["%s"] * len(ma_names))
    return frappe.db.sql(f"""
        SELECT parent, item_code, item_name, uom,
               quantity_required, stock_available, allocate_qty, shortage
        FROM `tabMaterial Allocation Item`
        WHERE parent IN ({fmt})
        ORDER BY parent, idx
    """, ma_names, as_dict=True)