import frappe

def update_server_script():
    script_name = 'Batch Planning — Approved BPs for Material Planning'
    scripts = frappe.get_all('Server Script', filters={'api_method': 'get_approved_batch_plannings'}, fields=['name'])
    if not scripts:
        print("Script not found by api_method 'get_approved_batch_plannings'")
        return
        
    for s in scripts:
        doc = frappe.get_doc('Server Script', s.name)
        new_script = """data = frappe.request.get_json() or {}

employee_function = data.get("employee_function") or ""
month = data.get("month") or ""

# Check if user is Administrator
is_admin = frappe.session.user == "Administrator"

filters = []

# If not admin, EF is mandatory
if not is_admin and not employee_function:
    frappe.response["message"] = []
else:
    # If EF provided (by admin or user), use it as filter
    if employee_function:
        filters.append(["employee_function", "=", employee_function])

    if month:
        filters.append(["month", "=", month])

    bps = frappe.get_all(
        "Batches Planned",
        filters=filters,
        fields=[
            "batch_planning_id as name",
            "month",
            "batch_type",
            "finished_item",
            "batch_creation",
            "employee_function"
        ],
        order_by="batch_planning_id asc",
        limit=1000
    )

    frappe.response["message"] = bps"""
        
        doc.script = new_script
        doc.save()
        frappe.db.commit()
        print(f"Updated Server Script: {doc.name}")

if __name__ == "__main__":
    update_server_script()
