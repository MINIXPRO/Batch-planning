import frappe
from custom_batch_planning.api.pr_integration import consolidate_items_table


def validate_purchase_order(doc, method):
    """
    Consolidate identical items (by item_code) and carry the single/multiple
    custom_batch_planning_no from the linked Material Request or child items
    to the parent Purchase Order header.

    Rules (simplified design):
    - Parent PO carries custom_batch_planning_no.
    - Item-level batch fields (custom_batch_reference) are NOT written.
    """

    # ── Step 1: Consolidate duplicate item rows and clear custom_batch_reference ──
    consolidate_items_table(doc)

    # ── Step 2: Set parent custom_batch_planning_no from child items or MR if missing ───
    if not doc.get("custom_batch_planning_no"):
        bp_nos = []
        for item in doc.items:
            if item.get("custom_batch_planning_no"):
                bp_nos.append(item.custom_batch_planning_no)
            elif item.get("material_request"):
                mr_bp_no = frappe.db.get_value(
                    "Material Request",
                    item.material_request,
                    "custom_batch_planning_no"
                )
                if mr_bp_no:
                    bp_nos.append(mr_bp_no)
        
        if bp_nos:
            unique_bp_nos = []
            for b in bp_nos:
                if b and b not in unique_bp_nos:
                    unique_bp_nos.append(b)
            doc.custom_batch_planning_no = ", ".join(unique_bp_nos)

    # ── Step 3: Recalculate taxes and totals ─────────────────────────────
    if hasattr(doc, "calculate_taxes_and_totals"):
        doc.calculate_taxes_and_totals()
