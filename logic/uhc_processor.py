import logging
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from .base_processor import BaseProcessor
from .pdf_template import PDFTemplate
from config import FACILITIES
import os

logger = logging.getLogger(__name__)

# UHC Rates
UHC_BASE_RATE = 85  # per leg
UHC_MILEAGE_RATE = 3  # per mile


class UHCProcessor(BaseProcessor):
    """Process UHC distance-based billing"""
    
    def process_excel(self, filepath):
        """Process UHC Excel file"""
        try:
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.lower().str.strip()
            return self._process_uhc(df)
        except Exception as e:
            logger.error(f"Error processing UHC file: {str(e)}", exc_info=True)
            raise
    
    def _process_uhc(self, df):
        """Process UHC distance-based billing"""
        processed_rows = []
        successful = 0
        failed = 0
        total_revenue = 0
        
        for idx, row in df.iterrows():
            try:
                logger.debug(f"Processing UHC row {idx}: {row.to_dict()}")
                patient_name = row['patient name']
                invoice_number = row['invoice number']
                dob = row['dob']
                member_id = row['member id']
                service_type = row['type of service'].lower()
                date_of_service = row['date of service']
                facility_name = row['facility name']
                destination_address = row['destination address']
                
                # Validate facility
                if facility_name not in FACILITIES:
                    raise ValueError(f"Unknown facility: {facility_name}")
                
                facility_address = FACILITIES[facility_name]
                
                # Mileage A: Facility to Destination
                mileage_a = self._calculate_distance(facility_address, destination_address)
                mileage_a_rounded = self._round_distance(mileage_a)
                
                # Calculate cost
                if service_type == 'one way':
                    distance = mileage_a_rounded
                    amount = UHC_BASE_RATE + (distance * UHC_MILEAGE_RATE)
                    legs = 1
                    mileage_b_rounded = 0
                else:  # round trip
                    # Mileage B: Destination to Facility
                    mileage_b = self._calculate_distance(destination_address, facility_address)
                    mileage_b_rounded = self._round_distance(mileage_b)
                    distance = mileage_a_rounded + mileage_b_rounded
                    amount = (UHC_BASE_RATE * 2) + (distance * UHC_MILEAGE_RATE)
                    legs = 2
                
                total_revenue += amount
                successful += 1
                
                # Generate PDF
                self._generate_uhc_pdf(invoice_number, patient_name, dob, member_id, 
                                       date_of_service, facility_name, destination_address,
                                       service_type, mileage_a_rounded, mileage_b_rounded, 
                                       amount, legs)
                
                processed_rows.append({
                    'invoice_number': invoice_number,
                    'patient_name': patient_name,
                    'dob': self._format_date(dob),
                    'member_id': member_id,
                    'type of service': service_type,
                    'date_of_service': self._format_date(date_of_service),
                    'facility_name': facility_name,
                    'destination_address': destination_address,
                    'distance': round(distance, 1),
                    'amount': round(amount, 2),
                    'status': 'SUCCESS',
                    'error': ''
                })
            
            except Exception as e:
                failed += 1
                error_msg = str(e)
                logger.warning(f"Row {idx} failed: {error_msg}")
                
                processed_rows.append({
                    'invoice_number': row.get('invoice number', ''),
                    'patient_name': row.get('patient name', ''),
                    'dob': self._format_date(row.get('dob', '')),
                    'member_id': row.get('member id', ''),
                    'type of service': row.get('type of service', ''),
                    'date_of_service': self._format_date(row.get('date of service', '')),
                    'facility_name': row.get('facility name', ''),
                    'destination_address': row.get('destination address', ''),
                    'distance': '',
                    'amount': '',
                    'status': 'FAILED',
                    'error': error_msg
                })
        
        # Save processed Excel
        self._save_processed_excel(processed_rows)
        
        # Create ZIP file
        zip_path = self.create_invoices_zip()
        
        return {
            'total_rows': len(df),
            'successful': successful,
            'failed': failed,
            'total_revenue': round(total_revenue, 2),
            'invoices_generated': successful,
            'zip_path': zip_path
        }
    
    def _generate_uhc_pdf(self, invoice_number, patient_name, dob,
                         member_id, date_of_service, facility_name,
                         destination_address, service_type, mileage_a,
                         mileage_b, amount, legs):
        """Generate UHC invoice PDF using template"""
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
            PDFTemplate.build_header(story)
            
            # Invoice details
            invoice_date, due_date = self._get_invoice_date_strings()
            bill_to = 'United Healthcare Insurance Company'
            PDFTemplate.build_invoice_details(story, invoice_number, invoice_date, due_date, bill_to)
            
            # Patient info section
            facility_address = FACILITIES.get(facility_name, 'N/A')
            dob_str = self._format_date(dob)
            info_data = [
                ['Patient Name:', '', patient_name],
                ['DOB:', '', dob_str],
                ['Member ID:', '', member_id],
                ['Date of Service:', '', self._format_date(date_of_service)],
                ['Type of Service:', '', service_type.title()],
            ]
            
            info_table = Table(info_data, colWidths=[1.5*inch, 0.5*inch, 5*inch])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (0, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Billing table - Item | Description | Type | Unit | Code | Rate (USD) | Amount
            base_styles = getSampleStyleSheet()
            desc_style = ParagraphStyle(
                'wrapped_desc',
                parent=base_styles['Normal'],
                fontSize=8,
                leading=9,
                alignment=0
            )
            base_code = 'A0130'
            mileage_code = 'S0209'
            
            if service_type.lower() in ['round trip', 'roundtrip', 'wheelchair roundtrip']:
                billing_data = [
                    ['Item', 'Description', 'Type', 'Unit', 'Code', 'Rate (USD)', 'Amount'],
                    ['1', Paragraph('Non-Emergent Transportation Wheelchair Van', desc_style), 'A Leg', '1', base_code, f'${UHC_BASE_RATE:.2f}', f'${UHC_BASE_RATE:.2f}'],
                    ['2', Paragraph('Non-Emergent Transportation Mileage', desc_style), 'A Leg', f'{mileage_a}', mileage_code, f'${UHC_MILEAGE_RATE:.2f}', f'${mileage_a * UHC_MILEAGE_RATE:.2f}'],
                    ['3', Paragraph('Non-Emergent Transportation Wheelchair Van', desc_style), 'B Leg', '1', base_code, f'${UHC_BASE_RATE:.2f}', f'${UHC_BASE_RATE:.2f}'],
                    ['4', Paragraph('Non-Emergent Transportation Mileage', desc_style), 'B Leg', f'{mileage_b}', mileage_code, f'${UHC_MILEAGE_RATE:.2f}', f'${mileage_b * UHC_MILEAGE_RATE:.2f}'],
                    ['', '', '', '', '', '', ''],
                ]
            else:
                billing_data = [
                    ['Item', 'Description', 'Type', 'Unit', 'Code', 'Rate (USD)', 'Amount'],
                    ['1', Paragraph('Non-Emergent Transportation Wheelchair Van', desc_style), 'A Leg', '1', base_code, f'${UHC_BASE_RATE:.2f}', f'${UHC_BASE_RATE:.2f}'],
                    ['2', Paragraph('Non-Emergent Transportation Mileage', desc_style), 'A Leg', f'{mileage_a}', mileage_code, f'${UHC_MILEAGE_RATE:.2f}', f'${mileage_a * UHC_MILEAGE_RATE:.2f}'],
                    ['', '', '', '', '', '', ''],
                ]
            
            col_widths = [0.4*inch, 2.5*inch, 0.7*inch, 0.5*inch, 0.7*inch, 1*inch, 1*inch]
            billing_table = Table(billing_data, colWidths=col_widths)
            billing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
            story.append(billing_table)
            story.append(Spacer(1, 0.15*inch))
            
            # Place of Service section
            place_data = [
                [
                    Paragraph('<b>Place of Service</b>', styles['normal']),
                    Paragraph(f'{facility_name}, {facility_address}', styles['normal']),
                    Paragraph('<font color="#2B5F7F">\u2194</font>', styles['normal']),
                    Paragraph(f'{destination_address}', styles['normal']),
                ]
            ]
            place_table = Table(place_data, colWidths=[1.2*inch, 3*inch, 0.4*inch, 2.2*inch])
            place_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (0, 0), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ]))
            story.append(place_table)
            story.append(Spacer(1, 0.2*inch))

            # Totals
            totals_data = [
                ['', '', '', '', '', 'Subtotal', f'${amount:.2f}'],
                ['', '', '', '', '', 'Total', f'${amount:.2f}']
            ]
            story.append(PDFTemplate.create_totals_table(totals_data, col_widths, subtotal_col=5, total_col=6))
            story.append(Spacer(1, 0.3*inch))

            # Payment details
            PDFTemplate.build_payment_section(story)
            
            # Footer
            PDFTemplate.build_footer(story)
            
            doc.build(story)
            logger.info(f"Generated UHC PDF: {filepath}")
        
        except Exception as e:
            logger.error(f"Error generating UHC PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise