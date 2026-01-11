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
    fetch(`/api/battery/${batteryId}`).then(response => response.json()).then(data => {
        document.getElementById("batteryModalAlerts").innerHTML = getBatteryAlerts(data).join('\n');
        document.getElementById('batteryModalAssetTag').innerText = data.asset_tag || 'N/A';
        document.getElementById('batteryModalStatus').innerText = data.status_label.name;
        document.getElementById('batteryModalPurchaseDate').innerText = data.purchased_date || 'N/A';

        document.getElementById('batteryModalCustomFields').innerHTML = '';
        console.log(data)
        for (const [name, field] of Object.entries(data.custom_fields)) { // convert object to iterable with array destructuring 
            const row = document.createElement('tr');
            const fieldCell = document.createElement('td');
            const valueCell = document.createElement('td');
            fieldCell.innerText = name;
            if (field.config === "display") {
                valueCell.innerText = field.value;
            } else if (field.config === "edit") {
                switch (field.type) { // create input based on type: text, number, select
                }
            } else {
                continue;
            }
            row.appendChild(fieldCell);
            row.appendChild(valueCell);
            document.getElementById('batteryModalCustomFields').appendChild(row);
        }

    });
    fetch('/api/locations').then(response => response.json()).then(locationsData => {
        const locationSelect = document.getElementById('batteryLocationSelect');
        locationSelect.innerHTML = ''; // clear existing options
        locationsData.forEach(location => {
            const option = document.createElement('option'); // create option element
            option.value = location.id;
            option.text = location.name;
            locationSelect.appendChild(option);
        })
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
    document.querySelector('#batteryUpdateForm > button[type="submit"]').onclick = function (e) {
        e.preventDefault();
    }
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
