document.getElementById('mode').addEventListener('change', function() {
    const invoiceNumberGroup = document.getElementById('invoiceNumberGroup');
    const invoiceHint = document.getElementById('invoiceHint');
    const invoiceInput = document.getElementById('invoiceNumber');
    
    if (this.value === 'JEWISHHOME') {
        invoiceNumberGroup.style.display = 'block';
        invoiceInput.placeholder = 'e.g., JH00160';
        invoiceInput.required = true;
        invoiceHint.textContent = 'Format: Letters + numbers (e.g., JH00160)';
    } else if (this.value === 'NJVETERANS') {
        invoiceNumberGroup.style.display = 'block';
        invoiceInput.placeholder = 'e.g., NJVA00050';
        invoiceInput.required = true;
        invoiceHint.textContent = 'Format: Letters + numbers (e.g., NJVA00050)';
    } else {
        invoiceNumberGroup.style.display = 'none';
        invoiceInput.required = false;
    }
});

document.getElementById('invoiceForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const mode = document.getElementById('mode').value;
    const file = document.getElementById('file').files[0];
    const invoiceNumber = document.getElementById('invoiceNumber').value;
    
    document.getElementById('error').style.display = 'none';
    document.getElementById('error').textContent = '';
    
    if (!mode) {
        showError('Please select a billing mode');
        return;
    }

    if (!file) {
        showError('Please select an Excel file');
        return;
    }

    if (mode === 'JEWISHHOME' && !invoiceNumber) {
        showError('Please enter an invoice number for Jewish Home billing');
        return;
    }
    
    const formData = new FormData();
    formData.append('mode', mode);
    formData.append('file', file);
    if (invoiceNumber) {
        formData.append('invoice_number', invoiceNumber);
    }
    
    try {
        const submitBtn = document.querySelector('.btn-primary');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = '⏳ Processing...';
        submitBtn.disabled = true;
        
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
        
        if (response.ok && data.success) {
            document.getElementById('invoiceForm').style.display = 'none';
            displayResults(data);
        } else {
            showError(data.error || 'Processing failed');
        }
    } catch (error) {
        console.error('Fetch error:', error);
        showError('Error: ' + error.message);
        const submitBtn = document.querySelector('.btn-primary');
        submitBtn.textContent = '✨ Generate Invoices';
        submitBtn.disabled = false;
    }
});

function displayResults(data) {
    const resultContent = document.getElementById('resultContent');
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadExcelBtn = document.getElementById('downloadExcelBtn');
    
    resultContent.innerHTML = `
        <table class="results-table">
            <tr>
                <td><strong>Total Rows:</strong></td>
                <td>${data.total_rows}</td>
            </tr>
            <tr>
                <td><strong>Successful:</strong></td>
                <td><span class="success">${data.successful}</span></td>
            </tr>
            <tr>
                <td><strong>Failed:</strong></td>
                <td><span class="error">${data.failed}</span></td>
            </tr>
            <tr>
                <td><strong>Total Revenue:</strong></td>
                <td>$${parseFloat(data.total_revenue).toFixed(2)}</td>
            </tr>
            <tr>
                <td><strong>Invoices Generated:</strong></td>
                <td>${data.invoices_generated}</td>
            </tr>
        </table>
    `;
    
    if (data.timestamp) {
        downloadBtn.onclick = () => downloadFile(`/api/download/${data.timestamp}`, `invoices_${data.timestamp}.zip`);
        downloadBtn.style.display = 'inline-block';
        
        downloadExcelBtn.onclick = () => downloadFile(`/api/download-excel/${data.timestamp}`, `processed_${data.timestamp}.xlsx`);
        downloadExcelBtn.style.display = 'inline-block';
    }
    
    document.getElementById('result').style.display = 'block';
}

function downloadFile(url, filename) {
    fetch(url)
        .then(response => {
            if (!response.ok) {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Download failed');
                    });
                } else {
                    throw new Error('Download failed with status ' + response.status);
                }
            }
            return response.blob();
        })
        .then(blob => {
            if (blob.type !== 'application/zip' && blob.type !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
                throw new Error('Invalid file received');
            }
            
            const link = document.createElement('a');
            const href = window.URL.createObjectURL(blob);
            link.href = href;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            window.URL.revokeObjectURL(href);
            document.body.removeChild(link);
        })
        .catch(error => {
            console.error('Download error:', error);
            showError('Download failed: ' + error.message);
        });
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    console.error('Error:', message);
}

// File handling
const fileWrapper = document.getElementById('fileWrapper');
const fileInput = document.getElementById('file');
const fileLabel = document.querySelector('.file-label');
const fileName = document.getElementById('fileName');

// Click to select file
fileWrapper.addEventListener('click', (e) => {
    if (e.target !== fileInput) {
        fileInput.click();
    }
});

// Drag and drop
fileWrapper.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileWrapper.classList.add('drag-over');
});

fileWrapper.addEventListener('dragleave', () => {
    fileWrapper.classList.remove('drag-over');
});

fileWrapper.addEventListener('drop', (e) => {
    e.preventDefault();
    fileWrapper.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        updateFileName();
    }
});

// File change
fileInput.addEventListener('change', updateFileName);

function updateFileName() {
    if (fileInput.files.length > 0) {
        const name = fileInput.files[0].name;
        fileName.textContent = `✓ Selected: ${name}`;
        fileName.classList.add('success');
        fileLabel.textContent = '✓ File selected';
    } else {
        fileName.textContent = '';
        fileName.classList.remove('success');
        fileLabel.textContent = '📤 Click or drag file here';
    }
}