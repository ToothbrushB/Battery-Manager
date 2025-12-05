function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    const bgColor = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
    
    toast.innerHTML = `
        <div class="toast-header ${bgColor} text-white">
            <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
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

document.addEventListener('DOMContentLoaded', function () {
    const startSyncButton = document.getElementById('startSyncButton');

    if (startSyncButton) {
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
                showToast(data.message, 'success');
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('An error occurred while starting the sync.', 'error');
            })
            .finally(() => {
                startSyncButton.disabled = false;
                startSyncButton.querySelector('.spinner-border').classList.add('d-none');
            });
        });
    }
});