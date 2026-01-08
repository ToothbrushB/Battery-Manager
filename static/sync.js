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
            document.querySelector('#statusModal .modal-body #networkStatus').innerText = data.status.network.status;
            document.querySelector('#statusModal .modal-body #syncStatus').innerText = data.status.sync.status;
            document.querySelector('#statusModal .modal-body #syncStatus').className = `bi bi-${data.status.sync.icon}`;
            document.querySelector('#statusModal .modal-body #lastSync').innerText = data.status.sync.last_sync;
        }).catch(error => {
            statusButton.className = 'btn m-2 btn-warning';
            statusButton.innerHTML = `Status Unknown <span><i class="bi bi-question-circle"></i></span>`;
            statusModalBody.innerHTML = `Error fetching status: ${error.message}`;
        });
}


function showToast(message, subject, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
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

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
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
    const modalBody = document.querySelector('#batteryModal .modal-body-text');
    modalBody.innerHTML = 'Loading...';
    fetch(`/api/battery/${batteryId}`).then(response => response.json()).then(data => {
        modalBody.innerHTML = getBatteryAlerts(data).join('\n') + `
                <table>
                    <tr>
                        <td>Tag</td>
                        <td>${data.asset_tag}</td>
                    </tr>
                    <tr>
                        <td>Status</td>
                        <td>${data.status_label.name}</td>
                    </tr>
                    <tr>
                        <td>Resistance</td>
                        <td>SOmething something something</td>
                    </tr>
                    <tr>
                        <td>Last Tested</td>
                        <td>2024-06-01 12:34:56</td>
                    </tr>
                    <tr>
                        <td>Cycles</td>
                        <td>150</td>
                    </tr>
                    <tr>
                        <td>Purchase Date</td>
                        <td>${data.purchased_date}</td> // TODO using Intl.RelativeTimeFormat
                    </tr>
                </table>
            <form>
                <label for="batteryStatusSelect" class="form-label mt-3">Update Battery Status</label>
                <select class="form-select mt-3" aria-label="Update Battery Status" id="batteryStatusSelect" name="batteryStatusSelect">
                    <option selected>Select status</option>
                    <!-- Populate options with possible statuses loaded dynamically -->
                </select>
                <label for="batteryNotes" class="form-label mt-3">Notes</label>
                <textarea class="form-control" id="batteryNotes" name="batteryNotes" rows="3"></textarea>
                <label for="batteryLocation" class="form-label mt-3">Location</label>
                <select class="form-select mt-3" aria-label="Battery Location" id="batteryLocation" name="batteryLocation">
                    <option selected>Select location</option>
                    <!-- Populate options with possible locations loaded dynamically -->
                </select>
                <label for="batteryUsageType" class="form-label mt-3">Usage Type</label>
                <select class="form-select mt-3" aria-label="Battery Usage Type" id="batteryUsageType" name="batteryUsageType">
                    <option selected>Select usage type</option>
                    <!-- Populate options with possible usage types loaded dynamically -->
                </select>
                <button type="submit" class="btn btn-primary mt-3">Update</button>
            </form>
                `
    });

    let chartCanvas = document.getElementById('batteryModalChart');
    let chart = new Chart(chartCanvas, {
        type: 'bar',
        data: {
            labels: ['Red', 'Blue', 'Yellow', 'Green', 'Purple', 'Orange'],
            datasets: [{
                label: '# of Votes',
                data: [12, 19, 3, 5, 2, 3],
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    document.getElementById('batteryModal').addEventListener('hidden.bs.modal', function (event) {
        chart.destroy();
    }, { once: true });
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
                showToast(data.message, 'Success', 'success');
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
    })});
    setInterval(periodic, 5000); // repeat every 5 seconds
    periodic(); // initial call
});
