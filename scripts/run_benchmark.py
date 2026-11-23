import sys
import os
from decimal import Decimal

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Product, RawMaterial, PackagingMaterial, ProductionRun, ProductionMaterialIssue, GSTInvoice, Customer, SalesOrder
from app.services.inventory_service import InventoryService
from scripts.seed_data import reset_and_seed_database
from app.routes.benchmark import execute_nit_benchmark

def run_benchmark_cli():
    print("=" * 80)
    print(" NIT TIRUCHIRAPPALLI WINTER INTERNSHIP 2026 — ERP BENCHMARK RUNNER")
    print("=" * 80)
    print("[1/3] Resetting and seeding demo database...")
    reset_and_seed_database()

    print("[2/3] Executing 18 benchmark scenario steps...")
    execute_nit_benchmark()

    print("[3/3] Performing automated benchmark assertions...")
    
    # Query live database state
    flour = RawMaterial.query.filter_by(name='Flour').first()
    oil = RawMaterial.query.filter_by(name='Cooking oil').first()
    pouch = PackagingMaterial.query.filter_by(name='200 g pouch').first()
    carton = PackagingMaterial.query.filter_by(name='Carton').first()
    product = Product.query.filter_by(sku='MUR-200G').first()

    flour_stock = InventoryService.get_stock('RAW_MATERIAL', flour.id)
    oil_stock = InventoryService.get_stock('RAW_MATERIAL', oil.id)
    pouch_stock = InventoryService.get_stock('PACKAGING', pouch.id)
    carton_stock = InventoryService.get_stock('PACKAGING', carton.id)
    fg_stock = InventoryService.get_stock('FINISHED_GOOD', product.id)

    prod_run = ProductionRun.query.filter_by(batch_number='BATCH-BM-2026-01').first()
    yield_var = prod_run.yield_variance_pct
    cost_per_pkt = prod_run.cost_per_packet

    oil_issue = ProductionMaterialIssue.query.filter_by(
        production_run_id=prod_run.id,
        raw_material_id=oil.id
    ).first()
    oil_var = oil_issue.variance_pct

    retailer = Customer.query.filter_by(name='Retailer A (Chennai Stores)').first()
    inv_a = GSTInvoice.query.filter_by(customer_id=retailer.id).first()
    ret_taxable = inv_a.taxable_amount
    ret_cgst = inv_a.cgst_amount
    ret_sgst = inv_a.sgst_amount
    ret_total = inv_a.total_amount
    ret_outstanding = retailer.get_outstanding_balance()

    distributor = Customer.query.filter_by(name='Distributor B (Bangalore Traders)').first()
    order_b = SalesOrder.query.filter_by(customer_id=distributor.id).first()
    dist_shortage = order_b.shortage_quantity

    # Table of tests: (Metric Name, Expected Display, Actual Display, Boolean Condition)
    tests = [
        ("Flour closing balance", "120 kg", f"{flour_stock} kg", abs(flour_stock - Decimal('120.00')) < Decimal('0.01')),
        ("Oil closing balance", "19.5 L", f"{oil_stock} L", abs(oil_stock - Decimal('19.50')) < Decimal('0.01')),
        ("Pouches closing balance", "306 pieces", f"{pouch_stock} pieces", abs(pouch_stock - Decimal('306.00')) < Decimal('0.01')),
        ("Cartons closing balance", "21 pieces", f"{carton_stock} pieces", abs(carton_stock - Decimal('21.00')) < Decimal('0.01')),
        ("Finished goods after dispatch", "88 packets", f"{fg_stock} packets", abs(fg_stock - Decimal('88.00')) < Decimal('0.01')),
        ("Yield variance %", "-6.00%", f"{yield_var}%", abs(yield_var - Decimal('-6.00')) < Decimal('0.01')),
        ("Oil consumption variance %", "+5.00%", f"{oil_var}%", abs(oil_var - Decimal('5.00')) < Decimal('0.01')),
        ("Retailer A taxable amount", "Rs. 7,500.00", f"Rs. {ret_taxable}", abs(ret_taxable - Decimal('7500.00')) < Decimal('0.01')),
        ("CGST (2.5%)", "Rs. 187.50", f"Rs. {ret_cgst}", abs(ret_cgst - Decimal('187.50')) < Decimal('0.01')),
        ("SGST (2.5%)", "Rs. 187.50", f"Rs. {ret_sgst}", abs(ret_sgst - Decimal('187.50')) < Decimal('0.01')),
        ("Invoice total", "Rs. 7,875.00", f"Rs. {ret_total}", abs(ret_total - Decimal('7875.00')) < Decimal('0.01')),
        ("Retailer A outstanding balance", "Rs. 3,875.00", f"Rs. {ret_outstanding}", abs(ret_outstanding - Decimal('3875.00')) < Decimal('0.01')),
        ("Distributor B stock shortage", "32 packets", f"{dist_shortage} packets", abs(dist_shortage - Decimal('32.00')) < Decimal('0.01')),
        ("Cost per packet", "Rs. 31.14", f"Rs. {cost_per_pkt}", abs(cost_per_pkt - Decimal('31.14')) < Decimal('0.05'))
    ]

    all_passed = True
    print("\n" + "-" * 80)
    print(f"{'METRIC':<32} | {'EXPECTED':<15} | {'ACTUAL':<15} | {'STATUS'}")
    print("-" * 80)
    for name, expected, actual, passed in tests:
        status = "[ PASS ]" if passed else "[ FAIL ]"
        if not passed:
            all_passed = False
        print(f"{name:<32} | {expected:<15} | {actual:<15} | {status}")
    print("-" * 80)

    if all_passed:
        print("\n>>> ALL BENCHMARK ASSERTIONS PASSED! 100% RECONCILIATION ACHIEVED! <<<")
        print("Valuation Method: Weighted Average Cost (WAC)")
        print("Costing Breakdown: RM Rs. 3,435.00 + Packaging Rs. 620.00 + Labour Rs. 1,200.00 + Power/Gas Rs. 600.00 = Total Rs. 5,855.00")
        print("Cost per packet: Rs. 5,855.00 / 188 good packets = Rs. 31.1436/pkt\n")
        return 0
    else:
        print("\n>>> CRITICAL: ONE OR MORE BENCHMARK ASSERTIONS FAILED! <<<\n")
        return 1

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        exit_code = run_benchmark_cli()
        sys.exit(exit_code)
