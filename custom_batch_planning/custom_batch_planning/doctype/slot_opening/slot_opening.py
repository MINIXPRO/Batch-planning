# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


# ═══════════════════════════════════════════════
# PART 1 — API: SCT Details & Calendar Data
# ═══════════════════════════════════════════════

@frappe.whitelist()
def get_sct_details(slot_master=None, date=None):

    if not slot_master:
        return []

    sct_name = frappe.db.get_value(
        "Slot Capacity Tracker",
        {"slot_master": slot_master},
        "name"
    )

    if not sct_name:
        return []

    filters = {"parent": sct_name}

    if date:
        filters["date"] = date

    return frappe.get_all(
        "Slot Capacity Detail",
        filters=filters,
        fields=[
            "name",
            "date",
            "total_capacity",
            "capacity_booked",
            "capacity_available",
            "batches_planned"
        ],
        ignore_permissions=True
    )


@frappe.whitelist()
def get_calendar_data(employee_function=None, project=None):

    if not employee_function:
        return []

    conditions = ["sct.employee_function = %(employee_function)s", "sct.docstatus != 2"]
    args = {"employee_function": employee_function}

    if project:
        conditions.append("sm.project = %(project)s")
        args["project"] = project

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            sct.name AS sct_name,
            sct.slot_master,
            sct.employee_headname,
            sm.project,
            scd.date,
            scd.total_capacity,
            scd.capacity_booked,
            scd.capacity_available

        FROM
            `tabSlot Capacity Tracker` sct

        JOIN
            `tabSlot Capacity Detail` scd
            ON scd.parent = sct.name

        INNER JOIN
            `tabSlot Master List` sm
            ON sm.name = sct.slot_master

        WHERE
            {where_clause}

        ORDER BY
            scd.date ASC
        """,
        args,
        as_dict=True
    )


# ═══════════════════════════════════════════════
# PART 2 — Slot Opening Controller
# ═══════════════════════════════════════════════

class SlotOpening(Document):

    # ═══════════════════════════════════════════
    # AUTONAME
    # ═══════════════════════════════════════════

    def autoname(self):

        if not self.batch_start_date and self.slot_master:
            self.batch_start_date = frappe.db.get_value(
                "Slot Master List",
                self.slot_master,
                "batch_start_date"
            )

        if not self.batch_start_date:
            frappe.throw("Planning Start Date is required.")

        yy, mm = str(self.batch_start_date).split("-")[:2]

        self.name = make_autoname(
            f"SO-{yy[2:]}-{mm}-.###"
        )

    # ═══════════════════════════════════════════
    # BEFORE SAVE
    # ═══════════════════════════════════════════

    def before_save(self):

        if self.slot_master:
            slot_master_data = frappe.db.get_value(
                "Slot Master List",
                self.slot_master,
                ["project", "batch_capacity"],
                as_dict=True
            )
            if slot_master_data:
                self.project = slot_master_data.get("project")
                batch_capacity = slot_master_data.get("batch_capacity") or 0
                for row in self.slot_booking:
                    row.total_slots = batch_capacity

        if self.slot_master and not self.employee_function:
            frappe.throw(
                "Please select an Employee Function first before selecting a Slot Master."
            )

        self._validate_slot_dates()

        self._check_duplicate_full_capacity()

    # ═══════════════════════════════════════════
    # VALIDATE SLOT DATES
    # ═══════════════════════════════════════════

    def _validate_slot_dates(self):

        if not self.slot_master:
            return

        sm = frappe.get_doc(
            "Slot Master List",
            self.slot_master
        )

        start_date = str(sm.batch_start_date)
        end_date = str(sm.batch_end_date)

        for row in self.slot_booking:

            if not row.slot_booking_date:
                frappe.throw(
                    f"Row {row.idx}: Slot Booking Date is mandatory!"
                )

            booking_date = str(row.slot_booking_date)

            if booking_date < start_date:

                frappe.throw(
                    f"Row {row.idx}: Slot Booking Date "
                    f"<b>{booking_date}</b> cannot be before "
                    f"Planning Start Date <b>{start_date}</b>!"
                )

            if booking_date > end_date:

                frappe.throw(
                    f"Row {row.idx}: Slot Booking Date "
                    f"<b>{booking_date}</b> cannot be after "
                    f"Planning End Date <b>{end_date}</b>!"
                )

    # ═══════════════════════════════════════════
    # CHECK DUPLICATE FULL CAPACITY
    # ═══════════════════════════════════════════

    def _check_duplicate_full_capacity(self):
        current_dates = [row.slot_booking_date for row in self.slot_booking]

        for date in current_dates:
            # Same slot_master pe same date ka koi aur Slot Opening hai?
            conflict = frappe.db.sql("""
                SELECT so.name
                FROM `tabSlot Opening` so
                JOIN `tabSlot Booking CT` sbc ON sbc.parent = so.name
                WHERE so.slot_master = %s
                AND so.employee_function = %s
                AND so.name != %s
                AND so.docstatus != 2
                AND sbc.slot_booking_date = %s
                LIMIT 1
            """, (self.slot_master, self.employee_function, self.name, date))

            if not conflict:
                continue

            # SCT mein available capacity check karo
            sct_available = frappe.db.sql("""
                SELECT IFNULL(SUM(scd.capacity_available), 0)
                FROM `tabSlot Capacity Detail` scd
                JOIN `tabSlot Capacity Tracker` sct ON sct.name = scd.parent
                WHERE sct.slot_master = %s
                AND scd.date = %s
            """, (self.slot_master, date))[0][0]

            # Current doc ki booking minus karo (jo abhi save ho rahi hai)
            current_booked = next(
                (int(r.booked_slots or 0) for r in self.slot_booking
                 if str(r.slot_booking_date) == str(date)), 0
            )

            if not self.is_new():
                old_booked = frappe.db.get_value(
                    "Slot Booking CT",
                    {"parent": self.name, "slot_booking_date": date},
                    "booked_slots"
                ) or 0
                net_booking = current_booked - int(old_booked)
            else:
                net_booking = current_booked

            if (int(sct_available) - net_booking) < 0:
                frappe.throw(
                    f"Slot Opening <b>{conflict[0][0]}</b> already exists "
                    f"for this Employee Function on <b>{date}</b> "
                    f"and capacity is full."
                )

    # ═══════════════════════════════════════════
    # UPDATE SCT
    # ═══════════════════════════════════════════

    def _update_sct(self):

        if not self.slot_master:
            return

        sct_name = frappe.db.get_value(
            "Slot Capacity Tracker",
            {"slot_master": self.slot_master},
            "name"
        )

        if not sct_name:
            return

        sct_doc = frappe.get_doc(
            "Slot Capacity Tracker",
            sct_name
        )

        for row in self.slot_booking:

            if not row.slot_booking_date:
                continue

            if not row.booked_slots:
                continue

            booked = int(row.booked_slots)

            sct_detail = next(
                (
                    d
                    for d in sct_doc.slot_capacity_detail
                    if str(d.date) == str(row.slot_booking_date)
                ),
                None
            )

            if not sct_detail:

                frappe.throw(
                    f"Date {row.slot_booking_date} "
                    f"not found in SCT ({sct_name})."
                )

            # Document is only updating SCT on submit now, so apply the full booked amount
            diff = booked

            available = int(sct_detail.capacity_available or 0)

            if diff > available:

                frappe.throw(
                    f"Date {row.slot_booking_date} has only "
                    f"{available} additional slot(s) available."
                )

            sct_detail.capacity_booked = (
                int(sct_detail.capacity_booked or 0) + diff
            )

            sct_detail.capacity_available = (
                int(sct_detail.total_capacity or 0)
                - int(sct_detail.capacity_booked)
            )

        sct_doc.flags.ignore_permissions = True
        sct_doc.flags.ignore_validate = True

        sct_doc.save()

        frappe.msgprint(
            f"Slot Capacity Tracker <b>{sct_name}</b> updated successfully.",
            title="✅ SCT Updated",
            indicator="green"
        )

    # ═══════════════════════════════════════════
    # ON SUBMIT
    # ═══════════════════════════════════════════

    def on_submit(self):
        if getattr(self, "workflow_state", None) == "Approved":
            self._update_sct()

    # ═══════════════════════════════════════════
    # ON CANCEL
    # ═══════════════════════════════════════════

    def on_cancel(self):

        self._reverse_sct()

    # ═══════════════════════════════════════════
    # ON TRASH
    # ═══════════════════════════════════════════

    def on_trash(self):

        if frappe.db.exists(
            "Batch Planning",
            {"slot_opening": self.name}
        ):

            frappe.throw(
                f"Cannot delete Slot Opening <b>{self.name}</b>. "
                f"Batch Planning exists for it."
            )

        # Skip reverse steps if the document was already canceled and processed
        if self.docstatus != 2:
            self._reverse_sct()

    # ═══════════════════════════════════════════
    # REVERSE SCT
    # ═══════════════════════════════════════════

    def _reverse_sct(self):

        if not self.slot_master:
            return

        sct_name = frappe.db.get_value(
            "Slot Capacity Tracker",
            {"slot_master": self.slot_master},
            "name"
        )

        if not sct_name:
            return

        sct_doc = frappe.get_doc(
            "Slot Capacity Tracker",
            sct_name
        )

        for row in self.slot_booking:

            if not row.slot_booking_date:
                continue

            if not row.booked_slots:
                continue

            booked = int(row.booked_slots)

            sct_detail = next(
                (
                    d
                    for d in sct_doc.slot_capacity_detail
                    if str(d.date) == str(row.slot_booking_date)
                ),
                None
            )

            if not sct_detail:

                frappe.log_error(
                    f"Date {row.slot_booking_date} not found in SCT ({sct_name})",
                    "Slot Opening Cancel"
                )

                continue

            sct_detail.capacity_booked = max(
                0,
                int(sct_detail.capacity_booked or 0)
                - booked
            )

            sct_detail.capacity_available = (
                int(sct_detail.total_capacity or 0)
                - int(sct_detail.capacity_booked)
            )

        sct_doc.flags.ignore_permissions = True
        sct_doc.flags.ignore_validate = True

        sct_doc.save()

        frappe.msgprint(
            f"Slot Capacity Tracker <b>{sct_name}</b> reversed successfully.",
            title="✅ SCT Reversed",
            indicator="blue"
        )


@frappe.whitelist()
def get_active_slot_masters(doctype, txt, searchfield, start=0, page_len=20, filters=None):
    if isinstance(filters, str):
        import json
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}

    employee_function = filters.get("employee_function") if filters else None

    if not employee_function:
        return []

    try:
        start = int(start)
    except (ValueError, TypeError):
        start = 0

    try:
        page_len = int(page_len)
    except (ValueError, TypeError):
        page_len = 20

    # Altered date constraint to evaluate against 'batch_end_date' directly
    query = """
        SELECT
            sm.name, sm.employee_function, sm.batch_start_date, sm.batch_end_date
        FROM
            `tabSlot Master List` sm
        INNER JOIN
            `tabSlot Capacity Tracker` sct ON sct.slot_master = sm.name
        WHERE
            sm.docstatus = 1
            AND sm.workflow_state = 'Approved'
            AND sm.batch_end_date >= CURDATE()
            AND sct.docstatus != 2
    """

    args = {}
    if employee_function:
        query += " AND sm.employee_function = %(employee_function)s"
        args["employee_function"] = employee_function

    if txt:
        query += " AND sm.name LIKE %(txt)s"
        args["txt"] = f"%{txt}%"

    query += """
        AND (
            SELECT SUM(scd.capacity_available)
            FROM `tabSlot Capacity Detail` scd
            WHERE scd.parent = sct.name
        ) > 0
    """

    query += " ORDER BY sm.name ASC LIMIT %(start)s, %(page_len)s"
    args["start"] = start
    args["page_len"] = page_len

    return frappe.db.sql(query, args, as_list=1)
