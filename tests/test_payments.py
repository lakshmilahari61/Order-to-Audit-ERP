from decimal import Decimal
import pytest
from app.models import Product, Customer
from app.services.sales_service import SalesService
from app.services.billing_service import BillingService
from app.services.payment_service import PaymentService

def test_payments_and_receivables(app):
    product = Product.query.filter_by(sku='MUR-200G').first()
    customer = Customer.query.filter_by(state='Tamil Nadu').first()

    # Create order: 20 packets @ ₹50 = ₹1,000 + 5% GST (₹50) = ₹1,050
    order = SalesService.create_order(
        salesman_id=1,
        customer_id=customer.id,
        items_data=[{'product_id': product.id, 'quantity': Decimal('20.00')}]
    )
    SalesService.approve_order(order.id, user_id=1)
    invoice = BillingService.create_invoice_from_order(order.id, user_id=1)
    assert invoice.total_amount == Decimal('1050.00')

    # Initial outstanding is ₹1,050
    assert invoice.get_outstanding() == Decimal('1050.00')
    assert customer.get_outstanding_balance() == Decimal('1050.00')

    # Case 1: Partial payment of ₹500
    payment1 = PaymentService.record_payment(
        customer_id=customer.id,
        invoice_id=invoice.id,
        payment_date='2026-11-22',
        amount_received=Decimal('500.00'),
        payment_mode='UPI',
        reference_number='UPI-REF-001',
        user_id=1
    )
    assert invoice.status == 'Partial'
    assert invoice.get_outstanding() == Decimal('550.00')
    assert customer.get_outstanding_balance() == Decimal('550.00')

    # Case 2: Overpayment attempt (attempting ₹600 when only ₹550 remains)
    with pytest.raises(ValueError) as exc:
        PaymentService.record_payment(
            customer_id=customer.id,
            invoice_id=invoice.id,
            payment_date='2026-11-22',
            amount_received=Decimal('600.00'),
            user_id=1
        )
    assert "exceeds the invoice outstanding" in str(exc.value)

    # Case 3: Settle the remaining ₹550
    PaymentService.record_payment(
        customer_id=customer.id,
        invoice_id=invoice.id,
        payment_date='2026-11-22',
        amount_received=Decimal('550.00'),
        payment_mode='NEFT/RTGS',
        reference_number='UTR-SETTLE-001',
        user_id=1
    )
    assert invoice.status == 'Paid'
    assert invoice.get_outstanding() == Decimal('0.00')
    assert customer.get_outstanding_balance() == Decimal('0.00')
