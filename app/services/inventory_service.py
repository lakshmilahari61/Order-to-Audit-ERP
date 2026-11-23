from decimal import Decimal, ROUND_HALF_UP
from app import db
from app.models import InventoryTransaction, RawMaterial, PackagingMaterial, Product, AuditLog

class InventoryService:
    """
    Central Inventory Ledger Service.
    Enforces the single immutable stock ledger rule:
    Closing stock = Opening + Receipts - Issues - Sales +/- Adjustments.
    Direct balance overwriting is strictly prohibited.
    """

    @staticmethod
    def get_stock(item_type: str, item_id: int) -> Decimal:
        """
        Calculates the real-time stock balance from the ledger.
        Positive quantities = additions (purchases, production output, opening)
        Negative quantities = reductions (production issues, dispatches)
        """
        balance = db.session.query(
            db.func.sum(InventoryTransaction.quantity)
        ).filter(
            InventoryTransaction.item_type == item_type,
            InventoryTransaction.item_id == item_id
        ).scalar()
        
        return Decimal(str(balance or '0.0000')).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    @staticmethod
    def check_stock(item_type: str, item_id: int, required_qty: Decimal):
        """
        Checks if required quantity is available.
        Returns: (is_sufficient: bool, current_stock: Decimal, shortage: Decimal)
        """
        current_stock = InventoryService.get_stock(item_type, item_id)
        required = Decimal(str(required_qty))
        if current_stock >= required:
            return True, current_stock, Decimal('0.00')
        else:
            shortage = required - current_stock
            return False, current_stock, shortage

    @staticmethod
    def record_movement(
        transaction_type: str,
        item_type: str,
        item_id: int,
        quantity: Decimal,
        unit: str,
        unit_cost: Decimal = Decimal('0.0000'),
        source_doc_type: str = None,
        source_doc_id: int = None,
        notes: str = None,
        allow_negative: bool = False
    ) -> InventoryTransaction:
        """
        Appends an immutable movement record to the inventory transaction ledger.
        For reductions, quantity must be negative.
        Validates that stock doesn't go negative unless explicitly authorized.
        """
        qty = Decimal(str(quantity))
        cost = Decimal(str(unit_cost))
        total_cost = (qty.copy_abs() * cost).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        current_balance = InventoryService.get_stock(item_type, item_id)
        new_balance = current_balance + qty

        if not allow_negative and new_balance < Decimal('0.0000'):
            raise ValueError(
                f"Insufficient stock for {item_type} ID {item_id}. "
                f"Current stock: {current_balance} {unit}, attempted deduction: {abs(qty)} {unit}."
            )

        tx = InventoryTransaction(
            transaction_type=transaction_type,
            item_type=item_type,
            item_id=item_id,
            quantity=qty,
            unit=unit,
            unit_cost=cost,
            total_cost=total_cost,
            running_balance=new_balance,
            source_doc_type=source_doc_type,
            source_doc_id=source_doc_id,
            notes=notes
        )
        db.session.add(tx)
        return tx

    @staticmethod
    def update_raw_material_wac(raw_material_id: int, purchase_qty: Decimal, purchase_rate: Decimal):
        """
        Updates the Weighted Average Cost (WAC) for raw materials.
        Formula:
        New WAC = ((Existing Stock * Existing WAC) + (Purchase Qty * Purchase Rate)) / (Existing Stock + Purchase Qty)
        """
        rm = RawMaterial.query.get(raw_material_id)
        if not rm:
            raise ValueError(f"Raw material ID {raw_material_id} not found.")

        current_stock = InventoryService.get_stock('RAW_MATERIAL', raw_material_id)
        # Ensure current stock cannot be treated as negative for valuation
        effective_current_stock = max(current_stock, Decimal('0.0000'))
        current_wac = Decimal(str(rm.current_rate or '0.0000'))
        
        purchased_qty = Decimal(str(purchase_qty))
        purchased_rate = Decimal(str(purchase_rate))

        total_qty = effective_current_stock + purchased_qty
        if total_qty > Decimal('0.0000'):
            new_wac = (
                (effective_current_stock * current_wac) + (purchased_qty * purchased_rate)
            ) / total_qty
            rm.current_rate = new_wac.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        else:
            rm.current_rate = purchased_rate.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

        return rm.current_rate

    @staticmethod
    def get_stock_summary(item_type: str):
        """
        Returns list of items with their calculated current stock and valuation.
        """
        summary = []
        if item_type == 'RAW_MATERIAL':
            items = RawMaterial.query.filter_by(is_active=True).all()
            for item in items:
                stock = InventoryService.get_stock('RAW_MATERIAL', item.id)
                rate = Decimal(str(item.current_rate or '0.0000'))
                val = (stock * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                summary.append({
                    'id': item.id,
                    'name': item.name,
                    'unit': item.unit,
                    'category': item.category,
                    'stock': stock,
                    'rate': rate,
                    'valuation': val,
                    'reorder_level': item.reorder_level,
                    'is_low_stock': stock <= Decimal(str(item.reorder_level or '0.00'))
                })
        elif item_type == 'PACKAGING':
            items = PackagingMaterial.query.filter_by(is_active=True).all()
            for item in items:
                stock = InventoryService.get_stock('PACKAGING', item.id)
                rate = Decimal(str(item.current_rate or '0.0000'))
                val = (stock * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                summary.append({
                    'id': item.id,
                    'name': item.name,
                    'unit': item.unit,
                    'stock': stock,
                    'rate': rate,
                    'valuation': val,
                    'reorder_level': item.reorder_level,
                    'is_low_stock': stock <= Decimal(str(item.reorder_level or '0.00'))
                })
        elif item_type == 'FINISHED_GOOD':
            items = Product.query.filter_by(is_active=True).all()
            for item in items:
                stock = InventoryService.get_stock('FINISHED_GOOD', item.id)
                price = Decimal(str(item.selling_price or '0.00'))
                val = (stock * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                summary.append({
                    'id': item.id,
                    'name': item.name,
                    'sku': item.sku,
                    'pack_size': item.pack_size,
                    'unit': item.unit,
                    'stock': stock,
                    'selling_price': price,
                    'valuation': val
                })
        return summary
