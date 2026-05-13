# Copyright (c) 2026, Shivam Singh and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


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
            "capacity_available"
        ],
        ignore_permissions=True
    )


class SlotOpening(Document):

    def autoname(self):

        if not self.batch_start_date and self.slot_master:
            self.batch_start_date = frappe.db.get_value(
                "Slot Master List",
                self.slot_master,
                "batch_start_date"
            )

        if not self.batch_start_date:
            frappe.throw("Batch Start Date is required.")

        yy, mm = str(self.batch_start_date).split("-")[:2]
        self.name = make_autoname(f"SO-{yy[2:]}-{mm}-.###")

    def before_save(self):

        self._validate_slot_dates()
        self._check_duplicate_full_capacity()

        if self.is_new():
            self._update_sct()

    def _validate_slot_dates(self):

        if not self.slot_master:
            return

        sm = frappe.get_doc("Slot Master List", self.slot_master)
        start_date, end_date = str(sm.batch_start_date), str(sm.batch_end_date)

        for row in self.slot_booking:

            if not row.slot_booking_date:
                frappe.throw(f"Row {row.idx}: Slot Booking Date is mandatory!")

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

    def _check_duplicate_full_capacity(self):

        current_dates = [row.slot_booking_date for row in self.slot_booking]

        existing_list = frappe.db.get_all(
            "Slot Opening",
            filters={
                "employee_function": self.employee_function,
                "custom_project": self.custom_project,
                "name": ["!=", self.name],
                "docstatus": ["!=", 2]
            },
            fields=["name", "total_batch_remained"]
        )

        for date in current_dates:

            for existing in existing_list:

                existing_dates = frappe.db.exists(
                    "Slot Booking CT",
                    {
                        "parent": existing.name,
                        "slot_booking_date": date
                    }
                )

                if existing_dates and existing.total_batch_remained == 0:

                    frappe.throw(
                        f"A Slot Opening <b>{existing.name}</b> already exists "
                        f"for <b>{self.function_head_name}</b> on "
                        f"<b>{date}</b> and its Batch Capacity is Full."
                    )

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

        sct_doc = frappe.get_doc("Slot Capacity Tracker", sct_name)

        for row in self.slot_booking:

            if not row.slot_booking_date or not row.booked_slots:
                continue

            booked = int(row.booked_slots)

            sct_detail = next(
                (
                    d for d in sct_doc.slot_capacity_detail
                    if str(d.date) == str(row.slot_booking_date)
                ),
                None
            )

            if not sct_detail:
                frappe.throw(
                    f"Date {row.slot_booking_date} not found in SCT ({sct_name})."
                )

            available = int(sct_detail.capacity_available or 0)

            if booked > available:
                frappe.throw(
                    f"Date {row.slot_booking_date} has only "
                    f"{available} slot(s) available."
                )

            sct_detail.capacity_booked = int(
                sct_detail.capacity_booked or 0
            ) + booked

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

    def on_submit(self):
        pass

    def on_cancel(self):
        self._reverse_sct()

    def on_trash(self):

        if frappe.db.exists(
            "Batch Creation",
            {"slot_opening": self.name}
        ):
            frappe.throw(
                f"Cannot delete Slot Opening <b>{self.name}</b>. "
                f"Batch Creation exists for it."
            )

        self._reverse_sct()

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

        sct_doc = frappe.get_doc("Slot Capacity Tracker", sct_name)

        for row in self.slot_booking:

            if not row.slot_booking_date or not row.booked_slots:
                continue

            booked = int(row.booked_slots)

            sct_detail = next(
                (
                    d for d in sct_doc.slot_capacity_detail
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
            f"Slot Capacity Tracker <b>{sct_name}</b> reversed successfully.",
            title="✅ SCT Reversed",
            indicator="blue"
        )