import frappe
def run():
	doc = frappe.get_doc("DocType", "Slot Opening")
	doc.is_submittable = 1
	doc.save()
