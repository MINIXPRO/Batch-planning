import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.has_column("Slot Booking CT", "booked_slots"):
		rename_field("Slot Booking CT", "booked_slots", "planning_capacity")
