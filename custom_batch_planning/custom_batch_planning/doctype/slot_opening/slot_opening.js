// ─────────────────────────────────────────────
// Slot Opening — Complete Merged Client Script
// ─────────────────────────────────────────────

frappe.ui.form.on('Slot Opening', {

    refresh: function (frm) {
        frm.page.clear_custom_actions();
        frm.set_df_property('total_batch_remained', 'hidden', 0);
        frm.refresh_field('total_batch_remained');

        // ── Capacity Button ──
        frm.add_custom_button('📊 Capacity Remained', function () {
            if (!frm.doc.slot_master) {
                frappe.msgprint('Please select a Slot Master first!');
                return;
            }
            frappe.call({
                method: 'custom_batch_planning.custom_batch_planning.doctype.slot_opening.slot_opening.get_sct_details',
                args: { slot_master: frm.doc.slot_master },
                callback: function (r) {
                    if (!r.message || !r.message.length) {
                        frappe.msgprint('No Slot Capacity Tracker found!');
                        return;
                    }
                    let rows = r.message.sort((a, b) => a.date > b.date ? 1 : -1)
                        .map(d => `
                    <tr> 
        <td>${d.date.split('-').reverse().join('-')}</td>
        <td>${d.total_capacity}</td>
        <td>${d.capacity_booked}</td>
        <td style="color:${d.capacity_available > 0 ? 'green' : 'red'}; font-weight:bold;">
            ${d.capacity_available}
        </td>
    </tr>
`).join('');
                    frappe.msgprint({
                        title: 'Capacity Remained',
                        message: `
                        <table class="table table-bordered" style="width:100%">
                            <thead style="background:#f0f0f0">
                                <tr>
                                    <th>Date</th>
                                    <th>Total</th>
                                    <th>Booked</th>
                                    <th>Available</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    `,
                        wide: true
                    });
                }
            });
        });

        // ── Create Batch Button — only for saved docs ──
        if (!frm.is_new()) {
            frm.add_custom_button(__('➕ Create Batch'), function () {
                if (frm.is_dirty()) {
                    frappe.msgprint(__('Please save the document before creating a Batch.'));
                    return;
                }
                frappe.new_doc('Batch Creation', {
                    slot_opening: frm.doc.name,
                    custom_employee_function: frm.doc.employee_function,
                    custom_project_id: frm.doc.custom_project,
                    custom_project_name: frm.doc.custom_project_name,
                    custom_function_head_name: frm.doc.function_head_name,
                    month: frm.doc.batch_start_date ? new Date(frm.doc.batch_start_date).toLocaleString('en-US', { month: 'long' }) : '',
                    custom_total_batches_planned: frm.doc.total_batches_planned
                }).then(() => {
                    if (!cur_frm) return;

                    // ── Slot Opening Table autofill ──
                    cur_frm.clear_table('slot_opening_table');
                    (frm.doc.slot_booking || []).forEach(function (row) {
                        let nr = cur_frm.add_child('slot_opening_table');
                        nr.slot_booking_date = row.slot_booking_date;
                        nr.how_many_slots_per_day = row.how_many_slots_per_day;
                        nr.total_slots = row.total_slots;
                        nr.booked_slots = row.booked_slots;
                        nr.availabe_capacity = row.availabe_capacity;
                        nr.reason = row.reason;
                    });
                    cur_frm.refresh_field('slot_opening_table');

                    // ── Batch Details autofill ──
                    cur_frm.clear_table('custom_batch_details');
                    (frm.doc.slot_booking || []).forEach(function (row) {
                        let count = parseInt(row.booked_slots) || 0;
                        for (let i = 0; i < count; i++) {
                            let child = cur_frm.add_child('custom_batch_details');
                            child.slot_booking_date = row.slot_booking_date;
                            child.slot_opening_id = frm.doc.name;
                            child.reason = row.reason;
                        }
                    });
                    cur_frm.refresh_field('custom_batch_details');
                });
            });
        }

        if (frm.doc.slot_master) {
            frappe.db.get_value(
                'Slot Master List',
                frm.doc.slot_master,
                ['batch_end_date', 'batch_start_date', 'batch_capacity'],
                function (data) {
                    if (data) {
                        frm.doc.__batch_end_date = data.batch_end_date;
                        frm.doc.__batch_start_date = data.batch_start_date;
                        frm.doc.__batch_capacity = data.batch_capacity;
                    }
                }
            );
            fetch_sct_remaining(frm);
        }
        set_slot_master_filter(frm);
        loadSlotOpeningCalendar(frm);
    },

    after_save: function (frm) {
        if (frm.doc.name.startsWith("SB-")) {
            frappe.set_route('Form', 'Slot Opening', frm.doc.name);
            return;
        }
        // Name not updated in form yet, fetch from DB by creation
        frappe.db.get_list('Slot Opening', {
            filters: { 'creation': frm.doc.creation },
            fields: ['name'],
            limit: 1
        }).then(function (r) {
            if (r && r.length && r[0].name.startsWith("SB-")) {
                window.location.href = `/app/slot-opening/${r[0].name}`;
            }
        });
    },

    employee_function: function (frm) {
        frm.set_value('slot_master', '');
        frm.set_value('total_batch_capacity', '');
        frm.set_value('total_batch_remained', '');
        frm.set_value('batch_start_date', '');
        frm.set_value('batch_end_date', '');
        frm.set_value('custom_project', '');
        frm.set_value('custom_project_name', '');
        frm.doc.__batch_end_date = null;
        frm.doc.__batch_start_date = null;
        frm.doc.__batch_capacity = null;
        set_slot_master_filter(frm);
        loadSlotOpeningCalendar(frm);
    },

    slot_master: function (frm) {
        if (!frm.doc.slot_master) {
            frm.set_value('total_batch_capacity', '');
            frm.set_value('total_batch_remained', '');
            frm.set_value('batch_start_date', '');
            frm.set_value('batch_end_date', '');
            frm.set_value('custom_project', '');
            frm.set_value('custom_project_name', '');
            frm.doc.__batch_end_date = null;
            frm.doc.__batch_start_date = null;
            frm.doc.__batch_capacity = null;
            return;
        }

        frappe.db.get_value(
            'Slot Master List',
            frm.doc.slot_master,
            ['batch_capacity', 'batch_end_date', 'batch_start_date', 'custom_project'],
            function (data) {
                if (!data) return;

                frm.doc.__batch_end_date = data.batch_end_date;
                frm.doc.__batch_start_date = data.batch_start_date;
                frm.doc.__batch_capacity = data.batch_capacity;

                let today = frappe.datetime.nowdate();

                if (data.batch_end_date && data.batch_end_date < today) {
                    frappe.msgprint({
                        title: '⚠️ Slot Master Expired',
                        message: `The selected Slot Master <b>${frm.doc.slot_master}</b> has expired.`,
                        indicator: 'red'
                    });
                    frm.set_value('slot_master', '');
                    return;
                }

                frm.set_value('batch_start_date', data.batch_start_date);
                frm.set_value('batch_end_date', data.batch_end_date);
                frm.set_value('custom_project', data.custom_project);
                if (data.custom_project) {
                    frappe.db.get_value('Project', data.custom_project, 'project_name', function (p_data) {
                        if (p_data && p_data.project_name) {
                            frm.set_value('custom_project_name', p_data.project_name);
                        } else {
                            frm.set_value('custom_project_name', '');
                        }
                    });
                } else {
                    frm.set_value('custom_project_name', '');
                }

                let total_capacity = calculate_total_capacity(
                    data.batch_start_date,
                    data.batch_end_date,
                    data.batch_capacity
                );
                frm.set_value('total_batch_capacity', total_capacity);
                calculate_totals(frm);
                fetch_sct_remaining(frm);

                // Auto-fill slot_booking rows only where capacity_available > 0
                frappe.call({
                    method: 'custom_batch_planning.custom_batch_planning.doctype.slot_opening.slot_opening.get_sct_details',
                    args: { slot_master: frm.doc.slot_master },
                    callback: function (r) {
                        if (!r.message || !r.message.length) return;

                        let available_dates = r.message
                            .sort((a, b) => a.date > b.date ? 1 : -1);

                        if (!available_dates.length) return;

                        frm.doc.slot_booking = [];
                        frm.refresh_field('slot_booking');

                        available_dates.forEach(function (d) {
                            let row = frm.add_child('slot_booking');
                            row.slot_booking_date = d.date;
                            row.batch_capacity = data.batch_capacity;
                            row.availabe_capacity = parseInt(d.capacity_available) || 0;
                            row.__sct_available = d.capacity_available;
                            if (parseInt(d.capacity_available) === 0) {
                                row.reason = '';
                            }
                        });

                        frm.refresh_field('slot_booking');
                        calculate_totals(frm);
                        loadSlotOpeningCalendar(frm);
                    }
                });
            }
        );
    },

    validate: function (frm) {
        let total_planned = parseInt(frm.doc.total_batches_planned) || 0;
        let capacity = parseInt(frm.doc.total_batch_capacity) || 0;
        if (capacity > 0 && total_planned > capacity) {
            frappe.throw(`⚠️ Total Batches Planned (${total_planned}) exceeds Total Batch Capacity (${capacity})!`);
        }
    }
});

// ─────────────────────────────────────────────
// Child Table — Slot Booking CT
// ─────────────────────────────────────────────

frappe.ui.form.on('Slot Booking CT', {

    slot_booking_date: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.slot_booking_date) return;

        if (row.slot_booking_date < frappe.datetime.nowdate()) {
            frappe.model.set_value(cdt, cdn, 'slot_booking_date', '');
            frappe.msgprint('⚠️ Slot Booking Date cannot be before today!');
            return;
        }

        let start = frm.doc.__batch_start_date || frm.doc.batch_start_date;
        let end = frm.doc.__batch_end_date || frm.doc.batch_end_date;

        if (start && row.slot_booking_date < start) {
            frappe.model.set_value(cdt, cdn, 'slot_booking_date', '');
            frappe.msgprint(`⚠️ Slot Booking Date cannot be before Batch Start Date: ${start}`);
            return;
        }
        if (end && row.slot_booking_date > end) {
            frappe.model.set_value(cdt, cdn, 'slot_booking_date', '');
            frappe.msgprint(`⚠️ Slot Booking Date cannot be after Batch End Date: ${end}`);
            return;
        }

        let duplicate = (frm.doc.slot_booking || []).filter(
            r => r.name !== row.name && r.slot_booking_date === row.slot_booking_date
        );
        if (duplicate.length > 0) {
            frappe.model.set_value(cdt, cdn, 'slot_booking_date', '');
            frappe.msgprint(`⚠️ Date ${row.slot_booking_date} already exists in another row!`);
            return;
        }

        if (!frm.doc.slot_master) return;

        frappe.call({
            method: 'custom_batch_planning.custom_batch_planning.doctype.slot_opening.slot_opening.get_sct_details',
            args: { slot_master: frm.doc.slot_master, date: row.slot_booking_date },
            callback: function (r) {
                if (!r.message || r.message.length === 0) {
                    frappe.msgprint(`⚠️ Date <b>${row.slot_booking_date}</b> not found in Slot Capacity Tracker!`);
                    frappe.model.set_value(cdt, cdn, 'slot_booking_date', '');
                    return;
                }

                let detail = r.message[0];
                let available = parseInt(detail.capacity_available) || 0;

                if (available <= 0) {
                    frappe.msgprint({
                        title: '⚠️ No Capacity Available',
                        message: `Date <b>${row.slot_booking_date}</b> has <b>0</b> capacity available.<br>
                                  Total: ${detail.total_capacity} | 
                                  Booked: ${detail.capacity_booked} | 
                                  Available: ${detail.capacity_available}`,
                        indicator: 'red'
                    });
                    frappe.model.set_value(cdt, cdn, 'slot_booking_date', '');
                    return;
                }

                row.__sct_available = available;
                row.availabe_capacity = available;
                row.__sct_detail_name = detail.name;
                frm.refresh_field('slot_booking');

                frappe.msgprint({
                    title: '✅ Capacity Available',
                    message: `Date <b>${row.slot_booking_date}</b>: <b>${available}</b> slot(s) available.`,
                    indicator: 'green'
                });
            }
        });
    },

    how_many_slots_per_day: function (frm, cdt, cdn) {
        calculate_total(frm, cdt, cdn);
    },

    total_slots: function (frm, cdt, cdn) {
        calculate_total(frm, cdt, cdn);
    },

    slot_booking_remove: function (frm) {
        calculate_totals(frm);
        fetch_sct_remaining(frm);
    }
});

// ─────────────────────────────────────────────
// Helper Functions
// ─────────────────────────────────────────────

function calculate_total_capacity(start_date, end_date, batch_capacity) {
    if (!start_date || !end_date || !batch_capacity) return 0;
    let start = frappe.datetime.str_to_obj(start_date);
    let end = frappe.datetime.str_to_obj(end_date);
    let num_days = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;
    return num_days * parseInt(batch_capacity);
}

function set_slot_master_filter(frm) {
    frm.set_query('slot_master', function () {
        let filters = {
            'docstatus': 1,
            'workflow_state': 'Approved',
            'batch_end_date': ['>=', frappe.datetime.nowdate()]
        };
        if (frm.doc.employee_function) {
            filters['employee_function'] = frm.doc.employee_function;
        }
        return { filters: filters };
    });
}

function calculate_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let new_booked = (parseInt(row.how_many_slots_per_day) || 0) * (parseInt(row.total_slots) || 0);

    let other_batches = (frm.doc.slot_booking || []).reduce(function (sum, r) {
        if (r.name === row.name) return sum;
        return sum + (parseInt(r.booked_slots) || 0);
    }, 0);

    let capacity = parseInt(frm.doc.total_batch_capacity) || 0;

    if (row.__sct_available !== undefined) {
        if (new_booked > row.__sct_available) {
            frappe.msgprint({
                title: '⚠️ SCT Capacity Exceeded',
                message: `Only <b>${row.__sct_available}</b> slot(s) available for this date in SCT.<br>
                          You are trying to book <b>${new_booked}</b>.`,
                indicator: 'orange'
            });
            frappe.model.set_value(cdt, cdn, 'how_many_slots_per_day', 0);
            frappe.model.set_value(cdt, cdn, 'total_slots', 0);
            frappe.model.set_value(cdt, cdn, 'booked_slots', 0);
            calculate_totals(frm);
            return;
        }
    }

    if (capacity > 0 && (other_batches + new_booked) > capacity) {
        frappe.msgprint(`⚠️ Total Batch Capacity exceeded! Max: ${capacity}, Already planned: ${other_batches}`);
        frappe.model.set_value(cdt, cdn, 'how_many_slots_per_day', 0);
        frappe.model.set_value(cdt, cdn, 'total_slots', 0);
        frappe.model.set_value(cdt, cdn, 'booked_slots', 0);
        calculate_totals(frm);
        return;
    }

    frappe.model.set_value(cdt, cdn, 'booked_slots', new_booked);
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_slots = 0, total_batches = 0;
    (frm.doc.slot_booking || []).forEach(function (row) {
        total_slots += parseInt(row.how_many_slots_per_day) || 0;
        total_batches += parseInt(row.booked_slots) || 0;
    });
    frm.set_value('total_slots_planned', total_slots);
    frm.set_value('total_batches_planned', total_batches);
    fetch_sct_remaining(frm);
}

function fetch_sct_remaining(frm) {
    if (!frm.doc.slot_master) return;
    frappe.call({
        method: 'custom_batch_planning.custom_batch_planning.doctype.slot_opening.slot_opening.get_sct_details',
        args: { slot_master: frm.doc.slot_master },
        callback: function (r) {
            if (!r.message) return;
            let db_total_available = r.message.reduce(
                (sum, d) => sum + (parseInt(d.capacity_available) || 0), 0
            );

            let remained = db_total_available;
            if (frm.is_new()) {
                let current_planned = parseInt(frm.doc.total_batches_planned) || 0;
                remained = db_total_available - current_planned;
            }

            frm.set_value('total_batch_remained', remained);
        }
    });
}

// ─────────────────────────────────────────────
// Calendar — Slot Capacity Tracker based
// ─────────────────────────────────────────────

function loadSlotOpeningCalendar(frm) {
    if (!frm.fields_dict.calenders) return;

    if (!frm.doc.employee_function) {
        frm.fields_dict.calenders.$wrapper.html(`
            <div style="padding:40px 20px; background:#f8fafc; border-radius:12px; text-align:center; border: 2px dashed #cbd5e1; margin: 20px 0;">
                <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.8;">📅</div>
                <h4 style="color:#0f172a; margin:0 0 8px 0; font-size: 18px; font-weight: 700;">Calendar Unavailable</h4>
                <p style="color:#64748b; margin:0; font-size: 14px;">Please select an <strong>Employee Function</strong> above to view the slot availability calendar.</p>
            </div>
        `);
        return;
    }

    const fullCalendarCSS = "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/index.global.min.css";
    const fullCalendarJS = "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/index.global.min.js";

    frm.fields_dict.calenders.$wrapper.html(`
        <div style="padding:16px; background:#f8fafc; border-radius:12px;">
            <div style="background:white; padding:24px; border-radius:12px; box-shadow:0 10px 25px -5px rgba(0,0,0,0.05), 0 8px 10px -6px rgba(0,0,0,0.01); border: 1px solid #e2e8f0;">
                <div style="margin-bottom:20px; display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:12px;">
                    <h3 style="margin:0; color:#0f172a; font-size:clamp(16px,2vw,20px); font-weight: 700; display:flex; align-items:center; gap:8px;">
                        <span style="font-size:24px;">📅</span> Slot Availability Calendar
                    </h3>
                    <div style="display:flex; flex-wrap:wrap; gap:16px; font-size:13px; font-weight:600; padding: 8px 16px; background: #f1f5f9; border-radius: 50px;">
                        <span style="display:flex; align-items:center;"><span style="display:inline-block;width:10px;height:10px;background:#10b981;border-radius:50%;margin-right:6px;box-shadow:0 2px 4px rgba(16,185,129,0.3);"></span>Available</span>
                        <span style="display:flex; align-items:center;"><span style="display:inline-block;width:10px;height:10px;background:#f59e0b;border-radius:50%;margin-right:6px;box-shadow:0 2px 4px rgba(245,158,11,0.3);"></span>Partial</span>
                        <span style="display:flex; align-items:center;"><span style="display:inline-block;width:10px;height:10px;background:#ef4444;border-radius:50%;margin-right:6px;box-shadow:0 2px 4px rgba(239,68,68,0.3);"></span>Full</span>
                    </div>
                </div>
                <div id="so-calendar-wrapper" style="min-height:500px; overflow:hidden;"></div>
                <div style="margin-top:20px; padding:12px 16px; background:#f0f9ff; border-radius:8px; border-left:4px solid #0ea5e9; display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">💡</span>
                    <small style="color:#0369a1; font-weight:500; font-size:13px;"><strong>Pro Tip:</strong> Click any date on the calendar to view a detailed breakdown of slots.</small>
                </div>
            </div>
        </div>
    `);

    if (!document.querySelector(`link[href="${fullCalendarCSS}"]`)) {
        let link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = fullCalendarCSS;
        document.head.appendChild(link);
    }

    if (typeof FullCalendar === "undefined") {
        let script = document.createElement("script");
        script.src = fullCalendarJS;
        script.onload = () => setTimeout(() => initSCTCalendar(frm), 100);
        document.head.appendChild(script);
    } else {
        setTimeout(() => initSCTCalendar(frm), 100);
    }
}

function initSCTCalendar(frm) {
    const wrapper = document.getElementById("so-calendar-wrapper");
    if (!wrapper) return;

    addSCTCalendarStyles();

    // Fetch SCT records filtered by employee_function if set
    let sct_filters = { 'docstatus': ['!=', 2] };
    if (frm.doc.employee_function) {
        sct_filters['employee_function'] = frm.doc.employee_function;
    }
    if (frm.doc.custom_project) {
        sct_filters['project'] = frm.doc.custom_project;
    }

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Slot Capacity Tracker',
            filters: sct_filters,
            fields: ['name', 'employee_function', 'employee_headname', 'slot_master'],
            limit_page_length: 999
        },
        callback: function (r) {
            if (!r.message || !r.message.length) {
                wrapper.innerHTML = '<p style="text-align:center; color:#888; padding:40px;">No Slot Capacity Tracker records found.</p>';
                return;
            }

            let promises = r.message.map(sct => {
                return new Promise(resolve => {
                    frappe.call({
                        method: 'frappe.client.get',
                        args: { doctype: 'Slot Capacity Tracker', name: sct.name },
                        callback: function (res) { resolve(res.message); }
                    });
                });
            });

            Promise.all(promises).then(docs => {
                let slotsByDate = {};

                docs.forEach(doc => {
                    if (!doc || !doc.slot_capacity_detail) return;
                    doc.slot_capacity_detail.forEach(row => {
                        let date = row.date;
                        let total = parseInt(row.total_capacity) || 0;
                        let booked = parseInt(row.capacity_booked) || 0;
                        let available = parseInt(row.capacity_available) || 0;

                        if (!slotsByDate[date]) {
                            slotsByDate[date] = { total: 0, booked: 0, available: 0, sources: [] };
                        }
                        slotsByDate[date].total += total;
                        slotsByDate[date].booked += booked;
                        slotsByDate[date].available += available;
                        slotsByDate[date].sources.push({
                            sct_name: doc.name,
                            slot_master: doc.slot_master,
                            employee_function: doc.employee_function,
                            employee_headname: doc.employee_headname,
                            total, booked, available
                        });
                    });
                });

                renderSCTCalendar(slotsByDate, wrapper);
            });
        }
    });
}

function renderSCTCalendar(slotsByDate, wrapper) {
    wrapper.innerHTML = '<div id="so-calendar"></div>';
    const calEl = document.getElementById("so-calendar");

    const calendar = new FullCalendar.Calendar(calEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth'
        },
        height: 'auto',
        expandRows: true,
        selectable: false,
        dayMaxEvents: false,
        fixedWeekCount: false,
        showNonCurrentDates: true,
        events: [],

        dateClick: function (info) {
            const dateStr = info.dateStr;
            const dayData = slotsByDate[dateStr];

            if (!dayData) {
                frappe.msgprint({
                    title: 'No Slots Configured',
                    message: `No slots configured for <strong>${dateStr}</strong>.`,
                    indicator: 'orange'
                });
                return;
            }

            const [y, m, d] = dateStr.split('-');
            const displayDate = `${d}-${m}-${y}`;

            // Build per-source rows
            let sourceRows = dayData.sources.map(s => `
                <tr>
                    <td>${s.slot_master || '-'}</td>
                    <td>${s.employee_function || '-'}</td>
                    <td>${s.employee_headname || '-'}</td>
                    <td style="text-align:center;">${s.total}</td>
                    <td style="text-align:center; color:#dc3545; font-weight:bold;">${s.booked}</td>
                    <td style="text-align:center; color:${s.available > 0 ? '#28a745' : '#dc3545'}; font-weight:bold;">${s.available}</td>
                </tr>
            `).join('');

            frappe.msgprint({
                title: `📅 Slot Details — ${displayDate}`,
                message: `
                    <div style="margin-bottom:12px; padding:10px; background:#f8f9fa; border-radius:6px; display:flex; flex-wrap:wrap; gap:16px;">
                        <span><strong>Total:</strong> ${dayData.total}</span>
                        <span><strong style="color:#dc3545;">Booked:</strong> ${dayData.booked}</span>
                        <span><strong style="color:#28a745;">Available:</strong> ${dayData.available}</span>
                    </div>
                    <div style="overflow-x:auto;">
                        <table class="table table-bordered" style="width:100%; font-size:13px;">
                            <thead style="background:#f0f0f0;">
                                <tr>
                                    <th>Slot Master</th>
                                    <th>Employee Function</th>
                                    <th>Head Name</th>
                                    <th>Total</th>
                                    <th>Booked</th>
                                    <th>Available</th>
                                </tr>
                            </thead>
                            <tbody>${sourceRows}</tbody>
                        </table>
                    </div>
                `,
                wide: true,
                indicator: dayData.available === 0 ? 'red' : dayData.available < dayData.total ? 'orange' : 'green'
            });
        },

        dayCellDidMount: function (info) {
            const year = info.date.getFullYear();
            const month = String(info.date.getMonth() + 1).padStart(2, '0');
            const day = String(info.date.getDate()).padStart(2, '0');
            const dateStr = `${year}-${month}-${day}`;
            const dayData = slotsByDate[dateStr];

            if (!dayData || dayData.total === 0) return;

            info.el.style.cursor = dayData.available > 0 ? 'pointer' : 'default';

            const indicator = document.createElement('div');
            indicator.className = 'sct-slot-indicator';

            if (dayData.available === 0) {
                indicator.innerHTML = `<strong>FULL</strong>`;
                indicator.style.cssText = `
                    font-size:11px; font-weight:700; margin-top:8px;
                    padding:4px 8px; border-radius:20px; text-align:center;
                    background:linear-gradient(135deg, #ef4444, #dc2626); color:white; letter-spacing:0.5px;
                    box-shadow: 0 2px 4px rgba(239, 68, 68, 0.25); border: 1px solid #b91c1c;
                `;
                info.el.classList.add('sct-fully-booked');
            } else if (dayData.booked > 0) {
                indicator.innerHTML = `${dayData.available}/${dayData.total} left`;
                indicator.style.cssText = `
                    font-size:11px; font-weight:700; margin-top:8px;
                    padding:4px 8px; border-radius:20px; text-align:center;
                    background:linear-gradient(135deg, #f59e0b, #d97706); color:white;
                    box-shadow: 0 2px 4px rgba(245, 158, 11, 0.25); border: 1px solid #b45309;
                `;
                info.el.classList.add('sct-partial');
            } else {
                indicator.innerHTML = `${dayData.available}/${dayData.total} free`;
                indicator.style.cssText = `
                    font-size:11px; font-weight:700; margin-top:8px;
                    padding:4px 8px; border-radius:20px; text-align:center;
                    background:linear-gradient(135deg, #10b981, #059669); color:white;
                    box-shadow: 0 2px 4px rgba(16, 185, 129, 0.25); border: 1px solid #047857;
                `;
                info.el.classList.add('sct-available');
            }

            const frame = info.el.querySelector('.fc-daygrid-day-frame');
            if (frame) frame.appendChild(indicator);
        }
    });

    calendar.render();
    setTimeout(() => { calendar.updateSize(); }, 300);

    // Responsive resize
    window.addEventListener('resize', () => { calendar.updateSize(); });
}

function addSCTCalendarStyles() {
    const old = document.getElementById('sct-calendar-styles');
    if (old) old.remove();

    const style = document.createElement('style');
    style.id = 'sct-calendar-styles';
    style.textContent = `
        #so-calendar-wrapper {
            display:block !important; position:relative !important;
            min-height:500px !important; overflow:hidden !important;
        }
        #so-calendar {
            display:block !important;
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            font-size:14px !important; color:#334155 !important;
        }
        #so-calendar table {
            border-collapse:separate !important; border-spacing:0 !important;
            width:100% !important; table-layout:fixed !important;
            border-radius: 10px !important; overflow: hidden !important;
        }
        #so-calendar td, #so-calendar th {
            padding:0 !important; border:1px solid #e2e8f0 !important; vertical-align:top !important;
        }
        #so-calendar .fc-col-header-cell {
            padding:14px 8px !important; font-weight:700 !important;
            text-align:center !important; background:#f8fafc !important; font-size:13px !important;
            color: #64748b !important; text-transform: uppercase !important; letter-spacing: 0.5px !important;
        }
        #so-calendar .fc-daygrid-day {
            min-height:110px !important; position:relative !important; overflow:visible !important;
            transition:all 0.2s ease !important;
        }
        #so-calendar .fc-daygrid-day:hover { 
            background:#f1f5f9 !important; 
            z-index: 10 !important;
        }
        #so-calendar .fc-daygrid-day-frame {
            height:100% !important; min-height:110px !important; padding:8px !important;
            display:flex !important; flex-direction:column !important;
        }
        #so-calendar .fc-daygrid-day-top {
            text-align:right !important; margin-bottom:8px !important;
        }
        #so-calendar .fc-daygrid-day-number {
            padding:6px 10px !important; font-size:14px !important; font-weight:600 !important;
            color: #475569 !important; text-decoration: none !important;
            border-radius: 50% !important; transition: all 0.2s ease !important; display: inline-block !important;
        }
        #so-calendar .fc-daygrid-day-number:hover {
            background: #cbd5e1 !important; color: #0f172a !important;
        }
        #so-calendar .sct-fully-booked  { background:#fef2f2 !important; }
        #so-calendar .sct-partial       { background:#fffbeb !important; }
        #so-calendar .sct-available     { background:#f0fdf4 !important; }
        #so-calendar .fc-day-past       { background:#f8fafc !important; opacity:0.6 !important; }
        #so-calendar .fc-day-today      { background:#eff6ff !important; box-shadow: inset 0 0 0 2px #3b82f6 !important; }
        #so-calendar .fc-day-today .fc-daygrid-day-number {
            background: #3b82f6 !important; color: white !important; box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3) !important;
        }
        #so-calendar .fc-day-today .fc-daygrid-day-number:hover {
            background: #2563eb !important; color: white !important;
        }
        #so-calendar .fc-toolbar {
            margin-bottom:24px !important; display:flex !important;
            justify-content:space-between !important; align-items:center !important;
            flex-wrap:wrap !important; gap:16px !important;
        }
        #so-calendar .fc-toolbar-title {
            font-size:clamp(18px,2.5vw,24px) !important; font-weight:800 !important; color:#0f172a !important;
            letter-spacing: -0.5px !important;
        }
        #so-calendar .fc-toolbar-chunk { display:flex !important; gap:8px !important; align-items:center !important; }
        
        /* Modern Button Styling */
        #so-calendar {
            --fc-button-bg-color: #ffffff;
            --fc-button-border-color: #cbd5e1;
            --fc-button-hover-bg-color: #f8fafc;
            --fc-button-hover-border-color: #94a3b8;
            --fc-button-active-bg-color: #3b82f6;
            --fc-button-active-border-color: #2563eb;
            --fc-button-text-color: #475569;
        }
        #so-calendar .fc-button-group {
            display: flex !important;
            gap: 6px !important;
            box-shadow: none !important;
        }
        #so-calendar .fc .fc-button-primary, #so-calendar .fc .fc-button {
            background:#ffffff !important; border:1px solid #cbd5e1 !important;
            color:#475569 !important; padding:8px 18px !important; border-radius:8px !important;
            cursor:pointer !important; font-size:14px !important; font-weight: 600 !important;
            transition:all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
            text-transform: capitalize !important;
            outline: none !important;
        }
        #so-calendar .fc .fc-button-primary:hover, #so-calendar .fc .fc-button:hover { 
            background:#f8fafc !important; border-color:#94a3b8 !important; 
            color: #0f172a !important; transform: translateY(-1px) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            z-index: 5 !important;
        }
        #so-calendar .fc .fc-button-primary:active, #so-calendar .fc .fc-button:active {
            transform: translateY(0) !important;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.05) !important;
        }
        #so-calendar .fc .fc-button-primary:not(:disabled).fc-button-active,
        #so-calendar .fc .fc-button-primary:not(:disabled):active { 
            background:linear-gradient(135deg, #3b82f6, #2563eb) !important; border-color:#1d4ed8 !important; color: white !important;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.4) !important;
        }
        #so-calendar .fc .fc-button-primary:disabled {
            opacity: 0.5 !important;
            cursor: not-allowed !important;
            background: #f1f5f9 !important;
            border-color: #e2e8f0 !important;
            box-shadow: none !important;
            transform: none !important;
        }
        
        #so-calendar .fc-view-harness        { position:relative !important; border-radius: 10px !important; overflow: hidden !important; box-shadow: 0 4px 15px -3px rgba(0, 0, 0, 0.05) !important; }
        #so-calendar .fc-scrollgrid         { border:1px solid #e2e8f0 !important; border-radius: 10px !important; }

        @media (max-width: 640px) {
            #so-calendar .fc-toolbar        { flex-direction:column !important; align-items:stretch !important; gap: 16px !important; }
            #so-calendar .fc-toolbar-chunk  { justify-content: center !important; }
            #so-calendar .fc-toolbar-title  { font-size:20px !important; text-align: center !important; }
            #so-calendar .fc-button         { padding:8px 12px !important; font-size:13px !important; flex: 1 !important; }
            #so-calendar .fc-daygrid-day    { min-height:90px !important; }
            #so-calendar .sct-slot-indicator { font-size:10px !important; padding:4px 6px !important; }
            #so-calendar .fc-col-header-cell { font-size:11px !important; padding:8px 4px !important; }
        }
    `;
    document.head.appendChild(style);
}