// tba.js - TBA Match Schedule Integration

let currentMatches = [];
let currentMatchForAssignment = null;
let currentEventKey = window.initialEventKey || '';

document.addEventListener('DOMContentLoaded', function () {
    // Render initial server-side data
    if (window.initialMatches && window.initialMatches.length > 0) {
        renderMatches(window.initialMatches);
    } else {
        updateEmptyState([]);
    }

    if (window.initialLastSyncedAt) {
        updateSyncInfo(window.initialLastSyncedAt);
    }

    document.getElementById('manualEntryToggle').addEventListener('change', toggleManualEntry);
    document.getElementById('fetchEventsBtn').addEventListener('click', fetchTeamEvents);
    document.getElementById('loadMatchesBtn').addEventListener('click', () => loadMatchesFromApi());
    document.getElementById('tbaSyncBtn').addEventListener('click', triggerTbaSync);
    document.getElementById('confirmAssignBtn').addEventListener('click', confirmBatteryAssignment);
});

function toggleManualEntry() {
    const manual = document.getElementById('manualEntryToggle').checked;
    document.getElementById('eventDropdownSection').classList.toggle('d-none', manual);
    document.getElementById('eventManualSection').classList.toggle('d-none', !manual);
}

async function fetchTeamEvents() {
    const teamKey = document.getElementById('teamKeyInput').value.trim();
    const year = document.getElementById('yearInput').value;
    if (!teamKey) {
        showToast('Please enter a team key (e.g. frc254)', 'Team Key Required', 'error');
        return;
    }
    const btn = document.getElementById('fetchEventsBtn');
    const spinner = document.getElementById('fetchEventsSpinner');
    btn.disabled = true;
    spinner.classList.remove('d-none');
    try {
        const resp = await fetch(`/api/tba/events?team_key=${encodeURIComponent(teamKey)}&year=${encodeURIComponent(year)}`);
        const data = await resp.json();
        if (!resp.ok) {
            showToast(data.message || 'Failed to fetch events', 'Error', 'error');
            return;
        }
        const select = document.getElementById('eventSelect');
        select.innerHTML = '<option value="">-- Select an event --</option>';
        data.forEach(event => {
            const opt = document.createElement('option');
            opt.value = event.key;
            opt.text = `${event.name} (${event.key})`;
            if (event.key === currentEventKey) opt.selected = true;
            select.appendChild(opt);
        });
        if (data.length === 0) {
            showToast('No events found for this team/year.', 'No Events', 'info');
        }
    } catch (err) {
        showToast(`Error fetching events: ${err.message}`, 'Error', 'error');
    } finally {
        btn.disabled = false;
        spinner.classList.add('d-none');
    }
}

async function loadMatchesFromApi(eventKeyOverride) {
    let eventKey = eventKeyOverride;
    if (!eventKey) {
        const manual = document.getElementById('manualEntryToggle').checked;
        eventKey = manual
            ? document.getElementById('eventKeyManual').value.trim()
            : document.getElementById('eventSelect').value;
    }
    if (!eventKey) {
        showToast('Please select or enter an event key.', 'Event Required', 'error');
        return;
    }
    const btn = document.getElementById('loadMatchesBtn');
    const spinner = document.getElementById('loadMatchesSpinner');
    btn.disabled = true;
    spinner.classList.remove('d-none');
    try {
        const resp = await fetch(`/api/tba/matches?event_key=${encodeURIComponent(eventKey)}`);
        const data = await resp.json();
        if (!resp.ok) {
            showToast(data.message || 'Failed to fetch matches', 'Error', 'error');
            return;
        }
        currentEventKey = eventKey;
        renderMatches(data.matches || []);
        if (data.last_synced_at) {
            updateSyncInfo(data.last_synced_at);
        }
        if ((data.matches || []).length === 0) {
            showToast('No matches in cache. Try clicking "Sync Now" to download from TBA.', 'No Matches', 'info');
        }
    } catch (err) {
        showToast(`Error fetching matches: ${err.message}. Showing cached data.`, 'Error', 'error');
    } finally {
        btn.disabled = false;
        spinner.classList.add('d-none');
    }
}

function updateSyncInfo(timestamp) {
    const syncInfoText = document.getElementById('syncInfoText');
    const date = new Date(parseFloat(timestamp) * 1000);
    syncInfoText.innerHTML = `Last synced: <span id="lastSyncedAtDisplay">${date.toLocaleString()}</span>`;
}

// ── Match display helpers ────────────────────────────────────────────────────

function formatMatchDisplay(match) {
    const levelMap = { 'qm': 'Qual', 'ef': 'EF', 'qf': 'QF', 'sf': 'SF', 'f': 'Final' };
    const level = levelMap[match.comp_level] || match.comp_level.toUpperCase();
    if (match.comp_level === 'qm') return `${level} ${match.match_number}`;
    return `${level} ${match.set_number}-${match.match_number}`;
}

function formatTime(timestamp) {
    if (!timestamp) return '--';
    return new Date(timestamp * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatTeams(teamKeys) {
    if (!teamKeys || teamKeys.length === 0) return '--';
    return teamKeys.map(k => k.replace('frc', '')).join(', ');
}

function winnerBadge(winner) {
    if (!winner) return '--';
    const color = winner === 'red' ? 'danger' : winner === 'blue' ? 'primary' : 'secondary';
    return `<span class="badge text-bg-${color}">${winner}</span>`;
}

function assignedBatteryCell(match) {
    if (match.assigned_battery) {
        return `${match.assigned_battery.name || ''} <span class="text-muted small">${match.assigned_battery.asset_tag || ''}</span>`;
    }
    return '<span class="text-muted fst-italic">None</span>';
}

function makeAssignBtn(match) {
    const btn = document.createElement('button');
    btn.className = 'btn btn-sm btn-outline-secondary';
    btn.textContent = 'Assign';
    btn.addEventListener('click', () => openAssignmentModal(match));
    return btn;
}

// ── Render functions ─────────────────────────────────────────────────────────

function renderMatches(matches) {
    currentMatches = matches;

    const upcoming = matches
        .filter(m => !m.actual_time)
        .sort((a, b) => {
            if (!a.predicted_time && !b.predicted_time) return a.match_number - b.match_number;
            if (!a.predicted_time) return 1;
            if (!b.predicted_time) return -1;
            return a.predicted_time - b.predicted_time;
        });

    const completed = matches
        .filter(m => !!m.actual_time)
        .sort((a, b) => b.actual_time - a.actual_time);

    const levelOrder = { 'qm': 0, 'ef': 1, 'qf': 2, 'sf': 3, 'f': 4 };
    const allSorted = [...matches].sort((a, b) => {
        const la = levelOrder[a.comp_level] ?? 99;
        const lb = levelOrder[b.comp_level] ?? 99;
        if (la !== lb) return la - lb;
        if (a.set_number !== b.set_number) return a.set_number - b.set_number;
        return a.match_number - b.match_number;
    });

    // Upcoming tab
    const upcomingBody = document.getElementById('upcomingMatchesBody');
    upcomingBody.innerHTML = '';
    upcoming.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatMatchDisplay(m)}</td>
            <td>${formatTime(m.predicted_time)}</td>
            <td><span class="badge text-bg-danger">${formatTeams(m.red_alliance)}</span></td>
            <td><span class="badge text-bg-primary">${formatTeams(m.blue_alliance)}</span></td>
            <td>${assignedBatteryCell(m)}</td>
            <td></td>`;
        tr.querySelector('td:last-child').appendChild(makeAssignBtn(m));
        upcomingBody.appendChild(tr);
    });
    document.getElementById('upcomingCount').textContent = upcoming.length;
    document.getElementById('upcomingEmpty').style.display = upcoming.length === 0 ? '' : 'none';

    // Completed tab
    const completedBody = document.getElementById('completedMatchesBody');
    completedBody.innerHTML = '';
    completed.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatMatchDisplay(m)}</td>
            <td>${formatTime(m.actual_time)}</td>
            <td><span class="badge text-bg-danger">${formatTeams(m.red_alliance)}</span></td>
            <td><span class="badge text-bg-primary">${formatTeams(m.blue_alliance)}</span></td>
            <td>${winnerBadge(m.winning_alliance)}</td>
            <td>${assignedBatteryCell(m)}</td>
            <td></td>`;
        tr.querySelector('td:last-child').appendChild(makeAssignBtn(m));
        completedBody.appendChild(tr);
    });
    document.getElementById('completedCount').textContent = completed.length;
    document.getElementById('completedEmpty').style.display = completed.length === 0 ? '' : 'none';

    // All tab
    const allBody = document.getElementById('allMatchesBody');
    allBody.innerHTML = '';
    allSorted.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatMatchDisplay(m)}</td>
            <td>${formatTime(m.predicted_time)}</td>
            <td>${formatTime(m.actual_time)}</td>
            <td><span class="badge text-bg-danger">${formatTeams(m.red_alliance)}</span></td>
            <td><span class="badge text-bg-primary">${formatTeams(m.blue_alliance)}</span></td>
            <td>${winnerBadge(m.winning_alliance)}</td>
            <td>${assignedBatteryCell(m)}</td>
            <td></td>`;
        tr.querySelector('td:last-child').appendChild(makeAssignBtn(m));
        allBody.appendChild(tr);
    });
    document.getElementById('allCount').textContent = matches.length;
    document.getElementById('allEmpty').style.display = matches.length === 0 ? '' : 'none';
}

function updateEmptyState(matches) {
    ['upcomingEmpty', 'completedEmpty', 'allEmpty'].forEach(id => {
        document.getElementById(id).style.display = '';
    });
    ['upcomingCount', 'completedCount', 'allCount'].forEach(id => {
        document.getElementById(id).textContent = '0';
    });
}

// ── Battery Assignment Modal ─────────────────────────────────────────────────

async function openAssignmentModal(match) {
    currentMatchForAssignment = match;

    document.getElementById('assignModalMatchDisplay').textContent = formatMatchDisplay(match);
    document.getElementById('assignModalRedAlliance').textContent = formatTeams(match.red_alliance);
    document.getElementById('assignModalBlueAlliance').textContent = formatTeams(match.blue_alliance);
    document.getElementById('assignModalTime').textContent = formatTime(match.predicted_time);

    const currentBattery = match.assigned_battery;
    document.getElementById('assignModalCurrentBattery').textContent =
        currentBattery ? `${currentBattery.name} (${currentBattery.asset_tag})` : 'None';

    const select = document.getElementById('batterySelectDropdown');
    select.innerHTML = '<option value="">-- None (unassign) --</option>';

    try {
        const resp = await fetch('/api/batteries');
        const batteries = await resp.json();
        batteries.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id;
            const statusPart = b.status ? ` · ${b.status}` : '';
            const locationPart = b.location ? ` @ ${b.location}` : '';
            opt.text = `${b.name} (${b.asset_tag})${statusPart}${locationPart}`;
            if (currentBattery && b.id === currentBattery.id) opt.selected = true;
            select.appendChild(opt);
        });
    } catch (err) {
        showToast('Error loading batteries: ' + err.message, 'Error', 'error');
    }

    new bootstrap.Modal(document.getElementById('assignBatteryModal')).show();
}

async function confirmBatteryAssignment() {
    if (!currentMatchForAssignment) return;

    const batteryIdRaw = document.getElementById('batterySelectDropdown').value;
    const matchKey = currentMatchForAssignment.key;

    try {
        const resp = await fetch('/api/tba/assign_battery', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                match_key: matchKey,
                battery_id: batteryIdRaw ? parseInt(batteryIdRaw, 10) : null,
            })
        });
        const data = await resp.json();

        if (data.status === 'error') {
            showToast(data.message, 'Error', 'error');
            return;
        }

        showToast('Battery assigned successfully!', 'Assignment', 'success');
        bootstrap.Modal.getInstance(document.getElementById('assignBatteryModal')).hide();
        // Refresh match list
        await loadMatchesFromApi(currentEventKey);
    } catch (err) {
        showToast(`Error assigning battery: ${err.message}`, 'Error', 'error');
    }
}

// ── TBA Sync ─────────────────────────────────────────────────────────────────

async function triggerTbaSync() {
    const btn = document.getElementById('tbaSyncBtn');
    const spinner = document.getElementById('tbaSyncSpinner');
    btn.disabled = true;
    spinner.classList.remove('d-none');

    try {
        const resp = await fetch('/api/tba/sync', { method: 'POST' });
        const data = await resp.json();
        const toast = showToast(data.message, 'TBA Sync', 'info', 30000);
        checkTbaSyncStatus(toast);
    } catch (err) {
        showToast(`Sync error: ${err.message}`, 'Error', 'error');
        btn.disabled = false;
        spinner.classList.add('d-none');
    }
}

async function checkTbaSyncStatus(toast) {
    try {
        const resp = await fetch('/api/tba/sync');
        const data = await resp.json();
        switch (data.status) {
            case 'started':
            case 'queued':
                toast.querySelector('.toast-body').textContent = `TBA sync in progress... (${data.status})`;
                setTimeout(() => checkTbaSyncStatus(toast), 2000);
                break;
            case 'finished':
                toast.querySelector('.toast-body').textContent = 'TBA sync completed!';
                setTimeout(() => toast.remove(), 3000);
                document.getElementById('tbaSyncBtn').disabled = false;
                document.getElementById('tbaSyncSpinner').classList.add('d-none');
                loadMatchesFromApi(currentEventKey);
                break;
            case 'failed':
                toast.querySelector('.toast-body').textContent = 'TBA sync failed!';
                toast.querySelector('.toast-header').className = 'toast-header bg-danger text-white';
                document.getElementById('tbaSyncBtn').disabled = false;
                document.getElementById('tbaSyncSpinner').classList.add('d-none');
                break;
        }
    } catch (err) {
        document.getElementById('tbaSyncBtn').disabled = false;
        document.getElementById('tbaSyncSpinner').classList.add('d-none');
    }
}
