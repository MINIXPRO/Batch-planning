import frappe

def run():
    print("--- Client Scripts ---")
    scripts = frappe.db.get_all("Client Script", filters={"dt": "Material Request"}, fields=["name", "enabled"])
    print(scripts)
    
    print("--- Custom Scripts ---")
    # Custom Script was renamed to Client Script in newer Frappe versions, but let's check both just in case
    try:
        custom_scripts = frappe.db.get_all("Custom Script", filters={"dt": "Material Request"}, fields=["name", "enabled"])
        print(custom_scripts)
    except Exception as e:
        print("Custom Script table not found or error:", e)
