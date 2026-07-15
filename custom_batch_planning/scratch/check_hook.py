import frappe

def run():
    sle = frappe.get_doc({"doctype": "Stock Ledger Entry", "voucher_type": "Stock Entry", "voucher_detail_no": "TEST"})
    print("Running before_save...")
    sle.run_method("before_save")
    print("Done")
