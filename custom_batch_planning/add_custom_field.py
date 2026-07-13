import frappe

def create_field():
    if not frappe.db.exists("Custom Field", "Stock Entry-custom_material_allocation"):
        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Stock Entry",
            "fieldname": "custom_material_allocation",
            "label": "Material Allocation",
            "fieldtype": "Link",
            "options": "Material Allocation",
            "insert_after": "purpose"
        })
        custom_field.insert()
        frappe.db.commit()
        print("Custom field created.")
    else:
        print("Custom field already exists.")
