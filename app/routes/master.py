from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Product, Customer, Supplier, RawMaterial, PackagingMaterial, BOM, BOMItem, AuditLog
from app.routes.auth import role_required

master_bp = Blueprint('master', __name__, url_prefix='/master')

# ----------------- PRODUCTS -----------------
@master_bp.route('/products', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner')
def products():
    if request.method == 'POST':
        name = request.form.get('name')
        sku = request.form.get('sku')
        category = request.form.get('category', 'Snacks')
        pack_size = request.form.get('pack_size', '200g')
        selling_price = Decimal(request.form.get('selling_price', '50.00'))
        gst_rate = Decimal(request.form.get('gst_rate', '5.00'))
        hsn_code = request.form.get('hsn_code', '21069099')

        prod = Product(
            name=name, sku=sku, category=category, pack_size=pack_size,
            selling_price=selling_price, gst_rate=gst_rate, hsn_code=hsn_code
        )
        db.session.add(prod)
        db.session.commit()
        flash(f"Product '{name}' created successfully.", "success")
        return redirect(url_for('master.products'))

    items = Product.query.order_by(Product.id.asc()).all()
    return render_template('master/products.html', products=items)

# ----------------- CUSTOMERS -----------------
@master_bp.route('/customers', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner', 'salesman')
def customers():
    if request.method == 'POST':
        name = request.form.get('name')
        customer_type = request.form.get('customer_type', 'Retailer')
        state = request.form.get('state', 'Tamil Nadu')
        gstin = request.form.get('gstin', '')
        billing_address = request.form.get('billing_address', '')
        contact_number = request.form.get('contact_number', '')

        cust = Customer(
            name=name, customer_type=customer_type, state=state,
            gstin=gstin, billing_address=billing_address, contact_number=contact_number
        )
        db.session.add(cust)
        db.session.commit()
        flash(f"Customer '{name}' added successfully.", "success")
        return redirect(url_for('master.customers'))

    items = Customer.query.order_by(Customer.id.asc()).all()
    return render_template('master/customers.html', customers=items)

# ----------------- SUPPLIERS -----------------
@master_bp.route('/suppliers', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner', 'production')
def suppliers():
    if request.method == 'POST':
        name = request.form.get('name')
        contact_details = request.form.get('contact_details', '')
        gstin = request.form.get('gstin', '')
        state = request.form.get('state', 'Tamil Nadu')
        address = request.form.get('address', '')

        supp = Supplier(name=name, contact_details=contact_details, gstin=gstin, state=state, address=address)
        db.session.add(supp)
        db.session.commit()
        flash(f"Supplier '{name}' added successfully.", "success")
        return redirect(url_for('master.suppliers'))

    items = Supplier.query.order_by(Supplier.id.asc()).all()
    return render_template('master/suppliers.html', suppliers=items)

# ----------------- RAW MATERIALS -----------------
@master_bp.route('/raw-materials', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner', 'production')
def raw_materials():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category', 'Grain / Flour')
        unit = request.form.get('unit', 'kg')
        current_rate = Decimal(request.form.get('current_rate', '0.00'))
        reorder_level = Decimal(request.form.get('reorder_level', '10.00'))

        rm = RawMaterial(name=name, category=category, unit=unit, current_rate=current_rate, reorder_level=reorder_level)
        db.session.add(rm)
        db.session.commit()
        flash(f"Raw Material '{name}' created successfully.", "success")
        return redirect(url_for('master.raw_materials'))

    items = RawMaterial.query.order_by(RawMaterial.id.asc()).all()
    return render_template('master/raw_materials.html', raw_materials=items)

# ----------------- PACKAGING MATERIALS -----------------
@master_bp.route('/packaging', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner', 'production')
def packaging():
    if request.method == 'POST':
        name = request.form.get('name')
        unit = request.form.get('unit', 'pieces')
        current_rate = Decimal(request.form.get('current_rate', '0.00'))
        reorder_level = Decimal(request.form.get('reorder_level', '50.00'))

        pm = PackagingMaterial(name=name, unit=unit, current_rate=current_rate, reorder_level=reorder_level)
        db.session.add(pm)
        db.session.commit()
        flash(f"Packaging Material '{name}' created successfully.", "success")
        return redirect(url_for('master.packaging'))

    items = PackagingMaterial.query.order_by(PackagingMaterial.id.asc()).all()
    return render_template('master/packaging.html', packaging_materials=items)

# ----------------- BILL OF MATERIALS (BOM) -----------------
@master_bp.route('/boms')
@login_required
def boms():
    items = BOM.query.order_by(BOM.id.asc()).all()
    products = Product.query.filter_by(is_active=True).all()
    raw_materials = RawMaterial.query.filter_by(is_active=True).all()
    packaging_materials = PackagingMaterial.query.filter_by(is_active=True).all()
    return render_template(
        'master/boms.html',
        boms=items,
        products=products,
        raw_materials=raw_materials,
        packaging_materials=packaging_materials
    )

@master_bp.route('/boms/new', methods=['POST'])
@login_required
@role_required('admin', 'owner', 'production')
def create_bom():
    product_id = int(request.form.get('product_id'))
    batch_size = Decimal(request.form.get('batch_size', '1.00'))
    expected_yield = Decimal(request.form.get('expected_yield', '200.00'))
    notes = request.form.get('notes', '')

    bom = BOM(
        product_id=product_id,
        batch_size=batch_size,
        expected_yield=expected_yield,
        notes=notes
    )
    db.session.add(bom)
    db.session.flush()

    # Process items
    material_types = request.form.getlist('item_material_type[]')
    item_ids = request.form.getlist('item_id[]')
    standard_qtys = request.form.getlist('item_qty[]')
    units = request.form.getlist('item_unit[]')

    for m_type, i_id, qty, unit in zip(material_types, item_ids, standard_qtys, units):
        if not i_id or not qty:
            continue
        bom_item = BOMItem(
            bom_id=bom.id,
            material_type=m_type,
            raw_material_id=int(i_id) if m_type == 'RAW_MATERIAL' else None,
            packaging_material_id=int(i_id) if m_type == 'PACKAGING' else None,
            standard_qty=Decimal(qty),
            unit=unit
        )
        db.session.add(bom_item)

    db.session.commit()
    flash("New Bill of Materials created successfully.", "success")
    return redirect(url_for('master.boms'))
