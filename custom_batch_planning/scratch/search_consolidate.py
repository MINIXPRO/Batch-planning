import os

def main():
    erpnext_path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext"
    results = []
    for root, dirs, files in os.walk(erpnext_path):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "consolidate" in content and "item" in content:
                            if "purchase_order" in path or "buying" in path:
                                results.append(path)
                except Exception:
                    pass
    print("Found files:", results)

if __name__ == "__main__":
    main()
