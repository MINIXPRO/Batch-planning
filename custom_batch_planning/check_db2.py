import frappe

def execute():
    print("--- Property Setters for Slot Opening ---")
    ps = frappe.get_all("Property Setter", filters={"doc_type": "Slot Opening"}, fields=["name", "field_name", "property", "value"])
    for p in ps:
        if p.value and "created_by" in str(p.value):
            print(f"FOUND 'created_by' IN PROPERTY SETTER: {p.name} - Field: {p.field_name} - Property: {p.property}")
            
    print("--- Custom Fields for Slot Opening ---")
    cf = frappe.get_all("Custom Field", filters={"dt": "Slot Opening"}, fields=["name", "fieldname", "default", "depends_on", "mandatory_depends_on", "read_only_depends_on"])
    for c in cf:
        for key in ["default", "depends_on", "mandatory_depends_on", "read_only_depends_on"]:
            val = c.get(key)
            if val and "created_by" in str(val):
                print(f"FOUND 'created_by' IN CUSTOM FIELD: {c.name} - Field: {c.fieldname} - Prop: {key}")
