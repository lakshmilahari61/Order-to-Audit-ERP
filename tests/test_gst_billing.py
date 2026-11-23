from decimal import Decimal
from app.models import Product, Customer
from app.services.sales_service import SalesService
from app.services.billing_service import BillingService

def test_gst_calculations_intra_and_inter_state(app):
    product = Product.query.filter_by(sku='MUR-200G').first()
    retailer_tn = Customer.query.filter_by(state='Tamil Nadu').first()
    distributor_ka = Customer.query.filter_by(state='Karnataka').first()

    # Intra-state order (Tamil Nadu -> Tamil Nadu): CGST 2.5% + SGST 2.5%
    order_tn = SalesService.create_order(
        salesman_id=1,
        customer_id=retailer_tn.id,
        items_data=[{'product_id': product.id, 'quantity': Decimal('100.00')}]
    )
    # 100 * 50 = ₹5,000 taxable. CGST = ₹125, SGST = ₹125, Total = ₹5,250
    assert order_tn.total_taxable_amount == Decimal('5000.00')
    assert order_tn.items[0].cgst_amount == Decimal('125.00')
    assert order_tn.items[0].sgst_amount == Decimal('125.00')
    assert order_tn.items[0].igst_amount == Decimal('0.00')
    assert order_tn.total_order_amount == Decimal('5250.00')

    # Inter-state order (Tamil Nadu -> Karnataka): IGST 5.0%
    order_ka = SalesService.create_order(
        salesman_id=1,
        customer_id=distributor_ka.id,
        items_data=[{'product_id': product.id, 'quantity': Decimal('100.00')}]
    )
    # 100 * 50 = ₹5,000 taxable. IGST = ₹250, Total = ₹5,250
    assert order_ka.total_taxable_amount == Decimal('5000.00')
    assert order_ka.items[0].cgst_amount == Decimal('0.00')
    assert order_ka.items[0].sgst_amount == Decimal('0.00')
    assert order_ka.items[0].igst_amount == Decimal('250.00')
    assert order_ka.total_order_amount == Decimal('5250.00')
