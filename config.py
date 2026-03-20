import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COMPANY_INFO = {
    'name': 'Fourline Travels LLC',
    'address': '645 Stelton St, Teaneck, NJ 07666',
    'phone': '551-313-8500',
    'email': 'info@fourlinetravels.com',
    'website': 'www.fourlinetravels.com',
}

FACILITIES = {
    'New Vista Nursing and Rehabilitation Center': '300 Broadway, Newark, NJ 07104',
    'Jewish Home Family': '10 Link Drive, Rockleigh, NJ 07647',
    'Peace Care St Joseph': '537 Pavonia Avenue, Jersey City, NJ 07306',
    'Emerson Health and Rehabilitation Center': '100 Kinderkamack Rd, Emerson, NJ 07630',
    'Peace Care St Anns': '198 Old Bergen Rd, Jersey City, NJ 07305',
    'Optima Care Castle Hill': '615 23rd Street, Union City, NJ 07087',
    'Optima care Harborview': '178 - 198 Ogden Ave., Jersey City, NJ 07306',
    'Acclaim Rehabilitation and Care Center (Alaris Health)': '198 Stevens Avenue, Jersey City, NJ 07305',
    'NJ Veterans Home (Menlo Park)': '132 Evergreen Rd, Edison, NJ 08837',
}

BILLING_MODES = {
    'UHC': {
        'name': 'UHC (Distance-Based)',
        'type': 'distance',
        'columns': ['patient_name', 'invoice_number', 'member_id', 'service_type', 'date_of_service', 'facility_name', 'patient_address'],
        'rates': {
            'base_code': 'A0130',
            'base_rate': 85,
            'mileage_code': 'S0209',
            'mileage_rate': 3,
        }
    },
    'NJVETERANS': {
        'name': 'Private Pay - NJ Veterans Home (Hourly)',
        'type': 'hourly',
        'columns': ['patient_name', 'date_of_service', 'facility_name', 'destination_address', 'service_type', 'hours'],
        'rates': {
            'hourly_rate': 125,
            'max_invoice_amount': 1000,
        }
    },
    'JEWISHHOME': {
        'name': 'Private Pay - Jewish Home (Distance-Based)',
        'type': 'distance',
        'columns': ['item', 'date_of_service', 'confirmation_no', 'patient_name', 'from_address', 'to_address'],
        'rates': {
            'base_rate': 70,
            'mileage_rate': 3,
            'legs': 2,
        }
    }
}

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')