import frappe

def map_purchase_receipt_fields(doc, method=None):
    # Derive the document-level Batch Planning No and Batch No from the linked Material Request references.
    # The Purchase Order may be used as an intermediate reference, but the Material Request is the source of truth.
    
    bp_nos = []
    batch_refs = []
    
    for item in doc.items:
        bp_no = None
        batch_ref = None
        
        # 1. Try to fetch from Material Request Item
        if item.get("material_request_item"):
            mri_data = frappe.db.get_value(
                "Material Request Item",
                item.material_request_item,
                ["custom_batch_planning_no", "custom_batch_reference"],
                as_dict=True
            )
            if mri_data:
                bp_no = mri_data.custom_batch_planning_no
                batch_ref = mri_data.custom_batch_reference
                
        # 2. Try to fetch from parent Material Request
        if (not bp_no or not batch_ref) and item.get("material_request"):
            mri_parent_bp = frappe.db.get_value(
                "Material Request",
                item.material_request,
                "custom_batch_planning_no"
            )
            if mri_parent_bp:
                bp_no = mri_parent_bp
                
        # 3. Fallback to Purchase Order Item
        if (not bp_no or not batch_ref) and item.get("purchase_order_item"):
            poi_data = frappe.db.get_value(
                "Purchase Order Item",
                item.purchase_order_item,
                ["custom_batch_planning_no"],
                as_dict=True
            )
            if poi_data:
                if not bp_no:
                    bp_no = poi_data.custom_batch_planning_no
                    
        # 4. Fallback to parent Purchase Order
        if (not bp_no or not batch_ref) and item.get("purchase_order"):
            po_parent_bp = frappe.db.get_value(
                "Purchase Order",
                item.purchase_order,
                "custom_batch_planning_no"
            )
            if po_parent_bp and not bp_no:
                bp_no = po_parent_bp
                
        # Collect references
        if bp_no:
            for x in bp_no.split(","):
                val = x.strip()
                if val:
                    bp_nos.append(val)
                    
        if batch_ref:
            for x in batch_ref.split(","):
                val = x.strip()
                if val:
                    batch_refs.append(val)
                    
    # Set parent document level custom_batch_planning_no (Link to Batch Planning)
    if bp_nos and not doc.get("custom_batch_planning_no"):
        unique_bp_nos = sorted(list(set(bp_nos)))
        for bp in unique_bp_nos:
            if frappe.db.exists("Batch Planning", bp):
                doc.custom_batch_planning_no = bp
                break
                
    # Set parent document level custom_batch_no (Link to Batches Planned)
    if batch_refs and not doc.get("custom_batch_no"):
        unique_batch_refs = sorted(list(set(batch_refs)))
        for batch in unique_batch_refs:
            clean_batch = batch.split(",")[0].strip() if "," in batch else batch.strip()
            if clean_batch and frappe.db.exists("Batches Planned", clean_batch):
                doc.custom_batch_no = clean_batch
                break


def map_stock_entry_fields(doc, method=None):
    # Retrieve the Purchase Receipt GRN reference
    pr_name = doc.get("purchase_receipt_no")
    if not pr_name:
        for item in doc.items or []:
            if item.get("reference_purchase_receipt"):
                pr_name = item.reference_purchase_receipt
                break
                
    if pr_name:
        pr_data = frappe.db.get_value(
            "Purchase Receipt",
            pr_name,
            ["custom_batch_planning_no", "custom_batch_no"],
            as_dict=True
        )
        if pr_data:
            if pr_data.custom_batch_planning_no and not doc.get("custom_batch_planning_no"):
                doc.custom_batch_planning_no = pr_data.custom_batch_planning_no
                
            if pr_data.custom_batch_no:
                if not doc.get("custom_batch_no"):
                    doc.custom_batch_no = pr_data.custom_batch_no
                if not doc.get("custom_batch_planning"):
                    doc.custom_batch_planning = pr_data.custom_batch_no


def map_purchase_invoice_fields(doc, method=None):
    # Retrieve the linked references from item rows
    pr_names = []
    po_names = []
    mr_names = []
    
    for item in doc.items or []:
        if item.get("purchase_receipt"):
            pr_names.append(item.purchase_receipt)
        if item.get("purchase_order"):
            po_names.append(item.purchase_order)
        if item.get("material_request"):
            mr_names.append(item.material_request)
            
    # 1. Prioritize Purchase Receipt (GRN) parent custom_batch_planning_no
    if pr_names:
        for pr in list(set(pr_names)):
            val = frappe.db.get_value("Purchase Receipt", pr, "custom_batch_planning_no")
            if val and not doc.get("custom_batch_planning_no"):
                doc.custom_batch_planning_no = val
                return
                
    # 2. Fallback to Purchase Order parent custom_batch_planning_no
    if po_names:
        for po in list(set(po_names)):
            val = frappe.db.get_value("Purchase Order", po, "custom_batch_planning_no")
            if val and not doc.get("custom_batch_planning_no"):
                doc.custom_batch_planning_no = val
                return
                
    # 3. Fallback to Material Request parent custom_batch_planning_no
    if mr_names:
        for mr in list(set(mr_names)):
            val = frappe.db.get_value("Material Request", mr, "custom_batch_planning_no")
            if val and not doc.get("custom_batch_planning_no"):
                doc.custom_batch_planning_no = val
                return


