import frappe

def run():
    scripts = frappe.get_all("Client Script", filters={"dt": "Slot Opening"})
    for s in scripts:
        doc = frappe.get_doc("Client Script", s.name)
        doc.enabled = 0
        doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("DISABLED_SCRIPTS:", [s.name for s in scripts])

if __name__ == "__main__":
    run()
