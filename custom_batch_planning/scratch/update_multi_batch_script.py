import frappe

def update_multi_batch_script():
    script_name = 'Batch Planning — Multi Batch Material Requirement Plan'
    scripts = frappe.get_all('Server Script', filters={'name': script_name}, fields=['name'])
    if not scripts:
        scripts = frappe.get_all('Server Script', filters={'api_method': 'get_multi_batch_material_plan'}, fields=['name'])
        
    if not scripts:
        print("Script not found")
        return
        
    for s in scripts:
        doc = frappe.get_doc('Server Script', s.name)
        with open('/home/shivam/frappe-bench/frappe-bench/apps/custom_batch_planning/custom_batch_planning/scratch/get_multi_batch_plan_fix.py', 'r') as f:
            new_script = f.read()
            
        doc.script = new_script
        doc.save()
        frappe.db.commit()
        print(f"Updated Server Script: {doc.name}")

if __name__ == "__main__":
    update_multi_batch_script()
