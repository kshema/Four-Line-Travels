from flask import Flask, render_template, request, send_file, jsonify
import os
import logging
from datetime import datetime
from config import BILLING_MODES, UPLOAD_FOLDER, OUTPUT_FOLDER, COMPANY_INFO
from logic.processor import BillingProcessor
from werkzeug.utils import secure_filename
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, 
            template_folder=TEMPLATE_FOLDER,
            static_folder=STATIC_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'xlsx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    return render_template('index.html', modes=list(BILLING_MODES.keys()))


@app.route('/api/modes')
def get_modes():
    modes_data = {}
    for key, mode in BILLING_MODES.items():
        modes_data[key] = {
            'name': mode['name'],
            'type': mode['type'],
            'columns': mode['columns']
        }
    return jsonify(modes_data)


@app.route('/api/process', methods=['POST'])
def process():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided', 'success': False}), 400
        
        mode = request.form.get('mode')
        invoice_number = request.form.get('invoice_number', '')
        
        if not mode or mode not in BILLING_MODES:
            return jsonify({'error': 'Invalid billing mode', 'success': False}), 400
        
        # Jewish Home mode requires invoice number
        if mode == 'JEWISHHOME' and not invoice_number:
            return jsonify({'error': 'Invoice number required for Jewish Home billing', 'success': False}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected', 'success': False}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only .xlsx files allowed', 'success': False}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        
        # Create output folder for this processing run
        output_folder = os.path.join(OUTPUT_FOLDER, timestamp)
        os.makedirs(output_folder, exist_ok=True)
        
        logger.info(f"Processing file: {upload_path} to folder: {output_folder}")
        
        # Process based on mode
        processor = BillingProcessor(mode, BILLING_MODES[mode], output_folder)
        
        try:
            if mode == 'JEWISHHOME':
                df = pd.read_excel(upload_path)
                df.columns = df.columns.str.lower().str.strip()
                results = processor._process_jewishhome(df, invoice_number)
            else:
                results = processor.process_excel(upload_path)
            
            results['success'] = True
            results['timestamp'] = timestamp
            results['mode'] = mode
            
            logger.info(f"Processing complete. Results: {results}")
            
            return jsonify(results), 200
        
        except Exception as e:
            logger.error(f"Processing error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e), 'success': False}), 500
    
    except Exception as e:
        logger.error(f"Request error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/download/<timestamp>')
def download_zip(timestamp):
    """Download ZIP file of invoices"""
    try:
        # Validate timestamp format (YYYYMMDD_HHMMSS = 15 chars)
        if not timestamp or len(timestamp) != 15:
            logger.warning(f"Invalid timestamp format: {timestamp}")
            return jsonify({'error': 'Invalid timestamp format'}), 400
        
        zip_filename = f"invoices_{timestamp}.zip"
        output_folder = os.path.join(OUTPUT_FOLDER, timestamp)
        file_path = os.path.join(output_folder, zip_filename)
        
        logger.info(f"Download request for ZIP: {file_path}")
        logger.info(f"Output folder: {output_folder}")
        
        if not os.path.exists(output_folder):
            logger.warning(f"Output folder not found: {output_folder}")
            logger.warning(f"Available folders: {os.listdir(OUTPUT_FOLDER) if os.path.exists(OUTPUT_FOLDER) else 'OUTPUT_FOLDER does not exist'}")
            return jsonify({'error': 'Processing folder not found'}), 404
        
        if not os.path.exists(file_path):
            logger.warning(f"ZIP file not found: {file_path}")
            logger.warning(f"Folder contents: {os.listdir(output_folder)}")
            return jsonify({'error': 'Invoice ZIP file not found'}), 404
        
        logger.info(f"Sending ZIP file: {file_path}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
    except Exception as e:
        logger.error(f"Download ZIP error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/api/download-excel/<timestamp>')
def download_excel(timestamp):
    """Download processed Excel file"""
    try:
        # Validate timestamp format
        if not timestamp or len(timestamp) != 15:
            logger.warning(f"Invalid timestamp format: {timestamp}")
            return jsonify({'error': 'Invalid timestamp format'}), 400
        
        output_folder = os.path.join(OUTPUT_FOLDER, timestamp)
        
        logger.info(f"Download request for Excel from: {output_folder}")
        
        if not os.path.exists(output_folder):
            logger.warning(f"Output folder not found: {output_folder}")
            return jsonify({'error': 'Processing folder not found'}), 404
        
        # Find the processed Excel file
        excel_file = None
        try:
            folder_contents = os.listdir(output_folder)
            logger.info(f"Folder contents: {folder_contents}")
            for file in folder_contents:
                if file.startswith('processed_') and file.endswith('.xlsx'):
                    excel_file = file
                    logger.info(f"Found Excel file: {excel_file}")
                    break
        except Exception as e:
            logger.error(f"Error listing folder: {str(e)}")
        
        if not excel_file:
            logger.warning(f"No processed Excel file found in: {output_folder}")
            return jsonify({'error': 'Processed Excel file not found'}), 404
        
        file_path = os.path.join(output_folder, excel_file)
        
        logger.info(f"Sending Excel file: {file_path}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Download Excel error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)