from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Purchase, PurchaseItem, Supplier, RawMaterial, PackagingMaterial, AuditLog
from app.services.inventory_service import InventoryService
from app.routes.auth import role_required

purchases_bp = Blueprint('purchases', __name__, url_prefix='/purchases')

@purchases_bp.route('/')
@login_required
def index():
    purchases = Purchase.query.order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).all()
    return render_template('purchases/list.html', purchases=purchases)

@purchases_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner', 'production')
def new_purchase():
    if request.method == 'POST':
        supplier_id = int(request.form.get('supplier_id'))
        invoice_number = request.form.get('invoice_number', '').strip()
        purchase_date_str = request.form.get('purchase_date')
        notes = request.form.get('notes', '')

        p_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else datetime.utcnow().date()

        material_types = request.form.getlist('material_type[]')
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        rates = request.form.getlist('rate[]')
        units = request.form.getlist('unit[]')

        if not item_ids:
            flash("Please add at least one line item.", "danger")
            return redirect(url_for('purchases.new_purchase'))

        purchase = Purchase(
            supplier_id=supplier_id,
            invoice_number=invoice_number,
            purchase_date=p_date,
            notes=notes,
            created_by_id=current_user.id
        )
        db.session.add(purchase)
        db.session.flush()

        grand_total = Decimal('0.00')

        for m_type, i_id, q_str, r_str, u_str in zip(material_types, item_ids, quantities, rates, units):
            if not i_id or not q_str:
                continue

            item_id = int(i_id)
            qty = Decimal(q_str)
            rate = Decimal(r_str)
            line_total = (qty * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            grand_total += line_total

            rm_id = item_id if m_type == 'RAW_MATERIAL' else None
            pkg_id = item_id if m_type == 'PACKAGING' else None

            # 1. Update Weighted Average Cost if Raw Material
            if m_type == 'RAW_MATERIAL':
                InventoryService.update_raw_material_wac(item_id, qty, rate)
            else:
                pm = PackagingMaterial.query.get(item_id)
                if pm:
                    pm.current_rate = rate.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

            # 2. Add Purchase Line Item
            p_item = PurchaseItem(
                purchase_id=purchase.id,
                material_type=m_type,
                raw_material_id=rm_id,
                packaging_material_id=pkg_id,
                quantity=qty,
                unit=u_str,
                unit_rate=rate,
                total_amount=line_total
            )
            db.session.add(p_item)

            # 3. Increase Stock in Inventory Ledger (Inward is positive)
            InventoryService.record_movement(
                transaction_type='PURCHASE',
                item_type=m_type,
                item_id=item_id,
                quantity=qty,
                unit=u_str,
                unit_cost=rate,
                source_doc_type='Purchase',
                source_doc_id=purchase.id,
                notes=f"Purchase Inv #{invoice_number} from {purchase.supplier.name}"
            )

        purchase.total_amount = grand_total

        db.session.add(AuditLog(
            user_id=current_user.id,
            action='RECORD_PURCHASE',
            entity_type='Purchase',
            entity_id=purchase.id,
            details=f"Purchase from {purchase.supplier.name} recorded. Total: ₹{grand_total}"
        ))

        db.session.commit()
        flash(f"Purchase invoice recorded successfully. Inventory updated.", "success")
        return redirect(url_for('purchases.index'))

    suppliers = Supplier.query.filter_by(is_active=True).all()
    raw_materials = RawMaterial.query.filter_by(is_active=True).all()
    packaging_materials = PackagingMaterial.query.filter_by(is_active=True).all()
    return render_template(
        'purchases/new.html',
        suppliers=suppliers,
        raw_materials=raw_materials,
        packaging_materials=packaging_materials,
        today_date=datetime.utcnow().strftime('%Y-%m-%d')
    )
