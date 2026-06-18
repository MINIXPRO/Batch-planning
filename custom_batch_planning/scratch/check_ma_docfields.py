import frappe

def run():
    print("Material Allocation fields:")
    meta = frappe.get_meta("Material Allocation")
    for f in meta.fields:
        print(f"FieldName: {f.fieldname} | Label: {f.label} | FieldType: {f.fieldtype} | Options: {f.options}")

    print("\nMaterial Allocation Item fields:")
    meta_item = frappe.get_meta("Material Allocation Item")
    for f in meta_item.fields:
        print(f"FieldName: {f.fieldname} | Label: {f.label} | FieldType: {f.fieldtype} | Options: {f.options}")
