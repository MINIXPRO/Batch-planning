import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today, now_datetime, add_days


class SlotMasterList(Document):

    # Auto-generate document name in format: SM-YY-MM-01
    def autoname(self):

        # Validate Batch Start Date
        if not self.batch_start_date:
            frappe.throw("Batch Start Date is required to generate name.")

        # Extract year and month
        date = getdate(self.batch_start_date)
        yy = str(date.year)[2:]
        mm = str(date.month).zfill(2)

        # Prefix Example: SM-25-05-
        prefix = f"SM-{yy}-{mm}-"

        # Get current series number from tabSeries
        current = frappe.db.sql(
            "SELECT `current` FROM `tabSeries` WHERE name = %s",
            prefix
        )

        # Determine next number
        next_num = int(current[0][0]) + 1 if current else 1

        # Generate candidate name
        candidate = f"{prefix}{str(next_num).zfill(2)}"

        # Ensure unique name
        while frappe.db.exists("Slot Master List", candidate):
            next_num += 1
            candidate = f"{prefix}{str(next_num).zfill(2)}"

        # Update tabSeries table
        frappe.db.sql(
            """
            INSERT INTO `tabSeries` (name, `current`)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE `current` = %s
            """,
            (prefix, next_num, next_num)
        )

        # Assign generated name
        self.name = candidate

    # Validation before save
    def before_save(self):

        # Set current transaction datetime
        self.transaction_date = now_datetime()

        # Set creator only for new document
        if self.is_new():
            self.created_by = frappe.session.user

        # Convert dates to string for comparison
        start_date = str(self.batch_start_date) if self.batch_start_date else None
        end_date = str(self.batch_end_date) if self.batch_end_date else None
        today_date = today()

        # Validate start date should not be in past
        if start_date and start_date < today_date:
            frappe.throw("Batch Start Date cannot be a past date.")

        # Validate end date should not be in past
        if end_date and end_date < today_date:
            frappe.throw("Batch End Date cannot be a past date.")

        # Validate start and end date logic
        if start_date and end_date:

            # Start date should be <= end date
            if start_date > end_date:
                frappe.throw(
                    "Batch Start Date must be less than or equal to Batch End Date."
                )

            s = getdate(start_date)
            e = getdate(end_date)

            # Ensure both dates belong to same month and year
            if s.month != e.month or s.year != e.year:
                frappe.throw(
                    "Batch Start Date and Batch End Date must be in the same month."
                )

        # Check overlapping slots
        existing = frappe.db.exists({
            "doctype": "Slot Master List",
            "employee_function": self.employee_function,
            "custom_project": self.custom_project,
            "name": ["!=", self.name],
            "docstatus": ["!=", 2],
            "batch_start_date": ["<=", self.batch_end_date],
            "batch_end_date": [">=", self.batch_start_date],
        })

        # If overlapping slot exists, throw detailed message
        if existing:

            existing_doc = frappe.get_doc("Slot Master List", existing)

            frappe.throw(
                f"Overlapping slot already exists for "
                f"<b>{existing_doc.employee_function_head_name}</b>.<br>"
                f"on Project <b>{existing_doc.custom_project}</b>.<br>"
                f"Existing Slot: <b>{existing_doc.name}</b><br>"
                f"From: "
                f"<b>{getdate(existing_doc.batch_start_date).strftime('%d-%m-%Y')}</b> "
                f"To: "
                f"<b>{getdate(existing_doc.batch_end_date).strftime('%d-%m-%Y')}</b><br>"
                f"Batch Capacity: <b>{existing_doc.batch_capacity}</b>"
            )

    # Create Slot Capacity Tracker on submit
    def before_submit(self):

        # Create new Slot Capacity Tracker document
        slot_capacity_tracker = frappe.new_doc("Slot Capacity Tracker")

        # Assign values
        slot_capacity_tracker.name = self.name.replace("SM-", "SCT-")
        slot_capacity_tracker.slot_master = self.name
        slot_capacity_tracker.employee_function = self.employee_function
        slot_capacity_tracker.employee_headname = (
            self.employee_function_head_name
        )
        slot_capacity_tracker.project = self.custom_project
        slot_capacity_tracker.batch_start_date = self.batch_start_date
        slot_capacity_tracker.batch_end_date = self.batch_end_date

        # Generate date-wise capacity records
        current_date = getdate(self.batch_start_date)
        batch_end = getdate(self.batch_end_date)

        while current_date <= batch_end:

            slot_capacity_tracker.append("slot_capacity_detail", {
                "date": current_date,
                "total_capacity": self.batch_capacity,
                "capacity_booked": 0,
                "capacity_available": self.batch_capacity,
            })

            current_date = add_days(current_date, 1)

        # Insert tracker document
        slot_capacity_tracker.insert(ignore_permissions=True)

    # Prevent deletion if Slot Opening exists
    def on_trash(self):

        if frappe.db.exists(
            "Slot Opening",
            {"slot_master": self.name}
        ):

            frappe.throw(
                f"Cannot delete Slot Master "
                f"<b>{self.name}</b>. "
                f"Slot Openings exist for it."
            )