import frappe

def run():
    print("Custom fields for Material Allocation:")
    cfs = frappe.get_all("Custom Field", filters={"dt": "Material Allocation"}, fields=["fieldname", "label", "fieldtype", "options"])
    for cf in cfs:
        print(f"FieldName: {cf.fieldname} | Label: {cf.label} | FieldType: {cf.fieldtype} | Options: {cf.options}")

    print("\nCustom fields for Material Allocation Item:")
    cfs_item = frappe.get_all("Custom Field", filters={"dt": "Material Allocation Item"}, fields=["fieldname", "label", "fieldtype", "options"])
    for cf in cfs_item:
        print(f"FieldName: {cf.fieldname} | Label: {cf.label} | FieldType: {cf.fieldtype} | Options: {cf.options}")
