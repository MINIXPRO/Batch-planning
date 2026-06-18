import os

def main():
    path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext/buying/doctype/purchase_order/purchase_order.py"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print("Lines in purchase_order.py:")
        for idx, line in enumerate(lines, 1):
            if "item" in line.lower() and ("duplicate" in line.lower() or "group" in line.lower() or "same" in line.lower()):
                print(f"{idx}: {line.strip()}")
    else:
        print("purchase_order.py not found")

if __name__ == "__main__":
    main()
