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

        # -----------------------------------------
        # Linked MAs
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
        # Linked MRs
        # -----------------------------------------

        mr_data = frappe.db.sql(f"""
            SELECT custom_batch_planning, COUNT(*) as cnt
            FROM `tabMaterial Request`
            WHERE custom_batch_planning IN ({fmt})
            AND docstatus IN (0, 1)
            GROUP BY custom_batch_planning
        """, bp_names, as_dict=True)
        mr_map = {r.custom_batch_planning: r.cnt for r in mr_data}

        for r in result:
            r.ma_count = ma_map.get(r.name, 0)
            r.mr_count = mr_map.get(r.name, 0)

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
                "custom_batch_planning": name,
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