import frappe

def run():
    meta = frappe.get_meta("Stock Entry Detail")
    print(f"Has to_custom_employee_function: {meta.has_field('to_custom_employee_function')}")
    print(f"Has custom_employee_function: {meta.has_field('custom_employee_function')}")
