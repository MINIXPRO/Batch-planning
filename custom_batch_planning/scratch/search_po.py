import os

def search():
    erpnext_path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext"
    results = []
    for root, dirs, files in os.walk(erpnext_path):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "def make_purchase_order" in content:
                            results.append(path)
                except Exception:
                    pass
    print("Found files:", results)

if __name__ == "__main__":
    search()
