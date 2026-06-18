import inspect

def main():
    # Let's inspect the accounts_controller file lines around 686
    path = "/home/shivam/frappe-bench/frappe-bench/apps/erpnext/erpnext/controllers/accounts_controller.py"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    print("Lines 670 to 710 in accounts_controller.py:")
    for i in range(670, min(710, len(lines))):
        print(f"{i+1}: {lines[i]}", end="")

if __name__ == "__main__":
    main()
