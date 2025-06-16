function showStatus(message, isError = false) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = isError ? 'error' : 'success';
    statusDiv.style.display = 'block';
}

function uploadFile() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    if (!file) {
        showStatus('Please select a CSV file to upload', true);
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('https://<your-backend-url>/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showStatus(data.message);
        } else {
            showStatus(data.message, true);
        }
    })
    .catch(error => {
        showStatus('Error uploading file: ' + error.message, true);
    });
}

function runScript() {
    fetch('https://<your-backend-url>/run-script', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showStatus(data.message);
        } else {
            showStatus(data.message, true);
        }
    })
    .catch(error => {
        showStatus('Error running script: ' + error.message, true);
    });
}