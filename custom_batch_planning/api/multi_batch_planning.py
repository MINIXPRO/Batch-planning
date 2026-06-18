# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import frappe
import json

# ═══════════════════════════════════════════════
# API 1 — Get Employee Functions
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_employee_functions():
    return frappe.db.sql("""
        SELECT name
        FROM `tabEmployee Function`
        ORDER BY name ASC
    """, as_dict=True)


# ═══════════════════════════════════════════════
# API 2 — Get Approved Batch Plannings
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_approved_batch_plannings(employee_function=None, month=None):
    is_admin = frappe.session.user == "Administrator"

    if not is_admin and not employee_function:
        return []

    filters = []
    if employee_function:
        filters.append(["employee_function", "=", employee_function])

    if month:
        filters.append(["month", "=", month])

    return frappe.get_all(
        "Batches Planned",
        filters=filters,
        fields=[
            "batch_planning_id as name",
            "month",
            "batch_type",
            "finished_item",
            "batch_planning",
            "employee_function"
        ],
        order_by="batch_planning_id asc",
        limit=1000
    )


# ═══════════════════════════════════════════════
# API 3 — Get Multi Batch Material Plan
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_multi_batch_material_plan(bp_names, employee_function=None):
    if isinstance(bp_names, str):
        bp_names = json.loads(bp_names)

    if not bp_names:
        return []

    today = frappe.utils.today()
    store_warehouse = ""
    lab_warehouses = []

    # ── Warehouses from Employee Function ──
    if employee_function:
        ef_doc = frappe.get_doc("Employee Function", employee_function)
        for r in (ef_doc.get("table_bukm") or []):
            if r.store_warehouse:
                store_warehouse = r.store_warehouse
                break
        for r in (ef_doc.get("table_szrn") or []):
            if r.lab_warehouse:
                lab_warehouses.append(r.lab_warehouse)

    # ── Get BOM Items ──
    bom_items = []
    for bp_name in bp_names:
        bp_doc = frappe.get_doc("Batches Planned", bp_name)
        if not bp_doc.batch_planning:
            continue

        bd_rows = frappe.db.sql("""
            SELECT bom_list, idx
            FROM `tabBatch Planning Detail`
            WHERE parent = %s AND batch_planning_id = %s
            LIMIT 1
        """, (bp_doc.batch_planning, bp_doc.batch_planning_id), as_dict=True)

        if not bd_rows:
            continue

        bd = bd_rows[0]
        batch_key = f"{bp_doc.batch_planning}-{bd.idx}"

        # Check Edited BOM First
        store = frappe.db.get_value("Batch BOM Store after Edit", {"batch_id": batch_key}, "name")

        if store:
            store_doc = frappe.get_doc("Batch BOM Store after Edit", store)
            for row in (store_doc.bom_components or []):
                bom_items.append({
                    "bp_name": bp_name,
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "uom": row.uom,
                    "required_qty": float(row.qty or 0)
                })
        else:
            if not bd.bom_list:
                continue
            items = frappe.db.sql("""
                SELECT item_code, item_name, stock_uom AS uom, qty_consumed_per_unit AS required_qty
                FROM `tabBOM Explosion Item`
                WHERE parent = %s
            """, bd.bom_list, as_dict=True)
            for row in items:
                bom_items.append({
                    "bp_name": bp_name,
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "uom": row.uom,
                    "required_qty": float(row.required_qty or 0)
                })

    # ── Current Batch Allocations Map (Specific to these BPs) ──
    fmt = ",".join(["%s"] * len(bp_names))
    allocated = frappe.db.sql(f"""
        SELECT ma.batches_planned AS bp_name, mai.item_code, SUM(mai.allocate_qty) AS allocated_qty
        FROM `tabMaterial Allocation` ma
        JOIN `tabMaterial Allocation Item` mai ON mai.parent = ma.name
        WHERE ma.batches_planned IN ({fmt})
            AND ma.docstatus != 2
            AND ma.allocation_status != 'Deallocated'
        GROUP BY ma.batches_planned, mai.item_code
    """, bp_names, as_dict=True)

    alloc_map = {}
    for a in allocated:
        alloc_map[(a.bp_name, a.item_code)] = float(a.allocated_qty or 0)

    # ── Combine BOM Requirement ──
    combined = {}
    for row in bom_items:
        item_code = row["item_code"]
        if item_code not in combined:
            combined[item_code] = {
                "item_code": item_code,
                "item_name": row["item_name"],
                "uom": row["uom"],
                "required_qty": 0,
                "allocated_qty": 0
            }
        combined[item_code]["required_qty"] += float(row["required_qty"] or 0)
        combined[item_code]["allocated_qty"] += alloc_map.get((row["bp_name"], item_code), 0)

    result = []
    for item_code, r in combined.items():
        qty_required = round(float(r["required_qty"] or 0), 6)

        # 1. Main Warehouse Stock (from Bin)
        main_stock = 0.0
        if store_warehouse:
            main_stock = float(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": store_warehouse}, "actual_qty") or 0.0)

        # 2. Lab Warehouse Stock (from Bin)
        lab_stock = 0.0
        for lab_wh in lab_warehouses:
            lab_stock += float(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": lab_wh}, "actual_qty") or 0.0)

        total_stock = main_stock + lab_stock

        # 3. Global Allocated Qty (Total across system for this EF)
        allocated_args = [item_code]
        allocated_query = """
            SELECT IFNULL(SUM(mai.allocate_qty), 0)
            FROM `tabMaterial Allocation Item` mai
            JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
            WHERE mai.item_code = %s
                AND ma.docstatus != 2
                AND ma.allocation_status != 'Deallocated'
        """
        if employee_function:
            allocated_query += " AND ma.employee_function = %s"
            allocated_args.append(employee_function)

        total_allocated_global = float(frappe.db.sql(allocated_query, tuple(allocated_args))[0][0] or 0)
        free_stock = max(main_stock - total_allocated_global, 0)

        # 4. Open PR
        open_pr = float(frappe.db.sql("""
            SELECT IFNULL(SUM(mri.qty - mri.ordered_qty), 0)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s AND mr.custom_employee_function = %s
            AND mr.docstatus = 1 AND mr.status IN ('Pending', 'Partially Ordered', 'Ordered')
            AND mri.qty > mri.ordered_qty
        """, (item_code, employee_function))[0][0] or 0)

        # 5. Open PO
        open_po = float(frappe.db.sql("""
            SELECT IFNULL(SUM(poi.qty - poi.received_qty), 0)
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE poi.item_code = %s AND poi.employee_function = %s
            AND po.docstatus = 1 AND po.status IN ('To Receive and Bill', 'To Receive')
            AND poi.qty > poi.received_qty
        """, (item_code, employee_function))[0][0] or 0)

        # 6. Open GRN
        open_grn = float(frappe.db.sql("""
            SELECT IFNULL(SUM(pri.qty - pri.returned_qty), 0)
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE pri.item_code = %s AND pri.employee_function = %s
            AND pr.docstatus = 1 AND pr.status IN ('To Bill', 'Partly Billed')
            AND pri.qty > pri.returned_qty
        """, (item_code, employee_function))[0][0] or 0)

        # 7. Expired Qty
        expired_qty = float(frappe.db.sql("""
            SELECT IFNULL(SUM(b.batch_qty), 0)
            FROM `tabBatch` b
            WHERE b.item = %s AND b.expiry_date IS NOT NULL AND b.expiry_date < %s AND b.batch_qty > 0
        """, (item_code, today))[0][0] or 0)

        usable_qty = max(main_stock - expired_qty, 0)

        # 8. Net Requirement
        net_requirement = max(round(qty_required - (free_stock + open_pr + open_po + open_grn), 6), 0)
        shortage = round(qty_required - total_stock, 2)

        result.append({
            "item_code": item_code,
            "item_name": r["item_name"],
            "uom": r["uom"],
            "required_qty": round(qty_required, 2),
            "allocated_qty": round(total_allocated_global, 2),
            "main_stock": round(main_stock, 2),
            "lab_stock": round(lab_stock, 2),
            "total_stock": round(total_stock, 2),
            "free_stock": round(free_stock, 2),
            "open_pr": round(open_pr, 2),
            "open_po": round(open_po, 2),
            "open_grn": round(open_grn, 2),
            "expired_qty": round(expired_qty, 2),
            "usable_qty": round(usable_qty, 2),
            "net_requirement": round(net_requirement, 2),
            "shortage": shortage if shortage > 0 else 0,
            "status": "shortage" if shortage > 0 else "ok"
        })

    return result