// ============================================================
// BATCHES PLANNED — CLIENT SCRIPT
// DocType: Batches Planned
// ============================================================

frappe.ui.form.on("Batches Planned", {
	refresh: function (frm) {
		frm.page.clear_custom_actions();
		render_bom_items(frm);
		render_mp_placeholder(frm);

		// ── Show buttons only if Approved ──
		if (frm.doc.workflow_state === "Approved") {
			frappe.db.get_value("Slot Opening", frm.doc.slot_opening_id, "batch_end_date", function(data) {
				let today = frappe.datetime.nowdate();
				if (!data || !data.batch_end_date || data.batch_end_date < today) return;

				frm.add_custom_button("Run Material Planning", function () {
				run_material_planning(frm);
			}).addClass("btn-primary");

			frm.add_custom_button(
				"Material Allocation",
				function () {
					frappe.call({
						method: "frappe.client.get_list",
						args: {
							doctype: "Material Allocation",
							filters: { batch_planning: frm.doc.name },
							fields: ["name", "allocation_status"],
							order_by: "creation desc",
						},
						// YE WALA BLOCK RAKHO — sirf callback change hoga
						callback: function (r) {
							let existing = r.message || [];
							let active = existing.filter(
								(d) => d.allocation_status !== "Deallocated",
							);
							if (active.length > 0) {
								frappe.confirm(
									`Materials already allocated via <b>${active.map((d) => d.name).join(", ")}</b>.<br><br>Do you still want to create a new Material Allocation?`,
									function () {
										open_new_ma(frm);
									}, // ← sirf naam change
								);
							} else {
								open_new_ma(frm); // ← sirf naam change
							}
						},
					});
				},
				"Create",
			);

			frm.add_custom_button(
				"Material Request",
				function () {
					let mp_data = frm._mp_data || [];

					if (!mp_data.length) {
						frappe.msgprint({
							title: "Run Material Planning First",
							message:
								"Please click <b>Run Material Planning</b> before creating a Material Request.",
							indicator: "orange",
						});
						return;
					}

					let shortage_items = mp_data
						.filter((row) => parseFloat(row.net_requirement || 0) > 0)
						.map((row) => ({
							item_code: row.item_code,
							qty: parseFloat(row.net_requirement),
							uom: row.uom,
							schedule_date: frappe.datetime.add_days(
								frappe.datetime.get_today(),
								1,
							),
						}));

					if (!shortage_items.length) {
						frappe.msgprint({
							title: "No Shortage",
							message:
								"All items have sufficient stock. No Material Request needed.",
							indicator: "green",
						});
						return;
					}

					frappe
						.new_doc("Material Request", {
							material_request_type: "Manufacture",
							custom_batch_no: frm.doc.name,
							custom_employee_function: frm.doc.employee_function,
							project: frm.doc.project,
							custom_project_name: frm.doc.project_name,
						})
						.then(() => {
							if (cur_frm) {
								cur_frm.clear_table("items");
								shortage_items.forEach((item) => {
									let row = cur_frm.add_child("items");
									row.item_code = item.item_code;
									row.qty = item.qty;
									row.uom = item.uom;
									row.schedule_date = item.schedule_date;
								});
								cur_frm.refresh_field("items");
							}
						});
				},
				"Create",
			);
			});
		}
	},
});

// ============================================================
// BOM COMPONENTS TAB
// ============================================================
function render_bom_items(frm) {
	let $field = frm.fields_dict["bom_items"];
	if (!$field) return;

	if (!frm.doc.batch_creation) {
		$field.$wrapper.html(empty_state("📦", "No Batch Creation linked to this record."));
		return;
	}

	frappe.call({
		method: "frappe.client.get",
		args: { doctype: "Batch Creation", name: frm.doc.batch_creation },
		callback: function (r) {
			if (!r.message) {
				$field.$wrapper.html(empty_state("❌", "Could not load Batch Creation."));
				return;
			}

			let rows = r.message.custom_batch_details || [];

			// UPDATED: Using helper to find matched row
			let matched = find_matched_row(rows, frm.doc.batch_planning_id, frm.doc.amended_from);

			if (!matched || !matched.bom_list) {
				$field.$wrapper.html(empty_state("📋", "No BOM linked to this batch."));
				return;
			}

			let batch_key = `${frm.doc.batch_creation}-${matched.idx}`;
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Batch BOM Store after Edit",
					filters: { batch_id: batch_key },
					fields: ["name"],
					limit: 1,
				},
				callback: function (store) {
					if (store.message && store.message.length > 0) {
						frappe.call({
							method: "frappe.client.get",
							args: {
								doctype: "Batch BOM Store after Edit",
								name: store.message[0].name,
							},
							callback: function (res) {
								let items = (res.message.bom_components || []).map(function (row) {
									return {
										item_code: row.item_code,
										item_name: row.item_name,
										uom: row.uom,
										qty: row.qty,
									};
								});
								render_bom_table_html(
									frm,
									items,
									matched.bom_list,
									frm.doc.finished_item,
									true,
								);
							},
						});
					} else {
						frappe.call({
							method: "frappe.client.get",
							args: { doctype: "BOM", name: matched.bom_list },
							callback: function (b) {
								if (!b.message) {
									$field.$wrapper.html(
										empty_state("❌", "BOM not found: " + matched.bom_list),
									);
									return;
								}
								let items = b.message.exploded_items || b.message.items || [];
								render_bom_table_html(
									frm,
									items,
									matched.bom_list,
									frm.doc.finished_item,
									false,
								);
							},
						});
					}
				},
			});
		},
	});
}

function render_bom_table_html(frm, items, bom_name, finished_item, is_edited) {
	let $field = frm.fields_dict["bom_items"];
	if (!$field) return;

	if (!items.length) {
		$field.$wrapper.html(empty_state("📦", "No items found in this BOM."));
		return;
	}

	let rows_html = items
		.map(function (item, i) {
			let bg = i % 2 === 0 ? "#f0faf4" : "#ffffff";
			return `
        <tr style="background:${bg};">
            <td style="padding:10px 12px; text-align:center; color:#6b7280; font-weight:600; font-size:13px;">${i + 1}</td>
            <td style="padding:10px 12px;">
                <span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:5px;
                    font-size:11px; font-weight:700; letter-spacing:0.3px; white-space:nowrap;">
                    ${item.item_code || ""}
                </span>
            </td>
            <td style="padding:10px 12px; color:#1f2937; font-size:13px;">${item.item_name || ""}</td>
            <td style="padding:10px 12px; text-align:center; color:#4b5563; font-size:12px;
                font-family:monospace;">${item.stock_uom || item.uom || ""}</td>
            <td style="padding:10px 12px; text-align:center; font-weight:700; color:#15803d;
                font-size:13px;">${parseFloat(item.qty_consumed_per_unit || item.qty || 0)}</td>
        </tr>`;
		})
		.join("");

	let edited_badge = is_edited
		? `<span style="background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;">✏️ Edited BOM</span>`
		: "";

	let html = `
    <div style="width:100%; box-sizing:border-box; font-family:inherit;">
        <div style="background:linear-gradient(135deg, #16a34a 0%, #14532d 100%);
            color:#fff; padding:16px 20px; border-radius:10px 10px 0 0;
            display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
            <div>
                <div style="font-size:15px; font-weight:700; margin-bottom:3px;">🧪 BOM Components ${edited_badge}</div>
                <div style="font-size:12px; opacity:0.85;">
                    BOM: <b>${bom_name}</b> &nbsp;|&nbsp; Finished Item: <b>${finished_item || "N/A"}</b>
                </div>
            </div>
            <div style="background:rgba(255,255,255,0.15); padding:8px 18px;
                border-radius:20px; font-weight:700; font-size:13px; white-space:nowrap;">
                📋 ${items.length} Items
            </div>
        </div>
        <div style="overflow-x:auto; border:1px solid #d1fae5; border-top:none; border-radius:0 0 10px 10px;">
            <table style="width:100%; border-collapse:collapse; font-family:inherit; font-size:13px;">
                <thead>
                    <tr style="background:#dcfce7;">
                        <th style="padding:11px 12px; text-align:center; color:#166534; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.8px; border-bottom:2px solid #bbf7d0;">#</th>
                        <th style="padding:11px 12px; text-align:left; color:#166534; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.8px; border-bottom:2px solid #bbf7d0;">Item Code</th>
                        <th style="padding:11px 12px; text-align:left; color:#166534; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.8px; border-bottom:2px solid #bbf7d0;">Item Name</th>
                        <th style="padding:11px 12px; text-align:center; color:#166534; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.8px; border-bottom:2px solid #bbf7d0;">UOM</th>
                        <th style="padding:11px 12px; text-align:center; color:#166534; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.8px; border-bottom:2px solid #bbf7d0;">Qty</th>
                    </tr>
                </thead>
                <tbody>${rows_html}</tbody>
            </table>
        </div>
        <div style="padding:8px 16px; background:#f0fdf4; border:1px solid #d1fae5; border-top:none; border-radius:0 0 10px 10px; font-size:12px; color:#166534;">
            ✅ <b>${items.length}</b> component(s) in this BOM
        </div>
    </div>`;
	$field.$wrapper.html(html);
}

function render_mp_placeholder(frm) {
	let $field = frm.fields_dict["material_planning"];
	if (!$field) return;

	$field.$wrapper.html(`
        <div style="padding:48px; text-align:center; color:#6b7280; border:2px dashed #d1fae5; border-radius:12px; margin:4px 0; background:#f0fdf4;">
            <div style="font-size:36px; margin-bottom:12px;">🏭</div>
            <div style="font-size:15px; font-weight:700; color:#166534; margin-bottom:6px;">Material Planning</div>
            <div style="font-size:13px; color:#4b5563;">Click <b style="color:#16a34a;">Run Material Planning</b> above to load stock data.</div>
        </div>
    `);
}

function run_material_planning(frm) {
	if (!frm.doc.employee_function || !frm.doc.batch_creation) {
		frappe.msgprint({
			title: "Missing",
			message: "Employee Function or Batch Creation missing.",
			indicator: "orange",
		});
		return;
	}

	let $field = frm.fields_dict["material_planning"];
	if ($field) {
		$field.$wrapper.html(`
            <div style="padding:48px; text-align:center; color:#6b7280;">
                <div style="width:36px; height:36px; border:3px solid #d1fae5; border-top-color:#16a34a; border-radius:50%; animation:mp-spin 0.8s linear infinite; margin:0 auto 14px;"></div>
                <style>@keyframes mp-spin { to { transform:rotate(360deg); } }</style>
                <div style="font-size:13px; color:#4b5563;">Fetching material planning data...</div>
            </div>
        `);
	}

	frappe.call({
		method: "frappe.client.get",
		args: { doctype: "Employee Function", name: frm.doc.employee_function },
		callback: function (ef) {
			let warehouse = (ef.message.table_bukm || []).find(
				(r) => r.store_warehouse,
			)?.store_warehouse;
			if (!warehouse) return frappe.msgprint("No store warehouse found.");

			frappe.call({
				method: "frappe.client.get",
				args: { doctype: "Batch Creation", name: frm.doc.batch_creation },
				callback: function (r) {
					let rows = r.message.custom_batch_details || [];

					// UPDATED: Using helper to find matched row
					let matched = find_matched_row(
						rows,
						frm.doc.batch_planning_id,
						frm.doc.amended_from,
					);

					if (!matched?.bom_list) return;

					let batch_key = `${frm.doc.batch_creation}-${matched.idx}`;
					frappe.call({
						method: "frappe.client.get_list",
						args: {
							doctype: "Batch BOM Store after Edit",
							filters: { batch_id: batch_key },
							fields: ["name"],
							limit: 1,
						},
						callback: function (store) {
							if (store.message && store.message.length > 0) {
								frappe.call({
									method: "frappe.client.get",
									args: {
										doctype: "Batch BOM Store after Edit",
										name: store.message[0].name,
									},
									callback: function (res) {
										let items = (res.message.bom_components || []).map(
											function (row) {
												return {
													item_code: row.item_code,
													item_name: row.item_name,
													qty_required: parseFloat(row.qty || 0),
												};
											},
										);
										fire_material_planning(frm, items, warehouse);
									},
								});
							} else {
								frappe.call({
									method: "frappe.client.get",
									args: { doctype: "BOM", name: matched.bom_list },
									callback: function (b) {
										let items = (
											b.message.exploded_items ||
											b.message.items ||
											[]
										).map((item) => ({
											item_code: item.item_code,
											item_name: item.item_name,
											qty_required: parseFloat(
												item.qty_consumed_per_unit || item.qty || 0,
											),
										}));
										fire_material_planning(frm, items, warehouse);
									},
								});
							}
						},
					});
				},
			});
		},
	});
}

function render_mp_table(frm, data, warehouse) {
	let $field = frm.fields_dict["material_planning"];
	let rows_html = data
		.map((row, i) => {
			let bg = i % 2 === 0 ? "#f0faf4" : "#ffffff";
			return `
        <tr style="background:${bg};">
            <td style="padding:9px 10px; text-align:center; color:#9ca3af; font-size:12px; font-weight:600;">${i + 1}</td>
            <td style="padding:9px 10px;"><span style="background:#16a34a; color:#fff; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; white-space:nowrap;">${row.item_code}</span></td>
            <td style="padding:9px 10px; color:#1f2937; font-size:12px;">${row.item_name || ""}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#d97706; font-size:12px;">${row.qty_required}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#15803d; font-size:12px;">${row.total_stock}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#1d4ed8; font-size:12px;">${row.main_stock}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#d97706; font-size:12px;">${row.allocated_qty}</td>
             <td style="padding:9px 10px; text-align:center; font-weight:700; font-size:12px; color:${parseFloat(row.free_stock) > 0 ? "#15803d" : "#dc2626"};">${row.free_stock}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#7c3aed; font-size:12px;">${row.lab_stock}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#7c3aed; font-size:12px;">${row.open_pr}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#1d4ed8; font-size:12px;">${row.open_po}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#059669; font-size:12px;">${row.open_grn}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; font-size:12px; color:${parseFloat(row.net_requirement) > 0 ? "#dc2626" : "#15803d"};">${row.net_requirement}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#15803d; font-size:12px;">${row.usable_qty != null ? row.usable_qty : "-"}</td>
            <td style="padding:9px 10px; text-align:center; font-weight:700; color:#dc2626; font-size:12px;">${row.expired_qty != null ? row.expired_qty : "-"}</td>
        </tr>`;
		})
		.join("");

	$field.$wrapper.html(`
    <div id="mp-table-container" style="width:100%; font-family:inherit;">
        <div style="background:linear-gradient(135deg, #16a34a 0%, #14532d 100%); color:#fff; padding:16px 20px; border-radius:10px 10px 0 0; display:flex; justify-content:space-between; align-items:center;">
            <div><div style="font-size:15px; font-weight:700;">🏭 Material Planning — Stock vs Requirement</div><div style="font-size:12px; opacity:0.85;">Warehouse: <b>${warehouse}</b></div></div>
        </div>
        <div style="overflow-x:auto; border:1px solid #d1fae5; border-top:none;"><table style="width:100%; border-collapse:collapse; min-width:1100px;">
            <thead><tr style="background:#dcfce7; border-bottom:2px solid #86efac;">
                <th style="${th_style()}">#</th>
                <th style="${th_style("left")}">Item Code</th>
                <th style="${th_style("left")}">Item Name</th>
                <th style="${th_style()}">Qty Req</th>
                <th style="${th_style()}">Total Stock</th>
                <th style="${th_style()}">Main Wh</th>
                   <th style="${th_style()}">Allocated</th>
                <th style="${th_style()}">Free Qty</th>
                <th style="${th_style()}">Lab Wise</th>
                <th style="${th_style()}">Open PR</th>
                <th style="${th_style()}">Open PO</th>
                <th style="${th_style()}">Open GRN</th>
                <th style="${th_style()}">Net Req</th>
                <th style="${th_style()}">Usable</th>
                <th style="${th_style()}">Expired Qty</th>
            </tr></thead>
            <tbody>${rows_html}</tbody>
        </table></div>
    </div>`);
}

// ============================================================
// HELPER FUNCTIONS
// ============================================================

// Find Matched Row — handles amended_from fallback for suffixes like -1, -2
function find_matched_row(rows, batch_planning_id, amended_from) {
	// 1. Exact match
	let matched = rows.find((r) => r.batch_planning_id === batch_planning_id);
	if (matched) return matched;

	// 2. Match via amended_from (original ID before amendment)
	if (amended_from) {
		matched = rows.find((r) => r.batch_planning_id === amended_from);
		if (matched) return matched;
	}

	// 3. Match via Base ID (strip trailing -1, -2 etc)
	let base_id = batch_planning_id.replace(/-\d+$/, "");
	matched = rows.find((r) => r.batch_planning_id === base_id);
	if (matched) return matched;

	return null;
}

function th_style(align = "center") {
	return `padding:11px 10px; text-align:${align}; color:#166534; font-weight:700; font-size:10px; text-transform:uppercase; white-space:nowrap;`;
}

function empty_state(icon, msg) {
	return `<div style="padding:48px; text-align:center; color:#6b7280; border:2px dashed #d1fae5; border-radius:12px; background:#f0fdf4;"><div style="font-size:36px;">${icon}</div><div style="font-size:13px;">${msg}</div></div>`;
}
function open_new_ma(frm) {
	frappe.new_doc("Material Allocation", {
		batch_planning: frm.doc.name,
		employee_function: frm.doc.employee_function,
		project_id: frm.doc.project,
		project_name: frm.doc.project_name,
		workflow_state: "Draft",
	});
}

function fire_material_planning(frm, items, warehouse) {
	frappe.call({
		method: "custom_batch_planning.custom_batch_planning.doctype.batches_planned.batches_planned.get_material_planning_data",
		args: {
			items: JSON.stringify(items),
			warehouse: warehouse,
			batch_planning: frm.doc.batch_creation,
			employee_function: frm.doc.employee_function,
		},
		callback: function (mp) {
			if (mp.message) {
				frm._mp_data = mp.message;
				render_mp_table(frm, mp.message, warehouse);
			}
		},
	});
}
