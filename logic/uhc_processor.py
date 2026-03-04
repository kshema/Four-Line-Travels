import logging
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from .base_processor import BaseProcessor
from config import FACILITIES

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
                member_id = row['member id']
                service_type = row['type of service'].lower()
                date_of_service = row['date of service']
                facility_name = row['facility name']
                patient_address = row['destination address']
                
                # Validate facility
                if facility_name not in FACILITIES:
                    raise ValueError(f"Unknown facility: {facility_name}")
                
                facility_address = FACILITIES[facility_name]
                
                # Calculate distance
                distance_to = self._calculate_distance(patient_address, facility_address)
                distance_to_rounded = self._round_distance(distance_to)
                
                # Calculate cost
                if service_type == 'one way':
                    distance = distance_to_rounded
                    amount = UHC_BASE_RATE + (distance * UHC_MILEAGE_RATE)
                    legs = 1
                    distance_from_rounded = 0
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
                                       service_type, distance_to_rounded, distance_from_rounded, 
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
    
    def _generate_uhc_pdf(self, invoice_number, patient_name, member_id, 
                         date_of_service, facility_name, patient_address,
                         service_type, distance_to, distance_from, amount, legs):
        """Generate UHC invoice PDF"""
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
                ['Member ID:', member_id, 'Due Date:', due_date],
            ]
            
            story.append(self._create_details_table(details_data))
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
            
            story.append(self._create_info_table(info_data))
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
            
            col_widths = [2*inch, 1.2*inch, 1.2*inch, 1.5*inch, 1.2*inch]
            story.append(self._create_billing_table(billing_data, col_widths))
            
            doc.build(story)
            logger.info(f"Generated UHC PDF: {filepath}")
        
        except Exception as e:
            logger.error(f"Error generating UHC PDF for {invoice_number}: {str(e)}", exc_info=True)
            raise