from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app import db
from app.models import Payment, GSTInvoice, Customer, AuditLog

class PaymentService:
    """
    Payments and Customer Receivables Service.
    Enforces that payments cannot exceed the outstanding invoice balance,
    calculates aging, and updates invoice payment status.
    """

    @staticmethod
    def record_payment(
        customer_id: int,
        invoice_id: int,
        payment_date,
        amount_received: Decimal,
        payment_mode: str = 'NEFT/RTGS',
        reference_number: str = None,
        notes: str = None,
        user_id: int = None
    ) -> Payment:
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"Customer ID {customer_id} not found.")

        amt = Decimal(str(amount_received)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amt <= Decimal('0.00'):
            raise ValueError("Payment amount must be greater than zero.")

        invoice = None
        if invoice_id:
            invoice = GSTInvoice.query.get(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice ID {invoice_id} not found.")
            
            outstanding = invoice.get_outstanding()
            if amt > outstanding:
                raise ValueError(
                    f"Payment amount (₹{amt}) exceeds the invoice outstanding balance (₹{outstanding})."
                )

        p_date = payment_date if isinstance(payment_date, datetime) else datetime.strptime(str(payment_date), '%Y-%m-%d').date()

        payment = Payment(
            customer_id=customer_id,
            invoice_id=invoice_id,
            invoice=invoice,
            payment_date=p_date,
            amount_received=amt,
            payment_mode=payment_mode,
            reference_number=reference_number,
            notes=notes,
            created_by_id=user_id
        )
        db.session.add(payment)
        db.session.flush()

        # Update invoice status
        if invoice:
            remaining = (outstanding - amt).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if remaining <= Decimal('0.00'):
                invoice.status = 'Paid'
            else:
                invoice.status = 'Partial'

        db.session.add(AuditLog(
            user_id=user_id,
            action='RECORD_PAYMENT',
            entity_type='Payment',
            entity_id=payment.id,
            details=f"Payment of ₹{amt} received from {customer.name} for Invoice {invoice.invoice_number if invoice else 'Account'}. Ref: {reference_number}"
        ))

        db.session.commit()
        return payment

    @staticmethod
    def get_customer_receivables_summary():
        """
        Calculates customer-wise invoiced, collected, and outstanding balances.
        """
        customers = Customer.query.filter_by(is_active=True).all()
        summary = []
        for cust in customers:
            invoiced = cust.get_total_invoiced()
            paid = cust.get_total_paid()
            outstanding = invoiced - paid
            summary.append({
                'customer_id': cust.id,
                'customer_name': cust.name,
                'customer_type': cust.customer_type,
                'state': cust.state,
                'invoiced': invoiced,
                'paid': paid,
                'outstanding': outstanding
            })
        return summary
