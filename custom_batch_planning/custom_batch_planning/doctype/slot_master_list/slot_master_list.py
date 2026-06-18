import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today, add_days, date_diff


class SlotMasterList(Document):

    # Auto-generate document name in format: SM-26-06-01
    def autoname(self):

        # Validate Batch Start Date
        if not self.batch_start_date:
            frappe.throw("Planning Start Date is required to generate name.")

        # Extract year and month
        date = getdate(self.batch_start_date)
        yy = str(date.year)[2:]
        mm = str(date.month).zfill(2)

        # Prefix Example: SM-26-06-
        prefix = f"SM-{yy}-{mm}-"

        # ✅ Fix 1: Use FOR UPDATE to prevent race condition on simultaneous saves
        current = frappe.db.sql(
            "SELECT `current` FROM `tabSeries` WHERE name = %s FOR UPDATE",
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

        # Validate Daily Batch Capacity (must be greater than or equal to 1)
        if not self.batch_capacity or int(self.batch_capacity) < 1:
            frappe.throw("Daily Batch Capacity must be greater than or equal to 1.")

        # Convert dates to string for comparison
        start_date = str(self.batch_start_date) if self.batch_start_date else None
        end_date = str(self.batch_end_date) if self.batch_end_date else None
        today_date = today()

        # ✅ Fix 2: Only validate past dates on new documents
        # Editing existing docs should not be blocked by past date check
        if self.is_new():
            if start_date and start_date < today_date:
                frappe.throw("Planning Start Date cannot be a past date.")

            if end_date and end_date < today_date:
                frappe.throw("Planning End Date cannot be a past date.")

        # Validate start and end date logic
        if start_date and end_date:

            # Start date should be <= end date
            if start_date > end_date:
                frappe.throw(
                    "Planning Start Date must be less than or equal to Planning End Date."
                )

            s = getdate(start_date)
            e = getdate(end_date)

            # Ensure both dates belong to same month and year
            if s.month != e.month or s.year != e.year:
                frappe.throw(
                    "Planning Start Date and Planning End Date must be in the same month."
                )

        # Check overlapping slots
        existing = frappe.db.exists({
            "doctype": "Slot Master List",
            "employee_function": self.employee_function,
            "project": self.project,
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
                f"<b>{existing_doc.employee_function_head_name}</b> and Project <b>{existing_doc.project}</b>.<br>"
                f"Existing Slot: <b>{existing_doc.name}</b><br>"
                f"From: "
                f"<b>{getdate(existing_doc.batch_start_date).strftime('%d-%m-%Y')}</b> "
                f"To: "
                f"<b>{getdate(existing_doc.batch_end_date).strftime('%d-%m-%Y')}</b><br>"
                f"Daily Batch Capacity: <b>{existing_doc.batch_capacity}</b>"
            )

    # Create Slot Capacity Tracker on submit
    def before_submit(self):

        # Create new Slot Capacity Tracker document
        slot_capacity_tracker = frappe.new_doc("Slot Capacity Tracker")

        # ✅ Fix 3: Use flags.name_set = True before assigning name manually
        slot_capacity_tracker.flags.name_set = True
        slot_capacity_tracker.name = self.name.replace("SM-", "SCT-")

        # Assign values
        slot_capacity_tracker.slot_master = self.name
        slot_capacity_tracker.employee_function = self.employee_function
        slot_capacity_tracker.employee_headname = self.employee_function_head_name
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

    # ✅ Fix 5: Block deletion if any Slot Opening exists (including cancelled)
    # Reason: cancelled Slot Openings still hold historical reference to this master
    # Deleting the master would orphan those cancelled records
    def on_trash(self):

        if frappe.db.exists(
            "Slot Opening",
            {"slot_master": self.name}
        ):
            frappe.throw(
                f"Cannot delete Slot Master "
                f"<b>{self.name}</b>. "
                f"Slot Openings exist for it (including cancelled). "
                f"Please delete all linked Slot Openings first."
            )


@frappe.whitelist()
def get_employee_function_projects(employee_function):
    if not employee_function:
        return []
    # Query Project list child table bypassing permissions
    rows = frappe.get_all(
        "Project list",
        filters={"parent": employee_function},
        fields=["projects"],
        ignore_permissions=True
    )
    return [r.projects for r in rows if r.projects]