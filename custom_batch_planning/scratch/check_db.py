import frappe

def run():
    print("tabBatch Creation:", frappe.db.sql("select count(*) from `tabBatch Creation`")[0][0])
    try:
        print("tabBatch Planning:", frappe.db.sql("select count(*) from `tabBatch Planning`")[0][0])
    except Exception as e:
        print("tabBatch Planning count failed:", e)

    # check if column project exists
    has_col = frappe.db.has_column("Batch Planning", "project")
    print("Does Batch Planning have project column in DB?", has_col)


