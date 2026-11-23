from decimal import Decimal
import pytest
from app.models import RawMaterial
from app.services.inventory_service import InventoryService

def test_inventory_ledger_and_wac(app):
    flour = RawMaterial.query.filter_by(name='Flour').first()
    assert flour is not None

    # Initial opening stock: 100 kg @ ₹42
    initial_stock = InventoryService.get_stock('RAW_MATERIAL', flour.id)
    assert initial_stock == Decimal('100.0000')

    # Update WAC with purchase of 60 kg @ ₹45
    # New WAC = (100 * 42 + 60 * 45) / 160 = 6900 / 160 = 43.125
    new_wac = InventoryService.update_raw_material_wac(flour.id, Decimal('60.0000'), Decimal('45.0000'))
    assert abs(new_wac - Decimal('43.1250')) < Decimal('0.0001')

    # Record purchase movement in ledger
    InventoryService.record_movement('PURCHASE', 'RAW_MATERIAL', flour.id, Decimal('60.0000'), 'kg', Decimal('45.0000'))
    stock_after_purchase = InventoryService.get_stock('RAW_MATERIAL', flour.id)
    assert stock_after_purchase == Decimal('160.0000')

    # Negative stock prevention
    with pytest.raises(ValueError) as exc:
        InventoryService.record_movement('PRODUCTION_ISSUE', 'RAW_MATERIAL', flour.id, Decimal('-200.0000'), 'kg')
    assert "Insufficient stock" in str(exc.value)
