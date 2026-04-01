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

// create battery info modal
function showBatteryInfoModal(batteryId) {
    let chartConfig = {};
    let chart;
    fetch(`/api/battery/${batteryId}`).then(response => response.json()).then(data => {
        document.getElementById("batteryModalAlerts").innerHTML = getBatteryAlerts(data).join('\n');
        document.getElementById('batteryModalAssetTag').innerText = data.asset_tag || 'N/A';
        document.getElementById('batteryModalPurchaseDate').innerText = data.purchased_date || 'N/A';
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

        const data2 = d3.csvParseRows(data.custom_fields['Battery Drain Curve'].value, function(d, i) {
            return {
            time: +d[0],
            voltage: +d[1], // Convert strings to numbers securely
            current: +d[2],
            capacity: +d[3],
            temperature: +d[4]
            };
        });

        if (data2.length > 0) {
            chartConfig = {
                type: 'line',
                data: {
                    datasets: [{
                        data: data2,
                        label: 'Battery Discharge',
                        tension: 0.1
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
                            }
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

        if (chartConfig) {
            chart = new Chart(chartCanvas, chartConfig);
        } else {
            chartCanvas.parentElement.innerText = "No chart data available.";
        }

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
            checkoutSelect.innerHTML = '';
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.text = targets.length ? 'Select an asset' : 'No allowed assets configured';
            checkoutSelect.appendChild(placeholder);
            const selectedValue = data.checkout_pending_asset_id || data.checked_out_to_asset_id || '';
            targets.forEach(target => {
                const option = document.createElement('option');
                option.value = target.id;
                option.text = target.name ? `${target.id} – ${target.name}` : target.id;
                if (target.id === selectedValue) {
                    option.selected = true;
                }
                checkoutSelect.appendChild(option);
            });
            checkoutSelect.disabled = targets.length === 0;
        });
    });


    document.getElementById('batteryModal').addEventListener('hidden.bs.modal', function (event) {
        chart.destroy();
    }, { once: true });
    document.querySelector('#batteryUpdateForm > button[type="submit"]').onclick = function (e) {
        e.preventDefault();
        const formData = new FormData(document.getElementById('batteryUpdateForm'));
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
                formElement.name = '_snipeit_battery_drain_curve_10';
                formElement.value = content;
                document.getElementById('batteryUpdateForm').appendChild(formElement);
                showToast('Battery drain curve uploaded. Please click Update to save changes.', 'Upload Successful', 'success');
            };
            reader.readAsText(file);


        }
    }
}

function periodicCheckSyncStatus(toast) {
    fetch('/api/sync').then(response => response.json()).then(data => {
        switch (data.status) {
            case 'started':
            case 'queued':
                toast.querySelector('.toast-body').innerText = `Sync in progress... Status: ${data.status}`;
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
        }
    });
}


// handle sync button click
document.addEventListener('DOMContentLoaded', function () {
    const startSyncButton = document.getElementById('startSyncButton');

    startSyncButton.addEventListener('click', function () {
        startSyncButton.disabled = true;
        startSyncButton.querySelector('.spinner-border').classList.remove('d-none');

        fetch('/api/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                toast = showToast(data.message, 'Syncing', 'success', timeout = 30000);
                periodicCheckSyncStatus(toast);
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('An error occurred while starting the sync.', 'Error', 'error');
            })
            .finally(() => {
                startSyncButton.disabled = false;
                startSyncButton.querySelector('.spinner-border').classList.add('d-none');
            });
    });

    Array.from(document.getElementsByClassName('batteryModalButton')).forEach(button => {
        button.addEventListener('click', function (event) {
            showBatteryInfoModal(button.getAttribute('data-battery-id'));
        })
    });
    setInterval(periodic, 5000); // repeat every 5 seconds
    periodic(); // initial call
});
