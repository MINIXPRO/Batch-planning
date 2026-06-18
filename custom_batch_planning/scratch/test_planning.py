import frappe
frappe.init(site="site_local", sites_path="sites")
frappe.connect()

columns = [c[0] for c in frappe.db.sql("DESC `tabBatch Planning`")]
print("Columns of tabBatch Planning:")
for c in columns:
    print("-", c)
