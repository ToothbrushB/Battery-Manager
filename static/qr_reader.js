
let html5QrCode;

const options = {
    fps: 10,    // Optional, frame per seconds for qr code scanning
    qrbox: { width: 250, height: 250 }  // Optional, if you want bounded box UI
};
function handleDecodeSuccess(decodedText, decodedResult) {
    // Handle on success condition with the decoded message.
    fetch('/api/qr_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ qr_data: decodedText })
    }).then(response => response.json()).then(data => {
        html5QrCode.pause();
        document.getElementById('batteryModal').addEventListener('hidden.bs.modal', function (event) {
            html5QrCode.resume();
        }, { once: true });
        new bootstrap.Modal(document.getElementById('batteryModal')).show();
        showBatteryInfoModal(data.id);
    });
}

let qrScanModal;
function stopReader() {
    html5QrCode.stop().then((ignore) => {
        // QR Code scanning is stopped.
    }).catch((err) => {
        // Stop failed, handle it.
    });
}

function init() {
// handle tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

    html5QrCode = new Html5Qrcode(/* element id */ "reader");
    qrScanModal = document.getElementById('readerModal');
    const cameraSelect = document.getElementById('cameraSelect');
    cameraSelect.addEventListener('change', (event) => {
        const cameraId = event.target.value;
        // restart camera scan
        html5QrCode.stop().then((ignore) => {
            html5QrCode.start(
                cameraId,
                options,
                handleDecodeSuccess,
                (errorMessage) => {
                    // parse error, ignore it.
                })
                .catch((err) => {
                    alert(`Unable to start scanning, error: ${err}`);
                });
        }).catch((err) => {
            // Stop failed, handle it.
        });
    });

    // Add an event listener for the 'shown.bs.modal' event
    qrScanModal.addEventListener('shown.bs.modal', function (event) {
        // This method will trigger user permissions ---- copied from docs quickstart
        Html5Qrcode.getCameras().then(devices => {
            /**
            * devices would be an array of objects of type:
            * { id: "id", label: "label" }
            */
            if (devices && devices.length) {
                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.id;
                    option.text = device.label || `Camera ${cameraSelect.length + 1}`;
                    cameraSelect.appendChild(option);
                });
                cameraId = devices[0].id;
                // start scanning
                html5QrCode.start(
                    cameraId,
                    options,
                    handleDecodeSuccess,
                    (errorMessage) => {
                        // parse error, ignore it.
                    })
                    .catch((err) => {
                        // Start failed, handle it.
                    });
            }
        }).catch(err => {
            // handle err
            console.log(err);
        });
    });

    qrScanModal.addEventListener('hidden.bs.modal', function (event) {
    stopReader();
});

}
document.addEventListener('DOMContentLoaded', init);


