import pandas as pd
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import logging
import googlemaps
from config import GOOGLE_MAPS_API_KEY, FACILITIES
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime, timedelta
import os
import zipfile

logger = logging.getLogger(__name__)

COMPANY_NAME = "Fourline Travels LLC"
COMPANY_ADDRESS = "645 Stelton St Teaneck 07666"
COMPANY_PHONE = "551-313-8500"
COMPANY_EMAIL = "info@fourlinetravels.com"
COMPANY_WEBSITE = "www.fourlinetravels.com"

# UHC Rates
UHC_BASE_RATE = 85  # per leg
UHC_MILEAGE_RATE = 3  # per mile

# NJ Veterans Rates
NJVETERANS_HOURLY_RATE = 125
NJVETERANS_MAX_INVOICE = 1000
NJVETERANS_STARTING_NUMBER = 53

# Jewish Home Rates
JEWISHHOME_BASE_RATE = 70  # per leg
JEWISHHOME_MILEAGE_RATE = 3  # per mile
JEWISHHOME_LEGS = 2


class BillingProcessor:
    def __init__(self, mode_key, mode_config, output_folder):
        self.mode_key = mode_key
        self.mode_config = mode_config
        self.output_folder = output_folder
        self.gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        self.results = []
    
    def process_excel(self, filepath):
        """Process Excel file based on billing mode"""
        try:
            df = pd.read_excel(filepath)
            # Normalize columns immediately
            df.columns = df.columns.str.lower().str.strip()
            
            if self.mode_key == 'UHC':
                result = self._process_uhc(df)
            elif self.mode_key == 'NJVETERANS':
                result = self._process_njveterans(df)
            elif self.mode_key == 'JEWISHHOME':
                result = self._process_jewishhome(df, None)
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            raise
    
    def _round_distance(self, distance):
        """Round distance with rule: < 0.5 rounds down, minimum 1 mile"""
        if distance < 0.5:
            return 1
        return round(distance)
    
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
                member_id = row['member id']
                service_type = row['type of service'].lower()
                date_of_service = row['date of service']
                facility_name = row['facility name']
                patient_address = row['destination address']
                
                # Validate facility
                if facility_name not in FACILITIES:
                    raise ValueError(f"Unknown facility: {facility_name}")
                
                facility_address = FACILITIES[facility_name]
                
                # Calculate distance separately for to and from
                distance_to = self._calculate_distance(patient_address, facility_address)
                distance_to_rounded = self._round_distance(distance_to)
                
                # Calculate cost
                if service_type == 'one way':
                    distance = distance_to_rounded
                    amount = UHC_BASE_RATE + (distance * UHC_MILEAGE_RATE)
                    legs = 1
                else:  # round trip
                    distance_from = self._calculate_distance(facility_address, patient_address)
                    distance_from_rounded = self._round_distance(distance_from)
                    distance = distance_to_rounded + distance_from_rounded
                    amount = (UHC_BASE_RATE * 2) + (distance * UHC_MILEAGE_RATE)
                    legs = 2
                
                total_revenue += amount
                successful += 1
                
                # Generate PDF
                self._generate_uhc_pdf(invoice_number, patient_name, member_id, 
                                   date_of_service, facility_name, patient_address,
                                   service_type, distance_to_rounded, distance_from_rounded if service_type.lower() == 'round trip' else 0, 
                                   amount, legs)
            
                processed_rows.append({
                    'invoice_number': invoice_number,
                    'patient_name': patient_name,
                    'member_id': member_id,
                    'type of service': service_type,
                    'date_of_service': str(date_of_service),
                    'facility_name': facility_name,
                    'patient_address': patient_address,
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
                    'member_id': row.get('member id', ''),
                    'type of service': row.get('type of service', ''),
                    'date_of_service': str(row.get('date of service', '')),
                    'facility_name': row.get('facility name', ''),
                    'patient_address': row.get('destination address', ''),
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
    
    def _process_njveterans(self, df):
        """Process NJ Veterans hourly billing"""
        processed_rows = []
        successful = 0
        failed = 0
        total_revenue = 0
        invoice_counter = NJVETERANS_STARTING_NUMBER
        current_invoice = f"NJVA{invoice_counter:05d}"
        current_amount = 0
        
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
                    invoice_counter += 1
                    current_invoice = f"NJVA{invoice_counter:05d}"
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
        
        self._save_processed_excel(processed_rows)
        
        # Create ZIP file
        zip_path = self.create_invoices_zip()
        
        return {
            'total_rows': len(df),
            'successful': successful,
            'failed': failed,
            'total_revenue': round(total_revenue, 2),
            'invoices_generated': invoice_counter - NJVETERANS_STARTING_NUMBER + 1,
            'zip_path': zip_path
        }
    
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
    
    def _calculate_distance(self, address1, address2):
        """Calculate distance between two addresses using Google Maps API"""
        try:
            result = self.gmaps.distance_matrix(address1, address2)
            
            # Check for valid response
            if result['rows'][0]['elements'][0].get('status') == 'ZERO_RESULTS':
                raise ValueError(f"Cannot find route from {address1} to {address2}")
            
            distance_meters = result['rows'][0]['elements'][0]['distance']['value']
            distance_miles = distance_meters / 1609.34
            return round(distance_miles, 1)
        except Exception as e:
            logger.warning(f"Distance calculation failed for {address1} to {address2}: {str(e)}")
            raise ValueError(f"Cannot calculate distance: {str(e)}")
    
    def _generate_uhc_pdf(self, invoice_number, patient_name, member_id, 
                         date_of_service, facility_name, patient_address,
                         service_type, distance_to, distance_from, amount, legs):
        """Generate UHC invoice PDF"""
        try:
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.output_folder, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()
            
            # Company header
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
            
            # Invoice details
            invoice_date = datetime.now().strftime('%m/%d/%Y')
            due_date = (datetime.now() + timedelta(days=15)).strftime('%m/%d/%Y')
            
            details_data = [
                ['Invoice Number:', invoice_number, 'Invoice Date:', invoice_date],
                ['Member ID:', member_id, 'Due Date:', due_date],
            ]
            
            details_table = Table(details_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            details_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(details_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Patient and service info
            info_data = [
                ['Patient Name:', patient_name],
                ['Date of Service:', str(date_of_service).split()[0]],
                ['Facility:', facility_name],
                ['Facility Address:', FACILITIES.get(facility_name, 'N/A')],
                ['Destination Address:', patient_address],
                ['Service Type:', service_type.upper()],
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Billing summary
            if service_type.lower() == 'round trip':
                billing_data = [
                    ['Description', 'Quantity', 'Rate', 'Calculation', 'Amount'],
                    ['Base Rate (A Leg)', '1', f'${UHC_BASE_RATE}.00', f'1×${UHC_BASE_RATE}', f'${UHC_BASE_RATE:.2f}'],
                    ['Mileage (A Leg)', f'{distance_to} miles', f'${UHC_MILEAGE_RATE}.00/mi', f'{distance_to}×${UHC_MILEAGE_RATE}', f'${distance_to * UHC_MILEAGE_RATE:.2f}'],
                    ['Base Rate (B Leg)', '1', f'${UHC_BASE_RATE}.00', f'1×${UHC_BASE_RATE}', f'${UHC_BASE_RATE:.2f}'],
                    ['Mileage (B Leg)', f'{distance_from} miles', f'${UHC_MILEAGE_RATE}.00/mi', f'{distance_from}×${UHC_MILEAGE_RATE}', f'${distance_from * UHC_MILEAGE_RATE:.2f}'],
                    ['', '', '', 'TOTAL', f'${amount:.2f}'],
                ]
            else:
                billing_data = [
                    ['Description', 'Quantity', 'Rate', 'Calculation', 'Amount'],
                    ['Base Rate (A Leg)', '1', f'${UHC_BASE_RATE}.00', f'1×${UHC_BASE_RATE}', f'${UHC_BASE_RATE:.2f}'],
                    ['Mileage (A Leg)', f'{distance_to} miles', f'${UHC_MILEAGE_RATE}.00/mi', f'{distance_to}×${UHC_MILEAGE_RATE}', f'${distance_to * UHC_MILEAGE_RATE:.2f}'],
                    ['', '', '', 'TOTAL', f'${amount:.2f}'],
                ]
            
            billing_table = Table(billing_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1.5*inch, 1.2*inch])
            billing_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
                ('FONT', (0, 1), (-1, -2), 'Helvetica', 10),
                ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#cccccc')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dddddd')),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(billing_table)
            
            doc.build(story)
            logger.info(f"Generated UHC PDF: {filepath}")
        
        except Exception as e:
            logger.error(f"Error generating UHC PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise
    
    def _generate_njveterans_pdf(self, invoice_number, patient_name, 
                                date_of_service, destination_address,
                                service_type, hours, amount):
        """Generate NJ Veterans invoice PDF"""
        try:
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.output_folder, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()
            
            # Company header
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
            
            # Invoice details
            invoice_date = datetime.now().strftime('%m/%d/%Y')
            due_date = (datetime.now() + timedelta(days=15)).strftime('%m/%d/%Y')
            
            details_data = [
                ['Invoice Number:', invoice_number, 'Invoice Date:', invoice_date],
                ['', '', 'Due Date:', due_date],
            ]
            
            details_table = Table(details_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            details_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(details_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Patient and service info
            info_data = [
                ['Patient Name:', patient_name],
                ['Date of Service:', str(date_of_service)],
                ['Destination:', destination_address],
                ['Service Type:', service_type.upper()],
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Billing summary
            billing_data = [
                ['Description', 'Hours', 'Rate', 'Amount'],
                ['Transport Service', f'{hours}', f'${NJVETERANS_HOURLY_RATE}.00/hr', f'${amount:.2f}'],
                ['', '', 'TOTAL', f'${amount:.2f}'],
            ]
            
            billing_table = Table(billing_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            billing_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
                ('FONT', (0, 1), (-1, -2), 'Helvetica', 10),
                ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#cccccc')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dddddd')),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(billing_table)
            
            doc.build(story)
            logger.info(f"Generated NJ Veterans PDF: {filepath}")
        
        except Exception as e:
            logger.error(f"Error generating NJ Veterans PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise
    
    def _generate_jewishhome_pdf(self, rows, grand_total, invoice_number):
        """Generate Jewish Home consolidated PDF"""
        try:
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.output_folder, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()
            
            # Company header
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
            
            # Invoice details
            invoice_date = datetime.now().strftime('%m/%d/%Y')
            due_date = (datetime.now() + timedelta(days=15)).strftime('%m/%d/%Y')
            
            details_data = [
                ['Invoice Number:', invoice_number, 'Invoice Date:', invoice_date],
                ['', '', 'Due Date:', due_date],
            ]
            
            details_table = Table(details_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            details_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ]))
            story.append(details_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Billing details table - with better column widths
            table_data = [
                ['Item', 'Date', 'Conf#', 'Patient', 'From', 'To', 'Miles', 'Legs', 'Amount']
            ]
            
            successful_rows = [r for r in rows if r.get('status') == 'SUCCESS']
            
            for row in successful_rows:
                # Format date to just show date (YYYY-MM-DD or MM/DD/YYYY)
                date_str = str(row.get('date_of_service', '')).split()[0]  # Remove time if present
                
                table_data.append([
                    str(row.get('item', '')),
                    date_str,
                    str(row.get('confirmation_no', ''))[:10],  # Truncate confirmation
                    str(row.get('name_of_patient', ''))[:12],  # Truncate patient name
                    str(row.get('from', ''))[:12],  # Truncate from address
                    str(row.get('to', ''))[:12],  # Truncate to address
                    str(row.get('total_miles', '')),
                    str(row.get('legs', '')),
                    f"${row.get('amount', '')}"
                ])
            
            # Add grand total row
            table_data.append(['', '', '', '', '', '', '', 'TOTAL:', f'${grand_total:.2f}'])
            
            # Better column widths for readability
            billing_table = Table(table_data, colWidths=[0.5*inch, 0.75*inch, 0.8*inch, 1*inch, 
                                                        1*inch, 1*inch, 0.6*inch, 0.5*inch, 0.8*inch])
            billing_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -2), 'Helvetica', 8),
                ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#cccccc')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dddddd')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (6, 0), (-1, -1), 'RIGHT'),  # Right align numbers
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
    
    def _save_processed_excel(self, rows):
        """Save processed data to Excel"""
        try:
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
                # Add all PDF files from output folder
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