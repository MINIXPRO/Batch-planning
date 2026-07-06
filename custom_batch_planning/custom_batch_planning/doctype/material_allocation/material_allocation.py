import frappe
import json
from frappe.model.document import Document
from frappe.utils import flt, getdate, today, now

class MaterialAllocation(Document):

    def validate(self):
        self.validate_planning_window()
        self.check_batch_planning_allocation_limit()
        for item in self.material_allocation:
            qty_requested = flt(item.allocate_qty)
            bom_qty = flt(item.quantity_required)
            stock = flt(item.stock_available)

            if qty_requested > stock:
                frappe.throw(
                    f"Row #{item.idx}: Stock Available ({stock}) is less than Qty Requested ({qty_requested}) for item {item.item_code}."
                )
            if qty_requested > bom_qty:
                frappe.throw(
                    f"Row #{item.idx}: Qty Requested ({qty_requested}) cannot exceed Consolidated BOM Qty ({bom_qty}) for item {item.item_code}."
                )
            if qty_requested != bom_qty and not (item.reason or "").strip():
                frappe.throw(
                    f"Row #{item.idx}: Reason is mandatory because Qty Requested ({qty_requested}) differs from Consolidated BOM Qty ({bom_qty}) for item {item.item_code}."
                )

    def check_batch_planning_allocation_limit(self):
        if not self.batch_planning:
            return
            
        for item in self.material_allocation:
            query = """
                SELECT IFNULL(SUM(mai.allocate_qty), 0)
                FROM `tabMaterial Allocation Item` mai
                INNER JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
                WHERE mai.item_code = %s 
                AND ma.batch_planning = %s
                AND ma.name != %s
                AND ma.docstatus != 2
                AND ma.allocation_status NOT IN ('Deallocated', 'Stock Entry Done')
                FOR UPDATE
            """
            
            already_allocated = flt(frappe.db.sql(query, (item.item_code, self.batch_planning, self.name or ""))[0][0])
            total = already_allocated + flt(item.allocate_qty)
            
            if total > flt(item.quantity_required):
                frappe.throw(
                    f"Row #{item.idx}: Total allocate quantity ({total}) exceeds quantity_required ({item.quantity_required}) for item {item.item_code}. "
                    f"(Already allocated across other documents: {already_allocated}, Requested here: {item.allocate_qty})"
                )

    def validate_planning_window(self):
        if not self.batch_planning:
            return
        
        latest_date = frappe.db.sql(
            """
            SELECT MAX(slot_booking_date)
            FROM `tabSlot Booking CT`
            WHERE parent = %s AND parenttype = 'Batch Planning'
            """,
            (self.batch_planning,)
        )
        
        if latest_date and latest_date[0][0]:
            d = getdate(latest_date[0][0])
            if d < getdate(today()):
                frappe.throw(
                    f"Material Allocation cannot be saved because the planning window for Batch Planning <b>{self.batch_planning}</b> (last date: {d}) has already passed."
                )

    @frappe.whitelist()
    def auto_allocate(self):
        """
        Auto Allocate Flow:
        1. Fetch warehouse from Employee Function.
        2. FEFO based batch allocation.
        3. Fallback for non-batch items.
        """
        if self.workflow_state != "Approved":
            frappe.throw("Allocation can only be performed when the document is in 'Approved' state.")

        if self.docstatus == 2:
            frappe.throw("Allocation cannot be performed on Cancelled documents.")

        warehouse = self.get_warehouse()
        if not warehouse:
            frappe.throw(f"No store warehouse found for Employee Function: {self.employee_function}")

        for item in self.material_allocation:
            item.qty_allocated = 0
            item.shortage = 0
            item.set("batch_details", [])

            qty_needed = flt(item.allocate_qty) if flt(item.allocate_qty) > 0 else flt(item.quantity_required)
            if qty_needed <= 0:
                continue

            item.stock_available = flt(frappe.db.get_value("Bin", {"item_code": item.item_code, "warehouse": warehouse}, "actual_qty"))

            batches = self.get_batches(item.item_code, warehouse)
            total_allocated = 0

            for b in batches:
                if total_allocated >= qty_needed:
                    break

                available = flt(b.actual_qty)
                if available <= 0:
                    continue

                allocate_qty = min(available, qty_needed - total_allocated)
                item.append("batch_details", {
                    "batch_no": b.batch_no,
                    "expiry_date": b.expiry_date,
                    "qty_available": available,
                    "qty_allocated": allocate_qty,
                })
                total_allocated += allocate_qty

            if total_allocated == 0 and flt(item.stock_available) >= qty_needed:
                total_allocated = qty_needed

            item.qty_allocated = total_allocated
            item.shortage = max(qty_needed - total_allocated, 0)

        self.allocation_status = "Allocated"
        if self.docstatus == 1:
            self.flags.ignore_validate_update_after_submit = True

        self.save()

        for item in self.material_allocation:
            item.db_update()

        self.save_allocation_log("Allocated")

        return True

    @frappe.whitelist()
    def deallocate(self):
        if self.docstatus == 2:
            frappe.throw("Cannot deallocate a Cancelled document.")

        existing_se = frappe.db.get_value(
            "Stock Entry",
            {"custom_material_allocation": self.name, "docstatus": 1},
            "name",
        )
        if existing_se:
            frappe.throw(
                f"⛔ Deallocation blocked. Stock Entry <b>{existing_se}</b> has already been "
                f"submitted. Items have been sent for manufacturing. "
                f"Please cancel the Stock Entry first."
            )

        for item in self.material_allocation:
            item.qty_allocated = 0
            item.shortage = flt(item.quantity_required)
            item.set("batch_details", [])

        self.allocation_status = "Deallocated"
        if self.docstatus == 1:
            self.flags.ignore_validate_update_after_submit = True

        self.save()

        self.save_allocation_log("Deallocated")

        return True

    def save_allocation_log(self, status):
        """Logs the allocation/deallocation activity to 'Material Allocation Log'."""
        existing = frappe.db.get_value(
            "Material Allocation Log",
            {"batch_planning": self.batch_planning},
            "name",
        )

        if existing:
            log = frappe.get_doc("Material Allocation Log", existing)
        else:
            log = frappe.new_doc("Material Allocation Log")
            log.batch_planning = self.batch_planning
            log.employee_function = self.employee_function
            log.project_id = self.project_id
            log.project_name = self.project_name

        for item in self.material_allocation:
            log.append("table", {
                "allocated_by": frappe.session.user,
                "allocated_on": now(),
                "material_allocation_id": self.name,
                "status": status,
                "item_code": item.item_code,
                "qty_allocated": item.qty_allocated if status == "Allocated" else 0,
            })

        existing_items = {}
        for r in (log.ma_logs or []):
            existing_items[r.item_code] = r

        for item in self.material_allocation:
            if status == "Allocated":
                if item.item_code in existing_items:
                    existing_items[item.item_code].qty_allocated += flt(item.allocate_qty)
                    existing_items[item.item_code].allocate_qty += flt(item.allocate_qty)
                    existing_items[item.item_code].allocated_on = now()
                else:
                    log.append("ma_logs", {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "uom": item.uom,
                        "quantity_required": flt(item.quantity_required),
                        "stock_available": flt(item.stock_available),
                        "allocate_qty": flt(item.allocate_qty),
                        "qty_allocated": flt(item.allocate_qty),
                        "shortage": flt(item.shortage),
                        "open_pr": flt(item.open_pr),
                        "open_po": flt(item.open_po),
                        "grn_qty": flt(item.grn_qty),
                        "status": "Allocated",
                        "allocated_on": now(),
                    })
            elif status == "Deallocated":
                if item.item_code in existing_items:
                    existing_items[item.item_code].qty_allocated -= flt(item.allocate_qty)
                    existing_items[item.item_code].allocate_qty -= flt(item.allocate_qty)
                    if existing_items[item.item_code].qty_allocated < 0:
                        existing_items[item.item_code].qty_allocated = 0
                    if existing_items[item.item_code].allocate_qty < 0:
                        existing_items[item.item_code].allocate_qty = 0

        log.save(ignore_permissions=True)

    def autoname(self):
        if self.batch_planning:
            count = frappe.db.count("Material Allocation", filters={"batch_planning": self.batch_planning})
            counter = str(count + 1).zfill(2)
            self.name = f"MA-{self.batch_planning}-{counter}"
        else:
            frappe.throw("Batch Planning is required to generate document name.")

    def get_warehouse(self):
        ef_doc = frappe.get_doc("Employee Function", self.employee_function)
        for row in ef_doc.get("table_bukm"):
            if row.store_warehouse:
                return row.store_warehouse
        return None

    def get_batches(self, item_code, warehouse):
        """Fetch batches with FEFO logic and exclude existing allocations."""
        return frappe.db.sql("""
            SELECT
                sle.batch_no,
                b.expiry_date,
                (SUM(sle.actual_qty) - IFNULL((
                    SELECT SUM(mbd.qty_allocated)
                    FROM `tabMA Batch Detail` mbd
                    INNER JOIN `tabMaterial Allocation` ma ON ma.name = mbd.parent
                    WHERE mbd.batch_no = sle.batch_no
                      AND ma.name != %s
                      AND ma.allocation_status = 'Allocated'
                      AND ma.docstatus != 2
                ), 0)) AS actual_qty
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabBatch` b ON b.name = sle.batch_no
            WHERE sle.item_code = %s
              AND sle.warehouse = %s
              AND sle.is_cancelled = 0
              AND sle.batch_no IS NOT NULL
              AND sle.batch_no != ''
              AND b.disabled = 0
              AND (b.expiry_date IS NULL OR b.expiry_date >= CURDATE())
            GROUP BY sle.batch_no, b.expiry_date
            HAVING (SUM(sle.actual_qty) - IFNULL((
                SELECT SUM(mbd.qty_allocated)
                FROM `tabMA Batch Detail` mbd
                INNER JOIN `tabMaterial Allocation` ma ON ma.name = mbd.parent
                WHERE mbd.batch_no = sle.batch_no
                  AND ma.name != %s
                  AND ma.allocation_status = 'Allocated'
                  AND ma.docstatus != 2
            ), 0)) > 0
            ORDER BY b.expiry_date ASC
        """, (self.name, item_code, warehouse, self.name), as_dict=True)

@frappe.whitelist()
def ma_get_allocated_qty(item_code, employee_function, exclude_parent=None, row_name=None):
    warehouse = None
    ef_doc = frappe.get_doc("Employee Function", employee_function)
    for row in ef_doc.get("table_bukm"):
        if row.store_warehouse:
            warehouse = row.store_warehouse
            break

    if not warehouse:
        return {"free_stock": 0, "allocated_qty": 0}

    total_stock = flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))

    query = """
        SELECT SUM(mai.qty_allocated)
        FROM `tabMaterial Allocation Item` mai
        INNER JOIN `tabMaterial Allocation` ma ON ma.name = mai.parent
        WHERE mai.item_code = %s AND ma.employee_function = %s
        AND ma.allocation_status NOT IN ('Deallocated', 'Stock Entry Done')
        AND ma.docstatus != 2
    """
    args = [item_code, employee_function]
    if exclude_parent:
        query += " AND ma.name != %s"
        args.append(exclude_parent)

    allocated_qty = flt(frappe.db.sql(query, tuple(args))[0][0])

    return {
        "free_stock": total_stock - allocated_qty,
        "allocated_qty": allocated_qty,
    }

@frappe.whitelist()
def get_open_pr_po(item_codes):
    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)

    result = {}
    for item_code in item_codes:
        open_pr = flt(frappe.db.sql("""
            SELECT SUM(mri.qty - mri.ordered_qty)
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mr.name = mri.parent
            WHERE mri.item_code = %s AND mr.docstatus = 1 AND mri.ordered_qty < mri.qty
        """, (item_code,))[0][0])

        open_po = flt(frappe.db.sql("""
            SELECT SUM(poi.qty - poi.received_qty)
            FROM `tabPurchase Order Item` poi
            JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE poi.item_code = %s AND poi.docstatus = 1 AND poi.received_qty < poi.qty
        """, (item_code,))[0][0])

        result[item_code] = {
            "open_pr": round(open_pr, 2),
            "open_po": round(open_po, 2),
        }

    return result

@frappe.whitelist(allow_guest=True)
def get_item_batch_expiry(item_codes):
    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)
    if not item_codes:
        return {}

    today_date = getdate(today())
    fmt = ",".join(["%s"] * len(item_codes))

    batches = frappe.db.sql(f"""
        SELECT b.item, b.name as batch_no, b.expiry_date, COALESCE(SUM(sle.actual_qty), 0) as qty
        FROM `tabBatch` b
        LEFT JOIN `tabStock Ledger Entry` sle ON sle.batch_no = b.name AND sle.is_cancelled = 0
        WHERE b.item IN ({fmt}) AND b.expiry_date IS NOT NULL AND b.disabled = 0
        GROUP BY b.item, b.name, b.expiry_date
    """, item_codes, as_dict=True)

    result = {}
    for b in batches:
        expiry = getdate(b.expiry_date)
        days_left = (expiry - today_date).days

        if days_left < 0:
            status, label = "expired", f"Expired ({abs(days_left)}d ago)"
        elif days_left <= 30:
            status, label = "expiring_soon", f"Expiring in {days_left}d"
        else:
            status, label = "ok", f"OK ({days_left}d left)"

        if b.item not in result:
            result[b.item] = {
                "status": status,
                "label": label,
                "days_left": days_left,
                "earliest_expiry": str(expiry),
                "batch_no": b.batch_no,
            }

    return result

@frappe.whitelist()
def on_stock_entry_submit(stock_entry_name):
    """
    Called when Stock Entry linked to a Material Allocation is submitted.
    Updates allocation_status to 'Stock Entry Done'.
    """
    ma_name = frappe.db.get_value(
        "Stock Entry",
        stock_entry_name,
        "custom_material_allocation"
    )
    if not ma_name:
        return

    ma_doc = frappe.get_doc("Material Allocation", ma_name)

    if ma_doc.allocation_status != "Allocated":
        return

    ma_doc.allocation_status = "Stock Entry Done"
    ma_doc.flags.ignore_validate_update_after_submit = True
    ma_doc.save(ignore_permissions=True)
    frappe.db.commit()

@frappe.whitelist()
def get_allocated_items(batch_planning, employee_function):
    log_name = frappe.db.get_value(
        "Material Allocation Log",
        {"batch_planning": batch_planning, "employee_function": employee_function},
        "name"
    )
    
    ma_count = frappe.db.count("Material Allocation", filters={
        "batch_planning": batch_planning,
        "employee_function": employee_function,
        "docstatus": 1
    })

    if not log_name:
        return {"items": [], "ma_count": ma_count}

    log_doc = frappe.get_doc("Material Allocation Log", log_name)
    return {"items": log_doc.get("ma_logs", []), "ma_count": ma_count}
