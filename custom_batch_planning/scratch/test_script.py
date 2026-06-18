import frappe
from custom_batch_planning.custom_batch_planning.doctype.slot_opening.slot_opening import get_active_slot_masters

def run():
    print("Testing get_active_slot_masters with employee_function=None...")
    res = get_active_slot_masters("Slot Master List", "", "name", 0, 20, {"employee_function": None})
    print("Result (None):", res)

    print("\nTesting get_active_slot_masters with employee_function='' (empty string)...")
    res_empty = get_active_slot_masters("Slot Master List", "", "name", 0, 20, {"employee_function": ""})
    print("Result (empty string):", res_empty)

    print("\nTesting get_active_slot_masters with empty/missing filters dict...")
    res_missing = get_active_slot_masters("Slot Master List", "", "name", 0, 20, {})
    print("Result (missing):", res_missing)

    print("\nTesting get_active_slot_masters with VP-COM-ENG-001...")
    res_valid = get_active_slot_masters("Slot Master List", "", "name", 0, 20, {"employee_function": "VP-COM-ENG-001"})
    print("Result (valid):", res_valid)
