import logging
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)

# Jewish Home Rates
JEWISHHOME_BASE_RATE = 70  # per leg
JEWISHHOME_MILEAGE_RATE = 3  # per mile
JEWISHHOME_LEGS = 2


class JewishHomeProcessor(BaseProcessor):
    """Process Jewish Home consolidated billing"""
    
    def process_excel(self, filepath, invoice_number=None):
        """Process Jewish Home Excel file"""
        try:
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.lower().str.strip()
            return self._process_jewishhome(df, invoice_number)
        except Exception as e:
            logger.error(f"Error processing Jewish Home file: {str(e)}", exc_info=True)
            raise
    
    def _process_jewishhome(self, df, invoice_number):
        """Process Jewish Home consolidated billing"""
        processed_rows = []
        successful = 0
        failed = 0
        total_revenue = 0
        grand_total = 0
        
        for idx, row in df.iterrows():
            try:
                logger.debug(f"Processing Jewish Home row {idx}: {row.to_dict()}")
                item = row['item']
                date_of_service = row['date of service']
                confirmation_no = row['confirmation no']
                patient_name = row['name of patient']
                from_address = row['from']
                to_address = row['to']
                
                # Calculate distance
                distance = self._calculate_distance(from_address, to_address)
                total_miles = distance * JEWISHHOME_LEGS
                
                amount = (JEWISHHOME_LEGS * JEWISHHOME_BASE_RATE) + (total_miles * JEWISHHOME_MILEAGE_RATE)
                grand_total += amount
                total_revenue += amount
                successful += 1
                
                processed_rows.append({
                    'item': item,
                    'date_of_service': str(date_of_service),
                    'confirmation_no': confirmation_no,
                    'name_of_patient': patient_name,
                    'from': from_address,
                    'to': to_address,
                    'total_miles': round(total_miles, 1),
                    'rate_per_leg': JEWISHHOME_BASE_RATE,
                    'rate_per_mile': JEWISHHOME_MILEAGE_RATE,
                    'legs': JEWISHHOME_LEGS,
                    'amount': round(amount, 2),
                    'status': 'SUCCESS',
                    'error': ''
                })
            
            except Exception as e:
                failed += 1
                error_msg = str(e)
                logger.warning(f"Row {idx} failed: {error_msg}")
                
                processed_rows.append({
                    'item': row.get('item', ''),
                    'date_of_service': str(row.get('date of service', '')),
                    'confirmation_no': row.get('confirmation no', ''),
                    'name_of_patient': row.get('name of patient', ''),
                    'from': row.get('from', ''),
                    'to': row.get('to', ''),
                    'total_miles': '',
                    'rate_per_leg': '',
                    'rate_per_mile': '',
                    'legs': '',
                    'amount': '',
                    'status': 'FAILED',
                    'error': error_msg
                })
        
        # Generate consolidated PDF
        self._generate_jewishhome_pdf(processed_rows, grand_total, invoice_number)
        
        # Save processed Excel
        self._save_processed_excel(processed_rows)
        
        # Create ZIP file
        zip_path = self.create_invoices_zip()
        
        return {
            'total_rows': len(df),
            'successful': successful,
            'failed': failed,
            'total_revenue': round(total_revenue, 2),
            'grand_total': round(grand_total, 2),
            'invoices_generated': 1,
            'zip_path': zip_path
        }
    
    def _generate_jewishhome_pdf(self, rows, grand_total, invoice_number):
        """Generate Jewish Home consolidated PDF"""
        try:
            import os
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.output_folder, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()
            
            # Company header
            story = self._create_header(story, styles)
            
            # Invoice details
            invoice_date, due_date = self._get_invoice_date_strings()
            
            details_data = [
                ['Invoice Number:', invoice_number, 'Invoice Date:', invoice_date],
                ['', '', 'Due Date:', due_date],
            ]
            
            story.append(self._create_details_table(details_data))
            story.append(Spacer(1, 0.3*inch))
            
            # Billing details table
            table_data = [
                ['Item', 'Date', 'Conf#', 'Patient', 'From', 'To', 'Miles', 'Legs', 'Amount']
            ]
            
            successful_rows = [r for r in rows if r.get('status') == 'SUCCESS']
            
            for row in successful_rows:
                date_str = str(row.get('date_of_service', '')).split()[0]
                
                table_data.append([
                    str(row.get('item', '')),
                    date_str,
                    str(row.get('confirmation_no', ''))[:10],
                    str(row.get('name_of_patient', ''))[:12],
                    str(row.get('from', ''))[:12],
                    str(row.get('to', ''))[:12],
                    str(row.get('total_miles', '')),
                    str(row.get('legs', '')),
                    f"${row.get('amount', '')}"
                ])
            
            # Add grand total row
            table_data.append(['', '', '', '', '', '', '', 'TOTAL:', f'${grand_total:.2f}'])
            
            # Better column widths for readability
            col_widths = [0.5*inch, 0.75*inch, 0.8*inch, 1*inch, 
                         1*inch, 1*inch, 0.6*inch, 0.5*inch, 0.8*inch]
            
            billing_table = Table(table_data, colWidths=col_widths)
            billing_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -2), 'Helvetica', 8),
                ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#cccccc')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dddddd')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (6, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(billing_table)
            
            doc.build(story)
            logger.info(f"Generated Jewish Home PDF: {filepath}")
        
        except Exception as e:
            logger.error(f"Error generating Jewish Home PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise