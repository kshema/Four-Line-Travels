import logging
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from .base_processor import BaseProcessor
import os
import re

logger = logging.getLogger(__name__)

# NJ Veterans Rates
NJVETERANS_HOURLY_RATE = 125
NJVETERANS_MAX_INVOICE = 1000


class NJVeteransProcessor(BaseProcessor):
    """Process NJ Veterans hourly billing"""
    
    def __init__(self, mode_key, mode_config, output_folder):
        super().__init__(mode_key, mode_config, output_folder)
        self.invoice_prefix = None
        self.starting_number = None
    
    def process_excel(self, filepath, invoice_number_prefix=None):
        """Process NJ Veterans Excel file with invoice number prefix"""
        try:
            if not invoice_number_prefix:
                raise ValueError("Invoice number prefix is required (e.g., NJVA00050)")
            
            # Parse prefix and extract number
            self._parse_invoice_prefix(invoice_number_prefix)
            
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.lower().str.strip()
            return self._process_njveterans(df)
        except Exception as e:
            logger.error(f"Error processing NJ Veterans file: {str(e)}", exc_info=True)
            raise
    
    def _parse_invoice_prefix(self, invoice_number_prefix):
        """Extract prefix and starting number from invoice number (e.g., NJVA00050 -> NJVA, 50)"""
        try:
            # Match pattern: letters followed by numbers (NJVA00050)
            match = re.match(r'^([A-Z]+)(\d+)$', invoice_number_prefix.strip())
            
            if not match:
                raise ValueError(f"Invalid invoice format. Expected format like 'NJVA00050', got '{invoice_number_prefix}'")
            
            self.invoice_prefix = match.group(1)  # NJVA
            self.starting_number = int(match.group(2))  # 50
            
            logger.info(f"Invoice prefix: {self.invoice_prefix}, Starting number: {self.starting_number}")
        
        except Exception as e:
            logger.error(f"Error parsing invoice prefix: {str(e)}")
            raise
    
    def _process_njveterans(self, df):
        """Process NJ Veterans hourly billing"""
        processed_rows = []
        successful = 0
        failed = 0
        total_revenue = 0
        invoice_counter = self.starting_number
        current_invoice = f"{self.invoice_prefix}{invoice_counter:05d}"
        current_amount = 0
        invoices_generated = 0
        
        for idx, row in df.iterrows():
            try:
                logger.debug(f"Processing NJ Veterans row {idx}: {row.to_dict()}")
                patient_name = row['patient name']
                date_of_service = row['date of service']
                facility_name = row['facility name']
                destination_address = row['destination address']
                service_type = row['roundtrip or one-way'].lower()
                hours = float(row['number of hours'])
                
                if hours <= 0:
                    raise ValueError("Hours must be greater than 0")
                
                amount = hours * NJVETERANS_HOURLY_RATE
                
                # Check if exceeds max
                if current_amount + amount > NJVETERANS_MAX_INVOICE:
                    invoices_generated += 1
                    invoice_counter += 1
                    current_invoice = f"{self.invoice_prefix}{invoice_counter:05d}"
                    current_amount = 0
                
                current_amount += amount
                total_revenue += amount
                successful += 1
                
                # Generate PDF
                self._generate_njveterans_pdf(current_invoice, patient_name, 
                                             date_of_service, destination_address,
                                             service_type, hours, amount)
                
                processed_rows.append({
                    'invoice_number': current_invoice,
                    'patient_name': patient_name,
                    'date_of_service': str(date_of_service),
                    'facility_name': facility_name,
                    'destination_address': destination_address,
                    'roundtrip or one-way': service_type,
                    'number_of_hours': hours,
                    'amount': round(amount, 2),
                    'status': 'SUCCESS',
                    'error': ''
                })
            
            except Exception as e:
                failed += 1
                error_msg = str(e)
                logger.warning(f"Row {idx} failed: {error_msg}")
                
                processed_rows.append({
                    'invoice_number': '',
                    'patient_name': row.get('patient name', ''),
                    'date_of_service': str(row.get('date of service', '')),
                    'facility_name': row.get('facility name', ''),
                    'destination_address': row.get('destination address', ''),
                    'roundtrip or one-way': row.get('roundtrip or one-way', ''),
                    'number_of_hours': row.get('number of hours', ''),
                    'amount': '',
                    'status': 'FAILED',
                    'error': error_msg
                })
        
        # Count last invoice if it has data
        if current_amount > 0:
            invoices_generated += 1
        
        self._save_processed_excel(processed_rows)
        
        # Create ZIP file
        zip_path = self.create_invoices_zip()
        
        return {
            'total_rows': len(df),
            'successful': successful,
            'failed': failed,
            'total_revenue': round(total_revenue, 2),
            'invoices_generated': invoices_generated,
            'zip_path': zip_path
        }
    
    def _generate_njveterans_pdf(self, invoice_number, patient_name, 
                                date_of_service, destination_address,
                                service_type, hours, amount):
        """Generate NJ Veterans invoice PDF matching template"""
        try:
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.output_folder, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, 
                                   topMargin=0.5*inch, bottomMargin=0.5*inch,
                                   leftMargin=0.75*inch, rightMargin=0.75*inch)
            story = []
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#000000'),
                spaceAfter=12,
                alignment=1,
                fontName='Helvetica-Bold'
            )
            
            section_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#000000'),
                spaceAfter=6,
                fontName='Helvetica-Bold'
            )
            
            # Company header
            story.append(Paragraph("FOURLINE TRAVELS LLC", title_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Company details
            company_details = [
                "645 Stelton Street, Teaneck, NJ 07666",
                "Phone: 551-313-8500 | Email: info@fourlinetravels.com",
                "Website: www.fourlinetravels.com"
            ]
            for detail in company_details:
                story.append(Paragraph(detail, styles['Normal']))
            
            story.append(Spacer(1, 0.2*inch))
            
            # Invoice header
            story.append(Paragraph("INVOICE", section_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Invoice details table
            invoice_date, due_date = self._get_invoice_date_strings()
            
            details_data = [
                ['Invoice Number:', invoice_number, 'Invoice Date:', invoice_date],
                ['Bill To:', 'NJ Veterans', 'Due Date:', due_date],
            ]
            
            details_table = self._create_details_table(details_data)
            story.append(details_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Service details
            story.append(Paragraph("SERVICE DETAILS", section_style))
            story.append(Spacer(1, 0.1*inch))
            
            service_data = [
                ['Patient Name:', patient_name],
                ['Date of Service:', str(date_of_service).split()[0]],
                ['Destination:', destination_address],
                ['Service Type:', service_type.upper()],
                ['Hours:', str(hours)],
            ]
            
            service_table = self._create_info_table(service_data)
            story.append(service_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Billing summary
            story.append(Paragraph("BILLING SUMMARY", section_style))
            story.append(Spacer(1, 0.1*inch))
            
            billing_data = [
                ['Description', 'Quantity', 'Rate', 'Amount'],
                ['Transport Service', f'{hours} hrs', f'${NJVETERANS_HOURLY_RATE}.00/hr', f'${amount:.2f}'],
                ['', '', 'TOTAL:', f'${amount:.2f}'],
            ]
            
            col_widths = [3*inch, 1*inch, 1.5*inch, 1.5*inch]
            billing_table = self._create_billing_table(billing_data, col_widths)
            story.append(billing_table)
            
            story.append(Spacer(1, 0.3*inch))
            
            # Payment terms
            story.append(Paragraph("Payment Terms", section_style))
            story.append(Paragraph("Payment is due within 15 days of invoice date.", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            # Footer
            footer_text = "Thank you for your business!"
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                alignment=1
            )
            story.append(Paragraph(footer_text, footer_style))
            
            doc.build(story)
            logger.info(f"Generated NJ Veterans PDF: {filepath}")
        
        except Exception as e:
            logger.error(f"Error generating NJ Veterans PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise