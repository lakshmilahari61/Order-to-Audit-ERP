from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import (
    SalesOrder, GSTInvoice, ProductionRun, ProductionMaterialIssue,
    Payment, Customer, Product, RawMaterial, PackagingMaterial, AuditLog
)
from app.services.inventory_service import InventoryService
from app.services.report_service import ReportService
from app.routes.auth import role_required

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    role_name = current_user.role.name if current_user.role else 'admin'
    return redirect(url_for(f'dashboard.{role_name}'))

@dashboard_bp.route('/owner')
@login_required
@role_required('owner', 'admin')
def owner():
    today = date.today()
    
    # 1. Sales & Orders
    today_invoices = GSTInvoice.query.filter(GSTInvoice.invoice_date == today, GSTInvoice.status != 'Cancelled').all()
    today_sales = sum((inv.total_amount for inv in today_invoices), Decimal('0.00'))
    
    all_invoices = GSTInvoice.query.filter(GSTInvoice.status != 'Cancelled').all()
    total_sales = sum((inv.total_amount for inv in all_invoices), Decimal('0.00'))
    
    total_orders = SalesOrder.query.count()
    pending_orders = SalesOrder.query.filter_by(status='Submitted').count()

    # 2. Production
    total_batches = ProductionRun.query.count()
    total_packets_produced = db.session.query(db.func.sum(ProductionRun.actual_good_output)).scalar() or Decimal('0.00')

    # 3. Stock Summaries & Alerts
    rm_summary = InventoryService.get_stock_summary('RAW_MATERIAL')
    pkg_summary = InventoryService.get_stock_summary('PACKAGING')
    fg_summary = InventoryService.get_stock_summary('FINISHED_GOOD')

    total_rm_val = sum((item['valuation'] for item in rm_summary), Decimal('0.00'))
    total_pkg_val = sum((item['valuation'] for item in pkg_summary), Decimal('0.00'))
    total_fg_val = sum((item['valuation'] for item in fg_summary), Decimal('0.00'))

    low_stock_alerts = [item for item in (rm_summary + pkg_summary) if item.get('is_low_stock')]

    # 4. Receivables
    total_invoiced = sum((inv.total_amount for inv in all_invoices), Decimal('0.00'))
    total_paid = db.session.query(db.func.sum(Payment.amount_received)).scalar() or Decimal('0.00')
    outstanding_receivables = total_invoiced - total_paid

    # 5. Production Variance Alerts (exceeding +/- 3%)
    variance_runs = ProductionRun.query.filter(
        db.or_(
            ProductionRun.yield_variance_pct > Decimal('3.00'),
            ProductionRun.yield_variance_pct < Decimal('-3.00')
        )
    ).all()

    mat_variance_issues = ProductionMaterialIssue.query.filter(
        db.or_(
            ProductionMaterialIssue.variance_pct > Decimal('3.00'),
            ProductionMaterialIssue.variance_pct < Decimal('-3.00')
        )
    ).all()

    # 6. Chart.js data (Product-wise sales & Monthly sales)
    products = Product.query.all()
    product_sales_labels = [p.name for p in products]
    product_sales_values = []
    for p in products:
        p_qty = db.session.query(db.func.sum(SalesOrder.items.property.mapper.class_.quantity)).join(SalesOrder).filter(
            SalesOrder.items.property.mapper.class_.product_id == p.id,
            SalesOrder.status.in_(['Approved', 'Invoiced', 'Dispatched'])
        ).scalar() or 0
        product_sales_values.append(float(p_qty))

    # Recent Costing & Margin
    recent_runs = ProductionRun.query.order_by(ProductionRun.production_date.desc()).limit(5).all()

    return render_template(
        'dashboard/owner.html',
        today_sales=today_sales,
        total_sales=total_sales,
        total_orders=total_orders,
        pending_orders=pending_orders,
        total_batches=total_batches,
        total_packets_produced=total_packets_produced,
        total_rm_val=total_rm_val,
        total_pkg_val=total_pkg_val,
        total_fg_val=total_fg_val,
        low_stock_alerts=low_stock_alerts,
        outstanding_receivables=outstanding_receivables,
        variance_runs=variance_runs,
        mat_variance_issues=mat_variance_issues,
        product_sales_labels=product_sales_labels,
        product_sales_values=product_sales_values,
        recent_runs=recent_runs,
        fg_summary=fg_summary
    )

@dashboard_bp.route('/admin')
@login_required
@role_required('admin', 'owner')
def admin():
    pending_orders = SalesOrder.query.filter_by(status='Submitted').order_by(SalesOrder.order_date.desc()).all()
    approved_orders = SalesOrder.query.filter_by(status='Approved').order_by(SalesOrder.order_date.desc()).all()
    invoiced_orders = SalesOrder.query.filter_by(status='Invoiced').order_by(SalesOrder.order_date.desc()).all()
    
    fg_summary = InventoryService.get_stock_summary('FINISHED_GOOD')
    recent_payments = Payment.query.order_by(Payment.payment_date.desc()).limit(5).all()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    return render_template(
        'dashboard/admin.html',
        pending_orders=pending_orders,
        approved_orders=approved_orders,
        invoiced_orders=invoiced_orders,
        fg_summary=fg_summary,
        recent_payments=recent_payments,
        recent_logs=recent_logs
    )

@dashboard_bp.route('/production')
@login_required
@role_required('production', 'admin', 'owner')
def production():
    recent_runs = ProductionRun.query.order_by(ProductionRun.production_date.desc()).limit(10).all()
    rm_summary = InventoryService.get_stock_summary('RAW_MATERIAL')
    pkg_summary = InventoryService.get_stock_summary('PACKAGING')
    
    # Active alerts
    alerts = []
    for r in recent_runs:
        if abs(float(r.yield_variance_pct)) > 3.0:
            alerts.append({
                'type': 'Yield Variance Alert',
                'batch': r.batch_number,
                'msg': f"Yield variance is {r.yield_variance_pct}% (Tolerance: ±3%)"
            })
    
    mat_issues = ProductionMaterialIssue.query.order_by(ProductionMaterialIssue.id.desc()).limit(20).all()
    for m in mat_issues:
        if abs(float(m.variance_pct)) > 3.0:
            alerts.append({
                'type': 'Material Variance Alert',
                'batch': m.production_run.batch_number if m.production_run else 'N/A',
                'msg': f"{m.item_name} consumption variance is {m.variance_pct}% (Planned: {m.planned_qty} {m.unit}, Actual: {m.actual_qty} {m.unit})"
            })

    return render_template(
        'dashboard/production.html',
        recent_runs=recent_runs,
        rm_summary=rm_summary,
        pkg_summary=pkg_summary,
        alerts=alerts
    )

@dashboard_bp.route('/salesman')
@login_required
@role_required('salesman', 'admin', 'owner')
def salesman():
    my_orders = SalesOrder.query.filter_by(salesman_id=current_user.id).order_by(SalesOrder.order_date.desc()).all()
    products = Product.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(is_active=True).all()
    
    # Finished goods availability for salesman guidance
    fg_summary = InventoryService.get_stock_summary('FINISHED_GOOD')

    return render_template(
        'dashboard/salesman.html',
        my_orders=my_orders,
        products=products,
        customers=customers,
        fg_summary=fg_summary
    )

@dashboard_bp.route('/auditor')
@login_required
@role_required('auditor', 'admin', 'owner')
def auditor():
    gst_summary = ReportService.get_gst_summary()
    recent_transactions = InventoryTransaction.query.order_by(InventoryTransaction.id.desc()).limit(15).all()
    receivables = ReportService.get_sales_register()
    purchases = ReportService.get_purchase_register()
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(25).all()

    return render_template(
        'dashboard/auditor.html',
        gst_summary=gst_summary,
        recent_transactions=recent_transactions,
        total_sales_count=len(receivables),
        total_purchases_count=len(purchases),
        audit_logs=audit_logs
    )
