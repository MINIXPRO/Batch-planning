import os

def search():
    po_js_path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext/buying/doctype/purchase_order/purchase_order.js"
    if os.path.exists(po_js_path):
        with open(po_js_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print("Lines containing Material Request in purchase_order.js:")
        for idx, line in enumerate(lines, 1):
            if "material request" in line.lower():
                print(f"{idx}: {line.strip()}")
    else:
        print("purchase_order.js not found at path")

if __name__ == "__main__":
    search()
