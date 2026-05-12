data = frappe.request.get_json() or {}
bp_names = data.get("bp_names") or []
employee_function = data.get("employee_function") or ""

if not bp_names:
    frappe.response["message"] = []
else:
    fmt = ",".join(["%s"] * len(bp_names))
    today = frappe.utils.today()

    # Get warehouse + lab warehouses from Employee Function
    store_warehouse = ""
    lab_warehouses = []
    if employee_function:
        ef_doc = frappe.get_doc("Employee Function", employee_function)
        # Check if table_bukm exists and has store_warehouse
        if hasattr(ef_doc, 'table_bukm'):
            store_warehouse = next((r.store_warehouse for r in (ef_doc.table_bukm or []) if r.store_warehouse), "")
        # Fallback to main table if not in child table
        if not store_warehouse:
            store_warehouse = ef_doc.store_warehouse
            
        if hasattr(ef_doc, 'table_szrn'):
            lab_warehouses = [r.lab_warehouse for r in (ef_doc.table_szrn or []) if r.lab_warehouse]
        if not lab_warehouses and ef_doc.lab_warehouse:
            lab_warehouses = [ef_doc.lab_warehouse]

    # Get BOM items
    bom_items = frappe.db.sql(f"""
        SELECT
            bd.batch_planning_id as bp_name,
            bi.item_code,
            bi.item_name,
            bi.stock_uom as uom,
            bi.qty_consumed_per_unit as required_qty
        FROM `tabBatches Planned` bp
        JOIN `tabBatch Creation` bc ON bc.name = bp.batch_creation
        JOIN `tabBatch Planning Detail` bd ON bd.parent = bc.name
        JOIN `tabBOM` bom ON bom.name = bd.bom_list
        JOIN `tabBOM Explosion Item` bi ON bi.parent = bom.name
        WHERE bp.batch_planning_id IN ({fmt})
        AND bom.is_active = 1
    """, bp_names, as_dict=True)

    # Get allocated qty from Material Allocation (linked to these BPs)
    allocated = frappe.db.sql(f"""
        SELECT
            ma.batch_planning as bp_name,
            mai.item_code,
            SUM(mai.allocate_qty) as allocated_qty
        FROM `tabMaterial Allocation` ma
        JOIN `tabMaterial Allocation Item` mai ON mai.parent = ma.name
        WHERE ma.batch_planning IN ({fmt})
        AND ma.docstatus != 2
        AND ma.allocation_status != 'Deallocated'
        GROUP BY ma.batch_planning, mai.item_code
    """, bp_names, as_dict=True)

    alloc_map = {}
    for a in allocated:
        key = (a.bp_name, a.item_code)
        alloc_map[key] = a.allocated_qty

    # Merge items across BPs
    combined = {}
    for row in bom_items:
        ic = row.item_code
        if ic not in combined:
            combined[ic] = {
                "item_code": ic,
                "item_name": row.item_name,
                "uom": row.uom,
                "required_qty": 0,
                "allocated_qty": 0,
            }
        combined[ic]["required_qty"] = round(combined[ic]["required_qty"] + float(row.required_qty or 0), 6)
        alloc = alloc_map.get((row.bp_name, ic), 0)
        combined[ic]["allocated_qty"] = round(combined[ic]["allocated_qty"] + float(alloc or 0), 6)

    result = []
    for item_code, r in combined.items():
        qty_required = r["required_qty"]

        # Main warehouse stock (Latest SLE)
        main_stock = 0.0
        if store_warehouse:
            main_stock_row = frappe.db.sql("""
                SELECT qty_after_transaction
                FROM `tabStock Ledger Entry`
                WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
                ORDER BY posting_date DESC, posting_time DESC, creation DESC
                LIMIT 1
            """, (item_code, store_warehouse))
            main_stock = float(main_stock_row[0][0]) if main_stock_row else 0.0

        # Lab wise stock
        lab_stock = 0.0
        for lab_wh in lab_warehouses:
            lab_row = frappe.db.sql("""
                SELECT qty_after_transaction
                FROM `tabStock Ledger Entry`
                WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
                ORDER BY posting_date DESC, posting_time DESC, creation DESC
                LIMIT 1
            """, (item_code, lab_wh))
            lab_stock += float(lab_row[0][0]) if lab_row else 0.0

        total_stock = main_stock + lab_stock

        # Global Allocated Qty (across all active Material Allocations)
        # Using the same logic as batches_planned.py
        allocated_query = """
            SELECT SUM(mai.qty_allocated)
            FROM `tabMaterial Allocation Item` mai
            JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
            WHERE mai.item_code = %s
              AND ma.docstatus != 2
              AND ma.allocation_status != 'Deallocated'
        """
        allocated_args = [item_code]
        if employee_function:
            allocated_query += " AND ma.employee_function = %s"
            allocated_args.append(employee_function)
            
        total_allocated_global = frappe.db.sql(allocated_query, tuple(allocated_args))[0][0] or 0
        total_allocated_global = float(total_allocated_global)

        free_stock = max(total_stock - total_allocated_global, 0)

        # Open Docs
        open_pr = float(frappe.db.sql("""
            SELECT IFNULL(SUM(mri.qty - mri.ordered_qty), 0)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s AND mr.docstatus = 1 AND mri.ordered_qty < mri.qty
        """, (item_code,))[0][0] or 0)

        open_po = float(frappe.db.sql("""
            SELECT IFNULL(SUM(poi.qty - poi.received_qty), 0)
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE poi.item_code = %s AND po.docstatus = 1 AND poi.received_qty < poi.qty
        """, (item_code,))[0][0] or 0)

        open_grn = float(frappe.db.sql("""
            SELECT IFNULL(SUM(pri.qty - pri.returned_qty), 0)
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE pri.item_code = %s AND pr.docstatus = 1
              AND pr.status NOT IN ('Closed', 'Return Issued')
              AND pri.returned_qty < pri.qty
        """, (item_code,))[0][0] or 0)

        # Expired qty
        expired_qty = float(frappe.db.sql("""
            SELECT IFNULL(SUM(b.batch_qty), 0)
            FROM `tabBatch` b
            WHERE b.item = %s AND b.expiry_date IS NOT NULL
              AND b.expiry_date < %s AND b.batch_qty > 0
        """, (item_code, today))[0][0] or 0)

        usable_qty = max(total_stock - expired_qty, 0)

        net_requirement = max(round(qty_required - (free_stock + open_pr + open_po + open_grn), 6), 0)

        shortage = round(qty_required - total_stock, 2)

        result.append({
            "item_code": item_code,
            "item_name": r["item_name"],
            "uom": r["uom"],
            "required_qty": round(qty_required, 2),
            "allocated_qty": round(r["allocated_qty"], 2), # This is local to selected BPs
            "total_stock": round(total_stock, 2),
            "main_stock": round(main_stock, 2),
            "lab_stock": round(lab_stock, 2),
            "free_stock": round(free_stock, 2),
            "open_pr": round(open_pr, 2),
            "open_po": round(open_po, 2),
            "open_grn": round(open_grn, 2),
            "net_requirement": round(net_requirement, 2),
            "usable_qty": round(usable_qty, 2),
            "expired_qty": round(expired_qty, 2),
            "shortage": shortage if shortage > 0 else 0,
            "status": "shortage" if shortage > 0 else "ok"
        })

    result.sort(key=lambda x: x["item_name"] or "")
    frappe.response["message"] = result
