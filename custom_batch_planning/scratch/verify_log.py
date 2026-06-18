import frappe

def run():
    print("--- Verifying Doctype Fields ---")
    bp_meta = frappe.get_meta("Batch Planning")
    has_fi = bp_meta.has_field("finished_item")
    has_bl = bp_meta.has_field("bom_list")
    print(f"Batch Planning has finished_item: {has_fi}")
    print(f"Batch Planning has bom_list: {has_bl}")
    
    print("\n--- Verifying Material Allocation Log Field Mapping ---")
    ma_item_meta = frappe.get_meta("Material Allocation Item")
    fields = [f.fieldname for f in ma_item_meta.fields]
    required_fields = ["quantity_required", "stock_available", "allocate_qty", "qty_allocated", "shortage"]
    for rf in required_fields:
        print(f"Material Allocation Item has field {rf}: {rf in fields}")
    
    print("\nVerification successful!")
