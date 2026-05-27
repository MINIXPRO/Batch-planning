# # Copyright (c) 2026, Shivam Singh and contributors
# # For license information, please see license.txt

# import frappe


# # ═══════════════════════════════════════════════
# # API — Batch Dashboard Data
# # ═══════════════════════════════════════════════

# @frappe.whitelist()
# def get_batch_dashboard_data(batch_planning=None):

#     filters = []

#     if batch_planning:
#         filters.append([
#             "batch_planning_id",
#             "like",
#             f"%{batch_planning}%"
#         ])

#     bps = frappe.get_all(
#         "Batches Planned",
#         filters=filters,
#         fields=[
#             "name",
#             "month",
#             "batch_type",
#             "finished_item",
#             "employee_function",
#             "employee_name",
#             "workflow_state"        # ← fetch actual status
#         ],
#         limit=100,
#         order_by="creation desc"
#     )

#     if not bps:
#         return []

#     bp_names = [bp.name for bp in bps]
#     fmt = ",".join(["%s"] * len(bp_names))

#     # -------------------------------------------------
#     # Material Requests
#     # -------------------------------------------------

#     mr_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabMaterial Request`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus IN (0, 1)
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     mr_map = {r.custom_batch_planning: r.cnt for r in mr_data}

#     # -------------------------------------------------
#     # Purchase Orders
#     # -------------------------------------------------

#     po_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabPurchase Order`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus IN (0, 1)
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     po_map = {r.custom_batch_planning: r.cnt for r in po_data}

#     # -------------------------------------------------
#     # Purchase Receipts (GRN)
#     # -------------------------------------------------

#     grn_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabPurchase Receipt`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus IN (0, 1)
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     grn_map = {r.custom_batch_planning: r.cnt for r in grn_data}

#     # -------------------------------------------------
#     # Purchase Invoices
#     # -------------------------------------------------

#     pi_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabPurchase Invoice`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus IN (0, 1)
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     pi_map = {r.custom_batch_planning: r.cnt for r in pi_data}

#     # -------------------------------------------------
#     # Material Allocations
#     # -------------------------------------------------

#     ma_data = frappe.db.sql(f"""
#         SELECT batch_planning, COUNT(*) as cnt
#         FROM `tabMaterial Allocation`
#         WHERE batch_planning IN ({fmt})
#         AND docstatus IN (0, 1)
#         GROUP BY batch_planning
#     """, bp_names, as_dict=True)
#     ma_map = {r.batch_planning: r.cnt for r in ma_data}

#     # -------------------------------------------------
#     # MR Pending (not converted to PO)
#     # -------------------------------------------------

#     pr_pending_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabMaterial Request`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus IN (0, 1)
#         AND per_ordered < 100
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     pr_pending_map = {
#         r.custom_batch_planning: r.cnt
#         for r in pr_pending_data
#     }

#     # -------------------------------------------------
#     # PO Pending (delivery pending)
#     # -------------------------------------------------

#     po_pending_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabPurchase Order`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus IN (0, 1)
#         AND per_received < 100
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     po_pending_map = {
#         r.custom_batch_planning: r.cnt
#         for r in po_pending_data
#     }

#     # -------------------------------------------------
#     # PR Pending (not submitted)
#     # -------------------------------------------------

#     pr_pending2_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabPurchase Receipt`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus = 0
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     pr_pending2_map = {
#         r.custom_batch_planning: r.cnt
#         for r in pr_pending2_data
#     }

#     # -------------------------------------------------
#     # PI Pending (not submitted)
#     # -------------------------------------------------

#     pi_pending_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(*) as cnt
#         FROM `tabPurchase Invoice`
#         WHERE custom_batch_planning IN ({fmt})
#         AND docstatus = 0
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     pi_pending_map = {
#         r.custom_batch_planning: r.cnt
#         for r in pi_pending_data
#     }

#     # -------------------------------------------------
#     # Material Issues
#     # -------------------------------------------------

#     issue_data = frappe.db.sql(f"""
#         SELECT custom_batch_planning, COUNT(DISTINCT name) as cnt
#         FROM `tabStock Entry`
#         WHERE custom_batch_planning IN ({fmt})
#         AND stock_entry_type = 'Material Issue'
#         AND docstatus = 1
#         GROUP BY custom_batch_planning
#     """, bp_names, as_dict=True)
#     issue_map = {
#         r.custom_batch_planning: r.cnt
#         for r in issue_data
#     }

#     # -------------------------------------------------
#     # Build Result
#     # -------------------------------------------------

#     result = []

#     for bp in bps:

#         n = bp.name

#         result.append({
#             "name":             n,
#             "month":            bp.month or "-",
#             "batch_type":       bp.batch_type or "-",
#             "finished_item":    bp.finished_item or "-",
#             "status":           bp.workflow_state or "Draft",  # ← actual status
#             "employee_name":    bp.employee_name or "-",
#             "employee_function":bp.employee_function or "-",
#             "mr_count":         mr_map.get(n, 0),
#             "po_count":         po_map.get(n, 0),
#             "grn_count":        grn_map.get(n, 0),
#             "pi_count":         pi_map.get(n, 0),
#             "ma_count":         ma_map.get(n, 0),
#             "pr_pending":       pr_pending_map.get(n, 0),
#             "po_pending":       po_pending_map.get(n, 0),
#             "pr_pending2":      pr_pending2_map.get(n, 0),
#             "pi_pending":       pi_pending_map.get(n, 0),
#             "issue_count":      issue_map.get(n, 0)
#         })

#     return result


# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import frappe


# ═══════════════════════════════════════════════
# API — Batch Dashboard Data
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_batch_dashboard_data(batch_planning=None):

    filters = []

    if batch_planning:
        filters.append([
            "batch_planning_id",
            "like",
            f"%{batch_planning}%"
        ])

    bps = frappe.get_all(
        "Batches Planned",
        filters=filters,
        fields=[
            "name",
            "month",
            "batch_type",
            "finished_item",
            "employee_function",
            "employee_name",
            "workflow_state"
        ],
        limit=100,
        order_by="creation desc"
    )

    if not bps:
        return []

    bp_names = [bp.name for bp in bps]
    fmt = ",".join(["%s"] * len(bp_names))

    # -------------------------------------------------
    # Material Requests
    # FIX: use custom_batch_no (not custom_batch_planning)
    # -------------------------------------------------

    mr_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabMaterial Request`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus IN (0, 1)
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    mr_map = {r.custom_batch_no: r.cnt for r in mr_data}

    # -------------------------------------------------
    # Purchase Orders
    # FIX: use custom_batch_no (not custom_batch_planning)
    # -------------------------------------------------

    po_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabPurchase Order`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus IN (0, 1)
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    po_map = {r.custom_batch_no: r.cnt for r in po_data}

    # -------------------------------------------------
    # Purchase Receipts (GRN)
    # FIX: use custom_batch_no (not custom_batch_planning)
    # -------------------------------------------------

    grn_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabPurchase Receipt`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus IN (0, 1)
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    grn_map = {r.custom_batch_no: r.cnt for r in grn_data}

    # -------------------------------------------------
    # Purchase Invoices
    # FIX: use custom_batch_no (not custom_batch_planning)
    # -------------------------------------------------

    pi_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabPurchase Invoice`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus IN (0, 1)
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    pi_map = {r.custom_batch_no: r.cnt for r in pi_data}

    # -------------------------------------------------
    # Material Allocations
    # CORRECT: uses batch_planning (standard field, no change needed)
    # -------------------------------------------------

    ma_data = frappe.db.sql(f"""
        SELECT batch_planning, COUNT(*) as cnt
        FROM `tabMaterial Allocation`
        WHERE batch_planning IN ({fmt})
        AND docstatus IN (0, 1)
        GROUP BY batch_planning
    """, bp_names, as_dict=True)
    ma_map = {r.batch_planning: r.cnt for r in ma_data}

    # -------------------------------------------------
    # MR Pending (not converted to PO)
    # FIX: use custom_batch_no
    # FIX: only submitted MRs (docstatus=1) to avoid draft inflation
    # -------------------------------------------------

    mr_pending_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabMaterial Request`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus = 1
        AND per_ordered < 100
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    mr_pending_map = {r.custom_batch_no: r.cnt for r in mr_pending_data}

    # -------------------------------------------------
    # PO Pending (delivery pending)
    # FIX: use custom_batch_no
    # -------------------------------------------------

    po_pending_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabPurchase Order`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus = 1
        AND per_received < 100
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    po_pending_map = {r.custom_batch_no: r.cnt for r in po_pending_data}

    # -------------------------------------------------
    # PR Pending (Purchase Receipts not submitted)
    # FIX: use custom_batch_no
    # -------------------------------------------------

    pr_pending_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabPurchase Receipt`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus = 0
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    pr_pending_map = {r.custom_batch_no: r.cnt for r in pr_pending_data}

    # -------------------------------------------------
    # PI Pending (Purchase Invoices not submitted)
    # FIX: use custom_batch_no
    # -------------------------------------------------

    pi_pending_data = frappe.db.sql(f"""
        SELECT custom_batch_no, COUNT(*) as cnt
        FROM `tabPurchase Invoice`
        WHERE custom_batch_no IN ({fmt})
        AND docstatus = 0
        GROUP BY custom_batch_no
    """, bp_names, as_dict=True)
    pi_pending_map = {r.custom_batch_no: r.cnt for r in pi_pending_data}

    # -------------------------------------------------
    # Material Issues (Stock Entry)
    # CORRECT: uses custom_batch_planning (confirmed correct field)
    # -------------------------------------------------

    issue_data = frappe.db.sql(f"""
        SELECT custom_batch_planning, COUNT(DISTINCT name) as cnt
        FROM `tabStock Entry`
        WHERE custom_batch_planning IN ({fmt})
        AND stock_entry_type = 'Material Issue'
        AND docstatus = 1
        GROUP BY custom_batch_planning
    """, bp_names, as_dict=True)
    issue_map = {r.custom_batch_planning: r.cnt for r in issue_data}

    # -------------------------------------------------
    # Build Result
    # -------------------------------------------------

    result = []

    for bp in bps:

        n = bp.name

        result.append({
            "name":              n,
            "month":             bp.month or "-",
            "batch_type":        bp.batch_type or "-",
            "finished_item":     bp.finished_item or "-",
            "status":            bp.workflow_state or "Draft",
            "employee_name":     bp.employee_name or "-",
            "employee_function": bp.employee_function or "-",
            "mr_count":          mr_map.get(n, 0),
            "po_count":          po_map.get(n, 0),
            "grn_count":         grn_map.get(n, 0),
            "pi_count":          pi_map.get(n, 0),
            "ma_count":          ma_map.get(n, 0),
            "pr_pending":        mr_pending_map.get(n, 0),   # MRs not converted to PO
            "po_pending":        po_pending_map.get(n, 0),   # PO delivery pending
            "pr_pending2":       pr_pending_map.get(n, 0),   # Purchase Receipts not submitted
            "pi_pending":        pi_pending_map.get(n, 0),   # Purchase Invoices not submitted
            "issue_count":       issue_map.get(n, 0)
        })

    return result