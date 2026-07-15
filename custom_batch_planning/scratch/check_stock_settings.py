import frappe
def run():
    print("Stock Settings:", frappe.db.get_value("Stock Settings", None, ["use_naming_series", "naming_series_prefix"], as_dict=True))
