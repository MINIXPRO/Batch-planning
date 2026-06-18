import frappe
from custom_batch_planning.custom_batch_planning.doctype.batch_planning.batch_planning import get_project_finished_items

def run():
    print("Testing get_project_finished_items with project 'PLTP-2025-0001'...")
    res = get_project_finished_items(None, "", None, 0, 20, {"project": "PLTP-2025-0001"})
    print("Result:", res)

    print("Testing get_project_finished_items with empty project...")
    res_empty = get_project_finished_items(None, "", None, 0, 20, {})
    print("Result empty:", res_empty)
