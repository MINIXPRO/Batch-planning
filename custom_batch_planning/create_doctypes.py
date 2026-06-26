import frappe

def run():
    frappe.flags.in_test = True # sometimes needed to bypass strict validations on creation
    
    # 1. Batch Planning Stock Entry
    if not frappe.db.exists("DocType", "Batch Planning Stock Entry"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Batch Planning Stock Entry",
            "module": "Custom Batch Planning",
            "custom": 1,
            "istable": 1,
            "fields": [
                {"fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "label": "Stock Entry", "in_list_view": 1},
                {"fieldname": "date", "fieldtype": "Date", "label": "Date", "in_list_view": 1},
                {"fieldname": "from_warehouse", "fieldtype": "Link", "options": "Warehouse", "label": "From Warehouse", "in_list_view": 1},
                {"fieldname": "to_warehouse", "fieldtype": "Link", "options": "Warehouse", "label": "To Warehouse", "in_list_view": 1},
                {"fieldname": "status", "fieldtype": "Data", "label": "Status", "in_list_view": 1}
            ]
        })
        doc.insert()
        print("Created Batch Planning Stock Entry")

    # 2. Batch Planning Item Issue
    if not frappe.db.exists("DocType", "Batch Planning Item Issue"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Batch Planning Item Issue",
            "module": "Custom Batch Planning",
            "custom": 1,
            "istable": 1,
            "fields": [
                {"fieldname": "item_code", "fieldtype": "Link", "options": "Item", "label": "Item Code", "in_list_view": 1},
                {"fieldname": "item_name", "fieldtype": "Data", "label": "Item Name", "in_list_view": 1},
                {"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "in_list_view": 1},
                {"fieldname": "uom", "fieldtype": "Link", "options": "UOM", "label": "UOM", "in_list_view": 1},
                {"fieldname": "from_warehouse", "fieldtype": "Link", "options": "Warehouse", "label": "From Warehouse", "in_list_view": 1},
                {"fieldname": "to_warehouse", "fieldtype": "Link", "options": "Warehouse", "label": "To Warehouse", "in_list_view": 1},
                {"fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "label": "Stock Entry", "in_list_view": 1}
            ]
        })
        doc.insert()
        print("Created Batch Planning Item Issue")
    
    frappe.db.commit()
