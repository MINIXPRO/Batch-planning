data = frappe.request.get_json() or {}

employee_function = data.get("employee_function") or ""
month = data.get("month") or ""

is_admin = frappe.session.user == "Administrator"

filters = []

if not is_admin and not employee_function:
    frappe.response["message"] = []
else:
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

    frappe.response["message"] = bps
