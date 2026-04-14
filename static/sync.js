const originalFetch = window.fetch; // inspired by AI
window.fetch = function (url, options = {}) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    options.headers = { // add csrf token to headers
        ...options.headers,
        'X-CSRFToken': csrfToken
    };
    return originalFetch(url, options);
}

function periodic() {
    const statusButton = document.getElementById('statusButton')
    const statusModalBody = document.querySelector('#statusModal .modal-body');
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            statusButton.className = `btn m-2 ${data.status.name === 'Operational' ? 'btn-success' : 'btn-danger'}`;
            statusButton.innerHTML = `${data.status.name} <span><i class="bi bi-${data.status.icon}"></i></span>`;
            document.querySelector('#statusModal .modal-body #networkStatus').innerHTML = `
            ${data.status.network.status}
            <ul>
                <li>IP Address: ${data.status.network.ip_address.join(", ") || 'N/A'}</li>
                <li>Ping RTT: ${data.status.network.ping + ' ms'}</li>
            </ul>
            `
            document.querySelector('#statusModal .modal-body #syncStatus').innerText = data.status.sync.status;
            document.querySelector('#statusModal .modal-body #syncStatus').className = `bi bi-${data.status.sync.icon}`;
            document.querySelector('#statusModal .modal-body #lastSync').innerText = data.status.sync.last_sync;
        }).catch(error => {
            statusButton.className = 'btn m-2 btn-warning';
            statusButton.innerHTML = `Status Unknown <span><i class="bi bi-question-circle"></i></span>`;
            statusModalBody.innerHTML = `Error fetching status: ${error.message}`;
        });
}


function showToast(message, subject, type = 'info', timeout = 5000) {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive'); // for screen readers
    toast.setAttribute('aria-atomic', 'true');

    const bgColor = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';

    toast.innerHTML = `
        <div class="toast-header ${bgColor} text-white">
            <strong class="me-auto">${subject}</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;

    toastContainer.appendChild(toast);

    // Auto-dismiss after specified timeout
    setTimeout(() => {
        toast.remove();
    }, timeout);
    return toast;
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

function getBatteryAlerts(battery) {
    const alerts = [
        { type: 'danger', condition: battery.resistance > 0.030, message: `High Resistance: ${battery.resistance} ohms` },
        { type: 'warning', condition: battery.cycles > 500, message: `High Cycle Count: ${battery.cycles} cycles` },
        { type: 'warning', condition: battery.ageInYears > 3, message: `Old Battery: ${battery.ageInYears} years` },
    ];

    return alerts.filter(alert => alert.condition).map(alert => `
        <div class="alert alert-${alert.type}" role="alert">
            ${alert.message}
            </div>
        `)
}

function setAssignmentMode(mode) {
    const assetBtn = document.getElementById('assignModeAssetBtn');
    const locationBtn = document.getElementById('assignModeLocationBtn');
    const assetSection = document.getElementById('checkoutAssignmentSection');
    const locationSection = document.getElementById('locationAssignmentSection');
    const checkoutSelect = document.getElementById('batteryCheckoutSelect');
    const locationSelect = document.getElementById('batteryLocationSelect');
    const modeInput = document.getElementById('batteryAssignmentMode');

    if (!assetBtn || !locationBtn || !assetSection || !locationSection || !modeInput) return;


    modeInput.value = mode || '';

    const isAsset = mode === 'asset';
    const isLocation = mode === 'location';

    assetBtn.classList.toggle('active', isAsset);
    assetBtn.classList.toggle('btn-primary', isAsset);
    assetBtn.classList.toggle('btn-outline-primary', !isAsset);

    locationBtn.classList.toggle('active', isLocation);
    locationBtn.classList.toggle('btn-primary', isLocation);
    locationBtn.classList.toggle('btn-outline-primary', !isLocation);

    assetSection.classList.toggle('d-none', !isAsset);
    locationSection.classList.toggle('d-none', !isLocation);

    if (checkoutSelect) {
        checkoutSelect.disabled = !isAsset || checkoutSelect.options.length <= 1;
        if (!isAsset) checkoutSelect.value = '';
    }
    if (locationSelect) {
        locationSelect.disabled = !isLocation;
    }
}

// create battery info modal
function showBatteryInfoModal(batteryId) {
    let chartConfig = null;
    let chart = null;
    let originalCheckedOutAssetId = null;
    fetch(`/api/battery/${batteryId}`).then(response => response.json()).then(data => {
        document.getElementById("batteryModalAlerts").innerHTML = getBatteryAlerts(data).join('\n');
        document.getElementById('batteryModalAssetTag').innerText = data.asset_tag || 'N/A';
        document.getElementById('batteryModalPurchaseDate').innerText = data.purchased_date || 'N/A';
        document.getElementById('batteryModalLocation').innerText = data.location ? data.location.name : 'N/A';
        document.querySelector('#batteryModal .modal-title').innerText = data.name;
        document.getElementById('batteryModalCustomFields').innerHTML = '';
        for (const [name, field] of Object.entries(data.custom_fields)) { // convert object to iterable with array destructuring 
            const row = document.createElement('tr');
            const fieldCell = document.createElement('td');
            const valueCell = document.createElement('td');
            fieldCell.innerText = name;
            if (field.custom_field.config === "display") {
                valueCell.innerText = field.value;
            } else if (field.custom_field.config === "edit") {
                switch (field.custom_field.type) { // create input based on type: text, number, select
                    case 'text':
                        const textInput = document.createElement('input');
                        textInput.name = field.field;
                        textInput.type = 'text';
                        textInput.className = 'form-control';
                        textInput.value = field.value || '';
                        valueCell.appendChild(textInput);
                        break;
                    case 'textarea':
                        const textArea = document.createElement('textarea');
                        textArea.className = 'form-control';
                        textArea.name = field.field;
                        textArea.value = field.value || '';
                        valueCell.appendChild(textArea);
                        break;
                    case 'listbox':
                    case 'radio':
                        const select = document.createElement('select');
                        select.className = 'form-select';
                        select.name = field.field;
                        field.custom_field.field_values_array.forEach(option => {
                            const optionElement = document.createElement('option');
                            optionElement.value = option;
                            optionElement.text = option;
                            if (option === field.value) {
                                optionElement.selected = true;
                            }
                            select.appendChild(optionElement);
                        });
                        valueCell.appendChild(select);
                        break;
                    default:
                        valueCell.innerText = field.value || '';
                }
            } else {
                continue;
            }
            row.appendChild(fieldCell);
            row.appendChild(valueCell);
            document.getElementById('batteryModalCustomFields').appendChild(row);
        }

        document.getElementById('batteryNotes').innerText = data.notes;


        fetch('/api/field_mappings').then(response => response.json()).then(mappings => {
            const voltageCurveMapping = mappings.find(m => m.name === 'Voltage Curve');
            if (!voltageCurveMapping || !voltageCurveMapping.db_column_name) {
                showToast('Voltage Curve field mapping not found. Please contact the administrator.', 'Error', 'error');
                return;
            }
            const mappingColumn = voltageCurveMapping.db_column_name;
            const customFields = data.custom_fields || {};
            const mappedField = Object.values(customFields).find(field => {
                if (!field) return false;
                const dbColumn = field.db_column_name || field.field;
                return dbColumn === mappingColumn;
            });

            const csvContent = (mappedField && typeof mappedField.value === 'string')
                ? mappedField.value.trim()
                : '';

            let chartData = csvContent ? d3.csvParseRows(csvContent, function (d) {
                return {
                    // time: +d[0],
                    voltage: +d[1], // Convert strings to numbers securely
                    // current: +d[2],
                    capacity: +d[3],
                    // temperature: +d[4]
                };
            }) : [];

            chartData = chartData.filter(point => Number.isFinite(point.voltage) && Number.isFinite(point.capacity));

            if (chartData.length > 0) {
                chartConfig = {
                    type: 'line',
                    data: {
                        datasets: [{
                            data: chartData,
                            label: 'Battery Discharge',
                            tension: 0.1,
                            pointRadius: 0
                        }],
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Voltage vs. Capacity Curve'
                            },
                        },
                        interaction: {
                            intersect: false,
                        },
                        scales: {
                            x: {
                                type: 'linear',
                                display: true,
                                title: {
                                    display: true,
                                    text: 'Capacity (Ah)'
                                },
                                suggestedMin: 0,
                                suggestedMax: 10
                            },
                            y: {
                                type: 'linear',
                                display: true,
                                title: {
                                    display: true,
                                    text: 'Voltage (V)'
                                },
                                suggestedMin: 0,
                                suggestedMax: 14
                            }
                        },
                        parsing: {
                            xAxisKey: 'capacity',
                            yAxisKey: 'voltage'
                        }
                    },
                };
            }
            let chartCanvas = document.getElementById('batteryModalChart');
            if (chartCanvas) {
                // If a Chart instance already exists for this canvas, destroy it first
                try {
                    const existing = Chart.getChart(chartCanvas);
                    if (existing) existing.destroy();
                } catch (e) {
                    // ignore
                }

                // Ensure there is a message element to show when no data is available
                let msgEl = document.getElementById('batteryModalChartMessage');
                if (!msgEl) {
                    msgEl = document.createElement('div');
                    msgEl.id = 'batteryModalChartMessage';
                    msgEl.className = 'text-muted small text-center mt-2';
                    chartCanvas.parentElement.appendChild(msgEl);
                }

                // Create chart only if config has datasets
                if (chartConfig && chartConfig.data && chartConfig.data.datasets && chartConfig.data.datasets.length > 0) {
                    msgEl.innerText = '';
                    chartCanvas.style.display = '';
                    chart = new Chart(chartCanvas, chartConfig);
                } else {
                    // No data: clear canvas and show friendly message but don't remove the canvas element
                    try {
                        const ctx = chartCanvas.getContext && chartCanvas.getContext('2d');
                        if (ctx) ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
                    } catch (e) {
                        // ignore
                    }
                    chartCanvas.style.display = 'none';
                    msgEl.innerText = 'No chart data available.';
                }
            }

        }).catch(error => {
            console.error('Error fetching field mappings:', error);
            showToast('An error occurred while fetching field mappings.', 'Error', 'error');
        })



        fetch('/api/locations').then(response => response.json()).then(locationsData => {
            const allowedLocations = locationsData.filter(location => location.allowed);
            const locationSelect = document.getElementById('batteryLocationSelect');
            locationSelect.innerHTML = ''; // clear existing options

            allowedLocations.forEach(parentLocation => {
                if (parentLocation.children && parentLocation.children.length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = parentLocation.name;
                    locationsData.filter(l => l.parent && l.parent.id === parentLocation.id).forEach(childLocation => {
                        const option = document.createElement('option'); // create option element
                        option.value = childLocation.id;
                        option.text = childLocation.name;
                        option.selected = childLocation.id === (data.location ? data.location.id : null);
                        optgroup.appendChild(option);
                    });
                    const parentOption = document.createElement('option'); // create option for parent location
                    parentOption.value = parentLocation.id;
                    parentOption.text = parentLocation.name;

                    parentOption.selected = parentLocation.id === (data.location ? data.location.id : null);
                    optgroup.appendChild(parentOption);
                    locationSelect.appendChild(optgroup);
                } else {
                    const option = document.createElement('option'); // create option element
                    option.value = parentLocation.id;
                    option.text = parentLocation.name;
                    option.selected = parentLocation.id === (data.location ? data.location.id : null);
                    locationSelect.appendChild(option);
                }
            });
            if (data.location === null || allowedLocations.map(l => l.id).includes(data.location.id) === false) {
                const option = document.createElement('option'); // create option element
                option.value = '';
                option.text = 'Unassigned';
                option.selected = true;
                locationSelect.appendChild(option);
            }
            const selectedLocationId = data.location ? data.location.id : '';
            locationSelect.value = selectedLocationId ? String(selectedLocationId) : '';

            const assetBtn = document.getElementById('assignModeAssetBtn');
            const locationBtn = document.getElementById('assignModeLocationBtn');
            if (assetBtn) {
                assetBtn.onclick = function () {
                    setAssignmentMode('asset');
                };
            }
            if (locationBtn) {
                locationBtn.onclick = function () {
                    setAssignmentMode('location');
                };
            }

            const isCheckedOut = !!(data.checkout_pending_asset_id || data.checked_out_to_asset_id);
            if (assetBtn) {
                assetBtn.title = isCheckedOut
                    ? 'Battery is already checked out. Check in first to assign to another asset.'
                    : '';
            }
            setAssignmentMode(isCheckedOut ? 'location' : 'asset');
        });

        fetch('/api/status_labels').then(response => response.json()).then(statusData => {
            const statusSelect = document.getElementById('batteryStatusSelect');
            statusSelect.innerHTML = ''; // clear existing options

            statusData.filter(s => s.allowed).forEach(status => {
                const option = document.createElement('option'); // create option element
                option.value = status.id;
                option.text = status.name;
                option.selected = status.id === data.status_label.id;
                statusSelect.appendChild(option);
            });
            if (data.status_label === null || statusData.map(s => s.id).includes(data.status_label.id) === false) {
                const option = document.createElement('option'); // create option element
                option.value = '';
                option.text = 'Unassigned';
                option.selected = true;
                statusSelect.appendChild(option);
            }
        });

        fetch('/api/checkout_targets').then(response => response.json()).then(targets => {
            const checkoutSelect = document.getElementById('batteryCheckoutSelect');
            const checkoutLockedMessage = document.getElementById('checkoutLockedMessage');
            checkoutSelect.innerHTML = '';
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.text = targets.length ? 'Select an asset' : 'No allowed assets configured';
            checkoutSelect.appendChild(placeholder);
            const selectedValue = data.checkout_pending_asset_id || data.checked_out_to_asset_id || '';
            originalCheckedOutAssetId = data.checked_out_to_asset_id || null;
            targets.forEach(target => {
                const option = document.createElement('option');
                option.value = target.id;
                option.text = target.name ? `${target.id} – ${target.name}` : target.id;
                if (originalCheckedOutAssetId && target.id !== originalCheckedOutAssetId) {
                    option.disabled = true;
                }
                if (target.id === selectedValue) {
                    option.selected = true;
                }
                checkoutSelect.appendChild(option);
            });
            if (checkoutLockedMessage) {
                checkoutLockedMessage.classList.toggle('d-none', !originalCheckedOutAssetId);
            }
            const selectedMode = document.getElementById('batteryAssignmentMode')?.value;
            checkoutSelect.disabled = targets.length === 0 || selectedMode !== 'asset';
        });
    });


    document.getElementById('batteryModal').addEventListener('hidden.bs.modal', function (event) {
        if (chart && typeof chart.destroy === 'function') {
            try { chart.destroy(); } catch (e) { /* ignore */ }
        }
        // restore canvas visibility for next open
        const chartCanvas = document.getElementById('batteryModalChart');
        if (chartCanvas) chartCanvas.style.display = '';
    }, { once: true });
    document.querySelector('#batteryUpdateForm > button[type="submit"]').onclick = function (e) {
        e.preventDefault();
        const formData = new FormData(document.getElementById('batteryUpdateForm'));
        const assignmentMode = document.getElementById('batteryAssignmentMode')?.value;

        if (!assignmentMode) {
            showToast('Please choose an assignment mode: Asset or Location.', 'Assignment Required', 'error');
            return;
        }

        if (assignmentMode === 'asset') {
            const target = document.getElementById('batteryCheckoutSelect')?.value || '';
            if (!target) {
                showToast('Please select an asset to assign.', 'Assignment Required', 'error');
                return;
            }
            if (originalCheckedOutAssetId && target !== originalCheckedOutAssetId) {
                showToast('Battery is already checked out. Check it in first before assigning a different asset.', 'Checkout Locked', 'error');
                return;
            }
            formData.set('batteryCheckoutTarget', target);
        } else if (assignmentMode === 'location') {
            const location = document.getElementById('batteryLocationSelect')?.value || '';
            if (!location) {
                showToast('Please select a location.', 'Assignment Required', 'error');
                return;
            }
            formData.set('batteryLocation', location);
            // Choosing location should check battery in
            formData.set('batteryCheckoutTarget', '');
        }

        fetch(`/api/battery/${batteryId}`, {
            method: 'PUT',
            body: JSON.stringify(Object.fromEntries(formData)),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(response => response.json()).then(data => {
            if (data.status && data.status === 'error') {
                showToast(data.message, 'Error', 'error');
                return;
            }
            showToast(data.message, 'Battery Update', 'success');
            document.getElementById('batteryModal').querySelector('.btn-close').click();
        }).catch(error => {
            console.error(error);
            showToast('An error occurred while updating the battery.', 'Error', 'error');
        });
    }

    document.getElementById('uploadBatteryChart').onclick = function (e) {
        e.preventDefault();
        const uploadInput = document.getElementById('batteryChartFile');
        if (uploadInput.files.length === 0) {
            showToast('Please select a file to upload.', 'Error', 'error');
            return;
        }
        const file = uploadInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                const content = e.target.result;
                const formElement = document.createElement('input');
                formElement.type = 'hidden';
                fetch('/api/field_mappings').then(response => response.json()).then(mappings => {
                    const voltageCurveMapping = mappings.find(m => m.name === 'Voltage Curve');
                    if (!voltageCurveMapping) {
                        showToast('Voltage Curve field mapping not found. Please contact the administrator.', 'Error', 'error');
                        return;
                    }
                    formElement.name = voltageCurveMapping.db_column_name;
                    formElement.value = content;
                    document.getElementById('batteryUpdateForm').appendChild(formElement);
                    showToast('Battery voltage curve uploaded. Please click Update to save changes.', 'Upload Successful', 'success');
                }).catch(error => {
                    console.error('Error fetching field mappings:', error);
                    showToast('An error occurred while fetching field mappings.', 'Error', 'error');
                })
            }
            reader.readAsText(file);


        }
    }
}

function periodicCheckSyncStatus(toast) {
    window.ApiClient.get('/api/sync', { retries: 1 }).then(({ data }) => {
        const syncStatus = data?.data?.job_status || data?.status;
        switch (syncStatus) {
            case 'started':
            case 'queued':
                toast.querySelector('.toast-body').innerText = `Sync in progress... Status: ${syncStatus}`;
                setTimeout(() => periodicCheckSyncStatus(toast), 1000); // check again in 1 second
                break;
            case 'finished':
                toast.querySelector('.toast-body').innerText = `Sync completed successfully.`;
                setTimeout(() => { toast.remove(); }, 3000);
                break;
            case 'failed':
                toast.querySelector('.toast-body').innerText = `Sync failed!`;
                toast.querySelector('.toast-header').className = 'toast-header bg-danger text-white';
                break;
            default:
                toast.querySelector('.toast-body').innerText = `Sync status: ${syncStatus || 'unknown'}`;
        }
    });
}


// handle sync button click
document.addEventListener('DOMContentLoaded', function () {
    const startSyncButton = document.getElementById('startSyncButton');

    if (startSyncButton) {
        startSyncButton.addEventListener('click', function () {
            startSyncButton.disabled = true;
            startSyncButton.querySelector('.spinner-border')?.classList.remove('d-none');

            window.ApiClient.post('/api/sync', {}, { retries: 1 })
            .then(({ data }) => {
                const message = data?.message || 'Sync started';
                toast = showToast(message, 'Syncing', 'success', timeout = 30000);
                periodicCheckSyncStatus(toast);
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('An error occurred while starting the sync.', 'Error', 'error');
            })
            .finally(() => {
                startSyncButton.disabled = false;
                startSyncButton.querySelector('.spinner-border')?.classList.add('d-none');
            });
        });
    }

    Array.from(document.getElementsByClassName('batteryModalButton')).forEach(button => {
        button.addEventListener('click', function (event) {
            showBatteryInfoModal(button.getAttribute('data-battery-id'));
        })
    });
    setInterval(periodic, 5000); // repeat every 5 seconds
    periodic(); // initial call
});
