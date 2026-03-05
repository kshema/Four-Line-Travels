let currentTimestamp = null;

// Mode change handler
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

// Display results in table format
function displayResults(data) {
    const resultDiv = document.getElementById('result');
    const resultContent = document.getElementById('resultContent');
    const downloadBtn = document.getElementById('downloadBtn');
    
    // Handle missing grand_total
    const grandTotal = data.grand_total !== undefined ? data.grand_total : data.total_revenue;
    
    let html = `
        <table class="results-table">
            <tr>
                <td><strong>Total Rows:</strong></td>
                <td>${data.total_rows}</td>
            </tr>
            <tr>
                <td><strong>Successful:</strong></td>
                <td>${data.successful}</td>
            </tr>
            <tr>
                <td><strong>Failed:</strong></td>
                <td>${data.failed}</td>
            </tr>
            <tr>
                <td><strong>Total Revenue:</strong></td>
                <td>$${parseFloat(data.total_revenue || 0).toFixed(2)}</td>
            </tr>
            <tr style="border-top: 2px solid #ccc; font-weight: bold;">
                <td><strong>Grand Total:</strong></td>
                <td>$${parseFloat(grandTotal || 0).toFixed(2)}</td>
            </tr>
        </table>
    `;
    
    resultContent.innerHTML = html;
    resultDiv.style.display = 'block';
    downloadBtn.style.display = 'inline-block';
    
    // Store timestamp for download
    currentTimestamp = data.timestamp;
}

// Download both files (ZIP + Excel) - only once
document.getElementById('downloadBtn').addEventListener('click', async function() {
    if (!currentTimestamp) return;
    
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = true;
    downloadBtn.textContent = '⏳ Downloading...';
    
    try {
        // Download ZIP file
        const zipResponse = await fetch(`/api/download/${currentTimestamp}`);
        if (!zipResponse.ok) {
            throw new Error('Failed to download ZIP file');
        }
        const zipBlob = await zipResponse.blob();
        const zipUrl = window.URL.createObjectURL(zipBlob);
        const zipLink = document.createElement('a');
        zipLink.href = zipUrl;
        zipLink.download = `invoices_${currentTimestamp}.zip`;
        document.body.appendChild(zipLink);
        zipLink.click();
        window.URL.revokeObjectURL(zipUrl);
        document.body.removeChild(zipLink);
        
        // Download Excel file (1 second delay)
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const excelResponse = await fetch(`/api/download-excel/${currentTimestamp}`);
        if (!excelResponse.ok) {
            throw new Error('Failed to download Excel file');
        }
        const excelBlob = await excelResponse.blob();
        const excelUrl = window.URL.createObjectURL(excelBlob);
        const excelLink = document.createElement('a');
        excelLink.href = excelUrl;
        excelLink.download = `processed_${currentTimestamp}.xlsx`;
        document.body.appendChild(excelLink);
        excelLink.click();
        window.URL.revokeObjectURL(excelUrl);
        document.body.removeChild(excelLink);
        
        // Clear files after downloads complete
        await new Promise(resolve => setTimeout(resolve, 1000));
        await clearAllFiles();
        
        downloadBtn.disabled = false;
        downloadBtn.textContent = '📥 Download Files (ZIP + Excel)';
        
    } catch (error) {
        console.error('Download error:', error);
        showError('Download failed: ' + error.message);
        downloadBtn.disabled = false;
        downloadBtn.textContent = '📥 Download Files (ZIP + Excel)';
    }
});

// Clear all files after download
async function clearAllFiles() {
    try {
        const response = await fetch('/api/clear-files', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        if (data.success) {
            console.log(`✓ Cleared ${data.cleared} files/folders`);
        }
    } catch (error) {
        console.error('Clear files error:', error);
    }
}

// Form submission
document.getElementById('invoiceForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const mode = document.getElementById('mode').value;
    const file = document.getElementById('file').files[0];
    const invoiceNumber = document.getElementById('invoiceNumber').value;
    
    document.getElementById('error').style.display = 'none';
    document.getElementById('error').textContent = '';
    
    // Validation
    if (!mode) {
        showError('Please select a billing mode');
        return;
    }

    if (!file) {
        showError('Please select an Excel file');
        return;
    }

    if ((mode === 'JEWISHHOME' || mode === 'NJVETERANS') && !invoiceNumber) {
        showError(`Please enter an invoice number for ${mode} billing`);
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

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    console.error('Error:', message);
}

// File handling - drag and drop + click
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

// Drag over
fileWrapper.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileWrapper.classList.add('drag-over');
});

// Drag leave
fileWrapper.addEventListener('dragleave', () => {
    fileWrapper.classList.remove('drag-over');
});

// Drop
fileWrapper.addEventListener('drop', (e) => {
    e.preventDefault();
    fileWrapper.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        updateFileName();
    }
});

// File input change
fileInput.addEventListener('change', updateFileName);

// Update file name display
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