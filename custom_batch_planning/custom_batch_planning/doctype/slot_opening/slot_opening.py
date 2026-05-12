# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


@frappe.whitelist()
def get_sct_details(slot_master=None, date=None):
    """
    Fetch Slot Capacity Tracker Details
    """

    if not slot_master:
        return []

    # Get SCT Name
    sct_name = frappe.db.get_value(
        "Slot Capacity Tracker",
        {"slot_master": slot_master},
        "name"
    )

    if not sct_name:
        return []

    filters = {
        "parent": sct_name
    }

    # Optional Date Filter
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
            "capacity_available"
        ],
        ignore_permissions=True
    )


class SlotOpening(Document):

    # ─────────────────────────────────────────────
    # Auto Naming
    # ─────────────────────────────────────────────
    def autoname(self):

        if not self.batch_start_date and self.slot_master:
            self.batch_start_date = frappe.db.get_value(
                "Slot Master List",
                self.slot_master,
                "batch_start_date"
            )

        if not self.batch_start_date:
            frappe.throw(
                "Batch Start Date is required to generate the naming series."
            )

        date_str = str(self.batch_start_date)
        parts = date_str.split("-")

        if len(parts) >= 2:

            yy = parts[0][2:]
            mm = parts[1]

            from frappe.model.naming import make_autoname

            self.name = make_autoname(f"SO-{yy}-{mm}-.###")

    # ─────────────────────────────────────────────
    # Before Save — Validation
    # ─────────────────────────────────────────────
    def before_save(self):

        self._validate_slot_dates()
        self._check_duplicate_full_capacity()
        self._update_sct()

    # ─────────────────────────────────────────────
    # Validate Slot Dates
    # ─────────────────────────────────────────────
    def _validate_slot_dates(self):

        if not self.slot_master:
            return

        sm = frappe.get_doc("Slot Master List", self.slot_master)

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
                    f"Batch Start Date <b>{start_date}</b>!"
                )

            if booking_date > end_date:
                frappe.throw(
                    f"Row {row.idx}: Slot Booking Date "
                    f"<b>{booking_date}</b> cannot be after "
                    f"Batch End Date <b>{end_date}</b>!"
                )

    # ─────────────────────────────────────────────
    # Check Duplicate Full Capacity
    # ─────────────────────────────────────────────
    def _check_duplicate_full_capacity(self):

        current_dates = [
            row.slot_booking_date for row in self.slot_booking
        ]

        for date in current_dates:

            existing_list = frappe.db.get_all(
                "Slot Opening",
                filters={
                    "employee_function": self.employee_function,
                    "custom_project": self.custom_project,
                    "name": ["!=", self.name],
                    "docstatus": ["!=", 2]
                },
                fields=[
                    "name",
                    "total_batch_remained"
                ]
            )

            for existing in existing_list:

                existing_dates = frappe.db.get_all(
                    "Slot Booking CT",
                    filters={
                        "parent": existing.name,
                        "slot_booking_date": date
                    },
                    fields=["slot_booking_date"]
                )

                if (
                    existing_dates and
                    existing.total_batch_remained == 0
                ):

                    frappe.throw(
                        f"A Slot Opening <b>{existing.name}</b> "
                        f"already exists for "
                        f"<b>{self.function_head_name}</b> "
                        f"on <b>{date}</b> and its "
                        f"Batch Capacity is <b>Full</b>. "
                        f"No more slots can be planned "
                        f"for this date."
                    )

    # ─────────────────────────────────────────────
    # Update SCT
    # ─────────────────────────────────────────────
    def _update_sct(self):

        if not self.slot_master:
            return

        # Run only on first save
        if not self.is_new():
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

            booked = int(row.booked_slots or 0)

            sct_detail = None

            for detail in sct_doc.slot_capacity_detail:

                if str(detail.date) == str(row.slot_booking_date):
                    sct_detail = detail
                    break

            if not sct_detail:

                frappe.throw(
                    f"Date {row.slot_booking_date} not found "
                    f"in Slot Capacity Tracker ({sct_name}). "
                    f"Please check the Slot Master configuration."
                )

            available = int(
                sct_detail.capacity_available or 0
            )

            if booked > available:

                frappe.throw(
                    f"Date {row.slot_booking_date} has only "
                    f"{available} slot(s) available, but "
                    f"you are trying to book {booked}."
                )

            sct_detail.capacity_booked = (
                int(sct_detail.capacity_booked or 0)
                + booked
            )

            sct_detail.capacity_available = (
                int(sct_detail.total_capacity or 0)
                - int(sct_detail.capacity_booked)
            )

        sct_doc.flags.ignore_permissions = True
        sct_doc.flags.ignore_validate = True

        sct_doc.save()

        frappe.msgprint(
            msg=(
                f"Slot Capacity Tracker "
                f"<b>{sct_name}</b> updated successfully."
            ),
            title="✅ SCT Updated",
            indicator="green"
        )

    # ─────────────────────────────────────────────
    # On Submit
    # ─────────────────────────────────────────────
    def on_submit(self):
        pass

    # ─────────────────────────────────────────────
    # On Cancel
    # ─────────────────────────────────────────────
    def on_cancel(self):

        self._reverse_sct()

    # ─────────────────────────────────────────────
    # On Delete
    # ─────────────────────────────────────────────
    def on_trash(self):

        # Block deletion if Batch Creation exists
        if frappe.db.exists(
            "Batch Creation",
            {"slot_opening": self.name}
        ):

            frappe.throw(
                f"Cannot delete Slot Opening "
                f"<b>{self.name}</b>. "
                f"Batch Creation exists for it. "
                f"Please delete the Batch Creation first."
            )

        self._reverse_sct()

    # ─────────────────────────────────────────────
    # Reverse SCT
    # ─────────────────────────────────────────────
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

            booked = int(row.booked_slots or 0)

            sct_detail = None

            for detail in sct_doc.slot_capacity_detail:

                if str(detail.date) == str(row.slot_booking_date):
                    sct_detail = detail
                    break

            if not sct_detail:

                frappe.log_error(
                    f"Date {row.slot_booking_date} not found "
                    f"in SCT ({sct_name}) during cancel/delete.",
                    "Slot Opening Cancel"
                )

                continue

            sct_detail.capacity_booked = max(
                0,
                int(sct_detail.capacity_booked or 0) - booked
            )

            sct_detail.capacity_available = (
                int(sct_detail.total_capacity or 0)
                - int(sct_detail.capacity_booked)
            )

        sct_doc.flags.ignore_permissions = True
        sct_doc.flags.ignore_validate = True

        sct_doc.save()

        frappe.msgprint(
            msg=(
                f"Slot Capacity Tracker "
                f"<b>{sct_name}</b> reversed successfully."
            ),
            title="✅ SCT Reversed",
            indicator="blue"
        )