# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import frappe


# ═══════════════════════════════════════════════
# API — Get All Batch Plannings
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_all_batch_plannings(employee_function=None):

    filters = ""
    values = []

    if employee_function:
        filters = "WHERE employee_function = %s"
        values.append(employee_function)

    result = frappe.db.sql(f"""
        SELECT
            name,
            month,
            batch_type,
            finished_item,
            employee_function,
            employee_name,
            workflow_state,
            docstatus,
            modified
        FROM `tabBatches Planned`
        {filters}
        ORDER BY modified DESC
        LIMIT 500
    """, values, as_dict=True)

    if result:

        bp_names = [r.name for r in result]
        fmt = ",".join(["%s"] * len(bp_names))

        # Build a map from Batches Planned name → Batch Planning parent name
        bp_parent_rows = frappe.db.sql(f"""
            SELECT name, batch_planning
            FROM `tabBatches Planned`
            WHERE name IN ({fmt})
        """, bp_names, as_dict=True)
        bp_to_parent = {r.name: r.batch_planning for r in bp_parent_rows}
        bp_parents = list(set([v for v in bp_to_parent.values() if v]))
        fmt_parents = ",".join(["%s"] * len(bp_parents)) if bp_parents else None

        # -----------------------------------------
        # Linked MAs  (by Batches Planned name)
        # -----------------------------------------

        ma_data = frappe.db.sql(f"""
            SELECT batches_planned, COUNT(*) as cnt
            FROM `tabMaterial Allocation`
            WHERE batches_planned IN ({fmt})
            AND docstatus IN (0, 1)
            GROUP BY batches_planned
        """, bp_names, as_dict=True)
        ma_map = {r.batches_planned: r.cnt for r in ma_data}

        # -----------------------------------------
        # Linked MRs  (by Batch Planning parent name)
        # -----------------------------------------

        mr_by_parent = {}
        if bp_parents and fmt_parents:
            mr_data = frappe.db.sql(f"""
                SELECT custom_batch_planning_no, COUNT(*) as cnt
                FROM `tabMaterial Request`
                WHERE custom_batch_planning_no IN ({fmt_parents})
                AND docstatus IN (0, 1)
                GROUP BY custom_batch_planning_no
            """, bp_parents, as_dict=True)
            mr_by_parent = {r.custom_batch_planning_no: r.cnt for r in mr_data}

        for r in result:
            r.ma_count = ma_map.get(r.name, 0)
            parent = bp_to_parent.get(r.name)
            r.mr_count = mr_by_parent.get(parent, 0) if parent else 0

    return result


# ═══════════════════════════════════════════════
# API — Cancel Batch Planning With Workflow
# ═══════════════════════════════════════════════

@frappe.whitelist()
def bp_cancel_with_workflow(name=None):

    if not name:
        return {"success": False, "error": "Name required"}

    try:

        # -----------------------------------------
        # Cancel Batches Planned
        # -----------------------------------------

        frappe.db.set_value(
            "Batches Planned",      # ← fixed from old "Batch Planning"
            name,
            {
                "workflow_state": "Cancelled",
                "docstatus": 2
            }
        )

        # -----------------------------------------
        # Cancel linked Material Allocations
        # -----------------------------------------

        linked_mas = frappe.get_all(
            "Material Allocation",
            filters={
                "batches_planned": name,
                "docstatus": ["!=", 2]
            },
            fields=["name", "docstatus"]
        )

        for ma in linked_mas:

            frappe.db.set_value(
                "Material Allocation",
                ma.name,
                {
                    "workflow_state": "Cancelled",
                    "docstatus": 2,
                    "allocation_status": "Deallocated"
                }
            )

        # -----------------------------------------
        # Cancel linked Material Requests
        # -----------------------------------------

        linked_mrs = frappe.get_all(
            "Material Request",
            filters={
                "custom_batch_planning_no": name,
                "docstatus": 1
            },
            fields=["name"]
        )

        for mr in linked_mrs:
            mr_doc = frappe.get_doc("Material Request", mr.name)
            mr_doc.flags.ignore_permissions = True
            mr_doc.cancel()

        frappe.db.commit()

        return {"success": True}

    except Exception as e:

        frappe.log_error(
            frappe.get_traceback(),
            f"bp_cancel_with_workflow failed for {name}"
        )

        return {"success": False, "error": str(e)}