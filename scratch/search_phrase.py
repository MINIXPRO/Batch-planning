import sys
sys.path.append('/home/shivam/frappe-bench/frappe-bench/apps/frappe')
sys.path.append('/home/shivam/frappe-bench/frappe-bench/apps/erpnext')

import frappe
frappe.init(site='site_local', sites_path='/home/shivam/frappe-bench/frappe-bench/sites')
frappe.connect()

import json

def run():
    # Check tabVersion for BP-26-07-004
    versions = frappe.db.get_all(
        "Version",
        filters={"ref_doctype": "Batch Planning", "docname": "BP-26-07-004"},
        fields=["name", "owner", "creation", "data"]
    )
    print("--- Versions for BP-26-07-004 ---")
    for v in versions:
        v_copy = v.copy()
        if "creation" in v_copy:
            v_copy["creation"] = str(v_copy["creation"])
        print(json.dumps(v_copy, indent=True))

if __name__ == "__main__":
    run()
