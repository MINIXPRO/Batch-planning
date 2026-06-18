// ============================================================
// BATCHES PLANNED — CLIENT SCRIPT
// DocType: Batches Planned
// ============================================================

frappe.ui.form.on("Batches Planned", {
	refresh: function (frm) {
		frm.page.clear_custom_actions();
		render_bom_items(frm);
		render_stock_entry_tab(frm);
		render_item_issue_tab(frm);

		// ── Show buttons only if Approved ──
		if (frm.doc.workflow_state === "Approved") {
			frappe.db.get_value(
				"Slot Opening",
				frm.doc.slot_opening_id,
				"batch_end_date",
				function (data) {
					let today = frappe.datetime.nowdate();
					if (!data || !data.batch_end_date || data.batch_end_date < today) return;

					frm.add_custom_button(
						"Material Allocation",
						function () {
							frappe.call({
								method: "frappe.client.get_list",
								args: {
									doctype: "Material Allocation",
									filters: { batches_planned: frm.doc.name },
									fields: ["name", "allocation_status"],
									order_by: "creation desc",
								},
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
											},
										);
									} else {
										open_new_ma(frm);
									}
								},
							});
						},
						"Create",
					);
				},
			);
		}
	},
});

// ============================================================
// BOM COMPONENTS TAB
// ============================================================
function render_bom_items(frm) {
	let $field = frm.fields_dict["bom_items"];
	if (!$field) return;

	if (!frm.doc.batch_planning) {
		$field.$wrapper.html(empty_state("📦", "No Batch Planning linked to this record."));
		return;
	}

	frappe.call({
		method: "frappe.client.get",
		args: { doctype: "Batch Planning", name: frm.doc.batch_planning },
		callback: function (r) {
			if (!r.message) {
				$field.$wrapper.html(empty_state("❌", "Could not load Batch Planning."));
				return;
			}

			let rows = r.message.custom_batch_details || [];
			let matched = find_matched_row(rows, frm.doc.batch_planning_id, frm.doc.amended_from);

			if (!matched || !matched.bom_list) {
				$field.$wrapper.html(empty_state("📋", "No BOM linked to this batch."));
				return;
			}

			let batch_key = `${frm.doc.batch_planning}-${matched.idx}`;
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



// ============================================================
// STOCK ENTRY TAB
// ============================================================
function render_stock_entry_tab(frm) {
	let $field = frm.fields_dict["stock_entry_details"];
	if (!$field) return;

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Stock Entry",
			filters: { custom_batch_planning: frm.doc.name },
			fields: ["name", "posting_date", "docstatus", "custom_material_allocation"],
			order_by: "creation desc",
		},
		callback: function (r) {
			let entries = r.message || [];

			if (!entries.length) {
				$field.$wrapper.html(`
                    <div style="padding:48px; text-align:center; color:#6b7280; border:2px dashed #d1fae5; border-radius:12px; background:#f0fdf4;">
                        <div style="font-size:36px;">📦</div>
                        <div style="font-size:15px; font-weight:700; color:#166534; margin-top:12px;">No Stock Entries Yet</div>
                        <div style="font-size:13px; color:#4b5563; margin-top:6px;">Stock Entries created from Material Allocation will appear here.</div>
                    </div>
                `);
				return;
			}

			let rows = entries
				.map((se, i) => {
					let status_color =
						se.docstatus === 1
							? "#16a34a"
							: se.docstatus === 2
								? "#dc2626"
								: "#d97706";
					let status_label =
						se.docstatus === 1
							? "Submitted"
							: se.docstatus === 2
								? "Cancelled"
								: "Draft";
					let bg = i % 2 === 0 ? "#f0faf4" : "#ffffff";
					return `
                    <tr style="background:${bg}; cursor:pointer;" onclick="frappe.set_route('Form', 'Stock Entry', '${se.name}')">
                        <td style="padding:10px 12px; text-align:center; color:#6b7280; font-size:12px;">${i + 1}</td>
                        <td style="padding:10px 12px;">
                            <span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:5px; font-size:11px; font-weight:700;">${se.name}</span>
                        </td>
                        <td style="padding:10px 12px; color:#1f2937; font-size:13px;">${se.posting_date || "-"}</td>
                        <td style="padding:10px 12px; color:#1f2937; font-size:13px;">${se.custom_material_allocation || "-"}</td>
                        <td style="padding:10px 12px;">
                            <span style="background:${status_color}20; color:${status_color}; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;">${status_label}</span>
                        </td>
                    </tr>
                `;
				})
				.join("");

			$field.$wrapper.html(`
                <div style="width:100%; font-family:inherit;">
                    <div style="background:linear-gradient(135deg, #16a34a 0%, #14532d 100%); color:#fff; padding:16px 20px; border-radius:10px 10px 0 0; display:flex; justify-content:space-between; align-items:center;">
                        <div style="font-size:15px; font-weight:700;">📦 Stock Entries</div>
                        <div style="background:rgba(255,255,255,0.15); padding:6px 16px; border-radius:20px; font-size:13px; font-weight:700;">${entries.length} Entry(s)</div>
                    </div>
                    <div style="overflow-x:auto; border:1px solid #d1fae5; border-top:none; border-radius:0 0 10px 10px;">
                        <table style="width:100%; border-collapse:collapse; font-size:13px;">
                            <thead>
                                <tr style="background:#dcfce7; border-bottom:2px solid #86efac;">
                                    <th style="padding:11px 12px; text-align:center; color:#166534; font-size:11px; text-transform:uppercase;">#</th>
                                    <th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Stock Entry</th>
                                    <th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Date</th>
                                    <th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Material Allocation</th>
                                    <th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Status</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>
            `);
		},
	});
}

function render_item_issue_tab(frm) {
	let $field = frm.fields_dict["item_issue_details"];
	if (!$field) return;

	frappe.call({
		method: "custom_batch_planning.custom_batch_planning.doctype.batches_planned.batches_planned.get_item_issue_data",
		args: { batch_planning: frm.doc.name },
		callback: function (r) {
			let items_list = r.message || [];

			if (!items_list.length) {
				$field.$wrapper.html(empty_state("📋", "No items issued yet. Items will appear here after Stock Entries are submitted."));
				return;
			}

			let rows_html = items_list.map(function (item, i) {
				let bg = i % 2 === 0 ? "#f0faf4" : "#ffffff";
				return `
					<tr style="background:${bg};">
						<td style="padding:10px 12px; text-align:center; color:#6b7280; font-weight:600; font-size:13px;">${i + 1}</td>
						<td style="padding:10px 12px;">
							<span style="background:#16a34a; color:#fff; padding:3px 10px; border-radius:5px; font-size:11px; font-weight:700; white-space:nowrap;">
								${item.item_code}
							</span>
						</td>
						<td style="padding:10px 12px; color:#1f2937; font-size:13px;">${item.item_name || ""}</td>
						<td style="padding:10px 12px; text-align:center; font-weight:700; color:#15803d; font-size:13px;">${item.qty}</td>
						<td style="padding:10px 12px; text-align:center; color:#4b5563; font-size:12px;">${item.uom || ""}</td>
						<td style="padding:10px 12px; color:#4b5563; font-size:12px;">${item.s_warehouse || "-"}</td>
						<td style="padding:10px 12px; color:#4b5563; font-size:12px;">${item.t_warehouse || "-"}</td>
					</tr>`;
			}).join("");

			$field.$wrapper.html(`
				<div style="width:100%; font-family:inherit;">
					<div style="background:linear-gradient(135deg, #16a34a 0%, #14532d 100%); color:#fff; padding:16px 20px; border-radius:10px 10px 0 0; display:flex; justify-content:space-between; align-items:center;">
						<div style="font-size:15px; font-weight:700;">📋 Item Issue — Consolidated Items</div>
						<div style="background:rgba(255,255,255,0.15); padding:6px 16px; border-radius:20px; font-size:13px; font-weight:700;">${items_list.length} Item(s)</div>
					</div>
					<div style="overflow-x:auto; border:1px solid #d1fae5; border-top:none; border-radius:0 0 10px 10px;">
						<table style="width:100%; border-collapse:collapse; font-size:13px;">
							<thead>
								<tr style="background:#dcfce7; border-bottom:2px solid #86efac;">
									<th style="padding:11px 12px; text-align:center; color:#166534; font-size:11px; text-transform:uppercase;">#</th>
									<th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Item Code</th>
									<th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Item Name</th>
									<th style="padding:11px 12px; text-align:center; color:#166534; font-size:11px; text-transform:uppercase;">Total Qty</th>
									<th style="padding:11px 12px; text-align:center; color:#166534; font-size:11px; text-transform:uppercase;">UOM</th>
									<th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Source Warehouse</th>
									<th style="padding:11px 12px; text-align:left; color:#166534; font-size:11px; text-transform:uppercase;">Target Warehouse</th>
								</tr>
							</thead>
							<tbody>${rows_html}</tbody>
						</table>
					</div>
					<div style="padding:8px 16px; background:#f0fdf4; border:1px solid #d1fae5; border-top:none; border-radius:0 0 10px 10px; font-size:12px; color:#166534;">
						✅ <b>${items_list.length}</b> unique item(s) across all submitted Stock Entries
					</div>
				</div>
			`);
		}
	});
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

function empty_state(icon, msg) {
	return `<div style="padding:48px; text-align:center; color:#6b7280; border:2px dashed #d1fae5; border-radius:12px; background:#f0fdf4;"><div style="font-size:36px;">${icon}</div><div style="font-size:13px;">${msg}</div></div>`;
}

function open_new_ma(frm) {
	frappe.new_doc("Material Allocation", {
		batch_planning: frm.doc.batch_planning,
		batches_planned: frm.doc.name,
		employee_function: frm.doc.employee_function,
		project_id: frm.doc.project,
		project_name: frm.doc.project_name,
		workflow_state: "Draft",
	});
}
