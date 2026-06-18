# custom_batch_planning/utils.py
import frappe

def propagate_batch_to_items(doc, method=None):
    """Copy parent Batch Planning link to each child row as `batch_reference`.
    Works for any DocType that has a child table (identified via meta).
    """
    batch = getattr(doc, "custom_batch_planning", None)
    if not batch:
        return
    # Iterate over all table fields (child tables) in the document
    for field in doc.meta.get_table_fields():
        child_rows = getattr(doc, field.fieldname, [])
        for row in child_rows:
            # Set the batch reference on the child row
            if hasattr(row, "batch_reference"):
                row.batch_reference = batch
    # Save changes without triggering another submit cycle
    doc.save(ignore_permissions=True)
