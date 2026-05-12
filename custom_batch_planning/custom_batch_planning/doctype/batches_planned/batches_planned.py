import frappe, json
from frappe.model.document import Document
from frappe.utils import flt


# ═══════════════════════════════════════════════
# Batches Planned
# ═══════════════════════════════════════════════
class BatchesPlanned(Document):

    # Prevent delete if Material Allocation exists
    def on_trash(self):

        if frappe.db.exists("Material Allocation", {"batch_planning": self.name}):

            frappe.throw(
                f"Cannot delete Batches Planned <b>{self.name}</b>. "
                f"Material Allocation exists for it."
            )


# ═══════════════════════════════════════════════
# API : Get Material Planning Data
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_material_planning_data(items, warehouse, batch_planning, employee_function):
    """
    Calculates stock, allocation,
    requirement and FEFO details.
    """

    # Convert JSON string to list
    if isinstance(items, str): items = json.loads(items)

    res = []

    # Loop through all items
    for item in items:

        item_code = item.get("item_code")
        qty_required = flt(item.get("qty_required"))

        # 1. Main Warehouse Stock
        sle_main = frappe.db.sql("""
            SELECT qty_after_transaction
            FROM `tabStock Ledger Entry`
            WHERE item_code=%s AND warehouse=%s
            AND is_cancelled=0
            ORDER BY posting_date DESC, posting_time DESC, creation DESC
            LIMIT 1
        """, (item_code, warehouse))

        main_stock = flt(sle_main[0][0]) if sle_main else 0.0

        # 2. Total / Lab Stock
        total_stock = frappe.db.get_value(
            "Stock Ledger Entry",
            {"item_code": item_code, "is_cancelled": 0},
            "sum(actual_qty)"
        ) or 0

        lab_stock = total_stock - main_stock

        # 3. Allocated Quantity
        allocated_qty = frappe.db.sql("""
            SELECT IFNULL(SUM(mai.allocate_qty),0)
            FROM `tabMaterial Allocation Item` mai
            INNER JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
            WHERE mai.item_code=%s
            AND ma.employee_function=%s
            AND ma.allocation_status='Allocated'
            AND ma.docstatus!=2
        """, (item_code, employee_function))[0][0] or 0

        # 4. Free Stock / Net Requirement
        free_stock = max(main_stock - allocated_qty, 0)
        net_requirement = max(qty_required - free_stock, 0)

        # 5. Open PR / PO
        open_pr = frappe.db.sql("""
            SELECT SUM(qty - ordered_qty)
            FROM `tabMaterial Request Item`
            WHERE item_code=%s
            AND docstatus=1
            AND qty > ordered_qty
        """, item_code)[0][0] or 0

        open_po = frappe.db.sql("""
            SELECT SUM(qty - received_qty)
            FROM `tabPurchase Order Item`
            WHERE item_code=%s
            AND docstatus=1
            AND qty > received_qty
        """, item_code)[0][0] or 0

        # Placeholder for future GRN logic
        open_grn = 0

        # 6. FEFO Batch Details
        batch_info = frappe.db.sql("""
            SELECT b.expiry_date, SUM(sle.actual_qty) as actual_qty
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabBatch` b ON b.name = sle.batch_no
            WHERE sle.item_code=%s
            AND sle.is_cancelled=0
            AND (b.expiry_date >= CURDATE() OR b.expiry_date IS NULL)
            GROUP BY sle.batch_no, b.expiry_date
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY b.expiry_date ASC
            LIMIT 1
        """, item_code, as_dict=True)

        # 7. Expired Quantity
        expired_qty = frappe.db.sql("""
            SELECT SUM(sle.actual_qty)
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabBatch` b ON b.name = sle.batch_no
            WHERE sle.item_code=%s
            AND sle.is_cancelled=0
            AND b.expiry_date < CURDATE()
        """, item_code)[0][0] or 0

        usable_qty = batch_info[0].actual_qty if batch_info else 0
        expiry_date = batch_info[0].expiry_date if batch_info else None

        # Final Response Row
        res.append({
            "item_code": item_code,
            "item_name": item.get("item_name"),
            "qty_required": qty_required,
            "total_stock": total_stock,
            "main_stock": main_stock,
            "lab_stock": lab_stock,
            "allocated_qty": allocated_qty,
            "free_stock": free_stock,
            "open_pr": open_pr,
            "open_po": open_po,
            "open_grn": open_grn,
            "net_requirement": net_requirement,
            "usable_qty": usable_qty,
            "expired_qty": expired_qty,
            "expiry_date": expiry_date
        })

    return res


# ═══════════════════════════════════════════════
# API : Get BOM Items for MA
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_bom_items_for_ma(batch_planning):

    # Fetch Batches Planned & Batch Creation
    bp = frappe.get_doc("Batches Planned", batch_planning)

    if not bp.batch_creation:
        frappe.throw("Batch Creation not linked!")

    bc = frappe.get_doc("Batch Creation", bp.batch_creation)

    matched = None

    # Match Batch Planning / Amendment / Base ID
    for row in (bc.custom_batch_details or []):

        if row.batch_planning_id in (
            batch_planning,
            bp.amended_from,
            batch_planning.rsplit("-", 1)[0]
        ):
            matched = row
            break

    # Validate BOM
    if not matched or not matched.bom_list:

        frappe.throw(f"BOM not found for: {batch_planning}")

    batch_key = f"{bp.batch_creation}-{matched.idx}"
    use_store, items = False, []

    # Use Edited BOM Store
    if matched.batch_type in ("Process Development", "Machine Trial"):

        bom_store = frappe.db.get_value(
            "Batch BOM Store after Edit",
            {"batch_id": batch_key},
            "name"
        )

        if bom_store:

            store_doc = frappe.get_doc(
                "Batch BOM Store after Edit",
                bom_store
            )

            items = store_doc.bom_components or []
            use_store = True

    # Default BOM
    if not use_store:

        bom = frappe.get_doc("BOM", matched.bom_list)
        items = bom.exploded_items or bom.items or []

    # Fetch Warehouse
    ef = frappe.get_doc("Employee Function", bp.employee_function)

    warehouse = next(
        (r.store_warehouse for r in (ef.table_bukm or []) if r.store_warehouse),
        None
    )

    result = []

    # Prepare Final Item List
    for item in items:

        # Qty / UOM Logic
        if use_store:

            qty, uom = float(item.qty or 0), item.uom or ""

        else:

            qty = float(
                item.qty_consumed_per_unit
                or item.stock_qty
                or item.qty
                or 0
            )

            uom = item.stock_uom or item.uom or ""

        item_code = item.item_code

        # Main Stock
        main_stock = float(
            frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": warehouse},
                "actual_qty"
            ) or 0
        )

        # Allocated Qty
        allocated_qty = frappe.db.sql("""
            SELECT IFNULL(SUM(mai.allocate_qty),0)
            FROM `tabMaterial Allocation Item` mai
            JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
            WHERE mai.item_code=%s
            AND ma.employee_function=%s
            AND ma.allocation_status='Allocated'
            AND ma.docstatus!=2
        """, (item_code, bp.employee_function))[0][0] or 0

        # Free Stock
        free_stock = max(main_stock - float(allocated_qty), 0)

        # Final Row
        result.append({
            "item_code": item_code,
            "item_name": item.item_name,
            "uom": uom,
            "quantity_required": round(qty, 6),
            "stock_available": round(free_stock, 2)
        })

    return result