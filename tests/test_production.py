from decimal import Decimal
from app.models import Product, BOM, RawMaterial, PackagingMaterial, ProductionRun
from app.services.production_service import ProductionService
from app.services.inventory_service import InventoryService

def test_production_variance_and_costing(app):
    product = Product.query.filter_by(sku='MUR-200G').first()
    bom = BOM.query.filter_by(product_id=product.id).first()
    flour = RawMaterial.query.filter_by(name='Flour').first()
    oil = RawMaterial.query.filter_by(name='Cooking oil').first()
    spice = RawMaterial.query.filter_by(name='Salt and spice mix').first()
    pouch = PackagingMaterial.query.filter_by(name='200 g pouch').first()
    carton = PackagingMaterial.query.filter_by(name='Carton').first()

    # Initial pouch stock is 500, carton stock is 30, FG stock is 50
    initial_pouch = InventoryService.get_stock('PACKAGING', pouch.id)
    assert initial_pouch == Decimal('500.0000')

    # Step 1: Record purchase of 60 kg flour @ ₹45 to update WAC to ₹43.125
    InventoryService.update_raw_material_wac(flour.id, Decimal('60.0000'), Decimal('45.0000'))
    InventoryService.record_movement('PURCHASE', 'RAW_MATERIAL', flour.id, Decimal('60.0000'), 'kg', Decimal('45.0000'))

    # Planned batch requirement test
    plan = ProductionService.calculate_planned_consumption(bom.id, Decimal('1.00'))
    assert plan['expected_output'] == Decimal('200.00')

    # Execute a run with 188 actual output (Yield var: -6%)
    # Oil issued: 10.5 L (Planned: 10 L -> Var: +5%)
    # Pouches issued: 188 good + 6 damaged = 194
    # Cartons issued: 9
    issues = [
        {'material_type': 'RAW_MATERIAL', 'raw_material_id': flour.id, 'planned_qty': Decimal('40.0000'), 'actual_qty': Decimal('40.0000'), 'unit': 'kg'},
        {'material_type': 'RAW_MATERIAL', 'raw_material_id': oil.id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('10.5000'), 'unit': 'litre'},
        {'material_type': 'RAW_MATERIAL', 'raw_material_id': spice.id, 'planned_qty': Decimal('1.2000'), 'actual_qty': Decimal('1.2000'), 'unit': 'kg'},
        {'material_type': 'PACKAGING', 'packaging_material_id': pouch.id, 'planned_qty': Decimal('200.0000'), 'actual_qty': Decimal('194.0000'), 'unit': 'pieces'},
        {'material_type': 'PACKAGING', 'packaging_material_id': carton.id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('9.0000'), 'unit': 'pieces'}
    ]

    run = ProductionService.execute_production_run(
        product_id=product.id,
        bom_id=bom.id,
        batch_number='BATCH-TEST-001',
        production_date='2026-11-22',
        batch_quantity=Decimal('1.00'),
        actual_good_output=Decimal('188.00'),
        material_issues_data=issues,
        damaged_packaging=Decimal('6.00'),
        labour_expense=Decimal('1200.00'),
        power_gas_expense=Decimal('600.00'),
        user_id=1
    )

    # Yield variance must be exactly -6.00%
    assert run.yield_variance_pct == Decimal('-6.00')

    # Finished goods must increase by 188 (50 initial + 188 = 238)
    fg_stock = InventoryService.get_stock('FINISHED_GOOD', product.id)
    assert fg_stock == Decimal('238.0000')

    # Pouch closing stock must be 500 - 194 = 306
    pouch_stock = InventoryService.get_stock('PACKAGING', pouch.id)
    assert pouch_stock == Decimal('306.0000')

    # Carton closing stock must be 30 - 9 = 21
    carton_stock = InventoryService.get_stock('PACKAGING', carton.id)
    assert carton_stock == Decimal('21.0000')

    # Unit cost per packet assertion
    assert run.cost_per_packet > Decimal('30.00')
    assert abs(run.cost_per_packet - Decimal('31.14')) < Decimal('0.05')
