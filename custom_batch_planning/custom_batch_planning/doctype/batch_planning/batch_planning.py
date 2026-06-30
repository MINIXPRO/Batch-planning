# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt
from frappe.model.naming import make_autoname


# Toggle to enable/disable after submit logic
ENABLE_AFTER_SUBMIT_LOGIC = True

# =========================================================
# MONTH MAP
# =========================================================

MONTH_MAP = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


# =========================================================
# HELPER — SCT batches_planned increment / decrement
# =========================================================

def _update_sct_batches_planned(slot_opening_id, slot_booking_date, delta):
    """
    Increment or decrement batches_planned in Slot Capacity Detail.
    delta = +1 for increment, -1 for decrement.
    Uses direct DB set_value for performance (no heavy parent doc save).
    """
    if not slot_opening_id or not slot_booking_date:
        return

    slot_master = frappe.db.get_value(
        "Slot Opening", slot_opening_id, "slot_master"
    )
    if not slot_master:
        return

    sct_name = frappe.db.get_value(
        "Slot Capacity Tracker", {"slot_master": slot_master}, "name"
    )
    if not sct_name:
        return

    sct_detail = frappe.db.get_value(
        "Slot Capacity Detail",
        {
            "parent": sct_name,
            "parenttype": "Slot Capacity Tracker",
            "date": slot_booking_date,
            },
        ["name", "batches_planned"],
        as_dict=True,
    )

    if not sct_detail:
        frappe.log_error(
            message=f"Date {slot_booking_date} not found in SCT {sct_name}",
            title="SCT batches_planned update failed",
        )
        return

    new_planned = max(0, int(sct_detail.batches_planned or 0) + delta)
    frappe.db.set_value(
        "Slot Capacity Detail", sct_detail.name, "batches_planned", new_planned
    )


# ═══════════════════════════════════════════════
# PART 1 — API: Get Valid Slot Openings
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_valid_slot_openings(employee_function, current_doc=None):
    """
    Returns Slot Openings where at least one date still has
    remaining capacity (per-date check).
    """
    today = frappe.utils.today()

    valid = frappe.db.sql(
        """
        SELECT DISTINCT so.name
        FROM `tabSlot Opening` so
        INNER JOIN `tabSlot Booking CT` sb ON sb.parent = so.name
        WHERE so.employee_function = %s
          AND sb.slot_booking_date >= %s
          AND EXISTS (
              SELECT 1
              FROM `tabSlot Booking CT` sb2
              WHERE sb2.parent = so.name
                AND sb2.slot_booking_date >= %s
                AND (
                    SELECT COUNT(*)
                    FROM `tabBatches Planned` bp
                    WHERE bp.slot_opening_id = so.name
                      AND bp.slot_booking_date = sb2.slot_booking_date
                ) < sb2.booked_slots
          )
    """,
        (employee_function, today, today),
        as_dict=True,
    )

    return [r.name for r in valid]


# ═══════════════════════════════════════════════
# PART 2 — API: Get Next Batch Counter
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_next_batch_counter(slot_opening_id, batch_type, exclude_ids=None):
    """
    Returns the next Batch Planning ID for a given Slot Opening + Batch Type.
    MAX-based (not COUNT-based) to avoid reuse of deleted numbers.
    """
    exclude_ids = json.loads(exclude_ids) if exclude_ids else []

    if not slot_opening_id or not batch_type:
        return ""

    type_map = {
        "Manufacturing": "MFG",
        "Process Development": "PD",
        "Machine Trial": "MT",
    }
    short_code = type_map.get(batch_type, "EXP")

    max_committed = (
        frappe.db.sql(
            """
        SELECT COALESCE(MAX(
            FLOOR(CAST(SUBSTRING_INDEX(batch_planning_id, '-', -1) AS DECIMAL(10,0)))
        ), 0)
        FROM `tabBatches Planned`
        WHERE slot_opening_id = %s AND batch_type = %s
          AND batch_planning_id REGEXP '^.+-[0-9]+$'
    """,
            (slot_opening_id, batch_type),
        )[0][0]
        or 0
    )

    max_draft = (
        frappe.db.sql(
            """
        SELECT COALESCE(MAX(
            FLOOR(CAST(SUBSTRING_INDEX(bpd.batch_planning_id, '-', -1) AS DECIMAL(10,0)))
        ), 0)
        FROM `tabBatch Planning Detail` bpd
        JOIN `tabBatch Planning` bc ON bpd.parent = bc.name
        WHERE bpd.slot_opening_id = %s AND bpd.batch_type = %s
          AND bc.docstatus != 2
          AND bpd.batch_planning_id REGEXP '^.+-[0-9]+$'
    """,
            (slot_opening_id, batch_type),
        )[0][0]
        or 0
    )

    next_num = max(int(max_committed), int(max_draft)) + 1

    if exclude_ids:
        while (
            f"{slot_opening_id}-{short_code}-{str(next_num).zfill(2)}"
            in exclude_ids
        ):
            next_num += 1

    return f"{slot_opening_id}-{short_code}-{str(next_num).zfill(2)}"


# ═══════════════════════════════════════════════
# PART 3 — Batch Planning Document Class
# ═══════════════════════════════════════════════

class BatchPlanning(Document):

    # ─────────────────────────────────────────
    # AUTONAME
    # ─────────────────────────────────────────

    def autoname(self):
        mm = None
        yy = None

        if self.month:
            mm = MONTH_MAP.get(self.month.strip().lower())

        if not mm and self.slot_opening:
            first_date = frappe.db.sql(
                """
                SELECT MIN(slot_booking_date) AS d
                FROM `tabSlot Booking CT`
                WHERE parent = %s
                  AND slot_booking_date >= CURDATE()
            """,
                self.slot_opening,
                as_dict=True,
            )

            if first_date and first_date[0].d:
                dt = getdate(first_date[0].d)
                mm = str(dt.month).zfill(2)
                yy = str(dt.year)[2:]

        if not mm:
            dt = getdate(frappe.utils.today())
            mm = str(dt.month).zfill(2)
            yy = str(dt.year)[2:]

        if not yy:
            yy = str(getdate(frappe.utils.today()).year)[2:]

        prefix = f"BP-{yy}-{mm}-"

        current = frappe.db.sql(
            "SELECT `current` FROM `tabSeries` WHERE name = %s", prefix
        )
        next_num = int(current[0][0]) + 1 if current else 1
        candidate = f"{prefix}{str(next_num).zfill(3)}"

        while frappe.db.exists("Batch Planning", candidate):
            next_num += 1
            candidate = f"{prefix}{str(next_num).zfill(3)}"

        frappe.db.sql(
            """
            INSERT INTO `tabSeries` (name, `current`) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE `current` = %s
        """,
            (prefix, next_num, next_num),
        )

        self.name = candidate

    # ─────────────────────────────────────────
    # VALIDATE
    # ─────────────────────────────────────────

    def validate(self):
        # 1. Employee Function must be selected before Slot Opening
        if self.slot_opening and not self.custom_employee_function:
            frappe.throw(
                "Please select an Employee Function first before selecting a Slot Opening."
            )

        # Auto-fill read-only fields from slot_opening
        if self.slot_opening:
            slot_opening_data = frappe.db.get_value(
                "Slot Opening",
                self.slot_opening,
                ["project", "batch_start_date", "slot_master"],
                as_dict=True
            )
            if slot_opening_data:
                self.project = slot_opening_data.get("project")
                self.custom_slot_master = slot_opening_data.get("slot_master")
                batch_start_date = slot_opening_data.get("batch_start_date")
                if batch_start_date:
                    import calendar
                    dt = getdate(batch_start_date)
                    self.month = calendar.month_name[dt.month]
        # *** New check: ensure only one Batch Planning per Slot Opening ***
        if self.slot_opening:
            existing = frappe.db.get_value(
                "Batch Planning",
                {"slot_opening": self.slot_opening, "name": ["!=", self.name]},
                "name",
            )
            if existing:
                frappe.throw(
                    f"Slot Opening {self.slot_opening} is already linked to Batch Planning {existing}. Only one Batch Planning per Slot Opening allowed."
                )
        
        if self.custom_employee_function:
            self.custom_employee_headname = frappe.db.get_value(
                "Employee Function",
                self.custom_employee_function,
                "function_head_name"
            )

        # 2. Cross-doc duplicate Batch Planning ID check
        for row in self.custom_batch_details or []:
            if row.batch_planning_id:
                existing_bc = frappe.db.get_value(
                    "Batches Planned",
                    {"batch_planning_id": row.batch_planning_id},
                    "batch_planning",
                )
                if existing_bc and existing_bc != self.name:
                    frappe.throw(
                        f"⚠️ Duplicate Batch Planning ID Detected!\n\n"
                        f"<b>{row.batch_planning_id}</b> (Row {row.idx}) is already linked to "
                        f"Batches Planned under <b>{existing_bc}</b>.\n\n"
                        f"Each Batch Planning ID must be unique."
                    )

        # 3. Within-doc duplicate Batch Planning ID check
        seen_ids = []
        for row in self.custom_batch_details or []:
            if row.batch_planning_id:
                if row.batch_planning_id in seen_ids:
                    frappe.throw(
                        f"⚠️ Duplicate Batch Planning ID <b>{row.batch_planning_id}</b> "
                        f"found in Row {row.idx}. Each row must have a unique ID."
                    )
                seen_ids.append(row.batch_planning_id)

        # 4. Basic field order checks
        for row in self.custom_batch_details or []:
            if row.finished_item and not row.batch_type:
                frappe.throw(
                    f"Row {row.idx}: Please select a Batch Type before selecting a Finished Item."
                )
            if row.bom_list and not row.finished_item:
                frappe.throw(
                    f"Row {row.idx}: Please select a Finished Item before selecting a BOM."
                )

        # 5. Batch Planning ID fallback auto-generation
        for row in self.custom_batch_details or []:
            if not row.batch_planning_id and row.slot_booking_date:
                try:
                    parsed_date = frappe.utils.getdate(row.slot_booking_date)
                    year = parsed_date.strftime("%y")
                    month = parsed_date.strftime("%m")
                    prefix = f"BC-{year}-{month}-.###"
                    row.batch_planning_id = make_autoname(prefix)
                except Exception:
                    pass

        # 6. Capacity Check: Ensure batches planned per date do not exceed booked capacity on Slot Opening
        if self.slot_opening:
            # Get the booked capacity per date from the Slot Opening
            booked_slots_data = frappe.get_all(
                "Slot Booking CT",
                filters={"parent": self.slot_opening},
                fields=["slot_booking_date", "booked_slots"]
            )
            booked_map = {}
            for d in booked_slots_data:
                date_key = frappe.utils.getdate(d.slot_booking_date)
                booked_map[date_key] = booked_map.get(date_key, 0) + (d.booked_slots or 0)
            
            # Count the batches being created per date in this Batch Planning doc
            planned_map = {}
            for row in self.custom_batch_details or []:
                if row.slot_booking_date:
                    date_key = frappe.utils.getdate(row.slot_booking_date)
                    planned_map[date_key] = planned_map.get(date_key, 0) + 1
            
            for d_key, count in planned_map.items():
                allowed = booked_map.get(d_key, 0)
                if count > allowed:
                    frappe.throw(
                        f"Cannot create {count} batches for {d_key}. You only booked "
                        f"{allowed} slot(s) for this date on Slot Opening {self.slot_opening}."
                    )

    # ─────────────────────────────────────────
    # COMMON METHOD — Create Batches Planned
    # ─────────────────────────────────────────

    def create_batches_planned_records(self):
        count = 0

        for row in self.custom_batch_details or []:
            existing = frappe.db.get_value(
                "Batches Planned",
                {"batch_planning_id": row.batch_planning_id},
                ["name", "batch_planning"],
                as_dict=True,
            )

            if existing:
                if existing.batch_planning == self.name:
                    continue
                else:
                    frappe.throw(
                        f"⚠️ Batch Planning ID <b>{row.batch_planning_id}</b> "
                        f"already exists under <b>{existing.batch_planning}</b>."
                    )

            batch_key = f"{self.name}-{row.idx}"
            bom_store = frappe.db.get_value(
                "Batch BOM Store after Edit",
                {"batch_id": batch_key},
                "bom_name",
            )

            bp = frappe.new_doc("Batches Planned")
            bp.batch_planning_id = row.batch_planning_id
            bp.slot_opening_id = row.slot_opening_id
            if row.slot_opening_id:
                bp.project = frappe.db.get_value("Slot Opening", row.slot_opening_id, "project")

            bp.employee_function = self.custom_employee_function
            bp.employee_name = self.custom_employee_headname
            bp.month = self.month
            bp.batch_type = row.batch_type
            bp.finished_item = row.finished_item
            bp.slot_booking_date = row.slot_booking_date
            bp.batch_planning = self.name
            bp.bom_list = bom_store if bom_store else row.bom_list

            bp.flags.ignore_permissions = True
            bp.flags.ignore_validate = True
            bp.flags.ignore_mandatory = True
            bp.flags.ignore_workflow = True

            bp.insert(ignore_permissions=True, ignore_mandatory=True)

            # ── SCT batches_planned increment (+1) ──
            _update_sct_batches_planned(
                row.slot_opening_id, row.slot_booking_date, +1
            )

            update_data = {
                "workflow_state": getattr(row, 'status', None),
            }
            if getattr(row, 'status', None) == "Approved":
                update_data["docstatus"] = 1
            elif getattr(row, 'status', None) == "Cancelled":
                update_data["docstatus"] = 2

            frappe.db.set_value(
                "Batches Planned", bp.name, update_data, update_modified=False
            )
            count += 1

        frappe.db.commit()
        return count

    # ─────────────────────────────────────────
    # HOOKS
    # ─────────────────────────────────────────

    def on_submit(self):
        if not ENABLE_AFTER_SUBMIT_LOGIC:
            return
        if getattr(self, 'workflow_state', None) != "Approved":
            return
        self.create_batches_planned_records()

    def on_trash(self):
        bp_list = frappe.get_all(
            "Batches Planned",
            filters={"batch_planning": self.name},
            fields=["name", "slot_opening_id", "slot_booking_date"],
        )

        # Pehle saare SCT decrements karo
        for bp in bp_list:
            _update_sct_batches_planned(
                bp.slot_opening_id, bp.slot_booking_date, -1
            )

        # Flag set karo — batches_planned.py ka on_trash dobara -1 na kare
        frappe.flags.skip_sct_decrement = True
        try:
            for bp in bp_list:
                frappe.delete_doc(
                    "Batches Planned",
                    bp.name,
                    ignore_permissions=True,
                    force=True,
                )
        finally:
            # Flag hamesha reset karo chahe error aaye ya na aaye
            frappe.flags.skip_sct_decrement = False


# ═══════════════════════════════════════════════
# PART 4 — FRONTEND BUTTON API
# ═══════════════════════════════════════════════

@frappe.whitelist()
def create_bulk_material_allocations(batch_planning_name):
    """
    Consolidated Flow:
    Combine all BOM items from all Batches Planned under this BP into a single Material Allocation doc.
    """
    parent_doc = frappe.get_doc("Batch Planning", batch_planning_name)
    if getattr(parent_doc, 'workflow_state', None) != "Approved":
        frappe.throw("Document is not in Approved state.")
    if parent_doc.docstatus != 1:
        frappe.throw("Document is not submitted yet.")

    warning_message = ""
    exists = frappe.db.exists(
        "Material Allocation",
        {
            "batch_planning": batch_planning_name,
            "allocation_status": ["!=", "Deallocated"],
            "docstatus": ["!=", 2]
        }
    )
    if exists:
        warning_message = f"Note: A Material Allocation ({exists}) already exists for Batch Planning {batch_planning_name}."

    batches = frappe.get_all(
        "Batches Planned",
        filters={"batch_planning": batch_planning_name},
        fields=["name", "employee_function"]
    )

    if not batches:
        frappe.throw("No Batches Planned found for this Batch Planning.")

    # Gather comma-separated string of Batches Planned names
    batches_planned_str = ", ".join([b.name for b in batches])

    # Get target warehouse for this batch planning (from parent_doc's custom_employee_function)
    if not parent_doc.custom_employee_function:
        frappe.throw("Employee Function is not set on Batch Planning.")

    ef = frappe.get_doc("Employee Function", parent_doc.custom_employee_function)
    warehouse = next(
        (r.store_warehouse for r in (ef.table_bukm or []) if r.store_warehouse),
        None,
    )

    if not warehouse:
        frappe.throw(f"No store warehouse found for Employee Function {parent_doc.custom_employee_function}")

    # Combine all BOM items (using get_consolidated_bom_components)
    consolidated_items = get_consolidated_bom_components(batch_planning_name)
    if not consolidated_items:
        frappe.throw("No items found to allocate.")

    # Create one consolidated Material Allocation doc data
    ma_data = {
        "doctype": "Material Allocation",
        "batch_planning": batch_planning_name,
        "batches_planned": batches_planned_str,
        "employee_function": parent_doc.custom_employee_function,
        "project_id": parent_doc.project,
        "project_name": frappe.db.get_value("Project", parent_doc.project, "project_name") if parent_doc.project else "",
        "workflow_state": "Draft",
        "material_allocation": []
    }

    for item in consolidated_items:
        item_code = item["item_code"]
        qty_required = flt(item["qty"])

        # Free stock — no batch planning linked
        free_stock = flt(frappe.db.sql("""
            SELECT IFNULL(SUM(actual_qty), 0)
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
            AND warehouse = %s
            AND (batch_planning_id IS NULL OR batch_planning_id = '')
            AND is_cancelled = 0
        """, (item_code, warehouse))[0][0] or 0.0)

        # Stock tagged with this Batch Planning (received via GRN, in main warehouse)
        bp_tagged_stock = flt(frappe.db.sql("""
            SELECT IFNULL(SUM(actual_qty), 0)
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
            AND warehouse = %s
            AND batch_planning_id = %s
            AND is_cancelled = 0
        """, (item_code, warehouse, batch_planning_name))[0][0] or 0.0)

        # Total stock available for allocation
        stock_qty = free_stock + bp_tagged_stock

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
                (item_code, parent_doc.custom_employee_function),
            )[0][0]
            or 0
        )
        # stock_qty already = free_stock + bp_tagged_stock
        # No need to subtract allocated_qty here — handled at allocation time via get_batches

        ma_data["material_allocation"].append({
            "doctype": "Material Allocation Item",
            "parenttype": "Material Allocation",
            "parentfield": "material_allocation",
            "item_code": item_code,
            "item_name": item["item_name"],
            "uom": item["uom"],
            "quantity_required": qty_required,
            "allocate_qty": qty_required,
            "stock_available": stock_qty  # now = free_stock + bp_tagged_stock
        })
    if warning_message:
        ma_data["warning"] = warning_message
    return ma_data


# ═══════════════════════════════════════════════

@frappe.whitelist()
def create_batches_planned(doc_name):
    """Called from a custom JS button on the Batch Planning form."""
    doc = frappe.get_doc("Batch Planning", doc_name)

    if getattr(doc, 'workflow_state', None) != "Approved":
        frappe.throw("Document is not in Approved state.")
    if doc.docstatus != 1:
        frappe.throw("Document is not submitted yet.")

    count = doc.create_batches_planned_records()
    return f"{count} Batches Planned record(s) created successfully."


# ═══════════════════════════════════════════════
# PART 5 — BOM Item Details
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_item_details_for_bom(item_codes):
    item_codes = json.loads(item_codes)
    if not item_codes:
        return []

    return frappe.db.sql(
        """
        SELECT name, item_group, min_order_qty, safety_stock
        FROM `tabItem`
        WHERE name IN %(items)s
    """,
        {"items": item_codes},
        as_dict=True,
    )


@frappe.whitelist()
def get_consolidated_bom_components(doc_name):
    doc = frappe.get_doc("Batch Planning", doc_name)
    components = {}

    for row in doc.custom_batch_details or []:
        if not row.bom_list:
            continue
        
        batch_key = f"{doc.name}-{row.idx}"
        bom_store = frappe.db.get_value(
            "Batch BOM Store after Edit", {"batch_id": batch_key}, "name"
        )
        
        use_store = False
        items = []
        if bom_store:
            store_doc = frappe.get_doc("Batch BOM Store after Edit", bom_store)
            items = store_doc.bom_components or []
            use_store = True
        else:
            bom = frappe.get_doc("BOM", row.bom_list)
            items = bom.exploded_items or bom.items or []
            
        for item in items:
            qty = flt(
                item.qty
                if use_store
                else (item.qty_consumed_per_unit or item.stock_qty or item.qty)
            )
            uom = item.uom if use_store else (item.stock_uom or item.uom)
            item_code = item.item_code
            item_name = item.item_name
            
            if item_code not in components:
                components[item_code] = {
                    "item_code": item_code,
                    "item_name": item_name,
                    "uom": uom,
                    "qty": 0.0
                }
            components[item_code]["qty"] += qty

    # Convert to sorted list
    sorted_components = sorted(components.values(), key=lambda x: x["item_code"])
    return sorted_components


@frappe.whitelist()
def get_material_planning_data(doc_name):
    doc = frappe.get_doc("Batch Planning", doc_name)
    employee_function = doc.custom_employee_function
    if not employee_function:
        frappe.throw("Employee Function is not set on this document.")

    ef_doc = frappe.get_doc("Employee Function", employee_function)

    # Get Main Warehouse from table_bukm
    warehouse = None
    for r in (ef_doc.table_bukm or []):
        if r.store_warehouse:
            warehouse = r.store_warehouse
            break

    if not warehouse:
        frappe.throw(f"No store warehouse found in Employee Function '{employee_function}'.")

    # Get Lab Warehouses from table_szrn
    lab_warehouses = [
        r.lab_warehouse for r in (ef_doc.get("table_szrn") or []) if r.lab_warehouse
    ]

    # Pre-build a list of batches with their BOM items
    # Order: by row index (idx) to deduct greedily batch-by-batch
    batches_data = []
    for row in doc.custom_batch_details or []:
        if not row.bom_list or not row.batch_planning_id:
            continue
        
        batch_key = f"{doc.name}-{row.idx}"
        bom_store = frappe.db.get_value(
            "Batch BOM Store after Edit", {"batch_id": batch_key}, "name"
        )
        
        use_store = False
        components = []
        if bom_store:
            store_doc = frappe.get_doc("Batch BOM Store after Edit", bom_store)
            components = store_doc.bom_components or []
            use_store = True
        else:
            bom = frappe.get_doc("BOM", row.bom_list)
            components = bom.exploded_items or bom.items or []
            
        batch_items = {}
        for comp in components:
            item_code = comp.item_code
            qty = flt(
                comp.qty if use_store
                else (comp.qty_consumed_per_unit or comp.stock_qty or comp.qty)
            )
            batch_items[item_code] = batch_items.get(item_code, 0.0) + qty
            
        batches_data.append({
            "batch_planning_id": row.batch_planning_id,
            "items": batch_items
        })

    # Get consolidated items
    consolidated_items = get_consolidated_bom_components(doc_name)

    res = []
    curr_today = frappe.utils.today()

    for item in consolidated_items:
        item_code = item.get("item_code")
        qty_required = flt(item.get("qty"))

        # 1. Main Warehouse Stock (from Bin)
        main_stock = flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))

        # 2. Lab Warehouse Stock (from Bin)
        lab_stock = 0.0
        for lab_wh in lab_warehouses:
            lab_stock += flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": lab_wh}, "actual_qty"))

        total_stock = main_stock + lab_stock

        # 3. Allocated Quantity (Global for this EF)
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

        # 4. Free Stock Calculation (SLE where batch_planning_id IS NULL)
        free_stock = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(actual_qty), 0)
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
            AND warehouse = %s
            AND (batch_planning_id IS NULL OR batch_planning_id = '')
            AND is_cancelled = 0
            """,
            (item_code, warehouse)
        )[0][0] or 0.0)
        free_stock = max(free_stock, 0.0)

        # Stock Available Calculation (free stock + stock tagged with this Batch Planning)
        stock_available = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(actual_qty), 0)
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
            AND warehouse = %s
            AND (
                batch_planning_id IS NULL
                OR batch_planning_id = ''
                OR batch_planning_id = %s
            )
            AND is_cancelled = 0
            """,
            (item_code, warehouse, doc.name)
        )[0][0] or 0.0)
        stock_available = max(stock_available, 0.0)

        # 5. Open MR, PO, GRN details (Global and BP levels)
        
        # A. Open MR
        global_mr_qty = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(mri.qty - mri.ordered_qty), 0)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s
            AND mr.custom_employee_function = %s
            AND mr.docstatus = 1
            AND mr.status NOT IN ('Ordered', 'Stopped', 'Cancelled')
            AND mri.qty > mri.ordered_qty
            """,
            (item_code, employee_function)
        )[0][0] or 0.0)

        bp_mr_qty = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(mri.qty - mri.ordered_qty), 0)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s
            AND mri.batch_planning_id = %s
            AND mr.docstatus = 1
            AND mr.status NOT IN ('Ordered', 'Stopped', 'Cancelled')
            AND mri.qty > mri.ordered_qty
            """,
            (item_code, doc.name)
        )[0][0] or 0.0)

        # B. Open PO
        global_po_qty = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(poi.qty - poi.received_qty), 0)
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE poi.item_code = %s
            AND poi.employee_function = %s
            AND po.docstatus = 1
            AND po.status NOT IN ('Completed', 'Cancelled')
            AND poi.qty > poi.received_qty
            """,
            (item_code, employee_function)
        )[0][0] or 0.0)

        bp_po_qty = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(poi.qty - poi.received_qty), 0)
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE poi.item_code = %s
            AND poi.batch_planning_id = %s
            AND po.docstatus = 1
            AND po.status NOT IN ('Completed', 'Cancelled')
            AND poi.qty > poi.received_qty
            """,
            (item_code, doc.name)
        )[0][0] or 0.0)

        # C. Open GRN
        global_grn_qty = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(pri.qty - pri.returned_qty), 0)
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE pri.item_code = %s
            AND pri.employee_function = %s
            AND pr.docstatus = 1
            AND pr.status NOT IN ('Completed', 'Cancelled')
            AND pri.qty > pri.returned_qty
            """,
            (item_code, employee_function)
        )[0][0] or 0.0)

        bp_grn_qty = flt(frappe.db.sql(
            """
            SELECT IFNULL(SUM(pri.qty - pri.returned_qty), 0)
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE pri.item_code = %s
            AND pri.batch_planning_id = %s
            AND pr.docstatus = 1
            AND pr.status NOT IN ('Completed', 'Cancelled')
            AND pri.qty > pri.returned_qty
            """,
            (item_code, doc.name)
        )[0][0] or 0.0)

        # 6. Consolidated Net Requirement Calculation using BP level quantities only
        net_requirement = max(qty_required - free_stock - bp_mr_qty - bp_po_qty - bp_grn_qty, 0.0)

        # 7. FEFO Batch & Usable Qty
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

        # 8. Expired Quantity
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
                "uom": item.get("uom"),
                "qty_required": round(qty_required, 2),
                "total_stock": round(total_stock, 2),
                "main_stock": round(main_stock, 2),
                "lab_stock": round(lab_stock, 2),
                "allocated_qty": round(flt(allocated_qty), 2),
                "free_stock": round(free_stock, 2),
                "stock_available": round(stock_available, 2),
                "global_mr_qty": global_mr_qty,
                "bp_mr_qty": bp_mr_qty,
                "global_po_qty": global_po_qty,
                "bp_po_qty": bp_po_qty,
                "global_grn_qty": global_grn_qty,
                "bp_grn_qty": bp_grn_qty,
                # Keep backward compatibility keys
                "open_pr": round(bp_mr_qty, 2),
                "open_po": round(bp_po_qty, 2),
                "open_grn": round(bp_grn_qty, 2),
                "mr_total_qty": round(bp_mr_qty, 2),
                "po_pending_qty": round(bp_po_qty, 2),
                "pr_total_qty": round(bp_grn_qty, 2),
                "net_requirement": round(net_requirement, 2),
                "usable_qty": round(usable_qty, 2),
                "expired_qty": round(flt(expired_qty), 2),
                "expiry_date": expiry_date,
            }
        )

    return {
        "results": res,
        "warehouse": warehouse
    }


@frappe.whitelist()
def make_material_request(doc_name):
    """Create a consolidated Material Request from Batch Planning, with warehouse auto-filled for each item."""
    doc = frappe.get_doc("Batch Planning", doc_name)
    if not doc.custom_employee_function:
        frappe.throw("Employee Function is not set on this Batch Planning.")
    # Retrieve main warehouse from Employee Function (table_bukm)
    ef_doc = frappe.get_doc("Employee Function", doc.custom_employee_function)
    warehouse = None
    for r in (ef_doc.table_bukm or []):
        if r.store_warehouse:
            warehouse = r.store_warehouse
            break
    if not warehouse:
        frappe.throw(f"No store warehouse found in Employee Function '{doc.custom_employee_function}'.")
    # Consolidate items across batches
    items = get_consolidated_bom_components(doc_name)
    if not items:
        frappe.throw("No items found to create Material Request.")
    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Manufacture"
    mr.custom_employee_function = doc.custom_employee_function
    mr.project = doc.project
    mr.custom_batch_planning_no = doc.name
    mr.flags.ignore_permissions = True
    for comp in items:
        row = mr.append("items", {})
        row.item_code = comp.get("item_code")
        row.qty = comp.get("qty")
        row.uom = comp.get("uom")
        row.warehouse = warehouse
        row.conversion_factor = 1
        row.batch_planning_id = doc.name
    mr.insert(ignore_permissions=True)
    frappe.db.commit()
    return mr.name

@frappe.whitelist()
def temp_db_fix():
    # 1. Drop empty tabBatch Planning table if it exists
    frappe.db.sql("DROP TABLE IF EXISTS `tabBatch Planning`")
    # 2. Rename tabBatch Creation to tabBatch Planning
    frappe.db.sql("RENAME TABLE `tabBatch Creation` TO `tabBatch Planning`")
    # 3. Rename batch_creation column to batch_planning in tabBatches Planned
    columns = [c[0] for c in frappe.db.sql("DESC `tabBatches Planned`")]
    if "batch_creation" in columns and "batch_planning" not in columns:
        frappe.db.sql("ALTER TABLE `tabBatches Planned` CHANGE COLUMN `batch_creation` `batch_planning` VARCHAR(255)")
    
    # 4. Check if renamed doctype options and fields are correct
    return {
        "status": "Fix completed successfully!",
        "tabBatch Planning count": frappe.db.sql("select count(*) from `tabBatch Planning`")[0][0],
        "tabBatches Planned columns": [c[0] for c in frappe.db.sql("DESC `tabBatches Planned`")]
    }


@frappe.whitelist()
def get_batch_wise_shortages(doc_name):
    doc = frappe.get_doc("Batch Planning", doc_name)
    
    # 1. Sum qty_needed across all batches by item_code
    item_requirements = {}
    for row in doc.custom_batch_details or []:
        if not row.bom_list or not row.batch_planning_id:
            continue

        batch_key = f"{doc.name}-{row.idx}"
        bom_store = frappe.db.get_value(
            "Batch BOM Store after Edit", {"batch_id": batch_key}, "name"
        )

        use_store = False
        items = []
        if bom_store:
            store_doc = frappe.get_doc("Batch BOM Store after Edit", bom_store)
            items = store_doc.bom_components or []
            use_store = True
        else:
            bom = frappe.get_doc("BOM", row.bom_list)
            items = bom.exploded_items or bom.items or []

        for item in items:
            item_code = item.item_code
            item_name = item.item_name
            uom = item.uom if use_store else (item.stock_uom or item.uom)
            qty_needed = flt(
                item.qty if use_store
                else (item.qty_consumed_per_unit or item.stock_qty or item.qty)
            )
            
            if item_code not in item_requirements:
                item_requirements[item_code] = {
                    "item_code": item_code,
                    "item_name": item_name,
                    "uom": uom,
                    "qty_needed": 0.0
                }
            item_requirements[item_code]["qty_needed"] += qty_needed

    shortages = []
    for item_code, req in item_requirements.items():
        # Query total open MR qty for this item under this Batch Planning
        open_mr_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(mri.qty - mri.ordered_qty), 0)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s
            AND mr.custom_batch_planning_no = %s
            AND mr.docstatus = 1
            AND mr.status NOT IN ('Stopped', 'Cancelled', 'Ordered')
            AND mri.qty > mri.ordered_qty
        """, (item_code, doc.name))[0][0] or 0

        shortage_qty = req["qty_needed"] - flt(open_mr_qty)

        if shortage_qty <= 0:
            continue

        shortages.append({
            "item_code": item_code,
            "item_name": req["item_name"],
            "qty": round(shortage_qty, 4),
            "uom": req["uom"],
            "custom_batch_planning_no": doc.name,
            "schedule_date": frappe.utils.add_days(frappe.utils.today(), 1)
        })

    return sorted(shortages, key=lambda x: x["item_code"])


@frappe.whitelist()
def get_project_finished_items(doctype, txt, searchfield, start, page_len, filters):
    project = filters.get("project") if filters else None
    
    if project:
        query = """
            SELECT DISTINCT bom.item
            FROM `tabBOM` bom
            INNER JOIN `tabItem` item ON item.name = bom.item
            WHERE bom.project = %(project)s
              AND bom.docstatus = 1
              AND bom.is_active = 1
              AND item.item_group = 'Finish Goods'
        """
        params = {"project": project}
        if txt:
            query += " AND bom.item LIKE %(txt)s"
            params["txt"] = f"%{txt}%"
        
        query += f" LIMIT {int(start)}, {int(page_len)}"
        return frappe.db.sql(query, params, as_dict=False)
    else:
        # Fallback to all Finish Goods items if no project is specified
        query = """
            SELECT name
            FROM `tabItem`
            WHERE item_group = 'Finish Goods'
              AND disabled = 0
        """
        params = {}
        if txt:
            query += " AND (name LIKE %(txt)s OR item_name LIKE %(txt)s)"
            params["txt"] = f"%{txt}%"
            
        query += f" LIMIT {int(start)}, {int(page_len)}"
        return frappe.db.sql(query, params, as_dict=False)


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
        filters={"custom_batch_planning_no": batch_planning},
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


# ═══════════════════════════════════════════════
# API : Get Item Issue Data (Consolidated Items)
# ═══════════════════════════════════════════════
@frappe.whitelist()
def get_item_issue_data(batch_planning):
    """
    Fetches all SUBMITTED Stock Entries linked to this Batch Planning,
    extracts child items, and returns a merged/deduplicated list.
    Duplicate items are merged by item_code with quantities summed.
    """
    entries = frappe.get_all(
        "Stock Entry",
        filters={
            "custom_batch_planning_no": batch_planning,
            "docstatus": 1,
        },
        fields=["name"],
    )

    if not entries:
        return []

    # Fetch all child items in one query for performance
    se_names = [e.name for e in entries]
    items = frappe.db.sql(
        """
        SELECT
            sed.item_code,
            sed.item_name,
            sed.qty,
            sed.uom,
            sed.s_warehouse,
            sed.t_warehouse
        FROM `tabStock Entry Detail` sed
        WHERE sed.parent IN %s
        AND sed.item_code IS NOT NULL
        AND sed.item_code != ''
        ORDER BY sed.item_code
        """,
        (se_names,),
        as_dict=True,
    )

    # Merge duplicates by item_code — sum quantities
    merged = {}
    for item in items:
        code = item.item_code
        if code in merged:
            merged[code]["qty"] = flt(merged[code]["qty"]) + flt(item.qty)
        else:
            merged[code] = {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": flt(item.qty),
                "uom": item.uom,
                "s_warehouse": item.s_warehouse,
                "t_warehouse": item.t_warehouse,
            }

    # Round quantities for display
    result = []
    for item in merged.values():
        item["qty"] = round(item["qty"], 3)
        result.append(item)

    return result

@frappe.whitelist()
def on_stock_entry_submit(doc, method):
    """
    When Stock Entry is submitted:
    1. Add one row to stock_entry_log child table on Batch Planning
    2. Add one row per item to item_issue_log child table on Batch Planning, aggregating qty for same item
    """
    batch_planning = doc.get("custom_batch_planning_no") or doc.get("custom_batch_planning")
    if not batch_planning:
        return

    # Check if doc exists
    if not frappe.db.exists("Batch Planning", batch_planning):
        return

    bp = frappe.get_doc("Batch Planning", batch_planning)

    # Check if Stock Entry already logged (avoid duplicates on re-submit)
    existing_se = [r.stock_entry for r in (bp.stock_entry_log or [])]
    if doc.name in existing_se:
        return

    bp.append("stock_entry_log", {
        "stock_entry": doc.name,
        "date": doc.posting_date,
        "from_warehouse": doc.from_warehouse,
        "to_warehouse": doc.to_warehouse,
        "status": "Submitted"
    })

    # Aggregate or add one row per item to item_issue_log
    existing_items = {}
    for r in (bp.item_issue_log or []):
        existing_items[r.item_code] = r

    for item in doc.items:
        if not item.item_code:
            continue
            
        if item.item_code in existing_items:
            existing_row = existing_items[item.item_code]
            existing_row.qty += item.qty
            if doc.name not in (existing_row.stock_entry or ""):
                existing_row.stock_entry = f"{existing_row.stock_entry}, {doc.name}" if existing_row.stock_entry else doc.name
        else:
            new_row = bp.append("item_issue_log", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "uom": item.uom,
                "from_warehouse": item.s_warehouse,
                "to_warehouse": item.t_warehouse,
                "stock_entry": doc.name
            })
            existing_items[item.item_code] = new_row

    bp.flags.ignore_permissions = True
    bp.flags.ignore_validate_update_after_submit = True
    bp.save(ignore_permissions=True)
    frappe.db.commit()