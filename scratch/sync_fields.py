import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    frappe.init(site="site_local")
    frappe.connect()
    
    # 1. Delete old custom_batch_no field on Material Request if it exists
    if frappe.db.exists("Custom Field", "Material Request-custom_batch_no"):
        print("Deleting Material Request-custom_batch_no...")
        frappe.delete_doc("Custom Field", "Material Request-custom_batch_no")
        
    # 2. Re-import or create the new custom field custom_batch_planning_no on Material Request
    custom_fields = {
        "Material Request": [
            {
                "fieldname": "custom_batch_planning_no",
                "label": "Batch Planning No",
                "fieldtype": "Link",
                "options": "Batch Planning",
                "insert_after": "material_request_type"
            }
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
    print("Custom fields synchronized successfully.")
