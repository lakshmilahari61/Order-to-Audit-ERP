from datetime import datetime
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

# ==========================================
# 1. USER & ROLE MODELS
# ==========================================

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # admin, salesman, production, auditor, owner
    description = db.Column(db.String(200))
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *role_names):
        return self.role and self.role.name in role_names

    def __repr__(self):
        return f"<User {self.username} ({self.role.name if self.role else 'No Role'})>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# 2. MASTER DATA MODELS
# ==========================================

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    customer_type = db.Column(db.String(50), default='Retailer') # Retailer, Distributor, Wholesaler
    gstin = db.Column(db.String(15))
    state = db.Column(db.String(50), nullable=False, default='Tamil Nadu')
    billing_address = db.Column(db.Text)
    contact_number = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('SalesOrder', backref='customer', lazy=True)
    invoices = db.relationship('GSTInvoice', backref='customer', lazy=True)
    payments = db.relationship('Payment', backref='customer', lazy=True)

    def get_total_invoiced(self):
        total = sum((inv.total_amount for inv in self.invoices if inv.status != 'Cancelled'), Decimal('0.00'))
        return total

    def get_total_paid(self):
        total = sum((p.amount_received for p in self.payments), Decimal('0.00'))
        return total

    def get_outstanding_balance(self):
        return self.get_total_invoiced() - self.get_total_paid()

    def __repr__(self):
        return f"<Customer {self.name} ({self.state})>"

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    contact_details = db.Column(db.String(150))
    gstin = db.Column(db.String(15))
    state = db.Column(db.String(50), default='Tamil Nadu')
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship('Purchase', backref='supplier', lazy=True)

    def __repr__(self):
        return f"<Supplier {self.name}>"

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True) # e.g. Murukku 200g
    sku = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50), default='Snacks') # Murukku, Mixture, Chips, Sweets
    pack_size = db.Column(db.String(50), default='200g')
    selling_price = db.Column(db.Numeric(10, 2), nullable=False) # e.g. 50.00
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00')) # 5.00%
    hsn_code = db.Column(db.String(20), default='21069099')
    unit = db.Column(db.String(20), default='packets')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    boms = db.relationship('BOM', backref='product', lazy=True)

    def __repr__(self):
        return f"<Product {self.name} (SKU: {self.sku})>"

class CustomerProductPrice(db.Model):
    """Optional customer-specific contracted selling prices"""
    __tablename__ = 'customer_product_prices'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    special_price = db.Column(db.Numeric(10, 2), nullable=False)

class RawMaterial(db.Model):
    __tablename__ = 'raw_materials'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True) # Flour, Cooking oil, Spice mix
    category = db.Column(db.String(50), default='Raw Material')
    unit = db.Column(db.String(20), nullable=False) # kg, litre, g, ml
    current_rate = db.Column(db.Numeric(10, 4), default=Decimal('0.0000')) # Weighted Average Cost
    reorder_level = db.Column(db.Numeric(10, 2), default=Decimal('10.00'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RawMaterial {self.name} ({self.unit})>"

class PackagingMaterial(db.Model):
    __tablename__ = 'packaging_materials'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True) # 200g pouch, Carton
    unit = db.Column(db.String(20), default='pieces')
    current_rate = db.Column(db.Numeric(10, 4), default=Decimal('0.0000')) # Rate per piece
    reorder_level = db.Column(db.Numeric(10, 2), default=Decimal('50.00'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PackagingMaterial {self.name}>"

# ==========================================
# 3. BILL OF MATERIALS (BOM)
# ==========================================

class BOM(db.Model):
    __tablename__ = 'boms'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_size = db.Column(db.Numeric(10, 2), default=Decimal('1.00')) # e.g. 1 batch
    expected_yield = db.Column(db.Numeric(10, 2), default=Decimal('200.00')) # e.g. 200 packets
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('BOMItem', backref='bom', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f"<BOM for {self.product.name if self.product else self.product_id} (Yield: {self.expected_yield})>"

class BOMItem(db.Model):
    __tablename__ = 'bom_items'
    id = db.Column(db.Integer, primary_key=True)
    bom_id = db.Column(db.Integer, db.ForeignKey('boms.id'), nullable=False)
    material_type = db.Column(db.String(20), nullable=False) # RAW_MATERIAL or PACKAGING
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=True)
    packaging_material_id = db.Column(db.Integer, db.ForeignKey('packaging_materials.id'), nullable=True)
    standard_qty = db.Column(db.Numeric(10, 4), nullable=False)
    unit = db.Column(db.String(20), nullable=False)

    raw_material = db.relationship('RawMaterial', lazy=True)
    packaging_material = db.relationship('PackagingMaterial', lazy=True)

    @property
    def item_name(self):
        if self.material_type == 'RAW_MATERIAL' and self.raw_material:
            return self.raw_material.name
        elif self.material_type == 'PACKAGING' and self.packaging_material:
            return self.packaging_material.name
        return "Unknown Item"

# ==========================================
# 4. PURCHASES
# ==========================================

class Purchase(db.Model):
    __tablename__ = 'purchases'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    invoice_number = db.Column(db.String(50))
    purchase_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    items = db.relationship('PurchaseItem', backref='purchase', cascade='all, delete-orphan', lazy=True)
    created_by = db.relationship('User', lazy=True)

class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    material_type = db.Column(db.String(20), nullable=False) # RAW_MATERIAL or PACKAGING
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=True)
    packaging_material_id = db.Column(db.Integer, db.ForeignKey('packaging_materials.id'), nullable=True)
    quantity = db.Column(db.Numeric(10, 4), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_rate = db.Column(db.Numeric(10, 4), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)

    raw_material = db.relationship('RawMaterial', lazy=True)
    packaging_material = db.relationship('PackagingMaterial', lazy=True)

    @property
    def item_name(self):
        if self.material_type == 'RAW_MATERIAL' and self.raw_material:
            return self.raw_material.name
        elif self.material_type == 'PACKAGING' and self.packaging_material:
            return self.packaging_material.name
        return "Unknown Material"

# ==========================================
# 5. PRODUCTION MODULE
# ==========================================

class ProductionRun(db.Model):
    __tablename__ = 'production_runs'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    bom_id = db.Column(db.Integer, db.ForeignKey('boms.id'), nullable=False)
    batch_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    production_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    batch_quantity = db.Column(db.Numeric(10, 2), default=Decimal('1.00')) # batches
    expected_output = db.Column(db.Numeric(10, 2), nullable=False) # e.g. 200 packets
    actual_good_output = db.Column(db.Numeric(10, 2), nullable=False) # e.g. 188 packets
    damaged_packaging = db.Column(db.Numeric(10, 2), default=Decimal('0.00')) # e.g. 6 pouches
    scrap_wastage = db.Column(db.Numeric(10, 2), default=Decimal('0.00')) # general scrap
    
    # Direct Overheads
    labour_expense = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    power_gas_expense = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    other_overhead = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    
    # Cost Breakdown Totals
    total_material_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    total_packaging_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    total_production_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    cost_per_packet = db.Column(db.Numeric(10, 4), default=Decimal('0.0000'))
    
    # Variances
    yield_variance_pct = db.Column(db.Numeric(6, 2), default=Decimal('0.00')) # ((Actual - Expected) / Expected) * 100
    
    notes = db.Column(db.Text)
    status = db.Column(db.String(30), default='Completed') # Planned, In-Progress, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    product = db.relationship('Product', lazy=True)
    bom = db.relationship('BOM', lazy=True)
    material_issues = db.relationship('ProductionMaterialIssue', backref='production_run', cascade='all, delete-orphan', lazy=True)
    created_by = db.relationship('User', lazy=True)

class ProductionMaterialIssue(db.Model):
    __tablename__ = 'production_material_issues'
    id = db.Column(db.Integer, primary_key=True)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id'), nullable=False)
    material_type = db.Column(db.String(20), nullable=False) # RAW_MATERIAL or PACKAGING
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=True)
    packaging_material_id = db.Column(db.Integer, db.ForeignKey('packaging_materials.id'), nullable=True)
    planned_qty = db.Column(db.Numeric(10, 4), nullable=False)
    actual_qty = db.Column(db.Numeric(10, 4), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_rate = db.Column(db.Numeric(10, 4), nullable=False)
    total_cost = db.Column(db.Numeric(12, 2), nullable=False)
    variance_pct = db.Column(db.Numeric(6, 2), default=Decimal('0.00')) # ((Actual - Planned) / Planned) * 100

    raw_material = db.relationship('RawMaterial', lazy=True)
    packaging_material = db.relationship('PackagingMaterial', lazy=True)

    @property
    def item_name(self):
        if self.material_type == 'RAW_MATERIAL' and self.raw_material:
            return self.raw_material.name
        elif self.material_type == 'PACKAGING' and self.packaging_material:
            return self.packaging_material.name
        return "Unknown Material"

class ProductionOutput(db.Model):
    __tablename__ = 'production_outputs'
    id = db.Column(db.Integer, primary_key=True)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    good_quantity = db.Column(db.Numeric(10, 2), nullable=False)
    damaged_quantity = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    scrap_quantity = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', lazy=True)

# ==========================================
# 6. INVENTORY TRANSACTIONS (IMMUTABLE LEDGER)
# ==========================================

class InventoryTransaction(db.Model):
    """
    Every single inventory change is written here. Stock balance is computed dynamically
    as Opening + Receipts - Issues - Sales +/- Adjustments. No direct overwrite allowed.
    """
    __tablename__ = 'inventory_transactions'
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(30), nullable=False, index=True)
    # PURCHASE, PRODUCTION_ISSUE, PRODUCTION_OUTPUT, DISPATCH, RETURN, ADJUSTMENT, OPENING_STOCK
    
    item_type = db.Column(db.String(20), nullable=False, index=True) # RAW_MATERIAL, PACKAGING, FINISHED_GOOD
    item_id = db.Column(db.Integer, nullable=False, index=True) # Refers to RawMaterial.id, PackagingMaterial.id, or Product.id
    
    quantity = db.Column(db.Numeric(10, 4), nullable=False) # Positive for additions/receipts, Negative for issues/dispatches
    unit = db.Column(db.String(20), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 4), default=Decimal('0.0000'))
    total_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    
    running_balance = db.Column(db.Numeric(10, 4), nullable=True) # Snapshot after this entry
    source_doc_type = db.Column(db.String(50)) # Purchase, ProductionRun, Dispatch, Adjustment
    source_doc_id = db.Column(db.Integer) # ID of source document
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<InventoryTransaction {self.transaction_type} {self.item_type} ID:{self.item_id} Qty:{self.quantity}>"

# ==========================================
# 7. SALES & ORDER MANAGEMENT
# ==========================================

class SalesOrder(db.Model):
    __tablename__ = 'sales_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. ORD-2026-0001
    salesman_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(30), default='Submitted', index=True)
    # Submitted, Approved, Rejected, Invoiced, Dispatched
    
    total_taxable_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    total_gst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    total_order_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    notes = db.Column(db.Text)
    shortage_quantity = db.Column(db.Numeric(10, 2), default=Decimal('0.00')) # Track stock deficit if unapprovable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    salesman = db.relationship('User', foreign_keys=[salesman_id], lazy=True)
    items = db.relationship('SalesOrderItem', backref='sales_order', cascade='all, delete-orphan', lazy=True)
    invoice = db.relationship('GSTInvoice', backref='sales_order', uselist=False, lazy=True)

    def __repr__(self):
        return f"<SalesOrder {self.order_number} ({self.status})>"

class SalesOrderItem(db.Model):
    __tablename__ = 'sales_order_items'
    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    taxable_amount = db.Column(db.Numeric(12, 2), nullable=False)
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00'))
    cgst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    sgst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    igst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)

    product = db.relationship('Product', lazy=True)

# ==========================================
# 8. GST INVOICES & DISPATCH
# ==========================================

class GSTInvoice(db.Model):
    __tablename__ = 'gst_invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. INV-2026-0001
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Preserved snapshot of customer details
    customer_name = db.Column(db.String(150), nullable=False)
    customer_gstin = db.Column(db.String(15))
    customer_state = db.Column(db.String(50), nullable=False)
    customer_address = db.Column(db.Text)
    
    taxable_amount = db.Column(db.Numeric(12, 2), nullable=False)
    cgst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    sgst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    igst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    pdf_path = db.Column(db.String(255))
    status = db.Column(db.String(30), default='Issued') # Issued, Paid, Partial, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan', lazy=True)
    dispatches = db.relationship('DispatchRecord', backref='invoice', lazy=True)
    payments = db.relationship('Payment', backref='invoice', lazy=True)

    def get_paid_amount(self):
        return sum((p.amount_received for p in self.payments), Decimal('0.00'))

    def get_outstanding(self):
        return self.total_amount - self.get_paid_amount()

    def __repr__(self):
        return f"<GSTInvoice {self.invoice_number} ({self.total_amount})>"

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('gst_invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    hsn_code = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    taxable_amount = db.Column(db.Numeric(12, 2), nullable=False)
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00'))
    cgst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    sgst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    igst_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)

    product = db.relationship('Product', lazy=True)

class DispatchRecord(db.Model):
    __tablename__ = 'dispatch_records'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('gst_invoices.id'), nullable=False)
    dispatch_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    vehicle_no = db.Column(db.String(50))
    carrier_name = db.Column(db.String(100))
    quantity_dispatched = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_by = db.relationship('User', lazy=True)

# ==========================================
# 9. PAYMENTS & RECEIVABLES
# ==========================================

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('gst_invoices.id'), nullable=True)
    payment_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    amount_received = db.Column(db.Numeric(12, 2), nullable=False)
    payment_mode = db.Column(db.String(50), default='NEFT/RTGS') # Cash, Cheque, UPI, NEFT/RTGS
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_by = db.relationship('User', lazy=True)

# ==========================================
# 10. AUDIT LOGS & EXPENSES
# ==========================================

class ExpenseOverhead(db.Model):
    __tablename__ = 'expenses_overheads'
    id = db.Column(db.Integer, primary_key=True)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id'), nullable=True)
    category = db.Column(db.String(50), nullable=False) # Labour, Power/Gas, Packing, Maintenance
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))
    expense_date = db.Column(db.Date, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True) # CREATE_ORDER, APPROVE_ORDER, POST_PURCHASE, etc.
    entity_type = db.Column(db.String(50), nullable=False, index=True) # SalesOrder, Purchase, ProductionRun, Payment
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', lazy=True)

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"
