import json
import os
import frappe

def run():
    print("Manually syncing custom fields from fixtures/custom_field.json...")
    
    app_path = frappe.get_app_path("custom_batch_planning")
    fixtures_path = os.path.join(app_path, "fixtures", "custom_field.json")
    
    if not os.path.exists(fixtures_path):
        print(f"Error: fixtures path {fixtures_path} does not exist!")
        return
        
    with open(fixtures_path, "r") as f:
        custom_fields = json.load(f)
        
    print(f"Loaded {len(custom_fields)} custom fields from JSON.")
    
    for field_name in ["Purchase Order Item-custom_batch_reference", "Purchase Invoice-custom_batch_no"]:
        if frappe.db.exists("Custom Field", field_name):
            frappe.delete_doc("Custom Field", field_name, ignore_permissions=True)
            print(f"Deleted obsolete custom field: {field_name}")
        
    for cf in custom_fields:
        if cf.get("doctype") != "Custom Field":
            continue
            
        name = cf.get("name")
        dt = cf.get("dt")
        fieldname = cf.get("fieldname")
        
        cf.pop("modified", None)
        
        if frappe.db.exists("Custom Field", name):
            doc = frappe.get_doc("Custom Field", name)
            doc.update(cf)
            doc.save(ignore_permissions=True)
            print(f"Updated Custom Field: {name}")
        else:
            existing = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, "name")
            if existing:
                print(f"Custom Field with dt={dt}, fieldname={fieldname} already exists under name={existing}. Updating it...")
                doc = frappe.get_doc("Custom Field", existing)
                doc.update(cf)
                doc.name = name
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc(cf)
                doc.insert(ignore_permissions=True)
                print(f"Inserted Custom Field: {name}")
                
    frappe.db.commit()
    print("Done manual syncing custom fields!")
