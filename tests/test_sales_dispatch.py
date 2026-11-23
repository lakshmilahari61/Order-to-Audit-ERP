from decimal import Decimal
import pytest
from app.models import Product, Customer, SalesOrder, GSTInvoice, DispatchRecord
from app.services.sales_service import SalesService
from app.services.billing_service import BillingService
from app.services.inventory_service import InventoryService

def test_sales_dispatch_and_shortage(app):
    product = Product.query.filter_by(sku='MUR-200G').first()
    customer = Customer.query.filter_by(state='Tamil Nadu').first()

    # Initial stock in seeded DB is 50 packets
    initial_stock = InventoryService.get_stock('FINISHED_GOOD', product.id)
    assert initial_stock == Decimal('50.0000')

    # Case 1: Order within stock (30 packets)
    order_ok = SalesService.create_order(
        salesman_id=1,
        customer_id=customer.id,
        items_data=[{'product_id': product.id, 'quantity': Decimal('30.00')}]
    )
    assert order_ok.status == 'Submitted'
    assert order_ok.shortage_quantity == Decimal('0.00')

    # Approve and invoice
    SalesService.approve_order(order_ok.id, user_id=1)
    assert order_ok.status == 'Approved'
    invoice = BillingService.create_invoice_from_order(order_ok.id, user_id=1)
    assert invoice.status == 'Issued'

    # Dispatch 30 packets -> stock decreases to 20
    InventoryService.record_movement('DISPATCH', 'FINISHED_GOOD', product.id, Decimal('-30.0000'), 'packets')
    new_stock = InventoryService.get_stock('FINISHED_GOOD', product.id)
    assert new_stock == Decimal('20.0000')

    # Case 2: Order exceeding available stock (Attempt to order 50 packets when only 20 available)
    order_excess = SalesService.create_order(
        salesman_id=1,
        customer_id=customer.id,
        items_data=[{'product_id': product.id, 'quantity': Decimal('50.00')}]
    )
    # Shortage should be 50 - 20 = 30 packets
    assert order_excess.shortage_quantity == Decimal('30.00')

    # Attempt to approve must raise ValueError and block
    with pytest.raises(ValueError) as exc:
        SalesService.approve_order(order_excess.id, user_id=1)
    assert "Stock shortage" in str(exc.value)
