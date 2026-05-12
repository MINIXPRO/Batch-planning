import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate

class MaterialAllocation(Document):
    
    @frappe.whitelist()
    def auto_allocate(self):
        """
        Auto Allocate Flow:
        1. Fetch warehouse from Employee Function.
        2. For each item, fetch batches sorted by expiry date (FEFO).
        3. Fill batch-wise details until quantity_required is met.
        4. If item has no batches but stock exists, allocate directly.
        5. Update allocation status and save.
        """

        if self.workflow_state != 'Approved':
            frappe.throw("Allocation can only be performed when the document is in 'Approved' state.")

        if self.docstatus == 2:
            frappe.throw("Allocation cannot be performed on Cancelled documents.")

        warehouse = self.get_warehouse()

        if not warehouse:
            frappe.throw(
                f"No store warehouse found for Employee Function: {self.employee_function}"
            )

        for item in self.material_allocation:

            # Reset allocation fields
            item.qty_allocated = 0
            item.shortage = 0
            item.set("batch_details", [])

            # FIX: Use allocate_qty as-is (user may have edited it), 
            # fallback to quantity_required only if allocate_qty is not set
            qty_needed = flt(item.allocate_qty) if flt(item.allocate_qty) > 0 else flt(item.quantity_required)

            if qty_needed <= 0:
                continue

            # -----------------------------------------------------------------
            # Fetch latest stock available from SLE
            # -----------------------------------------------------------------
            sle_stock = frappe.db.sql("""
                SELECT qty_after_transaction
                FROM `tabStock Ledger Entry`
                WHERE item_code = %s
                  AND warehouse = %s
                  AND is_cancelled = 0
                ORDER BY posting_date DESC,
                         posting_time DESC,
                         creation DESC
                LIMIT 1
            """, (item.item_code, warehouse))

            item.stock_available = (
                flt(sle_stock[0][0]) if sle_stock else 0.0
            )

            # -----------------------------------------------------------------
            # Fetch available batches (FEFO)
            # -----------------------------------------------------------------
            batches = self.get_batches(item.item_code, warehouse)

            total_allocated = 0

            for b in batches:

                if total_allocated >= qty_needed:
                    break

                available = flt(b.actual_qty)

                if available <= 0:
                    continue

                allocate_qty = min(
                    available,
                    qty_needed - total_allocated
                )

                item.append("batch_details", {
                    "batch_no": b.batch_no,
                    "expiry_date": b.expiry_date,
                    "qty_available": available,
                    "qty_allocated": allocate_qty
                })

                total_allocated += allocate_qty

            # -----------------------------------------------------------------
            # FIX: Fallback for NON-BATCH items
            # If no batches found but stock is available, allocate directly
            # -----------------------------------------------------------------
            if total_allocated == 0 and flt(item.stock_available) >= qty_needed:
                total_allocated = qty_needed

            # -----------------------------------------------------------------
            # Final allocation update
            # -----------------------------------------------------------------
            item.qty_allocated = total_allocated
            item.shortage = max(qty_needed - total_allocated, 0)

        # ---------------------------------------------------------------------
        # Update allocation status
        # ---------------------------------------------------------------------
        self.allocation_status = "Allocated"

        # Allow update after submit
        if self.docstatus == 1:
            self.flags.ignore_validate_update_after_submit = True

        self.save()

        # Explicit child row DB update
        for item in self.material_allocation:
            item.db_update()

        return True

    @frappe.whitelist()
    def deallocate(self):
        """
        Deallocate Flow:
        1. Clear batch details.
        2. Reset allocated quantities.
        3. Set status to Deallocated.
        """

        if self.docstatus == 2:
            frappe.throw("Cannot deallocate a Cancelled document.")

        for item in self.material_allocation:
            item.qty_allocated = 0
            item.shortage = flt(item.quantity_required)
            item.set("batch_details", [])

        self.allocation_status = "Deallocated"

        if self.docstatus == 1:
            self.flags.ignore_validate_update_after_submit = True

        self.save()

        return True

    def autoname(self):
        if self.batch_planning:
            count = frappe.db.count(
                "Material Allocation",
                filters={"batch_planning": self.batch_planning}
            )
            counter = str(count + 1).zfill(2)
            self.name = f"MA-{self.batch_planning}-{counter}"
        else:
            frappe.throw("Batch Planning is required to generate document name.")

    def get_warehouse(self):
        """
        Fetch store warehouse from Employee Function linked table.
        """

        ef_doc = frappe.get_doc(
            "Employee Function",
            self.employee_function
        )

        for row in ef_doc.get("table_bukm"):

            if row.store_warehouse:
                return row.store_warehouse

        return None

    def get_batches(self, item_code, warehouse):
        """
        Fetch available batches using FEFO logic.
        Existing allocations are deducted.
        """

        return frappe.db.sql("""

            SELECT
                sle.batch_no,
                b.expiry_date,

                (
                    SUM(sle.actual_qty)

                    - IFNULL((
                        SELECT SUM(mbd.qty_allocated)

                        FROM `tabMA Batch Detail` mbd

                        INNER JOIN `tabMaterial Allocation` ma
                            ON ma.name = mbd.parent

                        WHERE mbd.batch_no = sle.batch_no
                          AND ma.name != %s
                          AND ma.allocation_status = 'Allocated'
                          AND ma.docstatus != 2

                    ), 0)

                ) AS actual_qty

            FROM `tabStock Ledger Entry` sle

            INNER JOIN `tabBatch` b
                ON b.name = sle.batch_no

            WHERE sle.item_code = %s
              AND sle.warehouse = %s
              AND sle.is_cancelled = 0
              AND sle.batch_no IS NOT NULL
              AND sle.batch_no != ''
              AND b.disabled = 0
              AND (
                    b.expiry_date IS NULL
                    OR b.expiry_date >= CURDATE()
                  )

            GROUP BY
                sle.batch_no,
                b.expiry_date

            HAVING (
                SUM(sle.actual_qty)

                - IFNULL((
                    SELECT SUM(mbd.qty_allocated)

                    FROM `tabMA Batch Detail` mbd

                    INNER JOIN `tabMaterial Allocation` ma
                        ON ma.name = mbd.parent

                    WHERE mbd.batch_no = sle.batch_no
                      AND ma.name != %s
                      AND ma.allocation_status = 'Allocated'
                      AND ma.docstatus != 2

                ), 0)

            ) > 0

            ORDER BY
                b.expiry_date ASC

        """, (
            self.name,
            item_code,
            warehouse,
            self.name
        ), as_dict=True)


@frappe.whitelist()
def ma_get_allocated_qty(item_code, employee_function, exclude_parent=None, row_name=None):
    """
    Calculates current allocated quantity and free stock for an item using SLE.
    """
    warehouse = None
    ef_doc = frappe.get_doc("Employee Function", employee_function)
    for row in ef_doc.get("table_bukm"):
        if row.store_warehouse:
            warehouse = row.store_warehouse
            break
            
    if not warehouse:
        return {"free_stock": 0, "allocated_qty": 0}

    sle_stock = frappe.db.sql("""
        SELECT qty_after_transaction
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
          AND warehouse = %s
          AND is_cancelled = 0
        ORDER BY posting_date DESC, posting_time DESC, creation DESC
        LIMIT 1
    """, (item_code, warehouse))
    total_stock = flt(sle_stock[0][0]) if sle_stock else 0.0
    
    query = """
        SELECT SUM(mai.qty_allocated)
        FROM `tabMaterial Allocation Item` mai
        INNER JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
        WHERE mai.item_code = %s
        AND ma.employee_function = %s
        AND ma.allocation_status != 'Deallocated'
        AND ma.docstatus != 2
    """
    args = [item_code, employee_function]
    
    if exclude_parent:
        query += " AND ma.name != %s"
        args.append(exclude_parent)
        
    allocated_qty = frappe.db.sql(query, tuple(args))[0][0] or 0
    
    return {
        "free_stock": total_stock - allocated_qty,
        "allocated_qty": allocated_qty
    }


@frappe.whitelist()
def get_open_pr_po(item_codes):
    if isinstance(item_codes, str):
        import json
        item_codes = json.loads(item_codes)

    result = {}
    for item_code in item_codes:
        open_pr = frappe.db.sql("""
            SELECT IFNULL(SUM(mri.qty - mri.ordered_qty), 0)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s AND mr.docstatus = 1
            AND mri.ordered_qty < mri.qty
        """, (item_code,))[0][0] or 0

        open_po = frappe.db.sql("""
            SELECT IFNULL(SUM(poi.qty - poi.received_qty), 0)
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE poi.item_code = %s AND poi.docstatus = 1
            AND poi.received_qty < poi.qty
        """, (item_code,))[0][0] or 0

        result[item_code] = {
            'open_pr': round(float(open_pr), 2),
            'open_po': round(float(open_po), 2)
        }

    return result


@frappe.whitelist(allow_guest=True)
def get_item_batch_expiry(item_codes):
    if isinstance(item_codes, str):
        import json
        item_codes = json.loads(item_codes)

    if not item_codes:
        return {}

    from frappe.utils import getdate, today
    fmt = ",".join(["%s"] * len(item_codes))
    today_date = getdate(today())

    batches = frappe.db.sql(f"""
        SELECT
            b.item,
            b.name as batch_no,
            b.expiry_date,
            COALESCE(SUM(sle.actual_qty), 0) as qty
        FROM `tabBatch` b
        LEFT JOIN `tabStock Ledger Entry` sle ON sle.batch_no = b.name
            AND sle.is_cancelled = 0
        WHERE b.item IN ({fmt})
        AND b.expiry_date IS NOT NULL
        AND b.disabled = 0
        GROUP BY b.item, b.name, b.expiry_date
    """, item_codes, as_dict=True)

    result = {}
    for b in batches:
        item = b.item
        expiry = getdate(b.expiry_date)
        days_left = (expiry - today_date).days

        if days_left < 0:
            status = "expired"
            label = f"Expired ({abs(days_left)}d ago)"
        elif days_left <= 30:
            status = "expiring_soon"
            label = f"Expiring in {days_left}d"
        else:
            status = "ok"
            label = f"OK ({days_left}d left)"

        if item not in result:
            result[item] = {
                "status": status,
                "label": label,
                "days_left": days_left,
                "earliest_expiry": str(expiry),
                "batch_no": b.batch_no
            }

    return result