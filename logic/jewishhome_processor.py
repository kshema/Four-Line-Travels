import logging
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from .base_processor import BaseProcessor
from .pdf_template import PDFTemplate
import os

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
                
                # Use exact column names
                item = row['item']
                date_of_service = row['date of service']
                confirmation_no = row['confirmation no']
                patient_name = row['name of patient']
                from_address = row['from']
                to_address = row['to']
                
                # Validate required fields
                if not all([patient_name, from_address, to_address]):
                    raise ValueError(f"Missing required fields: patient_name={patient_name}, from={from_address}, to={to_address}")
                
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
        """Generate Jewish Home consolidated PDF using template"""
        try:
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.output_folder, filename)
            
            # Use landscape orientation
            doc = SimpleDocTemplate(filepath, pagesize=landscape(letter),
                                topMargin=0.4*inch,
                                bottomMargin=0.4*inch,
                                leftMargin=0.4*inch,
                                rightMargin=0.4*inch)
            story = []
            styles = PDFTemplate.get_styles()
            
            # Create custom style for wrapped addresses with smaller font
            base_styles = getSampleStyleSheet()
            address_style = ParagraphStyle(
                'wrapped_address',
                parent=base_styles['Normal'],
                fontSize=7,
                leading=8,
                alignment=0
            )
            
            # Header (landscape widths)
            PDFTemplate.build_header(story, col_widths=[4*inch, 6*inch])

            # Invoice details
            invoice_date, due_date = self._get_invoice_date_strings()
            bill_to = (
                f'Jewish Home Family<br/>'
                f'10 Link Dr Rockleigh NJ 07647'
            )
            PDFTemplate.build_invoice_details(story, invoice_number, invoice_date, due_date, bill_to, col_widths=[4*inch, 6*inch])

            # Rate info above table
            rate_info = Paragraph(
                f'<font size=9><b>Rate/Mile</b> = ${JEWISHHOME_MILEAGE_RATE} &nbsp;&nbsp; <b>Rate/Leg</b> = ${JEWISHHOME_BASE_RATE}</font>',
                styles['normal']
            )
            story.append(rate_info)
            story.append(Spacer(1, 0.1*inch))

            # Billing details table with wrapped text
            table_data = [
                ['Item', 'Date', 'Conf#', 'Patient Name', 'From Address', 'To Address', 'Miles', 'Legs', 'Amount']
            ]

            successful_rows = [r for r in rows if r.get('status') == 'SUCCESS']

            for row in successful_rows:
                date_str = str(row.get('date_of_service', '')).split()[0]
                
                # Wrap long addresses with smaller font size
                from_para = Paragraph(str(row.get('from', '')), address_style)
                to_para = Paragraph(str(row.get('to', '')), address_style)
                
                table_data.append([
                    str(row.get('item', '')),
                    date_str,
                    str(row.get('confirmation_no', ''))[:8],
                    str(row.get('name_of_patient', ''))[:18],
                    from_para,
                    to_para,
                    f"{row.get('total_miles', '')}",
                    str(row.get('legs', '')),
                    f"${row.get('amount', ''):.2f}"
                ])

            # Column widths for landscape (10.2 inches usable)
            col_widths = [0.4*inch, 0.65*inch, 0.65*inch, 1.3*inch, 2.5*inch, 2.5*inch, 0.65*inch, 0.6*inch, 0.8*inch]

            billing_table = Table(table_data, colWidths=col_widths, splitByRow=True)
            billing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (3, -1), 'CENTER'),
                ('ALIGN', (4, 0), (5, -1), 'LEFT'),
                ('ALIGN', (6, 0), (7, -1), 'CENTER'),
                ('ALIGN', (8, 0), (8, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            story.append(billing_table)
            story.append(Spacer(1, 0.15*inch))

            # Totals section
            totals_data = [
                ['', '', '', '', '', '', '', 'Subtotal', f'${grand_total:.2f}'],
                ['', '', '', '', '', '', '', 'Total', f'${grand_total:.2f}']
            ]
            story.append(PDFTemplate.create_totals_table(totals_data, col_widths, subtotal_col=6, total_col=8))
            story.append(Spacer(1, 0.15*inch))

            # Payment details
            PDFTemplate.build_payment_section(story, col_widths=[2*inch, 8.2*inch])

            # Footer
            PDFTemplate.build_footer(story, width=10.2*inch)
            
            doc.build(story)
            logger.info(f"Generated Jewish Home PDF: {filepath}")

        except Exception as e:
            logger.error(f"Error generating Jewish Home PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise