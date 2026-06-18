import os
import inspect

def main():
    path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext/controllers/buying_controller.py"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        print("validate_duplicate_items or similar in buying_controller.py?")
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            if "merge" in line.lower() or "consolidate" in line.lower() or "duplicate" in line.lower():
                print(f"{idx}: {line.strip()}")
    else:
        print("buying_controller.py not found")

if __name__ == "__main__":
    main()
