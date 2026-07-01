import frappe

def update_client_script():
    script_name = 'MA-Stock-Allocation-View'
    try:
        doc = frappe.get_doc('Client Script', script_name)
        
        new_function = """window.auto_allocate_all = function (frm) {
    let items = frm.doc.material_allocation || [];
    if (!items.length) return;

    frappe.confirm('⚠️ Warning: Auto Allocation will lock the quantities and update the stock. Continue?', function () {
        let done = 0;
        let promises = [];
        
        items.forEach(function (row) {
            let p = new Promise((resolve, reject) => {
                frappe.call({
                    method: 'ma_get_allocated_qty',
                    args: { item_code: row.item_code, employee_function: frm.doc.employee_function, exclude_parent: frm.doc.name, row_name: row.name },
                    callback: function (res) {
                        let fresh_stock = (res.message && res.message.free_stock) || 0;
                        let qty_to_transfer = fresh_stock >= (row.allocate_qty || 0)
                            ? (row.quantity_required || 0)
                            : Math.min(fresh_stock, row.quantity_required || 0);

                        frappe.model.set_value('Material Allocation Item', row.name, 'qty_allocated', qty_to_transfer)
                            .then(() => {
                                return frappe.model.set_value('Material Allocation Item', row.name, 'allocate_qty', qty_to_transfer);
                            })
                            .then(() => {
                                resolve();
                            })
                            .catch(reject);
                    }
                });
            });
            promises.push(p);
        });

        Promise.all(promises).then(() => {
            frm._allocating = true;
            frm.save().then(() => {
                // Save qty_allocated to DB for each row explicitly to ensure persistence
                let save_promises = items.map(row =>
                    frappe.call({
                        method: 'frappe.client.set_value',
                        args: {
                            doctype: 'Material Allocation Item',
                            name: row.name,
                            fieldname: 'qty_allocated',
                            value: row.qty_allocated
                        }
                    })
                );

                Promise.all(save_promises).then(() => {
                    frappe.call({
                        method: 'frappe.client.set_value',
                        args: { 
                            doctype: 'Material Allocation', 
                            name: frm.doc.name, 
                            fieldname: 'allocation_status', 
                            value: 'Allocated' 
                        },
                        callback: function () {
                            frappe.show_alert({ message: '✅ Auto Allocation done! Quantities are now locked.', indicator: 'green' });
                            setTimeout(function () { frm.reload_doc(); }, 1000);
                        }
                    });
                });
            });
        });
    });
};"""

        import re
        pattern = r"window\.auto_allocate_all = function \(frm\) \{.*?^\};"
        new_script = re.sub(pattern, new_function, doc.script, flags=re.DOTALL | re.MULTILINE)
        
        if new_script != doc.script:
            doc.script = new_script
            doc.save()
            frappe.db.commit()
            print(f"Successfully updated Client Script: {script_name}")
        else:
            print(f"No changes needed for Client Script: {script_name}")
            
    except frappe.DoesNotExistError:
        print(f"Client Script {script_name} does not exist.")
    except Exception as e:
        print(f"Error updating Client Script: {str(e)}")

if __name__ == "__main__":
    update_client_script()
