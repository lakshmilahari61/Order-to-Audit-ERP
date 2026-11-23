import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from flask import current_app
from app import db
from app.models import SalesOrder, GSTInvoice, InvoiceItem, AuditLog
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class BillingService:
    """
    GST Invoicing & PDF Generation Service.
    Enforces sequential numbering, exact Decimal tax arithmetic,
    and generates formal ReportLab PDF tax invoices.
    """

    @staticmethod
    def generate_invoice_number() -> str:
        """Generates sequential invoice number (INV-YYYY-XXXX)."""
        year = datetime.utcnow().strftime('%Y')
        count = GSTInvoice.query.filter(GSTInvoice.invoice_number.like(f'INV-{year}-%')).count() + 1
        return f"INV-{year}-{count:04d}"

    @staticmethod
    def create_invoice_from_order(order_id: int, user_id: int = None) -> GSTInvoice:
        """
        Converts an approved SalesOrder into an official GST Tax Invoice.
        Snapshots customer state and details to prevent retroactive mutation.
        """
        order = SalesOrder.query.get(order_id)
        if not order:
            raise ValueError(f"Sales order ID {order_id} not found.")

        if order.status not in ['Approved']:
            raise ValueError(f"Order must be in 'Approved' status to generate invoice. Current status: {order.status}")

        existing = GSTInvoice.query.filter_by(sales_order_id=order.id).first()
        if existing:
            return existing

        customer = order.customer
        inv_num = BillingService.generate_invoice_number()

        invoice = GSTInvoice(
            invoice_number=inv_num,
            sales_order_id=order.id,
            customer_id=customer.id,
            invoice_date=datetime.utcnow().date(),
            customer_name=customer.name,
            customer_gstin=customer.gstin or 'URP (Unregistered)',
            customer_state=customer.state,
            customer_address=customer.billing_address or '',
            taxable_amount=order.total_taxable_amount,
            cgst_amount=Decimal('0.00'),
            sgst_amount=Decimal('0.00'),
            igst_amount=Decimal('0.00'),
            total_amount=Decimal('0.00'),
            status='Issued'
        )
        db.session.add(invoice)
        db.session.flush()

        tot_cgst = Decimal('0.00')
        tot_sgst = Decimal('0.00')
        tot_igst = Decimal('0.00')
        tot_taxable = Decimal('0.00')
        tot_amount = Decimal('0.00')

        for item in order.items:
            inv_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=item.product_id,
                product_name=item.product.name,
                hsn_code=item.product.hsn_code,
                quantity=item.quantity,
                unit_price=item.unit_price,
                taxable_amount=item.taxable_amount,
                gst_rate=item.gst_rate,
                cgst_amount=item.cgst_amount,
                sgst_amount=item.sgst_amount,
                igst_amount=item.igst_amount,
                total_amount=item.total_amount
            )
            db.session.add(inv_item)

            tot_taxable += item.taxable_amount
            tot_cgst += item.cgst_amount
            tot_sgst += item.sgst_amount
            tot_igst += item.igst_amount
            tot_amount += item.total_amount

        invoice.taxable_amount = tot_taxable
        invoice.cgst_amount = tot_cgst
        invoice.sgst_amount = tot_sgst
        invoice.igst_amount = tot_igst
        invoice.total_amount = tot_amount

        order.status = 'Invoiced'

        # Generate PDF
        pdf_path = BillingService.generate_invoice_pdf(invoice)
        invoice.pdf_path = pdf_path

        db.session.add(AuditLog(
            user_id=user_id,
            action='GENERATE_GST_INVOICE',
            entity_type='GSTInvoice',
            entity_id=invoice.id,
            details=f"Invoice {inv_num} generated for {customer.name}. Total: ₹{tot_amount} (CGST: ₹{tot_cgst}, SGST: ₹{tot_sgst}, IGST: ₹{tot_igst})"
        ))

        db.session.commit()
        return invoice

    @staticmethod
    def generate_invoice_pdf(invoice: GSTInvoice) -> str:
        """
        Renders a formal, professional GST Tax Invoice using ReportLab.
        Returns the absolute filesystem path to the PDF.
        """
        instance_dir = os.path.join(current_app.root_path, '..', 'instance', 'invoices')
        os.makedirs(instance_dir, exist_ok=True)
        pdf_filename = f"{invoice.invoice_number}.pdf"
        filepath = os.path.join(instance_dir, pdf_filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#0F172A'),
            alignment=1,
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'InvoiceSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#475569'),
            alignment=1,
            spaceAfter=12
        )
        body_bold = ParagraphStyle(
            'BodyBold',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            fontName='Helvetica-Bold'
        )
        body_normal = ParagraphStyle(
            'BodyNormal',
            parent=styles['Normal'],
            fontSize=9,
            leading=12
        )

        elements.append(Paragraph("<b>TAX INVOICE</b>", title_style))
        elements.append(Paragraph("Prototype Demonstration — NIT Tiruchirappalli Winter Internship 2026", subtitle_style))

        # Company & Customer Box Table
        factory_name = current_app.config.get('FACTORY_NAME', 'South Indian Traditional Foods Ltd.')
        factory_addr = current_app.config.get('FACTORY_ADDRESS', 'Thuvakudi, Tiruchirappalli, Tamil Nadu')
        factory_gstin = current_app.config.get('FACTORY_GSTIN', '33AAAAA0000A1Z5')
        factory_state = current_app.config.get('FACTORY_STATE', 'Tamil Nadu')

        header_data = [
            [
                Paragraph(f"<b>Seller Details:</b><br/>"
                          f"<b>{factory_name}</b><br/>"
                          f"{factory_addr}<br/>"
                          f"GSTIN: <b>{factory_gstin}</b><br/>"
                          f"State: {factory_state}", body_normal),
                Paragraph(f"<b>Invoice No:</b> {invoice.invoice_number}<br/>"
                          f"<b>Invoice Date:</b> {invoice.invoice_date.strftime('%d-%b-%Y')}<br/>"
                          f"<b>Place of Supply:</b> {invoice.customer_state}<br/>"
                          f"<b>Status:</b> {invoice.status}", body_normal)
            ],
            [
                Paragraph(f"<b>Billed To (Customer):</b><br/>"
                          f"<b>{invoice.customer_name}</b><br/>"
                          f"{invoice.customer_address or 'Address on file'}<br/>"
                          f"GSTIN: {invoice.customer_gstin or 'URP'}<br/>"
                          f"State: {invoice.customer_state}", body_normal),
                Paragraph(f"<b>Order Reference:</b> {invoice.sales_order.order_number if invoice.sales_order else 'N/A'}<br/>"
                          f"<b>Payment Terms:</b> Due within 30 days<br/>"
                          f"<b>Tax Type:</b> {'Intra-state (CGST + SGST)' if invoice.cgst_amount > 0 else 'Inter-state (IGST)'}", body_normal)
            ]
        ]

        header_table = Table(header_data, colWidths=[270, 270])
        header_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 12))

        # Item Details Table
        # Columns: S.No, Description, HSN, Qty, Rate, Taxable, CGST, SGST, IGST, Total
        item_headers = ['#', 'Description', 'HSN', 'Qty', 'Rate (₹)', 'Taxable (₹)', 'CGST (₹)', 'SGST (₹)', 'IGST (₹)', 'Total (₹)']
        items_rows = [item_headers]

        for idx, item in enumerate(invoice.items, start=1):
            items_rows.append([
                str(idx),
                item.product_name,
                item.hsn_code,
                f"{item.quantity:.0f}",
                f"{item.unit_price:.2f}",
                f"{item.taxable_amount:.2f}",
                f"{item.cgst_amount:.2f}",
                f"{item.sgst_amount:.2f}",
                f"{item.igst_amount:.2f}",
                f"{item.total_amount:.2f}"
            ])

        # Add Totals row
        items_rows.append([
            "", "Total", "", "", "",
            f"{invoice.taxable_amount:.2f}",
            f"{invoice.cgst_amount:.2f}",
            f"{invoice.sgst_amount:.2f}",
            f"{invoice.igst_amount:.2f}",
            f"{invoice.total_amount:.2f}"
        ])

        col_widths = [20, 120, 45, 35, 45, 60, 50, 50, 50, 65]
        item_table = Table(items_rows, colWidths=col_widths)
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 15))

        # Bottom Summary & Signatory Table
        summary_data = [
            [
                Paragraph("<b>Terms & Conditions:</b><br/>"
                          "1. Goods once sold will not be taken back.<br/>"
                          "2. Interest @ 18% p.a. charged for overdue payments.<br/>"
                          "3. Subject to Tiruchirappalli jurisdiction.", body_normal),
                Paragraph(f"<b>Taxable Value:</b> ₹{invoice.taxable_amount:,.2f}<br/>"
                          f"<b>CGST (2.5%):</b> ₹{invoice.cgst_amount:,.2f}<br/>"
                          f"<b>SGST (2.5%):</b> ₹{invoice.sgst_amount:,.2f}<br/>"
                          f"<b>IGST (5.0%):</b> ₹{invoice.igst_amount:,.2f}<br/>"
                          f"<font size=11 color='#0F172A'><b>Grand Total: ₹{invoice.total_amount:,.2f}</b></font>", body_normal)
            ],
            [
                Paragraph("<i>Note: Prototype dummy GST data for internship evaluation.</i>", body_normal),
                Paragraph(f"<b>For {factory_name}</b><br/><br/><br/>Authorized Signatory", body_bold)
            ]
        ]
        summary_table = Table(summary_data, colWidths=[300, 240])
        summary_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)

        doc.build(elements)
        return filepath
