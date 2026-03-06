import logging
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from .base_processor import BaseProcessor
from .pdf_template import PDFTemplate
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
            
            self._parse_invoice_prefix(invoice_number_prefix)
            
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.lower().str.strip()
            return self._process_njveterans(df)
        except Exception as e:
            logger.error(f"Error processing NJ Veterans file: {str(e)}", exc_info=True)
            raise
    
    def _parse_invoice_prefix(self, invoice_number_prefix):
        """Extract prefix and starting number from invoice number"""
        try:
            match = re.match(r'^([A-Z]+)(\d+)$', invoice_number_prefix.strip())
            
            if not match:
                raise ValueError(f"Invalid invoice format. Expected format like 'NJVA00050', got '{invoice_number_prefix}'")
            
            self.invoice_prefix = match.group(1)
            self.starting_number = int(match.group(2))
            
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
        current_items = []
        invoices_generated = 0
        
        for idx, row in df.iterrows():
            try:
                logger.debug(f"Processing NJ Veterans row {idx}: {row.to_dict()}")
                patient_name = row['patient name']
                date_of_service = row['date of service']
                facility_name = row['facility name']
                destination_address = row['destination address']
                service_type = row['type of service'].lower()
                hours = float(row['number of hours'])
                
                if hours <= 0:
                    raise ValueError("Hours must be greater than 0")
                
                amount = hours * NJVETERANS_HOURLY_RATE
                
                # Check if exceeds max
                if current_amount + amount >= NJVETERANS_MAX_INVOICE and current_items:
                    self._generate_njveterans_pdf(current_invoice, current_items, current_amount)
                    invoices_generated += 1
                    
                    invoice_counter += 1
                    current_invoice = f"{self.invoice_prefix}{invoice_counter:05d}"
                    current_amount = 0
                    current_items = []
                
                current_amount += amount
                total_revenue += amount
                successful += 1
                
                current_items.append({
                    'item_num': len(current_items) + 1,
                    'patient_name': patient_name,
                    'date_of_service': str(date_of_service).split()[0],
                    'trip_type': service_type.title(),
                    'hours': hours,
                    'rate': NJVETERANS_HOURLY_RATE,
                    'amount': round(amount, 2)
                })
                
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
        
        # Generate PDF for last invoice
        if current_items:
            self._generate_njveterans_pdf(current_invoice, current_items, current_amount)
            invoices_generated += 1
        
        self._save_processed_excel(processed_rows)
        zip_path = self.create_invoices_zip()
        
        return {
            'total_rows': len(df),
            'successful': successful,
            'failed': failed,
            'total_revenue': round(total_revenue, 2),
            'invoices_generated': invoices_generated,
            'zip_path': zip_path
        }
    
    def _generate_njveterans_pdf(self, invoice_number, items, total_amount):
        """Generate NJ Veterans invoice PDF using template"""
        try:
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.output_folder, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                topMargin=0*inch,
                                bottomMargin=0*inch,
                                leftMargin=0*inch,
                                rightMargin=0*inch)
            story = []
            styles = PDFTemplate.get_styles()
            
            # Header
            header_left = Paragraph(f'<font size=24><b>INVOICE</b></font>', styles['title'])
            header_right = Paragraph(
                f'<b>{PDFTemplate.COMPANY_NAME}</b><br/>'
                f'{PDFTemplate.COMPANY_ADDRESS}<br/>'
                f'{PDFTemplate.COMPANY_CITY_STATE}<br/>'
                f'{PDFTemplate.COMPANY_PHONE}<br/>'
                f'<u>{PDFTemplate.COMPANY_EMAIL}</u><br/>'
                f'<u>{PDFTemplate.COMPANY_WEBSITE}</u>',
                styles['header_text']
            )
            story.append(PDFTemplate.create_header(header_left, header_right))

            # Invoice details
            invoice_date, due_date = self._get_invoice_date_strings()

            details_left = Paragraph(
                f'<b>Invoice No.</b> {invoice_number}<br/>'
                f'<b>Date of Issue</b> {invoice_date}<br/>'
                f'<b>Due Date</b> {due_date}',
                styles['normal']
            )

            details_right = Paragraph(
                f'<b>Bill To</b><br/>'
                f'New Jersey Veterans Home<br/>'
                f'Menlo Park<br/>'
                f'732-452-4245<br/>'
                f'<u>saar.kamanda@dmava.nj.gov</u>',
                styles['normal']
            )

            details_data = [[details_left, details_right]]
            story.append(PDFTemplate.create_details_section(details_data, [2*inch, 5*inch]))
            story.append(Spacer(1, 0.2*inch))

            # Line items
            items_data = [[
                'Item', 'Name of the Patient', 'Date of Service', 'Trip Type',
                'Hours', 'Rate/Hr (USD)', 'Amount'
            ]]

            for item in items:
                items_data.append([
                    str(item['item_num']),
                    item['patient_name'],
                    item['date_of_service'],
                    item['trip_type'],
                    f"{item['hours']:.2f}",
                    f"${item['rate']:.2f}",
                    f"${item['amount']:.2f}"
                ])

            items_data.append(['', '', '', '', '', '', ''])

            col_widths = [0.4*inch, 1.3*inch, 0.95*inch, 1.1*inch, 0.9*inch, 1*inch, 1*inch]
            story.append(PDFTemplate.create_line_items_table(items_data, col_widths))
            story.append(Spacer(1, 0.2*inch))

            # Totals
            totals_data = [
                ['', '', '', '', '', 'Subtotal', f'${total_amount:.2f}'],
                ['', '', '', '', '', 'Total', f'${total_amount:.2f}']
            ]
            story.append(PDFTemplate.create_totals_table(totals_data, col_widths))
            story.append(Spacer(1, 0.3*inch))

            # Payment details
            payment_left = Paragraph(
                f'<b>Payment Details</b><br/><br/>'
                f'<b>Bank Name</b><br/>'
                f'<b>Company Name</b><br/>'
                f'<b>Account number</b><br/>'
                f'<b>Routing number</b>',
                styles['normal']
            )

            payment_right = Paragraph(
                f'<br/><br/>'
                f'Chase Bank<br/>'
                f'Fourline Travels LLC<br/>'
                f'591661668<br/>'
                f'021202337',
                styles['normal']
            )

            payment_data = [[payment_left, payment_right]]
            story.append(PDFTemplate.create_payment_section(payment_data))
            story.append(Spacer(1, 0.5*inch))

            # Footer
            story.append(PDFTemplate.create_footer('<b>Thank you for your business!</b>'))
            
            doc.build(story)
            logger.info(f"Generated NJ Veterans PDF: {filepath}")
        
        except Exception as e:
            logger.error(f"Error generating NJ Veterans PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise