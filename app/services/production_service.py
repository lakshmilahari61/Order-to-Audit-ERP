from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app import db
from app.models import (
    BOM, BOMItem, Product, RawMaterial, PackagingMaterial,
    ProductionRun, ProductionMaterialIssue, ProductionOutput,
    ExpenseOverhead, AuditLog
)
from app.services.inventory_service import InventoryService

class ProductionService:
    """
    BOM-based Production & Variance Service.
    Handles material issuance, actual good output, damaged packaging,
    scrap/wastage, overhead costing, and variance calculations.
    """

    @staticmethod
    def get_bom_details(product_id: int):
        """Fetches active BOM for a product with its component items."""
        return BOM.query.filter_by(product_id=product_id, is_active=True).first()

    @staticmethod
    def calculate_planned_consumption(bom_id: int, batch_quantity: Decimal):
        """
        Calculates standard planned requirement for each ingredient and packaging item.
        """
        bom = BOM.query.get(bom_id)
        if not bom:
            raise ValueError(f"BOM ID {bom_id} not found.")

        planned_items = []
        batches = Decimal(str(batch_quantity))
        expected_output = (Decimal(str(bom.expected_yield)) * batches).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        for item in bom.items:
            std_qty = Decimal(str(item.standard_qty))
            planned_qty = (std_qty * batches).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
            rate = Decimal('0.0000')
            if item.material_type == 'RAW_MATERIAL' and item.raw_material:
                rate = Decimal(str(item.raw_material.current_rate or '0.0000'))
            elif item.material_type == 'PACKAGING' and item.packaging_material:
                rate = Decimal(str(item.packaging_material.current_rate or '0.0000'))

            planned_items.append({
                'material_type': item.material_type,
                'raw_material_id': item.raw_material_id,
                'packaging_material_id': item.packaging_material_id,
                'name': item.item_name,
                'standard_qty': std_qty,
                'planned_qty': planned_qty,
                'unit': item.unit,
                'rate': rate
            })

        return {
            'bom': bom,
            'expected_output': expected_output,
            'items': planned_items
        }

    @staticmethod
    def execute_production_run(
        product_id: int,
        bom_id: int,
        batch_number: str,
        production_date,
        batch_quantity: Decimal,
        actual_good_output: Decimal,
        material_issues_data: list,
        damaged_packaging: Decimal = Decimal('0.00'),
        scrap_wastage: Decimal = Decimal('0.00'),
        labour_expense: Decimal = Decimal('0.00'),
        power_gas_expense: Decimal = Decimal('0.00'),
        other_overhead: Decimal = Decimal('0.00'),
        notes: str = None,
        user_id: int = None
    ) -> ProductionRun:
        """
        Atomically executes a production run:
        1. Validates BOM and inputs.
        2. Deducts raw materials and packaging from inventory ledger.
        3. Adds finished goods output to inventory ledger.
        4. Calculates Material and Yield variances against standard tolerance (3%).
        5. Computes total cost and cost per packet.
        6. Logs audit trail and overhead expenses.
        """
        bom = BOM.query.get(bom_id)
        if not bom:
            raise ValueError(f"BOM ID {bom_id} not found.")

        batches = Decimal(str(batch_quantity))
        expected_output = (Decimal(str(bom.expected_yield)) * batches).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        actual_output = Decimal(str(actual_good_output))

        # 1. Yield Variance: ((Actual - Expected) / Expected) * 100
        if expected_output > Decimal('0.00'):
            yield_variance_pct = (((actual_output - expected_output) / expected_output) * Decimal('100.00')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:
            yield_variance_pct = Decimal('0.00')

        # Create ProductionRun instance
        run = ProductionRun(
            product_id=product_id,
            bom_id=bom_id,
            batch_number=batch_number,
            production_date=production_date if isinstance(production_date, datetime) else datetime.strptime(str(production_date), '%Y-%m-%d').date(),
            batch_quantity=batches,
            expected_output=expected_output,
            actual_good_output=actual_output,
            damaged_packaging=Decimal(str(damaged_packaging)),
            scrap_wastage=Decimal(str(scrap_wastage)),
            labour_expense=Decimal(str(labour_expense)),
            power_gas_expense=Decimal(str(power_gas_expense)),
            other_overhead=Decimal(str(other_overhead)),
            yield_variance_pct=yield_variance_pct,
            notes=notes,
            status='Completed',
            created_by_id=user_id
        )
        db.session.add(run)
        db.session.flush() # Populate run.id

        total_rm_cost = Decimal('0.00')
        total_pkg_cost = Decimal('0.00')

        # 2. Process material issues
        for m_data in material_issues_data:
            m_type = m_data['material_type']
            rm_id = m_data.get('raw_material_id')
            pkg_id = m_data.get('packaging_material_id')
            planned_qty = Decimal(str(m_data['planned_qty']))
            actual_qty = Decimal(str(m_data['actual_qty']))
            unit = m_data['unit']
            
            # Fetch current rate for valuation
            if m_type == 'RAW_MATERIAL':
                rm = RawMaterial.query.get(rm_id)
                rate = Decimal(str(rm.current_rate or '0.0000'))
            else:
                pm = PackagingMaterial.query.get(pkg_id)
                rate = Decimal(str(pm.current_rate or '0.0000'))

            # Material variance %: ((Actual - Planned) / Planned) * 100
            if planned_qty > Decimal('0.0000'):
                mat_var_pct = (((actual_qty - planned_qty) / planned_qty) * Decimal('100.00')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            else:
                mat_var_pct = Decimal('0.00')

            issue_cost = (actual_qty * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            if m_type == 'RAW_MATERIAL':
                total_rm_cost += issue_cost
                item_id = rm_id
            else:
                total_pkg_cost += issue_cost
                item_id = pkg_id

            # Save issue record
            issue = ProductionMaterialIssue(
                production_run_id=run.id,
                material_type=m_type,
                raw_material_id=rm_id,
                packaging_material_id=pkg_id,
                planned_qty=planned_qty,
                actual_qty=actual_qty,
                unit=unit,
                unit_rate=rate,
                total_cost=issue_cost,
                variance_pct=mat_var_pct
            )
            db.session.add(issue)

            # Deduct from Inventory Ledger (outward movement is negative)
            InventoryService.record_movement(
                transaction_type='PRODUCTION_ISSUE',
                item_type=m_type,
                item_id=item_id,
                quantity=-actual_qty,
                unit=unit,
                unit_cost=rate,
                source_doc_type='ProductionRun',
                source_doc_id=run.id,
                notes=f"Batch {batch_number} issue"
            )

        # 3. Increase Finished Goods stock in Inventory Ledger
        product = Product.query.get(product_id)
        InventoryService.record_movement(
            transaction_type='PRODUCTION_OUTPUT',
            item_type='FINISHED_GOOD',
            item_id=product_id,
            quantity=actual_output,
            unit=product.unit if product else 'packets',
            unit_cost=Decimal('0.0000'), # Will update with cost_per_packet
            source_doc_type='ProductionRun',
            source_doc_id=run.id,
            notes=f"Batch {batch_number} good output"
        )

        # 4. Save Production Output details
        out = ProductionOutput(
            production_run_id=run.id,
            product_id=product_id,
            good_quantity=actual_output,
            damaged_quantity=Decimal(str(damaged_packaging)),
            scrap_quantity=Decimal(str(scrap_wastage))
        )
        db.session.add(out)

        # 5. Calculate Costing
        total_prod_cost = (
            total_rm_cost + total_pkg_cost +
            Decimal(str(labour_expense)) +
            Decimal(str(power_gas_expense)) +
            Decimal(str(other_overhead))
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if actual_output > Decimal('0.00'):
            cost_per_pkt = (total_prod_cost / actual_output).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        else:
            cost_per_pkt = Decimal('0.0000')

        run.total_material_cost = total_rm_cost
        run.total_packaging_cost = total_pkg_cost
        run.total_production_cost = total_prod_cost
        run.cost_per_packet = cost_per_pkt

        # 6. Overhead breakdown records
        if labour_expense > Decimal('0.00'):
            db.session.add(ExpenseOverhead(
                production_run_id=run.id,
                category='Labour',
                amount=Decimal(str(labour_expense)),
                description=f"Batch {batch_number} labour charges"
            ))
        if power_gas_expense > Decimal('0.00'):
            db.session.add(ExpenseOverhead(
                production_run_id=run.id,
                category='Power/Gas',
                amount=Decimal(str(power_gas_expense)),
                description=f"Batch {batch_number} gas & electricity"
            ))

        # 7. Audit Log
        db.session.add(AuditLog(
            user_id=user_id,
            action='EXECUTE_PRODUCTION_RUN',
            entity_type='ProductionRun',
            entity_id=run.id,
            details=f"Batch {batch_number}: Expected {expected_output}, Produced {actual_output}, Yield Var: {yield_variance_pct}%, Cost/pkt: ₹{cost_per_pkt}"
        ))

        return run
