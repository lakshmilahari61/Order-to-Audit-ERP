from decimal import Decimal
from app import db
from app.models import Product, RawMaterial, PackagingMaterial, ProductionRun, ProductionMaterialIssue, GSTInvoice, Customer, SalesOrder
from app.services.inventory_service import InventoryService
from app.routes.benchmark import execute_nit_benchmark

def test_benchmark_scenario_end_to_end(app):
    """
    Automated assertion of the complete NIT Trichy Winter Internship 2026 benchmark.
    """
    execute_nit_benchmark()

    flour = RawMaterial.query.filter_by(name='Flour').first()
    oil = RawMaterial.query.filter_by(name='Cooking oil').first()
    pouch = PackagingMaterial.query.filter_by(name='200 g pouch').first()
    carton = PackagingMaterial.query.filter_by(name='Carton').first()
    product = Product.query.filter_by(sku='MUR-200G').first()

    # 1. Stock assertions
    flour_stock = InventoryService.get_stock('RAW_MATERIAL', flour.id)
    assert abs(flour_stock - Decimal('120.00')) < Decimal('0.01'), f"Flour stock mismatch: {flour_stock}"

    oil_stock = InventoryService.get_stock('RAW_MATERIAL', oil.id)
    assert abs(oil_stock - Decimal('19.50')) < Decimal('0.01'), f"Oil stock mismatch: {oil_stock}"

    pouch_stock = InventoryService.get_stock('PACKAGING', pouch.id)
    assert abs(pouch_stock - Decimal('306.00')) < Decimal('0.01'), f"Pouch stock mismatch: {pouch_stock}"

    carton_stock = InventoryService.get_stock('PACKAGING', carton.id)
    assert abs(carton_stock - Decimal('21.00')) < Decimal('0.01'), f"Carton stock mismatch: {carton_stock}"

    fg_stock = InventoryService.get_stock('FINISHED_GOOD', product.id)
    assert abs(fg_stock - Decimal('88.00')) < Decimal('0.01'), f"Finished goods stock mismatch: {fg_stock}"

    # 2. Production variance assertions
    prod_run = ProductionRun.query.filter_by(batch_number='BATCH-BM-2026-01').first()
    assert prod_run is not None
    assert abs(prod_run.yield_variance_pct - Decimal('-6.00')) < Decimal('0.01')

    oil_issue = ProductionMaterialIssue.query.filter_by(production_run_id=prod_run.id, raw_material_id=oil.id).first()
    assert oil_issue is not None
    assert abs(oil_issue.variance_pct - Decimal('5.00')) < Decimal('0.01')

    # 3. Costing assertions
    assert abs(prod_run.cost_per_packet - Decimal('31.14')) < Decimal('0.05')

    # 4. Invoicing assertions (Retailer A in Tamil Nadu - Intra-state 5% GST = 2.5% CGST + 2.5% SGST)
    retailer = Customer.query.filter_by(name='Retailer A (Chennai Stores)').first()
    inv_a = GSTInvoice.query.filter_by(customer_id=retailer.id).first()
    assert inv_a is not None
    assert abs(inv_a.taxable_amount - Decimal('7500.00')) < Decimal('0.01')
    assert abs(inv_a.cgst_amount - Decimal('187.50')) < Decimal('0.01')
    assert abs(inv_a.sgst_amount - Decimal('187.50')) < Decimal('0.01')
    assert abs(inv_a.total_amount - Decimal('7875.00')) < Decimal('0.01')

    # 5. Receivables assertion
    assert abs(retailer.get_outstanding_balance() - Decimal('3875.00')) < Decimal('0.01')

    # 6. Distributor B shortage assertion
    distributor = Customer.query.filter_by(name='Distributor B (Bangalore Traders)').first()
    order_b = SalesOrder.query.filter_by(customer_id=distributor.id).first()
    assert order_b is not None
    assert abs(order_b.shortage_quantity - Decimal('32.00')) < Decimal('0.01')
