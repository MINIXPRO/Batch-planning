# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


# ═══════════════════════════════════════════════
# Batches Planned
# ═══════════════════════════════════════════════
class BatchesPlanned(Document):

    def on_trash(self):
        # 1. Prevent delete if Material Allocation exists
        if frappe.db.exists("Material Allocation", {"batch_planning": self.name}):
            frappe.throw(
                f"Cannot delete Batches Planned <b>{self.name}</b>. "
                f"Material Allocation exists for it."
            )

        # 2. Skip SCT decrement if called from Batch Creation on_trash
        #    (Batch Creation on_trash already handles decrement before delete)
        if frappe.flags.get("skip_sct_decrement"):
            return

        # 3. ── SCT batches_planned decrement (-1) ──
        if self.slot_opening_id and self.slot_booking_date:
            slot_master = frappe.db.get_value(
                "Slot Opening", self.slot_opening_id, "slot_master"
            )
            if slot_master:
                sct_name = frappe.db.get_value(
                    "Slot Capacity Tracker", {"slot_master": slot_master}, "name"
                )
                if sct_name:
                    sct_detail = frappe.db.get_value(
                        "Slot Capacity Detail",
                        {
                            "parent": sct_name,
                            "parenttype": "Slot Capacity Tracker",
                            "date": self.slot_booking_date,
                        },
                        ["name", "batches_planned"],
                        as_dict=True,
                    )
                    if sct_detail:
                        new_planned = max(0, int(sct_detail.batches_planned or 0) - 1)
                        frappe.db.set_value(
                            "Slot Capacity Detail",
                            sct_detail.name,
                            "batches_planned",
                            new_planned,
                        )


# ═══════════════════════════════════════════════
# API : Get Material Planning Data
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_material_planning_data(items, warehouse, batch_planning, employee_function):
    """
    Calculates:
    - Main warehouse stock (SLE)
    - Lab warehouse stock (SLE filtered by EF)
    - Allocation (Filtered by EF)
    - Open PR / PO / GRN (EF filtered)
    - Net requirement
    - FEFO batch details
    """
    if isinstance(items, str):
        items = json.loads(items)

    res = []
    curr_today = today()

    # Get Lab Warehouses from Employee Function
    ef_doc = frappe.get_doc("Employee Function", employee_function)
    lab_warehouses = [
        r.lab_warehouse for r in (ef_doc.get("table_szrn") or []) if r.lab_warehouse
    ]

    for item in items:
        item_code = item.get("item_code")
        qty_required = flt(item.get("qty_required"))

        # 1. Main Warehouse Stock (Latest from SLE)
        sle_main = frappe.db.sql(
            """
            SELECT qty_after_transaction
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
            ORDER BY posting_date DESC, posting_time DESC, creation DESC
            LIMIT 1
        """,
            (item_code, warehouse),
        )

        main_stock = flt(sle_main[0][0]) if sle_main else 0.0

        # 2. Lab Warehouse Stock
        lab_stock = 0.0
        for lab_wh in lab_warehouses:
            row = frappe.db.sql(
                """
                SELECT qty_after_transaction FROM `tabStock Ledger Entry`
                WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
                ORDER BY posting_date DESC, posting_time DESC, creation DESC LIMIT 1
            """,
                (item_code, lab_wh),
            )
            if row:
                lab_stock += flt(row[0][0])

        total_stock = main_stock + lab_stock

        # 3. Allocated Quantity (Global for this EF)
        # FIX: Exclude both 'Deallocated' AND 'Stock Entry Done'
        allocated_qty = (
            frappe.db.sql(
                """
            SELECT IFNULL(SUM(mai.allocate_qty), 0)
            FROM `tabMaterial Allocation Item` mai
            INNER JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
            WHERE mai.item_code = %s
            AND ma.employee_function = %s
            AND ma.allocation_status NOT IN ('Deallocated', 'Stock Entry Done')
            AND ma.docstatus != 2
        """,
                (item_code, employee_function),
            )[0][0]
            or 0
        )

        # 4. Open PR
        open_pr = (
            frappe.db.sql(
                """
            SELECT IFNULL(SUM(mri.qty - mri.ordered_qty), 0)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s AND mr.custom_employee_function = %s
            AND mr.docstatus = 1 AND mr.status IN ('Pending', 'Partially Ordered', 'Ordered')
            AND mri.qty > mri.ordered_qty
        """,
                (item_code, employee_function),
            )[0][0]
            or 0
        )

        # 5. Open PO
        open_po = (
            frappe.db.sql(
                """
            SELECT IFNULL(SUM(poi.qty - poi.received_qty), 0)
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE poi.item_code = %s AND poi.employee_function = %s
            AND po.docstatus = 1 AND po.status IN ('To Receive and Bill', 'To Receive')
            AND poi.qty > poi.received_qty
        """,
                (item_code, employee_function),
            )[0][0]
            or 0
        )

        # 6. Open GRN
        open_grn = (
            frappe.db.sql(
                """
            SELECT IFNULL(SUM(pri.qty - pri.returned_qty), 0)
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE pri.item_code = %s AND pri.employee_function = %s
            AND pr.docstatus = 1 AND pr.status IN ('To Bill', 'Partly Billed')
            AND pri.qty > pri.returned_qty
        """,
                (item_code, employee_function),
            )[0][0]
            or 0
        )

        # 7. Free Stock & Net Requirement
        free_stock = max(main_stock - flt(allocated_qty), 0)
        net_requirement = max(
            qty_required - (free_stock + open_pr + open_po + open_grn), 0
        )

        # 8. FEFO Batch & Usable Qty
        batch_info = frappe.db.sql(
            """
            SELECT b.expiry_date, SUM(sle.actual_qty) AS actual_qty
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabBatch` b ON b.name = sle.batch_no
            WHERE sle.item_code = %s AND sle.is_cancelled = 0
            AND (b.expiry_date >= %s OR b.expiry_date IS NULL)
            GROUP BY sle.batch_no, b.expiry_date
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY b.expiry_date ASC LIMIT 1
        """,
            (item_code, curr_today),
            as_dict=True,
        )

        # 9. Expired Quantity
        expired_qty = (
            frappe.db.sql(
                """
            SELECT IFNULL(SUM(sle.actual_qty), 0)
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabBatch` b ON b.name = sle.batch_no
            WHERE sle.item_code = %s AND sle.is_cancelled = 0
            AND b.expiry_date < %s
        """,
                (item_code, curr_today),
            )[0][0]
            or 0
        )

        usable_qty = flt(batch_info[0].actual_qty) if batch_info else 0
        expiry_date = batch_info[0].expiry_date if batch_info else None

        res.append(
            {
                "item_code": item_code,
                "item_name": item.get("item_name"),
                "qty_required": round(qty_required, 2),
                "total_stock": round(total_stock, 2),
                "main_stock": round(main_stock, 2),
                "lab_stock": round(lab_stock, 2),
                "allocated_qty": round(flt(allocated_qty), 2),
                "free_stock": round(free_stock, 2),
                "open_pr": round(flt(open_pr), 2),
                "open_po": round(flt(open_po), 2),
                "open_grn": round(flt(open_grn), 2),
                "net_requirement": round(net_requirement, 2),
                "usable_qty": round(usable_qty, 2),
                "expired_qty": round(flt(expired_qty), 2),
                "expiry_date": expiry_date,
            }
        )

    return res


# ═══════════════════════════════════════════════
# API : Get BOM Items for MA
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_bom_items_for_ma(batch_planning):
    bp = frappe.get_doc("Batches Planned", batch_planning)
    if not bp.batch_creation:
        frappe.throw("Batch Creation not linked!")

    bc = frappe.get_doc("Batch Creation", bp.batch_creation)
    matched = next(
        (
            row
            for row in (bc.custom_batch_details or [])
            if row.batch_planning_id
            in (
                batch_planning,
                bp.amended_from,
                batch_planning.rsplit("-", 1)[0],
            )
        ),
        None,
    )

    if not matched or not matched.bom_list:
        frappe.throw(f"BOM not found for: {batch_planning}")

    batch_key = f"{bp.batch_creation}-{matched.idx}"
    use_store = False
    items = []

    # Process Development / Machine Trial check
    if matched.batch_type in ("Process Development", "Machine Trial"):
        bom_store = frappe.db.get_value(
            "Batch BOM Store after Edit", {"batch_id": batch_key}, "name"
        )
        if bom_store:
            store_doc = frappe.get_doc("Batch BOM Store after Edit", bom_store)
            items = store_doc.bom_components or []
            use_store = True

    if not use_store:
        bom = frappe.get_doc("BOM", matched.bom_list)
        items = bom.exploded_items or bom.items or []

    # Get Warehouse
    ef = frappe.get_doc("Employee Function", bp.employee_function)
    warehouse = next(
        (r.store_warehouse for r in (ef.table_bukm or []) if r.store_warehouse),
        None,
    )

    result = []
    for item in items:
        qty = flt(
            item.qty
            if use_store
            else (item.qty_consumed_per_unit or item.stock_qty or item.qty)
        )
        uom = item.uom if use_store else (item.stock_uom or item.uom)
        item_code = item.item_code

        # Main Stock
        sle = frappe.db.sql(
            """
            SELECT qty_after_transaction FROM `tabStock Ledger Entry`
            WHERE item_code = %s AND warehouse = %s AND is_cancelled = 0
            ORDER BY posting_date DESC, posting_time DESC, creation DESC LIMIT 1
        """,
            (item_code, warehouse),
        )
        main_stock = flt(sle[0][0]) if sle else 0.0

        # Allocated Qty
        # FIX: Exclude both 'Deallocated' AND 'Stock Entry Done'
        allocated_qty = (
            frappe.db.sql(
                """
            SELECT IFNULL(SUM(mai.allocate_qty), 0)
            FROM `tabMaterial Allocation Item` mai
            JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
            WHERE mai.item_code = %s AND ma.employee_function = %s
            AND ma.allocation_status NOT IN ('Deallocated', 'Stock Entry Done')
            AND ma.docstatus != 2
        """,
                (item_code, bp.employee_function),
            )[0][0]
            or 0
        )

        free_stock = max(main_stock - flt(allocated_qty), 0)

        result.append(
            {
                "item_code": item_code,
                "item_name": item.item_name,
                "uom": uom,
                "quantity_required": round(qty, 6),
                "stock_available": round(free_stock, 2),
            }
        )

    return result


# ═══════════════════════════════════════════════
# API : Get Stock Entry Items
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_stock_entry_items(batch_planning):
    """
    Fetches all Stock Entries linked to the batch planning ID,
    extracts the underlying child items, and returns a merged list with combined quantities.
    """
    entries = frappe.get_all(
        "Stock Entry",
        filters={"custom_batch_planning": batch_planning},
        fields=["name"],
    )

    merged = {}
    for se in entries:
        items = frappe.get_all(
            "Stock Entry Detail",
            filters={"parent": se.name},
            fields=["item_code", "item_name", "qty", "uom", "s_warehouse", "t_warehouse"],
            ignore_permissions=True,
        )
        for item in items:
            if not item.item_code:
                continue
            if item.item_code in merged:
                merged[item.item_code]["qty"] += item.qty
            else:
                merged[item.item_code] = dict(item)

    return list(merged.values())