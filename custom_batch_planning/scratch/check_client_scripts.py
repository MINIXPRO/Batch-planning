import frappe
def run():
    scripts = frappe.get_all("Client Script", filters={"dt": "Purchase Receipt"}, fields=["name", "script"])
    for s in scripts:
        print("Script:", s.name)
        print(s.script)
