import frappe

def run():
    logs = frappe.get_all("Error Log", filters={"method": "map_sle_fields hook executed"}, fields=["method", "error"], limit=5, order_by="creation desc")
    for log in logs:
        print(f"{log.method}: {log.error}")
