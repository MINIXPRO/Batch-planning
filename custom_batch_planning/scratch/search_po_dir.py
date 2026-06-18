import os

def main():
    path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext/buying/doctype/purchase_order"
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line_no, line in enumerate(f, 1):
                            if "merge" in line.lower() or "consolidate" in line.lower():
                                print(f"{filepath}:{line_no} -> {line.strip()}")
                except Exception:
                    pass
    else:
        print("purchase_order folder not found")

if __name__ == "__main__":
    main()
