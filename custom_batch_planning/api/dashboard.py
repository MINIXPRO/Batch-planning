import frappe

@frappe.whitelist()
def get_batch_dashboard_data(batch_planning=None):

    filters = []

    if batch_planning:
        filters.append([
            "batch_planning",
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
            "workflow_state",
            "batch_planning"
        ],
        limit=1000,
        order_by="creation desc"
    )

    if not bps:
        return []

    bp_names = [bp.name for bp in bps]
    bp_parents = list(set([bp.batch_planning for bp in bps if bp.batch_planning]))
    fmt = ",".join(["%s"] * len(bp_names)) if bp_names else ""
    fmt_parents = ",".join(["%s"] * len(bp_parents)) if bp_parents else ""

    mr_map = {}
    if bp_parents:
        mr_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabMaterial Request`
            WHERE custom_batch_planning_no IN ({fmt_parents})
            AND docstatus IN (0, 1)
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        mr_map = {r.custom_batch_planning_no: r.cnt for r in mr_data}

    po_map = {}
    if bp_parents:
        po_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabPurchase Order`
            WHERE docstatus IN (0, 1)
              AND custom_batch_planning_no IN ({fmt_parents})
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        po_map = {r.custom_batch_planning_no: r.cnt for r in po_data}

    grn_map = {}
    if bp_parents:
        grn_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabPurchase Receipt`
            WHERE custom_batch_planning_no IN ({fmt_parents})
            AND docstatus IN (0, 1)
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        grn_map = {r.custom_batch_planning_no: r.cnt for r in grn_data}

    pi_map = {}
    if bp_parents:
        pi_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabPurchase Invoice`
            WHERE custom_batch_planning_no IN ({fmt_parents})
            AND docstatus IN (0, 1)
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        pi_map = {r.custom_batch_planning_no: r.cnt for r in pi_data}

    ma_map = {}
    if bp_parents:
        ma_data = frappe.db.sql(f"""
            SELECT batch_planning, COUNT(*) as cnt
            FROM `tabMaterial Allocation`
            WHERE batch_planning IN ({fmt_parents})
            AND docstatus IN (0, 1)
            GROUP BY batch_planning
        """, bp_parents, as_dict=True)
        ma_map = {r.batch_planning: r.cnt for r in ma_data}

    mr_pending_map = {}
    if bp_parents:
        mr_pending_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabMaterial Request`
            WHERE custom_batch_planning_no IN ({fmt_parents})
            AND docstatus = 1
            AND per_ordered < 100
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        mr_pending_map = {r.custom_batch_planning_no: r.cnt for r in mr_pending_data}

    po_pending_map = {}
    if bp_parents:
        po_pending_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabPurchase Order`
            WHERE docstatus = 1
              AND per_received < 100
              AND custom_batch_planning_no IN ({fmt_parents})
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        po_pending_map = {r.custom_batch_planning_no: r.cnt for r in po_pending_data}

    pr_pending_map = {}
    if bp_parents:
        pr_pending_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabPurchase Receipt`
            WHERE custom_batch_planning_no IN ({fmt_parents})
            AND docstatus = 0
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        pr_pending_map = {r.custom_batch_planning_no: r.cnt for r in pr_pending_data}

    pi_pending_map = {}
    if bp_parents:
        pi_pending_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(*) as cnt
            FROM `tabPurchase Invoice`
            WHERE custom_batch_planning_no IN ({fmt_parents})
            AND docstatus = 0
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        pi_pending_map = {r.custom_batch_planning_no: r.cnt for r in pi_pending_data}

    issue_map = {}
    if bp_parents:
        issue_data = frappe.db.sql(f"""
            SELECT custom_batch_planning_no, COUNT(DISTINCT name) as cnt
            FROM `tabStock Entry`
            WHERE custom_batch_planning_no IN ({fmt_parents})
            AND stock_entry_type = 'Material Issue'
            AND docstatus = 1
            GROUP BY custom_batch_planning_no
        """, bp_parents, as_dict=True)
        issue_map = {r.custom_batch_planning_no: r.cnt for r in issue_data}

    result_dict = {}
    for bp in bps:
        parent = bp.batch_planning
        if not parent:
            continue
            
        n = bp.name

        if parent not in result_dict:
            result_dict[parent] = {
                "name":              parent,
                "batch_planning":    parent,
                "batches_planned":   n,
                "month":             bp.month or "-",
                "batch_type":        bp.batch_type or "-",
                "finished_item":     bp.finished_item or "-",
                "status":            bp.workflow_state or "Draft",
                "employee_name":     bp.employee_name or "-",
                "employee_function": bp.employee_function or "-",
                "mr_count":          mr_map.get(parent, 0),
                "po_count":          po_map.get(parent, 0),
                "grn_count":         grn_map.get(parent, 0),
                "pi_count":          pi_map.get(parent, 0),
                "ma_count":          ma_map.get(parent, 0),
                "pr_pending":        mr_pending_map.get(parent, 0),
                "po_pending":        po_pending_map.get(parent, 0),
                "pr_pending2":       pr_pending_map.get(parent, 0),
                "pi_pending":        pi_pending_map.get(parent, 0),
                "issue_count":       issue_map.get(parent, 0)
            }
        else:
            result_dict[parent]["batches_planned"] += f",{n}"

    return list(result_dict.values())
