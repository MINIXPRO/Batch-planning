import frappe

def main():
    # 1. Material Request Item custom fields
    if not frappe.db.exists("Custom Field", "Material Request Item-custom_batch_planning_no"):
        print("Creating Material Request Item-custom_batch_planning_no...")
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Material Request Item",
            "fieldname": "custom_batch_planning_no",
            "label": "Batch Planning No",
            "fieldtype": "Link",
            "options": "Batch Planning",
            "insert_after": "item_code"
        }).insert()
        
    if not frappe.db.exists("Custom Field", "Material Request Item-custom_batch_reference"):
        print("Creating Material Request Item-custom_batch_reference...")
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Material Request Item",
            "fieldname": "custom_batch_reference",
            "label": "Batch Reference",
            "fieldtype": "Data",
            "insert_after": "custom_batch_planning_no"
        }).insert()

    # 2. Purchase Order Item custom fields
    if not frappe.db.exists("Custom Field", "Purchase Order Item-custom_batch_planning_no"):
        print("Creating Purchase Order Item-custom_batch_planning_no...")
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Purchase Order Item",
            "fieldname": "custom_batch_planning_no",
            "label": "Batch Planning No",
            "fieldtype": "Data",
            "insert_after": "item_code"
        }).insert()
        
    if not frappe.db.exists("Custom Field", "Purchase Order Item-custom_batch_reference"):
        print("Creating Purchase Order Item-custom_batch_reference...")
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Purchase Order Item",
            "fieldname": "custom_batch_reference",
            "label": "Batch Reference",
            "fieldtype": "Data",
            "insert_after": "custom_batch_planning_no"
        }).insert()

    # 3. Purchase Order header custom field
    if not frappe.db.exists("Custom Field", "Purchase Order-custom_batch_planning_no"):
        print("Creating Purchase Order-custom_batch_planning_no...")
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Purchase Order",
            "fieldname": "custom_batch_planning_no",
            "label": "Batch Planning No",
            "fieldtype": "Data",
            "read_only": 1,
            "insert_after": "supplier"
        }).insert()
        
    frappe.db.commit()
    print("Database committed successfully.")

if __name__ == "__main__":
    main()
