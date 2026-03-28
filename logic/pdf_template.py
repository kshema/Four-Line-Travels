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
    
    # Payment Info
    BANK_NAME = "Chase Bank"
    BANK_COMPANY = "Fourline Travels LLC"
    ACCOUNT_NUMBER = "591661668"
    ROUTING_NUMBER = "021202337"
    
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
    def build_header(story, col_widths=None):
        """Build complete header section and append to story"""
        styles = PDFTemplate.get_styles()
        if col_widths is None:
            col_widths = [2*inch, 5*inch]
        
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
        
        header_data = [[header_left, header_right]]
        header_table = Table(header_data, colWidths=col_widths)
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
        
        story.append(header_table)
        story.append(Spacer(1, 0.15*inch))

    @staticmethod
    def build_invoice_details(story, invoice_number, invoice_date, due_date, bill_to_text, col_widths=None):
        """Build invoice details section and append to story"""
        styles = PDFTemplate.get_styles()
        if col_widths is None:
            col_widths = [2*inch, 5*inch]
        
        details_left_style = ParagraphStyle(
            'DetailsLeft',
            parent=styles['normal'],
            fontSize=10,
            textColor=TEXT_COLOR,
            alignment=0
        )
        
        details_left = Paragraph(
            f'<b>Invoice No:</b> {invoice_number}<br/>'
            f'<b>Date of Issue:</b> {invoice_date}<br/>'
            f'<b>Due Date:</b> {due_date}',
            details_left_style
        )
        
        details_right = Paragraph(
            f'<b>Bill To</b><br/>{bill_to_text}',
            styles['normal']
        )
        
        details_data = [[details_left, details_right]]
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
        
        story.append(details_table)
        story.append(Spacer(1, 0.2*inch))

    @staticmethod
    def build_payment_section(story, col_widths=None):
        """Build payment details section and append to story"""
        styles = PDFTemplate.get_styles()
        if col_widths is None:
            col_widths = [2*inch, 5*inch]
        
        payment_left = Paragraph(
            f'<b>Payment Details</b><br/><br/>'
            f'<b>Bank Name:</b><br/>'
            f'<b>Company Name:</b><br/>'
            f'<b>Account number:</b><br/>'
            f'<b>Routing number:</b>',
            styles['normal']
        )
        
        payment_right = Paragraph(
            f'<br/><br/>'
            f'{PDFTemplate.BANK_NAME}<br/>'
            f'{PDFTemplate.BANK_COMPANY}<br/>'
            f'{PDFTemplate.ACCOUNT_NUMBER}<br/>'
            f'{PDFTemplate.ROUTING_NUMBER}',
            styles['normal']
        )
        
        payment_data = [[payment_left, payment_right]]
        payment_table = Table(payment_data, colWidths=col_widths)
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
        
        story.append(payment_table)
        story.append(Spacer(1, 0.15*inch))

    @staticmethod
    def build_footer(story, width=7*inch):
        """Build footer section and append to story"""
        styles = PDFTemplate.get_styles()
        footer_data = [[Paragraph('<b>Thank you for your business!</b>', styles['footer'])]]
        
        footer_table = Table(footer_data, colWidths=[width])
        footer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HEADER_COLOR),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        story.append(footer_table)

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
    def create_totals_table(totals_data, col_widths, subtotal_col=5, total_col=6):
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