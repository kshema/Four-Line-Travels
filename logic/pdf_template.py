from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

# Template colors - consistent across all PDFs
HEADER_COLOR = colors.HexColor('#2B5F7F')
TEXT_COLOR = colors.HexColor('#000000')
SUBTOTAL_COLOR = colors.HexColor('#E8EEF5')
TOTAL_COLOR = colors.HexColor('#2B5F7F')
WHITE = colors.white
LIGHT_GREY = colors.HexColor('#F5F5F5')
BORDER_COLOR = colors.black


class PDFTemplate:
    """Base PDF template with consistent styling"""
    
    # Company Info
    COMPANY_NAME = "FOURLINE TRAVELS LLC"
    COMPANY_ADDRESS = "645 Stelton St"
    COMPANY_CITY_STATE = "Teaneck, NJ, 07666"
    COMPANY_PHONE = "Phone 551-313-8500"
    COMPANY_EMAIL = "info@fourlinetravels.com"
    COMPANY_WEBSITE = "www.fourlinetravels.com"
    
    # Default margins
    TOP_MARGIN = 0 * inch
    BOTTOM_MARGIN = 0 * inch
    LEFT_MARGIN = 0 * inch
    RIGHT_MARGIN = 0 * inch
    
    @staticmethod
    def get_styles():
        """Get predefined styles"""
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=WHITE,
            spaceAfter=6,
            alignment=0,
            fontName='Helvetica-Bold'
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Normal'],
            fontSize=11,
            textColor=TEXT_COLOR,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=TEXT_COLOR
        )
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=14,
            textColor=WHITE,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        
        header_text_style = ParagraphStyle(
            'HeaderText',
            parent=styles['Normal'],
            fontSize=11,
            textColor=WHITE,
            alignment=2
        )
        
        return {
            'title': title_style,
            'section': section_style,
            'normal': normal_style,
            'footer': footer_style,
            'header_text': header_text_style
        }
    
    @staticmethod
    def create_header(left_content, right_content):
        """Create standard header with blue background"""
        header_data = [[left_content, right_content]]
        
        header_table = Table(header_data, colWidths=[2*inch, 5*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HEADER_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 15),
            ('RIGHTPADDING', (1, 0), (1, 0), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        return header_table

    @staticmethod
    def create_details_section(details_data, col_widths=None):
        """Create invoice details section"""
        if col_widths is None:
            col_widths = [2*inch, 5*inch]
        
        details_table = Table(details_data, colWidths=col_widths)
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, 0), 15),
            ('LEFTPADDING', (1, 0), (1, 0), 15),
            ('RIGHTPADDING', (1, 0), (1, 0), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        return details_table
    
    @staticmethod
    def create_line_items_table(items_data, col_widths):
        """Create line items table with headers"""
        items_table = Table(items_data, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -2), 1, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, WHITE]),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return items_table
    
    @staticmethod
    def create_totals_table(totals_data, col_widths, subtotal_col=6, total_col=7):
        """Create subtotal and total section"""
        totals_table = Table(totals_data, colWidths=col_widths)
        totals_table.setStyle(TableStyle([
            ('BACKGROUND', (subtotal_col, 0), (total_col, 0), SUBTOTAL_COLOR),
            ('BACKGROUND', (subtotal_col, 1), (total_col, 1), TOTAL_COLOR),
            ('TEXTCOLOR', (subtotal_col, 1), (total_col, 1), WHITE),
            ('ALIGN', (subtotal_col, 0), (total_col, 1), 'RIGHT'),
            ('FONTNAME', (subtotal_col, 0), (total_col, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (subtotal_col, 0), (total_col, 1), 10),
            ('TOPPADDING', (subtotal_col, 0), (total_col, 1), 8),
            ('BOTTOMPADDING', (subtotal_col, 0), (total_col, 1), 8),
            ('RIGHTPADDING', (subtotal_col, 0), (total_col, 1), 10),
        ]))
        
        return totals_table
    
    @staticmethod
    def create_payment_section(payment_data):
        """Create payment details section"""
        payment_table = Table(payment_data, colWidths=[2*inch, 5*inch])
        payment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, 0), 15),
            ('LEFTPADDING', (1, 0), (1, 0), 15),
            ('RIGHTPADDING', (1, 0), (1, 0), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        return payment_table
    
    @staticmethod
    def create_footer(footer_text):
        """Create blue footer section"""
        footer_data = [[Paragraph(footer_text, PDFTemplate.get_styles()['footer'])]]
        
        footer_table = Table(footer_data, colWidths=[7*inch])
        footer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HEADER_COLOR),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        return footer_table