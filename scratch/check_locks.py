import sys
sys.path.append('/home/shivam/frappe-bench/frappe-bench/apps/frappe')
sys.path.append('/home/shivam/frappe-bench/frappe-bench/apps/erpnext')

import frappe
frappe.init(site='site_local', sites_path='/home/shivam/frappe-bench/frappe-bench/sites')
frappe.connect()

def run():
    try:
        processes = frappe.db.sql("SHOW FULL PROCESSLIST", as_dict=True)
        print("--- Active Processes ---")
        for p in processes:
            # Only print processes that are not this process itself
            if p.get("Info") and "SHOW FULL PROCESSLIST" in p.get("Info"):
                continue
            print(f"ID: {p.get('Id')} | User: {p.get('User')} | Host: {p.get('Host')} | db: {p.get('db')} | Command: {p.get('Command')} | Time: {p.get('Time')} | State: {p.get('State')} | Info: {p.get('Info')}")
            
            # If a process is Sleeping and has been active or is blocking, we can choose to kill it
            # Especially if it is a gunicorn or other web worker holding lock
            if p.get("Command") == "Sleep" and p.get("Time", 0) > 30:
                print(f" -> Killing sleeping process ID {p.get('Id')}")
                frappe.db.sql(f"KILL {p.get('Id')}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
