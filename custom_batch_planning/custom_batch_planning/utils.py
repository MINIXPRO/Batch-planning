# custom_batch_planning/utils.py
import frappe

def propagate_batch_to_items(doc, method=None):
    """
    DEPRECATED — item-level batch propagation removed as part of the
    Batch Planning Document Linking Simplification.

    The single parent-level `custom_batch_planning_no` (Link → Batch Planning)
    is now the only reference maintained across MR, PO, GRN, PI, and
    Stock Entry.  No child-row fields are written.
    """
    pass
