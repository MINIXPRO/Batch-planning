import os

def search():
    erpnext_path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext"
    matches = []
    for root, dirs, files in os.walk(erpnext_path):
        for file in files:
            if file.endswith((".py", ".js")):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line_no, line in enumerate(f, 1):
                            if "consolidate" in line.lower() and ("purchase_order" in line.lower() or "buying_settings" in line.lower() or "material_request" in line.lower()):
                                matches.append(f"{path}:{line_no} -> {line.strip()}")
                except Exception:
                    pass
                    
    print(f"Found {len(matches)} matches:")
    for m in matches[:50]:
        print(m)

if __name__ == "__main__":
    search()
