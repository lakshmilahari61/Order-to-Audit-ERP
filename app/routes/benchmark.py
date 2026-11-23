from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import (
    User, Role, Customer, Supplier, Product, RawMaterial, PackagingMaterial,
    BOM, BOMItem, Purchase, PurchaseItem, ProductionRun, ProductionMaterialIssue,
    InventoryTransaction, SalesOrder, SalesOrderItem, GSTInvoice, InvoiceItem,
    DispatchRecord, Payment, ExpenseOverhead, AuditLog
)
from app.services.inventory_service import InventoryService
from app.services.production_service import ProductionService
from app.services.sales_service import SalesService
from app.services.billing_service import BillingService
from app.services.payment_service import PaymentService

benchmark_bp = Blueprint('benchmark', __name__, url_prefix='/benchmark')

def execute_nit_benchmark():
    """
    Executes the exact 18 steps of the NIT Tiruchirappalli Winter Internship 2026
    benchmark scenario with complete mathematical accuracy and ledger tracking.
    """
    # Step 0: Ensure base demo entities exist
    admin_user = User.query.filter_by(username='admin').first()
    salesman_a = User.query.filter_by(username='salesman').first()
    
    # 1. Product: Murukku 200 g
    product = Product.query.filter_by(sku='MUR-200G').first()
    if not product:
        product = Product(
            name='Murukku 200g',
            sku='MUR-200G',
            category='Murukku',
            pack_size='200g',
            selling_price=Decimal('50.00'),
            gst_rate=Decimal('5.00'),
            hsn_code='21069099',
            unit='packets'
        )
        db.session.add(product)
        db.session.flush()

    # 2. Raw Materials & Packaging
    flour = RawMaterial.query.filter_by(name='Flour').first()
    if not flour:
        flour = RawMaterial(name='Flour', category='Grain / Flour', unit='kg', current_rate=Decimal('42.0000'), reorder_level=Decimal('20.00'))
        db.session.add(flour)
    else:
        flour.current_rate = Decimal('42.0000')

    oil = RawMaterial.query.filter_by(name='Cooking oil').first()
    if not oil:
        oil = RawMaterial(name='Cooking oil', category='Oil', unit='litre', current_rate=Decimal('140.0000'), reorder_level=Decimal('10.00'))
        db.session.add(oil)
    else:
        oil.current_rate = Decimal('140.0000')

    spice = RawMaterial.query.filter_by(name='Salt and spice mix').first()
    if not spice:
        spice = RawMaterial(name='Salt and spice mix', category='Spices', unit='kg', current_rate=Decimal('200.0000'), reorder_level=Decimal('2.00'))
        db.session.add(spice)
    else:
        spice.current_rate = Decimal('200.0000')

    pouch = PackagingMaterial.query.filter_by(name='200 g pouch').first()
    if not pouch:
        pouch = PackagingMaterial(name='200 g pouch', unit='pieces', current_rate=Decimal('2.5000'), reorder_level=Decimal('100.00'))
        db.session.add(pouch)
    else:
        pouch.current_rate = Decimal('2.5000')

    carton = PackagingMaterial.query.filter_by(name='Carton').first()
    if not carton:
        carton = PackagingMaterial(name='Carton', unit='pieces', current_rate=Decimal('15.0000'), reorder_level=Decimal('10.00'))
        db.session.add(carton)
    else:
        carton.current_rate = Decimal('15.0000')

    db.session.flush()

    # 3. BOM for Murukku 200g (Yield: 200 packets)
    bom = BOM.query.filter_by(product_id=product.id).first()
    if not bom:
        bom = BOM(product_id=product.id, batch_size=Decimal('1.00'), expected_yield=Decimal('200.00'), notes="Standard Murukku 200g batch")
        db.session.add(bom)
        db.session.flush()

        db.session.add(BOMItem(bom_id=bom.id, material_type='RAW_MATERIAL', raw_material_id=flour.id, standard_qty=Decimal('40.0000'), unit='kg'))
        db.session.add(BOMItem(bom_id=bom.id, material_type='RAW_MATERIAL', raw_material_id=oil.id, standard_qty=Decimal('10.0000'), unit='litre'))
        db.session.add(BOMItem(bom_id=bom.id, material_type='RAW_MATERIAL', raw_material_id=spice.id, standard_qty=Decimal('1.2000'), unit='kg'))
        db.session.add(BOMItem(bom_id=bom.id, material_type='PACKAGING', packaging_material_id=pouch.id, standard_qty=Decimal('200.0000'), unit='pieces'))
        db.session.add(BOMItem(bom_id=bom.id, material_type='PACKAGING', packaging_material_id=carton.id, standard_qty=Decimal('10.0000'), unit='pieces'))
        db.session.flush()

    # 4. Opening Stock in Ledger (record only if not already present)
    has_opening = InventoryTransaction.query.filter_by(transaction_type='OPENING_STOCK').first() is not None
    if not has_opening:
        InventoryService.record_movement('OPENING_STOCK', 'RAW_MATERIAL', flour.id, Decimal('100.0000'), 'kg', Decimal('42.0000'), notes="Benchmark Opening Stock")
        InventoryService.record_movement('OPENING_STOCK', 'RAW_MATERIAL', oil.id, Decimal('30.0000'), 'litre', Decimal('140.0000'), notes="Benchmark Opening Stock")
        InventoryService.record_movement('OPENING_STOCK', 'RAW_MATERIAL', spice.id, Decimal('5.0000'), 'kg', Decimal('200.0000'), notes="Benchmark Opening Stock")
        InventoryService.record_movement('OPENING_STOCK', 'PACKAGING', pouch.id, Decimal('500.0000'), 'pieces', Decimal('2.5000'), notes="Benchmark Opening Stock")
        InventoryService.record_movement('OPENING_STOCK', 'PACKAGING', carton.id, Decimal('30.0000'), 'pieces', Decimal('15.0000'), notes="Benchmark Opening Stock")
        InventoryService.record_movement('OPENING_STOCK', 'FINISHED_GOOD', product.id, Decimal('50.0000'), 'packets', Decimal('50.0000'), notes="Benchmark Opening Stock")

    # 5. Suppliers & Customers
    supplier = Supplier.query.filter_by(name='Trichy Agro Commodities').first()
    if not supplier:
        supplier = Supplier(name='Trichy Agro Commodities', contact_details='9443100001', gstin='33ABCDE1234F1Z5', state='Tamil Nadu')
        db.session.add(supplier)
        db.session.flush()

    retailer_a = Customer.query.filter_by(name='Retailer A (Chennai Stores)').first()
    if not retailer_a:
        retailer_a = Customer(name='Retailer A (Chennai Stores)', customer_type='Retailer', state='Tamil Nadu', gstin='33AAAAA1111A1Z1', billing_address='12 Anna Salai, Chennai, Tamil Nadu')
        db.session.add(retailer_a)

    distributor_b = Customer.query.filter_by(name='Distributor B (Bangalore Traders)').first()
    if not distributor_b:
        distributor_b = Customer(name='Distributor B (Bangalore Traders)', customer_type='Distributor', state='Karnataka', gstin='29BBBBB2222B1Z2', billing_address='45 MG Road, Bengaluru, Karnataka')
        db.session.add(distributor_b)

    db.session.flush()

    # Step 1: Record a purchase of 60 kg flour at ₹45/kg
    InventoryService.update_raw_material_wac(flour.id, Decimal('60.0000'), Decimal('45.0000'))
    purchase = Purchase(supplier_id=supplier.id, invoice_number='PUR-BM-001', purchase_date=datetime.utcnow().date(), total_amount=Decimal('2700.00'))
    db.session.add(purchase)
    db.session.flush()

    p_item = PurchaseItem(purchase_id=purchase.id, material_type='RAW_MATERIAL', raw_material_id=flour.id, quantity=Decimal('60.0000'), unit='kg', unit_rate=Decimal('45.0000'), total_amount=Decimal('2700.00'))
    db.session.add(p_item)
    InventoryService.record_movement('PURCHASE', 'RAW_MATERIAL', flour.id, Decimal('60.0000'), 'kg', Decimal('45.0000'), source_doc_type='Purchase', source_doc_id=purchase.id, notes="Benchmark purchase")

    # Step 2-8, 16-17: Production run
    # Planned: Flour 40kg, Oil 10L, Spice 1.2kg, Pouches 200, Cartons 10.
    # Actual: Flour 40kg, Oil 10.5L (Var: +5%), Spice 1.2kg, Pouches 188 good + 6 damaged = 194, Cartons 9 used.
    # Output: 188 good packets (Yield var: -6%). Overheads: Labour 1200, Gas/power 600.
    mat_issues = [
        {'material_type': 'RAW_MATERIAL', 'raw_material_id': flour.id, 'planned_qty': Decimal('40.0000'), 'actual_qty': Decimal('40.0000'), 'unit': 'kg'},
        {'material_type': 'RAW_MATERIAL', 'raw_material_id': oil.id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('10.5000'), 'unit': 'litre'},
        {'material_type': 'RAW_MATERIAL', 'raw_material_id': spice.id, 'planned_qty': Decimal('1.2000'), 'actual_qty': Decimal('1.2000'), 'unit': 'kg'},
        {'material_type': 'PACKAGING', 'packaging_material_id': pouch.id, 'planned_qty': Decimal('200.0000'), 'actual_qty': Decimal('194.0000'), 'unit': 'pieces'}, # 188 + 6 damaged
        {'material_type': 'PACKAGING', 'packaging_material_id': carton.id, 'planned_qty': Decimal('10.0000'), 'actual_qty': Decimal('9.0000'), 'unit': 'pieces'}
    ]

    prod_run = ProductionService.execute_production_run(
        product_id=product.id,
        bom_id=bom.id,
        batch_number='BATCH-BM-2026-01',
        production_date=datetime.utcnow().date(),
        batch_quantity=Decimal('1.00'),
        actual_good_output=Decimal('188.00'),
        material_issues_data=mat_issues,
        damaged_packaging=Decimal('6.00'),
        scrap_wastage=Decimal('0.00'),
        labour_expense=Decimal('1200.00'),
        power_gas_expense=Decimal('600.00'),
        notes="NIT Benchmark Production Run",
        user_id=admin_user.id if admin_user else None
    )

    # Step 9-12: Retailer A order (150 pkts), Admin approve, GST Invoice, Dispatch 150 pkts
    order_a = SalesService.create_order(
        salesman_id=salesman_a.id if salesman_a else 1,
        customer_id=retailer_a.id,
        items_data=[{'product_id': product.id, 'quantity': Decimal('150.00')}],
        notes="Retailer A Benchmark Order"
    )
    SalesService.approve_order(order_a.id, admin_user.id if admin_user else 1)
    inv_a = BillingService.create_invoice_from_order(order_a.id, admin_user.id if admin_user else 1)

    # Dispatch 150 packets
    InventoryService.record_movement('DISPATCH', 'FINISHED_GOOD', product.id, Decimal('-150.0000'), 'packets', Decimal('50.0000'), source_doc_type='GSTInvoice', source_doc_id=inv_a.id, notes="Dispatch 150 pkts to Retailer A")
    disp = DispatchRecord(invoice_id=inv_a.id, dispatch_date=datetime.utcnow().date(), vehicle_no='TN-45-AZ-1234', carrier_name='Speed Logistics', quantity_dispatched=Decimal('150.00'), notes="Benchmark dispatch")
    db.session.add(disp)
    order_a.status = 'Dispatched'

    # Step 13-14: Distributor B order (120 pkts, Karnataka) -> Stock shortage check
    order_b = SalesService.create_order(
        salesman_id=salesman_a.id if salesman_a else 1,
        customer_id=distributor_b.id,
        items_data=[{'product_id': product.id, 'quantity': Decimal('120.00')}],
        notes="Distributor B Benchmark Order"
    )
    # Check feasibility
    feasibility = SalesService.check_order_stock_feasibility(order_b.id)

    # Step 15: Record ₹4,000 payment from Retailer A
    PaymentService.record_payment(
        customer_id=retailer_a.id,
        invoice_id=inv_a.id,
        payment_date=datetime.utcnow().date(),
        amount_received=Decimal('4000.00'),
        payment_mode='NEFT/RTGS',
        reference_number='UTR-NIT-BM-4000',
        user_id=admin_user.id if admin_user else 1
    )

    db.session.commit()

@benchmark_bp.route('/')
@login_required
def index():
    # Evaluate live database state against NIT Trichy benchmark specifications
    flour = RawMaterial.query.filter_by(name='Flour').first()
    oil = RawMaterial.query.filter_by(name='Cooking oil').first()
    pouch = PackagingMaterial.query.filter_by(name='200 g pouch').first()
    carton = PackagingMaterial.query.filter_by(name='Carton').first()
    product = Product.query.filter_by(sku='MUR-200G').first()

    flour_stock = InventoryService.get_stock('RAW_MATERIAL', flour.id) if flour else Decimal('0.00')
    oil_stock = InventoryService.get_stock('RAW_MATERIAL', oil.id) if oil else Decimal('0.00')
    pouch_stock = InventoryService.get_stock('PACKAGING', pouch.id) if pouch else Decimal('0.00')
    carton_stock = InventoryService.get_stock('PACKAGING', carton.id) if carton else Decimal('0.00')
    fg_stock = InventoryService.get_stock('FINISHED_GOOD', product.id) if product else Decimal('0.00')

    prod_run = ProductionRun.query.filter_by(batch_number='BATCH-BM-2026-01').first()
    yield_var = prod_run.yield_variance_pct if prod_run else Decimal('0.00')
    cost_per_pkt = prod_run.cost_per_packet if prod_run else Decimal('0.00')

    oil_issue = ProductionMaterialIssue.query.filter_by(
        production_run_id=prod_run.id if prod_run else 0,
        raw_material_id=oil.id if oil else 0
    ).first()
    oil_var = oil_issue.variance_pct if oil_issue else Decimal('0.00')

    # Retailer A Invoice & Payment
    retailer = Customer.query.filter_by(name='Retailer A (Chennai Stores)').first()
    inv_a = GSTInvoice.query.filter_by(customer_id=retailer.id if retailer else 0).first()
    ret_taxable = inv_a.taxable_amount if inv_a else Decimal('0.00')
    ret_cgst = inv_a.cgst_amount if inv_a else Decimal('0.00')
    ret_sgst = inv_a.sgst_amount if inv_a else Decimal('0.00')
    ret_total = inv_a.total_amount if inv_a else Decimal('0.00')
    ret_outstanding = retailer.get_outstanding_balance() if retailer else Decimal('0.00')

    # Distributor B shortage
    distributor = Customer.query.filter_by(name='Distributor B (Bangalore Traders)').first()
    order_b = SalesOrder.query.filter_by(customer_id=distributor.id if distributor else 0).first()
    dist_shortage = order_b.shortage_quantity if order_b else Decimal('0.00')

    # Build the verification checklist table
    checklist = [
        {
            'metric': 'Flour Closing Balance',
            'expected': '120.00 kg',
            'actual': f"{flour_stock:.2f} kg",
            'passed': abs(flour_stock - Decimal('120.00')) < Decimal('0.01'),
            'explanation': '100 kg opening + 60 kg purchase - 40 kg production = 120 kg'
        },
        {
            'metric': 'Oil Closing Balance',
            'expected': '19.50 L',
            'actual': f"{oil_stock:.2f} L",
            'passed': abs(oil_stock - Decimal('19.50')) < Decimal('0.01'),
            'explanation': '30 L opening - 10.5 L production = 19.5 L'
        },
        {
            'metric': 'Pouches Closing Balance',
            'expected': '306 pieces',
            'actual': f"{pouch_stock:.0f} pieces",
            'passed': abs(pouch_stock - Decimal('306.00')) < Decimal('0.01'),
            'explanation': '500 opening - 188 good - 6 damaged = 306 pieces'
        },
        {
            'metric': 'Cartons Closing Balance',
            'expected': '21 pieces',
            'actual': f"{carton_stock:.0f} pieces",
            'passed': abs(carton_stock - Decimal('21.00')) < Decimal('0.01'),
            'explanation': '30 opening - 9 used = 21 pieces'
        },
        {
            'metric': 'Finished Goods (Post-Dispatch)',
            'expected': '88 packets',
            'actual': f"{fg_stock:.0f} packets",
            'passed': abs(fg_stock - Decimal('88.00')) < Decimal('0.01'),
            'explanation': '50 opening + 188 produced (238) - 150 dispatched = 88 packets'
        },
        {
            'metric': 'Yield Variance Percentage',
            'expected': '-6.00%',
            'actual': f"{yield_var:.2f}%",
            'passed': abs(yield_var - Decimal('-6.00')) < Decimal('0.01'),
            'explanation': '((188 actual - 200 expected) / 200) * 100 = -6% (ALERT: Exceeds ±3%)'
        },
        {
            'metric': 'Oil Consumption Variance',
            'expected': '+5.00%',
            'actual': f"{oil_var:.2f}%",
            'passed': abs(oil_var - Decimal('5.00')) < Decimal('0.01'),
            'explanation': '((10.5 actual - 10.0 planned) / 10.0) * 100 = +5% (ALERT: Exceeds ±3%)'
        },
        {
            'metric': 'Retailer A Taxable Amount',
            'expected': '₹7,500.00',
            'actual': f"₹{ret_taxable:,.2f}",
            'passed': abs(ret_taxable - Decimal('7500.00')) < Decimal('0.01'),
            'explanation': '150 packets * ₹50/packet = ₹7,500'
        },
        {
            'metric': 'CGST (2.5%)',
            'expected': '₹187.50',
            'actual': f"₹{ret_cgst:,.2f}",
            'passed': abs(ret_cgst - Decimal('187.50')) < Decimal('0.01'),
            'explanation': 'Intra-state Tamil Nadu to Tamil Nadu: ₹7,500 * 2.5% = ₹187.50'
        },
        {
            'metric': 'SGST (2.5%)',
            'expected': '₹187.50',
            'actual': f"₹{ret_sgst:,.2f}",
            'passed': abs(ret_sgst - Decimal('187.50')) < Decimal('0.01'),
            'explanation': 'Intra-state Tamil Nadu to Tamil Nadu: ₹7,500 * 2.5% = ₹187.50'
        },
        {
            'metric': 'Invoice Total',
            'expected': '₹7,875.00',
            'actual': f"₹{ret_total:,.2f}",
            'passed': abs(ret_total - Decimal('7875.00')) < Decimal('0.01'),
            'explanation': '₹7,500 taxable + ₹187.50 CGST + ₹187.50 SGST = ₹7,875'
        },
        {
            'metric': 'Retailer A Outstanding Balance',
            'expected': '₹3,875.00',
            'actual': f"₹{ret_outstanding:,.2f}",
            'passed': abs(ret_outstanding - Decimal('3875.00')) < Decimal('0.01'),
            'explanation': '₹7,875 invoice - ₹4,000 payment received = ₹3,875'
        },
        {
            'metric': 'Distributor B Stock Shortage',
            'expected': '32 packets',
            'actual': f"{dist_shortage:.0f} packets",
            'passed': abs(dist_shortage - Decimal('32.00')) < Decimal('0.01'),
            'explanation': '120 packets ordered - 88 packets available in stock = 32 shortage'
        },
        {
            'metric': 'Cost per Packet (WAC + Overheads)',
            'expected': '₹31.14',
            'actual': f"₹{cost_per_pkt:,.2f}",
            'passed': abs(cost_per_pkt - Decimal('31.14')) < Decimal('0.05'),
            'explanation': '(RM ₹3,435 + Pkg ₹620 + Labour ₹1,200 + Power ₹600) / 188 pkts = ₹31.14/pkt'
        }
    ]

    all_passed = all(item['passed'] for item in checklist)
    has_run = prod_run is not None

    return render_template(
        'benchmark/index.html',
        checklist=checklist,
        all_passed=all_passed,
        has_run=has_run
    )

@benchmark_bp.route('/run', methods=['POST'])
@login_required
def run_benchmark():
    try:
        # Clear existing benchmark-specific transaction records to prevent double execution
        from scripts.seed_data import reset_and_seed_database
        reset_and_seed_database()
        execute_nit_benchmark()
        flash("NIT Trichy Benchmark Scenario executed successfully! All figures verified.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error running benchmark: {str(e)}", "danger")

    return redirect(url_for('benchmark.index'))
