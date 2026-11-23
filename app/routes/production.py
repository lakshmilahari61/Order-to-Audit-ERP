from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Product, BOM, ProductionRun, ProductionMaterialIssue
from app.services.production_service import ProductionService
from app.services.inventory_service import InventoryService
from app.routes.auth import role_required

production_bp = Blueprint('production', __name__, url_prefix='/production')

@production_bp.route('/')
@login_required
def index():
    runs = ProductionRun.query.order_by(ProductionRun.production_date.desc(), ProductionRun.id.desc()).all()
    return render_template('production/list.html', runs=runs)

@production_bp.route('/api/bom-plan/<int:product_id>')
@login_required
def bom_plan(product_id):
    """API endpoint to dynamically fetch BOM requirements for frontend form."""
    batches = Decimal(request.args.get('batches', '1.00'))
    bom = ProductionService.get_bom_details(product_id)
    if not bom:
        return jsonify({'error': 'No active BOM found for this product'}), 404

    plan = ProductionService.calculate_planned_consumption(bom.id, batches)
    items = []
    for item in plan['items']:
        items.append({
            'material_type': item['material_type'],
            'raw_material_id': item['raw_material_id'],
            'packaging_material_id': item['packaging_material_id'],
            'name': item['name'],
            'planned_qty': float(item['planned_qty']),
            'unit': item['unit'],
            'rate': float(item['rate'])
        })

    return jsonify({
        'bom_id': bom.id,
        'batch_size': float(bom.batch_size),
        'expected_yield': float(plan['expected_output']),
        'items': items
    })

@production_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('production', 'admin', 'owner')
def new_run():
    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        bom_id = int(request.form.get('bom_id'))
        batch_number = request.form.get('batch_number').strip()
        prod_date_str = request.form.get('production_date')
        batches = Decimal(request.form.get('batch_quantity', '1.00'))
        
        actual_output = Decimal(request.form.get('actual_good_output', '0.00'))
        damaged_pkg = Decimal(request.form.get('damaged_packaging', '0.00'))
        scrap = Decimal(request.form.get('scrap_wastage', '0.00'))
        labour = Decimal(request.form.get('labour_expense', '0.00'))
        power_gas = Decimal(request.form.get('power_gas_expense', '0.00'))
        notes = request.form.get('notes', '')

        p_date = datetime.strptime(prod_date_str, '%Y-%m-%d').date() if prod_date_str else datetime.utcnow().date()

        # Parse material issues from form
        material_types = request.form.getlist('material_type[]')
        rm_ids = request.form.getlist('raw_material_id[]')
        pkg_ids = request.form.getlist('packaging_material_id[]')
        planned_qtys = request.form.getlist('planned_qty[]')
        actual_qtys = request.form.getlist('actual_qty[]')
        units = request.form.getlist('unit[]')

        issues_data = []
        for m_type, rm_id, pkg_id, p_qty, a_qty, u in zip(material_types, rm_ids, pkg_ids, planned_qtys, actual_qtys, units):
            issues_data.append({
                'material_type': m_type,
                'raw_material_id': int(rm_id) if rm_id and rm_id != 'None' else None,
                'packaging_material_id': int(pkg_id) if pkg_id and pkg_id != 'None' else None,
                'planned_qty': Decimal(p_qty),
                'actual_qty': Decimal(a_qty),
                'unit': u
            })

        try:
            run = ProductionService.execute_production_run(
                product_id=product_id,
                bom_id=bom_id,
                batch_number=batch_number,
                production_date=p_date,
                batch_quantity=batches,
                actual_good_output=actual_output,
                material_issues_data=issues_data,
                damaged_packaging=damaged_pkg,
                scrap_wastage=scrap,
                labour_expense=labour,
                power_gas_expense=power_gas,
                notes=notes,
                user_id=current_user.id
            )
            db.session.commit()
            flash(f"Production Run '{batch_number}' completed successfully. Finished goods increased by {actual_output} units.", "success")
            return redirect(url_for('production.view_run', run_id=run.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error executing production run: {str(e)}", "danger")
            return redirect(url_for('production.new_run'))

    products = Product.query.filter_by(is_active=True).all()
    year = datetime.utcnow().strftime('%Y')
    run_count = ProductionRun.query.count() + 1
    suggested_batch_no = f"BATCH-{year}-{run_count:04d}"
    return render_template(
        'production/new.html',
        products=products,
        suggested_batch_no=suggested_batch_no,
        today_date=datetime.utcnow().strftime('%Y-%m-%d')
    )

@production_bp.route('/<int:run_id>')
@login_required
def view_run(run_id):
    run = ProductionRun.query.get_or_404(run_id)
    return render_template('production/view.html', run=run)

@production_bp.route('/variances')
@login_required
def variances():
    runs = ProductionRun.query.order_by(ProductionRun.production_date.desc()).all()
    issues = ProductionMaterialIssue.query.order_by(ProductionMaterialIssue.id.desc()).all()
    return render_template('production/variance.html', runs=runs, issues=issues)
