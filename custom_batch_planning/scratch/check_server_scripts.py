import frappe
def run():
    scripts = frappe.get_all("Server Script", fields=["name", "script_type", "reference_doctype", "doctype_event"])
    for s in scripts:
        print(s)
