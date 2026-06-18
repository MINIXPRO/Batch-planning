import frappe

def run():
    print("=== Sample Project custom_function_info rows ===")
    rows = frappe.db.get_all("Employee Function Child", fields=["parent", "function_code", "role"], limit=10)
    for r in rows:
        print(f"Project: {r.parent} | Function Code: {r.function_code} | Role: {r.role}")
        
    print("\n=== Sample Employee Function project_list rows ===")
    rows_ef = frappe.db.get_all("Project list", fields=["parent", "projects"], limit=10)
    for r in rows_ef:
        print(f"Employee Function: {r.parent} | Projects: {r.projects}")
