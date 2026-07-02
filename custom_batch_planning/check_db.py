import frappe

def execute():
    print("--- Client Scripts ---")
    client_scripts = frappe.get_all("Client Script", fields=["name", "dt", "script"])
    for s in client_scripts:
        if s.script and "created_by" in s.script:
            print(f"FOUND 'created_by' IN CLIENT SCRIPT: {s.name} (DocType: {s.dt})")
    
    print("--- Server Scripts ---")
    server_scripts = frappe.get_all("Server Script", fields=["name", "reference_doctype", "script"])
    for s in server_scripts:
        if s.script and "created_by" in s.script:
            print(f"FOUND 'created_by' IN SERVER SCRIPT: {s.name} (DocType: {s.reference_doctype})")
