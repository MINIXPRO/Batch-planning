import frappe

def main():
    try:
        meta = frappe.get_meta("Project")
        print("Fields:")
        for f in meta.fields:
            if "name" in f.fieldname or "title" in f.fieldname:
                print(f"- {f.fieldname}: {f.label} ({f.fieldtype})")
        
        project = frappe.get_all("Project", limit=1)
        if project:
            doc = frappe.get_doc("Project", project[0].name)
            print("Sample Project Doc:")
            print(doc.as_dict())
    except Exception as e:
        print("Error:", e)
