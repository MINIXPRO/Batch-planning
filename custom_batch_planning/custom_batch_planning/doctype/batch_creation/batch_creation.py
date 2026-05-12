# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

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


# ═══════════════════════════════════════════════
# PART 1 — API: Get Valid Slot Openings
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_valid_slot_openings(employee_function, current_doc=None):

    today = frappe.utils.today()

    valid = frappe.db.sql("""
        SELECT DISTINCT so.name
        FROM `tabSlot Opening` so
        INNER JOIN `tabSlot Booking CT` sb
            ON sb.parent = so.name
        WHERE so.employee_function = %s
        AND sb.slot_booking_date >= %s
        AND so.name NOT IN (
            SELECT slot_opening FROM `tabBatch Creation`
            WHERE docstatus != 2
            AND slot_opening IS NOT NULL
            AND name != %s
        )
    """, (employee_function, today, current_doc or ""), as_dict=True)

    return [r.name for r in valid]


# ═══════════════════════════════════════════════
# PART 2 — Batch Creation Logic
# ═══════════════════════════════════════════════

class BatchCreation(Document):

    # =====================================================
    # AUTONAME
    # =====================================================

    def autoname(self):
        """
        Generate name in format:
        BC-YY-MM-001
        """

        mm = None
        yy = None

        # Strategy 1 → month field
        if self.month:
            mm = MONTH_MAP.get(
                self.month.strip().lower()
            )

        # Strategy 2 → Slot Opening booking date
        if not mm and self.slot_opening:

            first_date = frappe.db.sql(
                """
                SELECT MIN(slot_booking_date) as d
                FROM `tabSlot Booking CT`
                WHERE parent = %s
                AND slot_booking_date >= CURDATE()
                """,
                self.slot_opening,
                as_dict=True
            )

            if first_date and first_date[0].d:

                dt = getdate(first_date[0].d)

                mm = str(dt.month).zfill(2)
                yy = str(dt.year)[2:]

        # Strategy 3 → Current date fallback
        if not mm:

            from frappe.utils import today

            dt = getdate(today())

            mm = str(dt.month).zfill(2)
            yy = str(dt.year)[2:]

        # Year fallback
        if not yy:

            from frappe.utils import today

            yy = str(getdate(today()).year)[2:]

        # Prefix
        prefix = f"BC-{yy}-{mm}-"

        # Get current sequence
        current = frappe.db.sql(
            """
            SELECT `current`
            FROM `tabSeries`
            WHERE name = %s
            """,
            prefix
        )

        next_num = (
            int(current[0][0]) + 1
            if current
            else 1
        )

        candidate = (
            f"{prefix}{str(next_num).zfill(3)}"
        )

        # Ensure uniqueness
        while frappe.db.exists(
            "Batch Creation",
            candidate
        ):

            next_num += 1

            candidate = (
                f"{prefix}{str(next_num).zfill(3)}"
            )

        # Update tabSeries
        frappe.db.sql(
            """
            INSERT INTO `tabSeries`
            (name, `current`)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
            `current` = %s
            """,
            (prefix, next_num, next_num)
        )

        self.name = candidate

    # =====================================================
    # VALIDATE
    # =====================================================

    def validate(self):

        # Prevent duplicate Batch Creation
        if self.slot_opening:

            existing = frappe.db.get_value(
                "Batch Creation",
                {
                    "slot_opening": self.slot_opening,
                    "name": ["!=", self.name],
                    "docstatus": ["!=", 2]
                },
                "name"
            )

            if existing:

                frappe.throw(
                    f"⚠️ Batch Creation "
                    f"<b>{existing}</b> already exists "
                    f"for Slot Opening "
                    f"<b>{self.slot_opening}</b>."
                )

        # Generate Batch Planning IDs
        for row in (self.custom_batch_details or []):

            if not row.batch_planning_id:

                if row.slot_booking_date:

                    try:

                        parsed_date = frappe.utils.getdate(
                            row.slot_booking_date
                        )

                        year = parsed_date.strftime("%y")
                        month = parsed_date.strftime("%m")

                        prefix = (
                            f"BC-{year}-{month}-.###"
                        )

                        row.batch_planning_id = (
                            frappe.model.naming.make_autoname(
                                prefix
                            )
                        )

                    except Exception:
                        pass

    # =====================================================
    # COMMON METHOD
    # =====================================================

    def create_batches_planned_records(self):

        count = 0

        for row in (self.custom_batch_details or []):

            # -----------------------------------------
            # CHECK EXISTING
            # -----------------------------------------

            existing = frappe.db.get_value(
                "Batches Planned",
                {
                    "batch_planning_id":
                    row.batch_planning_id
                },
                "name"
            )

            # Cancel & delete old document
            if existing:

                old_doc = frappe.get_doc(
                    "Batches Planned",
                    existing
                )

                if old_doc.docstatus == 1:

                    old_doc.flags.ignore_permissions = True
                    old_doc.flags.ignore_workflow = True

                    old_doc.cancel()

                frappe.delete_doc(
                    "Batches Planned",
                    existing,
                    force=1,
                    ignore_permissions=True
                )

            # -----------------------------------------
            # GENERATE BATCH KEY
            # -----------------------------------------

            batch_key = (
                f"{self.name}-{row.idx}"
            )

            # -----------------------------------------
            # FETCH BOM
            # -----------------------------------------

            bom_store = frappe.db.get_value(
                "Batch BOM Store after Edit",
                {"batch_id": batch_key},
                "bom_name"
            )

            # -----------------------------------------
            # CREATE DOCUMENT
            # -----------------------------------------

            bp = frappe.new_doc(
                "Batches Planned"
            )

            bp.batch_planning_id = (
                row.batch_planning_id
            )

            bp.slot_opening_id = (
                row.slot_opening_id
            )

            # Project from Slot Opening
            if row.slot_opening_id:

                bp.project = frappe.db.get_value(
                    "Slot Opening",
                    row.slot_opening_id,
                    "custom_project"
                )

            # Fallback project
            if not bp.project:

                bp.project = getattr(
                    self,
                    "custom_project",
                    None
                )

            # Main fields
            bp.employee_function = (
                self.custom_employee_function
            )

            bp.employee_name = (
                self.custom_function_head_name
            )

            bp.month = self.month

            bp.batch_type = row.batch_type

            bp.finished_item = (
                row.finished_item
            )

            bp.slot_booking_date = (
                row.slot_booking_date
            )

            bp.batch_creation = self.name

            # BOM logic
            bp.bom_list = (
                bom_store
                if bom_store
                else row.bom_list
            )

            # Ignore validations
            bp.flags.ignore_permissions = True
            bp.flags.ignore_validate = True
            bp.flags.ignore_mandatory = True
            bp.flags.ignore_workflow = True

            # Insert document
            bp.insert(
                ignore_permissions=True,
                ignore_mandatory=True
            )

            # -----------------------------------------
            # UPDATE STATUS
            # -----------------------------------------

            update_data = {
                "status": row.status,
                "workflow_state": row.status
            }

            if row.status == "Approved":

                update_data["docstatus"] = 1

            elif row.status == "Cancelled":

                update_data["docstatus"] = 2

            frappe.db.set_value(
                "Batches Planned",
                bp.name,
                update_data,
                update_modified=False
            )

            count += 1

        frappe.db.commit()

        return count

    # =====================================================
    # ON SUBMIT
    # =====================================================

    def on_submit(self):

        if not ENABLE_AFTER_SUBMIT_LOGIC:
            return

        if self.workflow_state != "Approved":
            return

        self.create_batches_planned_records()

    # =====================================================
    # ON TRASH
    # =====================================================

    def on_trash(self):

        if frappe.db.exists(
            "Batches Planned",
            {"batch_creation": self.name}
        ):

            frappe.throw(
                f"Cannot delete Batch Creation "
                f"<b>{self.name}</b>. "
                f"Batches Planned exist for it."
            )


# ═══════════════════════════════════════════════
# PART 3 — FRONTEND BUTTON API
# ═══════════════════════════════════════════════

@frappe.whitelist()
def create_batches_planned(doc_name):

    doc = frappe.get_doc(
        "Batch Creation",
        doc_name
    )

    # Validation
    if doc.workflow_state != "Approved":

        frappe.throw(
            "Document is not in Approved state."
        )

    if doc.docstatus != 1:

        frappe.throw(
            "Document is not submitted yet."
        )

    # Create records
    count = (
        doc.create_batches_planned_records()
    )

    return (
        f"{count} Batches Planned "
        f"record(s) created successfully."
    )


# ═══════════════════════════════════════════════
# PART 4 — BOM Item Details for Checkbox Filter
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_item_details_for_bom(item_codes):
    import json
    item_codes = json.loads(item_codes)

    if not item_codes:
        return []

    result = frappe.db.sql("""
        SELECT
            name,
            item_group,
            min_order_qty,
            safety_stock
        FROM `tabItem`
        WHERE name IN %(items)s
    """, {'items': item_codes}, as_dict=True)

    return result