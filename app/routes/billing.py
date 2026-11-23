import os
from flask import Blueprint, render_template, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from app.models import GSTInvoice, SalesOrder
from app.services.billing_service import BillingService
from app.routes.auth import role_required

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/')
@login_required
def index():
    invoices = GSTInvoice.query.order_by(GSTInvoice.invoice_date.desc(), GSTInvoice.id.desc()).all()
    return render_template('billing/list.html', invoices=invoices)

@billing_bp.route('/create/<int:order_id>')
@login_required
@role_required('admin', 'owner')
def create_invoice(order_id):
    try:
        invoice = BillingService.create_invoice_from_order(order_id, current_user.id)
        flash(f"GST Invoice {invoice.invoice_number} generated successfully.", "success")
        return redirect(url_for('billing.view_invoice', invoice_id=invoice.id))
    except Exception as e:
        flash(f"Error generating invoice: {str(e)}", "danger")
        return redirect(url_for('sales.index'))

@billing_bp.route('/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = GSTInvoice.query.get_or_404(invoice_id)
    return render_template('billing/view.html', invoice=invoice)

@billing_bp.route('/<int:invoice_id>/pdf')
@login_required
def download_pdf(invoice_id):
    invoice = GSTInvoice.query.get_or_404(invoice_id)
    if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
        # Regenerate PDF if not found
        invoice.pdf_path = BillingService.generate_invoice_pdf(invoice)
        from app import db
        db.session.commit()

    return send_file(
        invoice.pdf_path,
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf",
        mimetype='application/pdf'
    )
