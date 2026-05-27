# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import getdate

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
        JOIN `tabBatch Creation` bc ON bpd.parent = bc.name
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
# PART 3 — Batch Creation Document Class
# ═══════════════════════════════════════════════

class BatchCreation(Document):

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

        prefix = f"BC-{yy}-{mm}-"
        current = frappe.db.sql(
            "SELECT `current` FROM `tabSeries` WHERE name = %s", prefix
        )
        next_num = int(current[0][0]) + 1 if current else 1
        candidate = f"{prefix}{str(next_num).zfill(3)}"

        while frappe.db.exists("Batch Creation", candidate):
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

        # 2. Cross-doc duplicate Batch Planning ID check
        for row in self.custom_batch_details or []:
            if row.batch_planning_id:
                existing_bc = frappe.db.get_value(
                    "Batches Planned",
                    {"batch_planning_id": row.batch_planning_id},
                    "batch_creation",
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
                    row.batch_planning_id = frappe.model.naming.make_autoname(
                        prefix
                    )
                except Exception:
                    pass

        # # 6. Per-date capacity check
        # if self.slot_opening:
        #     for row in self.custom_batch_details or []:
        #         if not row.slot_booking_date:
        #             continue

        #         date_capacity = int(
        #             frappe.db.get_value(
        #                 "Slot Booking CT",
        #                 {
        #                     "parent": self.slot_opening,
        #                     "slot_booking_date": row.slot_booking_date,
        #                 },
        #                 "booked_slots",
        #             )
        #             or 0
        #         )

        #         already_created = frappe.db.count(
        #             "Batches Planned",
        #             {
        #                 "slot_opening_id": self.slot_opening,
        #                 "slot_booking_date": row.slot_booking_date,
        #             },
        #         )

        #         current_doc_count = len(
        #             [
        #                 r
        #                 for r in self.custom_batch_details or []
        #                 if r.slot_booking_date == row.slot_booking_date
        #                 and r.idx != row.idx
        #             ]
        #         )

        #         total = already_created + current_doc_count + 1

        #         if total > date_capacity:
        #             frappe.throw(
        #                 f"⚠️ Slot fully booked for <b>{row.slot_booking_date}</b>! "
        #                 f"Capacity: {date_capacity} | Already Created: {already_created}"
        #             )

    # ─────────────────────────────────────────
    # COMMON METHOD — Create Batches Planned
    # ─────────────────────────────────────────

    def create_batches_planned_records(self):
        count = 0

        for row in self.custom_batch_details or []:
            existing = frappe.db.get_value(
                "Batches Planned",
                {"batch_planning_id": row.batch_planning_id},
                ["name", "batch_creation"],
                as_dict=True,
            )

            if existing:
                if existing.batch_creation == self.name:
                    continue
                else:
                    frappe.throw(
                        f"⚠️ Batch Planning ID <b>{row.batch_planning_id}</b> "
                        f"already exists under <b>{existing.batch_creation}</b>."
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
                bp.project = frappe.db.get_value(
                    "Slot Opening", row.slot_opening_id, "custom_project"
                )
            if not bp.project:
                bp.project = getattr(self, "custom_project", None)

            bp.employee_function = self.custom_employee_function
            bp.employee_name = self.custom_function_head_name
            bp.month = self.month
            bp.batch_type = row.batch_type
            bp.finished_item = row.finished_item
            bp.slot_booking_date = row.slot_booking_date
            bp.batch_creation = self.name
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
                "status": row.status,
                "workflow_state": row.status,
            }
            if row.status == "Approved":
                update_data["docstatus"] = 1
            elif row.status == "Cancelled":
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
        if self.workflow_state != "Approved":
            return
        self.create_batches_planned_records()

    def on_trash(self):
        bp_list = frappe.get_all(
            "Batches Planned",
            filters={"batch_creation": self.name},
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
def create_batches_planned(doc_name):
    """Called from a custom JS button on the Batch Creation form."""
    doc = frappe.get_doc("Batch Creation", doc_name)

    if doc.workflow_state != "Approved":
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