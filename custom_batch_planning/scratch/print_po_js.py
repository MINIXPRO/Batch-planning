import os

def main():
    po_js_path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext/buying/doctype/purchase_order/purchase_order.js"
    if os.path.exists(po_js_path):
        with open(po_js_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print("Lines 480 to 600 of purchase_order.js:")
        for idx in range(480, min(600, len(lines))):
            print(f"{idx+1}: {lines[idx]}", end="")

if __name__ == "__main__":
    main()
