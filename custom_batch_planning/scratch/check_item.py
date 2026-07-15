import frappe

def run():
    print(frappe.db.get_value("Item", "CN05010006", ["has_batch_no", "create_new_batch", "batch_number_series"], as_dict=True))
