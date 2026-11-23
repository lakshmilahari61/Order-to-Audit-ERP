from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Payment, GSTInvoice, Customer
from app.services.payment_service import PaymentService
from app.routes.auth import role_required

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
@login_required
def index():
    payments = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()
    receivables_summary = PaymentService.get_customer_receivables_summary()
    return render_template('payments/list.html', payments=payments, receivables_summary=receivables_summary)

@payments_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner')
def new_payment():
    if request.method == 'POST':
        customer_id = int(request.form.get('customer_id'))
        invoice_id = request.form.get('invoice_id')
        invoice_id = int(invoice_id) if invoice_id and invoice_id != 'None' else None
        amount_received = Decimal(request.form.get('amount_received', '0.00'))
        payment_date_str = request.form.get('payment_date')
        payment_mode = request.form.get('payment_mode', 'NEFT/RTGS')
        reference_number = request.form.get('reference_number', '').strip()
        notes = request.form.get('notes', '')

        p_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else datetime.utcnow().date()

        try:
            payment = PaymentService.record_payment(
                customer_id=customer_id,
                invoice_id=invoice_id,
                payment_date=p_date,
                amount_received=amount_received,
                payment_mode=payment_mode,
                reference_number=reference_number,
                notes=notes,
                user_id=current_user.id
            )
            flash(f"Payment of ₹{amount_received:,.2f} recorded successfully.", "success")
            return redirect(url_for('payments.index'))
        except ValueError as ve:
            flash(str(ve), "danger")
            return redirect(url_for('payments.new_payment'))
        except Exception as e:
            flash(f"Error recording payment: {str(e)}", "danger")
            return redirect(url_for('payments.new_payment'))

    customers = Customer.query.filter_by(is_active=True).all()
    invoices = GSTInvoice.query.filter(GSTInvoice.status.in_(['Issued', 'Partial'])).all()
    # Compute outstanding for display
    invoice_list = []
    for inv in invoices:
        out = inv.get_outstanding()
        if out > Decimal('0.00'):
            invoice_list.append({
                'id': inv.id,
                'number': inv.invoice_number,
                'customer_name': inv.customer_name,
                'customer_id': inv.customer_id,
                'total': inv.total_amount,
                'outstanding': out
            })

    return render_template(
        'payments/new.html',
        customers=customers,
        invoices=invoice_list,
        today_date=datetime.utcnow().strftime('%Y-%m-%d')
    )
