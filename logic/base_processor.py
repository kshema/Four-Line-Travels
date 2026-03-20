import logging
import googlemaps
from config import GOOGLE_MAPS_API_KEY
from datetime import datetime, timedelta
import os
import zipfile

logger = logging.getLogger(__name__)


class BaseProcessor:
    """Base class for all billing processors"""
    
    def __init__(self, mode_key, mode_config, output_folder):
        self.mode_key = mode_key
        self.mode_config = mode_config
        self.output_folder = output_folder
        self.gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    
    def _calculate_distance(self, address1, address2):
        """Calculate distance between two addresses using Google Maps API (in miles)"""
        try:
            result = self.gmaps.distance_matrix(address1, address2, units="imperial")
            
            # Check for valid response
            if result['rows'][0]['elements'][0].get('status') == 'ZERO_RESULTS':
                raise ValueError(f"Cannot find route from {address1} to {address2}")
            
            distance_text = result['rows'][0]['elements'][0]['distance']['text']
            distance_miles = float(distance_text.replace(' mi', '').replace(',', ''))
            return round(distance_miles, 1)
        except Exception as e:
            logger.warning(f"Distance calculation failed for {address1} to {address2}: {str(e)}")
            raise ValueError(f"Cannot calculate distance: {str(e)}")
    
    def _round_distance(self, distance):
        """Round distance with rule: < 0.5 rounds down, minimum 1 mile"""
        if distance < 0.5:
            return 1
        return round(distance)
    
    @staticmethod
    def _format_date(date_val):
        """Format date as MM-DD-YYYY"""
        try:
            if hasattr(date_val, 'strftime'):
                return date_val.strftime('%m-%d-%Y')
            date_str = str(date_val).split()[0]
            if date_str in ('', 'NaT', 'nan', 'None'):
                return ''
            if '-' in date_str and len(date_str) == 10:
                parts = date_str.split('-')
                return f"{parts[1]}-{parts[2]}-{parts[0]}"
            return date_str
        except Exception:
            return ''
    
    def _save_processed_excel(self, rows):
        """Save processed data to Excel"""
        try:
            import pandas as pd
            df = pd.DataFrame(rows)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_folder, f"processed_{timestamp}.xlsx")
            df.to_excel(output_path, index=False)
            logger.info(f"Saved processed Excel: {output_path}")
        except Exception as e:
            logger.error(f"Error saving processed Excel: {str(e)}", exc_info=True)
            raise
    
    def create_invoices_zip(self):
        """Create a zip file of all generated invoices and processed Excel"""
        zip_filename = f"invoices_{os.path.basename(self.output_folder)}.zip"
        zip_path = os.path.join(self.output_folder, zip_filename)
        
        try:
            logger.info(f"Creating ZIP file: {zip_path}")
            logger.info(f"Output folder: {self.output_folder}")
            logger.info(f"Folder contents: {os.listdir(self.output_folder)}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                file_count = 0
                for file in os.listdir(self.output_folder):
                    if file.endswith('.pdf') or file.endswith('.xlsx'):
                        file_path = os.path.join(self.output_folder, file)
                        zipf.write(file_path, arcname=file)
                        file_count += 1
                        logger.info(f"Added to ZIP: {file}")
                
                logger.info(f"ZIP created with {file_count} files")
            
            if os.path.exists(zip_path):
                logger.info(f"ZIP file created successfully: {zip_path}")
                return zip_path
            else:
                logger.error(f"ZIP file was not created: {zip_path}")
                raise Exception("ZIP file creation failed")
        
        except Exception as e:
            logger.error(f"Error creating zip file: {str(e)}", exc_info=True)
            raise
    
    def _get_invoice_date_strings(self):
        """Get formatted invoice and due dates"""
        invoice_date = datetime.now().strftime('%m/%d/%Y')
        due_date = (datetime.now() + timedelta(days=15)).strftime('%m/%d/%Y')
        return invoice_date, due_date