import sys
import os
from decimal import Decimal
from datetime import datetime

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import (
    Role, User, Product, Customer, Supplier, RawMaterial,
    PackagingMaterial, BOM, BOMItem, InventoryTransaction
)
from app.services.inventory_service import InventoryService

def reset_and_seed_database():
    """
    Drops and recreates all database tables cleanly,
    then populates roles, demo users, master materials, BOMs, and opening balances.
    """
    print("[*] Rebuilding database tables cleanly...")
    db.drop_all()
    db.create_all()

    print("[*] Seeding user roles...")
    roles = {
        'admin': Role(name='admin', description='Administrator with full approval, master data, and dispatch rights'),
        'salesman': Role(name='salesman', description='Field sales personnel for order entry and tracking'),
        'production': Role(name='production', description='Factory supervisor for batch production, issues, and variances'),
        'auditor': Role(name='auditor', description='Accountant and auditor with read-only access and report exports'),
        'owner': Role(name='owner', description='Business owner with executive dashboard, variance alerts, and KPIs')
    }
    for r in roles.values():
        db.session.add(r)
    db.session.flush()

    print("[*] Seeding demo users...")
    users = [
        ('admin', 'admin123', 'Suresh Kumar (Admin)', roles['admin']),
        ('salesman', 'sales123', 'Senthil Kumar (Salesman A)', roles['salesman']),
        ('salesman_b', 'sales123', 'Mani Raja (Salesman B)', roles['salesman']),
        ('production', 'prod123', 'Muthu Vel (Production Supervisor)', roles['production']),
        ('auditor', 'audit123', 'Lakshmi Narayanan (Accountant / Auditor)', roles['auditor']),
        ('owner', 'owner123', 'Ramasamy (Managing Director / Owner)', roles['owner'])
    ]
    for username, password, full_name, role in users:
        u = User(username=username, full_name=full_name, role_id=role.id)
        u.set_password(password)
        db.session.add(u)
    db.session.flush()

    print("[*] Seeding master products...")
    murukku = Product(
        name='Murukku 200g', sku='MUR-200G', category='Murukku', pack_size='200g',
        selling_price=Decimal('50.00'), gst_rate=Decimal('5.00'), hsn_code='21069099', unit='packets'
    )
    mixture = Product(
        name='Mixture 250g', sku='MIX-250G', category='Mixture', pack_size='250g',
        selling_price=Decimal('60.00'), gst_rate=Decimal('5.00'), hsn_code='21069099', unit='packets'
    )
    chips = Product(
        name='Potato Chips 100g', sku='CHP-100G', category='Chips', pack_size='100g',
        selling_price=Decimal('35.00'), gst_rate=Decimal('5.00'), hsn_code='20052000', unit='packets'
    )
    sweets = Product(
        name='Mysore Pak 200g', sku='SWT-200G', category='Sweets', pack_size='200g',
        selling_price=Decimal('90.00'), gst_rate=Decimal('5.00'), hsn_code='21069099', unit='packets'
    )
    for p in [murukku, mixture, chips, sweets]:
        db.session.add(p)
    db.session.flush()

    print("[*] Seeding raw materials & packaging...")
    flour = RawMaterial(name='Flour', category='Grain / Flour', unit='kg', current_rate=Decimal('42.0000'), reorder_level=Decimal('20.00'))
    oil = RawMaterial(name='Cooking oil', category='Oil', unit='litre', current_rate=Decimal('140.0000'), reorder_level=Decimal('10.00'))
    spice = RawMaterial(name='Salt and spice mix', category='Spices', unit='kg', current_rate=Decimal('200.0000'), reorder_level=Decimal('2.00'))
    besan = RawMaterial(name='Gram flour (Besan)', category='Flour', unit='kg', current_rate=Decimal('65.0000'), reorder_level=Decimal('15.00'))
    sugar = RawMaterial(name='Sugar', category='Sweetener', unit='kg', current_rate=Decimal('40.0000'), reorder_level=Decimal('20.00'))
    
    for rm in [flour, oil, spice, besan, sugar]:
        db.session.add(rm)

    pouch200 = PackagingMaterial(name='200 g pouch', unit='pieces', current_rate=Decimal('2.5000'), reorder_level=Decimal('100.00'))
    carton = PackagingMaterial(name='Carton', unit='pieces', current_rate=Decimal('15.0000'), reorder_level=Decimal('10.00'))
    pouch250 = PackagingMaterial(name='250 g pouch', unit='pieces', current_rate=Decimal('2.8000'), reorder_level=Decimal('50.00'))
    
    for pm in [pouch200, carton, pouch250]:
        db.session.add(pm)
    db.session.flush()

    print("[*] Seeding suppliers & customers...")
    supp1 = Supplier(name='Trichy Agro Commodities', contact_details='9443100001', gstin='33ABCDE1234F1Z5', state='Tamil Nadu', address='Grain Market, Thuvakudi, Trichy')
    supp2 = Supplier(name='Ponni Edible Oils', contact_details='9443100002', gstin='33XYZAB5678C1Z2', state='Tamil Nadu', address='Industrial Area, Karur Road, Trichy')
    db.session.add_all([supp1, supp2])

    cust1 = Customer(
        name='Retailer A (Chennai Stores)', customer_type='Retailer', state='Tamil Nadu',
        gstin='33AAAAA1111A1Z1', billing_address='12 Anna Salai, Chennai, Tamil Nadu', contact_number='9840100001'
    )
    cust2 = Customer(
        name='Distributor B (Bangalore Traders)', customer_type='Distributor', state='Karnataka',
        gstin='29BBBBB2222B1Z2', billing_address='45 MG Road, Bengaluru, Karnataka', contact_number='9845100002'
    )
    cust3 = Customer(
        name='Madurai Supermarket', customer_type='Retailer', state='Tamil Nadu',
        gstin='33CCCCC3333C1Z3', billing_address='8 West Tower Street, Madurai, Tamil Nadu', contact_number='9842100003'
    )
    db.session.add_all([cust1, cust2, cust3])
    db.session.flush()

    print("[*] Seeding standard BOM for Murukku 200g...")
    bom = BOM(product_id=murukku.id, batch_size=Decimal('1.00'), expected_yield=Decimal('200.00'), notes="Standard 200g Murukku recipe (NIT Trichy Benchmark)")
    db.session.add(bom)
    db.session.flush()

    bom_items = [
        BOMItem(bom_id=bom.id, material_type='RAW_MATERIAL', raw_material_id=flour.id, standard_qty=Decimal('40.0000'), unit='kg'),
        BOMItem(bom_id=bom.id, material_type='RAW_MATERIAL', raw_material_id=oil.id, standard_qty=Decimal('10.0000'), unit='litre'),
        BOMItem(bom_id=bom.id, material_type='RAW_MATERIAL', raw_material_id=spice.id, standard_qty=Decimal('1.2000'), unit='kg'),
        BOMItem(bom_id=bom.id, material_type='PACKAGING', packaging_material_id=pouch200.id, standard_qty=Decimal('200.0000'), unit='pieces'),
        BOMItem(bom_id=bom.id, material_type='PACKAGING', packaging_material_id=carton.id, standard_qty=Decimal('10.0000'), unit='pieces')
    ]
    for bi in bom_items:
        db.session.add(bi)
    db.session.flush()

    print("[*] Seeding opening inventory into transaction ledger...")
    # Flour 100 kg @ 42, Cooking oil 30 L @ 140, Spice mix 5 kg @ 200, Pouches 500 @ 2.50, Cartons 30 @ 15, FG 50 pkts @ 50
    InventoryService.record_movement('OPENING_STOCK', 'RAW_MATERIAL', flour.id, Decimal('100.0000'), 'kg', Decimal('42.0000'), notes="Opening stock")
    InventoryService.record_movement('OPENING_STOCK', 'RAW_MATERIAL', oil.id, Decimal('30.0000'), 'litre', Decimal('140.0000'), notes="Opening stock")
    InventoryService.record_movement('OPENING_STOCK', 'RAW_MATERIAL', spice.id, Decimal('5.0000'), 'kg', Decimal('200.0000'), notes="Opening stock")
    InventoryService.record_movement('OPENING_STOCK', 'PACKAGING', pouch200.id, Decimal('500.0000'), 'pieces', Decimal('2.5000'), notes="Opening stock")
    InventoryService.record_movement('OPENING_STOCK', 'PACKAGING', carton.id, Decimal('30.0000'), 'pieces', Decimal('15.0000'), notes="Opening stock")
    InventoryService.record_movement('OPENING_STOCK', 'FINISHED_GOOD', murukku.id, Decimal('50.0000'), 'packets', Decimal('50.0000'), notes="Opening stock")

    db.session.commit()
    print("[+] Database initialized and seeded successfully!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        reset_and_seed_database()
