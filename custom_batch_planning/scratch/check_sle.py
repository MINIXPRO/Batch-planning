import frappe

def run():
    columns = frappe.db.get_table_columns("Stock Ledger Entry")
    custom_cols = [c for c in columns if c.startswith("custom_")]
    print("Custom columns in Stock Ledger Entry:", custom_cols)
    print("All columns:", columns)
