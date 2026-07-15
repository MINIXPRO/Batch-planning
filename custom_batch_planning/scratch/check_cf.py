import frappe

def run():
    cf = frappe.db.get_value("Custom Field", {"dt": "Stock Entry Detail", "fieldname": "to_batch_planning_id"}, ["name", "creation"], as_dict=True)
    print(f"Custom Field 'to_batch_planning_id' created at: {cf.creation if cf else 'Not Found'}")
