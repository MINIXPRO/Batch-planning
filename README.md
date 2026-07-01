# Custom Batch Planning

A custom Frappe/ERPNext application built for **Micro Crispr Private Limited (MCPL)** to manage batch
manufacturing slot planning, capacity tracking, and material allocation across the production lifecycle.

---

## Overview

This app introduces a structured workflow for planning manufacturing batches against limited
production slots, allocating materials per batch, and propagating batch-level traceability through
the procurement chain (Material Request → Purchase Order → Goods Receipt Note).

It is designed to plug into an existing ERPNext instance and works alongside core ERPNext modules
(Manufacturing, Buying, Stock) without modifying their core behavior — all customizations are done via
custom fields, custom doctypes, fixtures, and hooks.

---

## Document Hierarchy

The core planning flow follows this hierarchy:

```
Slot Master
   └── Slot Opening
         └── Batch Creation
               └── Batches Planned
                     └── Batch Planning
                           └── Material Allocation
                                 └── Stock Entry / Material Issue
```

Each level narrows scope: a Slot Master defines available capacity windows, a Slot Opening books
specific slots against dates, Batch Planning converts booked slots into actual manufacturing batches,
and Material Allocation reserves stock against those batches before issue.

---

## Core Doctypes

### Slot Master / Slot Opening
Defines and books manufacturing capacity slots by date. Tracks `total_batch_capacity` and per-date
booked slots via the `Slot Booking CT` child table. Includes UI logic to hide action buttons
(`Create Slot Opening`, `Create Batch`) once capacity is exhausted or the batch end date has passed.

### Batch Planning
Created against a Slot Opening (enforced 1-to-1 relationship). Contains the `custom_batch_details`
child table where individual batches are defined per booking date. On submit/approval, batches are
converted into `Batches Planned` records. Server-side validation ensures the number of batches
planned per date never exceeds the slots booked for that date on the linked Slot Opening.

### Batches Planned
The finalized record of an approved batch, created automatically from Batch Planning on approval.
Acts as the canonical batch reference used downstream in procurement and stock movements.

### Material Allocation
One Material Allocation per Batch Planning (1:1 relationship). Reserves required materials against a
batch. Validation logic (server-side only) checks:
- `stock_available < qty_requested`
- `qty_requested > quantity_required`

Only `qty_requested` and `reason` are editable on child rows in Draft state; all other fields are
read-only once allocation begins.

### Net Requirement Calculation
```
Net Requirement = max(
    total_qty_required - free_stock - open_mr_qty - open_po_qty - open_grn_qty,
    0
)
```
All quantities are filtered by `batch_planning_id`, an Inventory Dimension custom field
(`apply_to_all_doctypes: 1`) applied across Material Request Item, Purchase Order Item, and related
stock documents — not by `employee_function`, which is a separate dimension used elsewhere.

Stock available for Material Allocation = free stock + stock tagged with the current Batch Planning
name in the Stock Ledger Entry (SLE).

---

## Batch Traceability Through Procurement

The `batch_planning_id` field is propagated through the full procurement chain so that every
purchase document can be traced back to the batch that triggered it:

```
Material Request → Purchase Order → Goods Receipt Note (GRN)
```

This is implemented via `hooks_po_grn.py`, which copies `batch_planning_id` forward at each
document creation step. Custom fields for this dimension are added to MR Item and PO Item via
fixtures.

---

## Workflows

### Slot Opening Workflow
States: `Draft → Pending Approval From Accounts → Approved / Rejected → Cancelled`

Only the `Approved` state has `doc_status: 1`, meaning the document is only truly submitted
(docstatus 0 → 1) when explicitly approved via the workflow's `Approve` transition — not on a plain
save or generic Submit action.

Because of this, server-side logic that should only run on actual approval (e.g. updating the Slot
Capacity Tracker) is hooked into `on_submit` with an explicit guard:

```python
def on_submit(doc, method):
    if doc.workflow_state != "Approved":
        return
    update_slot_capacity_tracker(doc)
```

This avoids the earlier bug where capacity tracker updates fired on every Draft save via
`before_save`.

### Batch Planning Workflow
Includes states for Manufacturing User approval before a Batch Planning document can progress to
batch creation. On submit (approval), `create_batches_planned_records()` generates the corresponding
`Batches Planned` entries from `custom_batch_details`.

---

## Validation Rules

- **One Batch Planning per Slot Opening** — enforced server-side to keep batch ownership
  unambiguous; all batches for a given Slot Opening live inside a single Batch Planning document.
- **Per-date capacity check** — the number of `custom_batch_details` rows assigned to a given date
  cannot exceed the `planning_capacity` value for that same date in the Slot Opening's `Slot Booking CT`
  child table. This mirrors the client-side `has_remaining` logic exactly, so UI and server stay in
  sync.
- **Material Allocation field locking** — only `allocate_qty`/`qty_requested` and `reason` are
  editable in Draft; all other Material Allocation Item fields are read-only.

---

## Client-Side Behavior

- **Create Slot Opening** button is hidden on Slot Master List once `batch_end_date` has passed.
- **Create Batch** button on Slot Opening is hidden when `has_remaining` is false (no unconverted
  booked slots remain) or when `batch_end_date` has passed.
- Client Scripts and DocType JS files are placed under `public/js/` with explicit `doctype_js`
  entries in `hooks.py`, due to a known issue where triple-nested module structures prevent Frappe's
  default JS auto-detection.

---

## Fixtures & Deployment

This app uses Frappe's fixture system to migrate customizations (Custom Fields, Inventory
Dimensions, DocTypes marked custom) from local development to staging/production without requiring
Developer Mode on those environments.

### Workflow
```bash
bench export-fixtures
git add .
git commit -m "Update fixtures"
git push origin main
```
Staging then pulls and runs:
```bash
bench pull
bench migrate
bench restart
```

### Notes
- `hooks.py` fixtures export `Custom Field`, `DocType` (where `custom: 1`), and `Inventory
  Dimension`. Workflows are intentionally excluded from fixtures and managed manually per
  environment.
- DocTypes deployed without Developer Mode must have `custom: 1` explicitly set — a `custom: None`
  value will silently break fixture sync.
- Client Scripts requiring custom JS must be migrated to `public/js/` with corresponding
  `doctype_js` hook entries; standalone Client Script records alone are not sufficient for nested
  module structures.

---



## Local Development

```bash
cd ~/frappe-bench/frappe-bench
bench --site site_local console
```

Secondary bench (used for `mr_updatebutton` work):
```bash
cd ~/ProjectX/frappe-drive
```

## Contributing

Internal MCPL project. Changes should be tested against `site_local` before fixture export. Any
schema or workflow change affecting staging/production must go through Vinay for deployment
coordination after fixture sync is verified.

---

## License

Proprietary — Micro Crispr Private Limited (MCPL). Internal use only.