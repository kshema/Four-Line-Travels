import logging
import googlemaps
from config import GOOGLE_MAPS_API_KEY
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import zipfile

logger = logging.getLogger(__name__)

COMPANY_NAME = "Fourline Travels LLC"
COMPANY_ADDRESS = "645 Stelton St Teaneck 07666"
COMPANY_PHONE = "551-313-8500"
COMPANY_EMAIL = "info@fourlinetravels.com"
COMPANY_WEBSITE = "www.fourlinetravels.com"


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
        """Create a zip file of all generated invoices"""
        zip_filename = f"invoices_{os.path.basename(self.output_folder)}.zip"
        zip_path = os.path.join(self.output_folder, zip_filename)
        
        try:
            logger.info(f"Creating ZIP file: {zip_path}")
            logger.info(f"Output folder: {self.output_folder}")
            logger.info(f"Folder contents: {os.listdir(self.output_folder)}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                pdf_count = 0
                for file in os.listdir(self.output_folder):
                    if file.endswith('.pdf'):
                        file_path = os.path.join(self.output_folder, file)
                        zipf.write(file_path, arcname=file)
                        pdf_count += 1
                        logger.info(f"Added PDF to ZIP: {file}")
                
                logger.info(f"ZIP created with {pdf_count} PDFs")
            
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
    
    def _create_header(self, story, styles):
        """Add company header to PDF"""
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            alignment=1
        )
        
        story.append(Paragraph(COMPANY_NAME, header_style))
        story.append(Paragraph(COMPANY_ADDRESS, styles['Normal']))
        story.append(Paragraph(f"Phone: {COMPANY_PHONE}", styles['Normal']))
        story.append(Paragraph(f"Email: {COMPANY_EMAIL}", styles['Normal']))
        story.append(Paragraph(COMPANY_WEBSITE, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_details_table(self, details_data):
        """Create invoice details table"""
        table = Table(details_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return table
    
    def _create_info_table(self, info_data):
        """Create patient/service info table"""
        table = Table(info_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        return table
    
    def _create_billing_table(self, billing_data, col_widths):
        """Create billing summary table"""
        table = Table(billing_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
            ('FONT', (0, 1), (-1, -2), 'Helvetica', 10),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dddddd')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return table