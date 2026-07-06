import sys
sys.path.append('/home/shivam/frappe-bench/frappe-bench/apps/frappe')
import frappe
frappe.init(site='site_local')
frappe.connect()
print('Exists:', frappe.db.exists('Custom Field', 'Stock Entry-custom_batch_no'))
