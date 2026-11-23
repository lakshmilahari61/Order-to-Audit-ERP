from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import SalesOrder, SalesOrderItem, Customer, Product
from app.services.sales_service import SalesService
from app.services.inventory_service import InventoryService
from app.routes.auth import role_required

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/')
@login_required
def index():
    if current_user.has_role('salesman'):
        orders = SalesOrder.query.filter_by(salesman_id=current_user.id).order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc()).all()
    else:
        orders = SalesOrder.query.order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc()).all()
    return render_template('sales/list.html', orders=orders)

@sales_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('salesman', 'admin', 'owner')
def new_order():
    if request.method == 'POST':
        customer_id = int(request.form.get('customer_id'))
        notes = request.form.get('notes', '')

        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        items_data = []
        for p_id, q_str in zip(product_ids, quantities):
            if not p_id or not q_str:
                continue
            qty = Decimal(q_str)
            if qty > Decimal('0.00'):
                items_data.append({
                    'product_id': int(p_id),
                    'quantity': qty
                })

        if not items_data:
            flash("Please add at least one valid item to the order.", "danger")
            return redirect(url_for('sales.new_order'))

        try:
            order = SalesService.create_order(
                salesman_id=current_user.id,
                customer_id=customer_id,
                items_data=items_data,
                notes=notes
            )
            db.session.commit()
            if order.shortage_quantity > Decimal('0.00'):
                flash(f"Order {order.order_number} submitted. Note: Immediate stock shortage of {order.shortage_quantity} units detected.", "warning")
            else:
                flash(f"Order {order.order_number} submitted successfully for admin verification.", "success")
            return redirect(url_for('sales.index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating order: {str(e)}", "danger")
            return redirect(url_for('sales.new_order'))

    customers = Customer.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).all()
    
    # Send current stock info for client-side display
    stock_map = {p.id: float(InventoryService.get_stock('FINISHED_GOOD', p.id)) for p in products}

    return render_template(
        'sales/new.html',
        customers=customers,
        products=products,
        stock_map=stock_map
    )

@sales_bp.route('/<int:order_id>/review', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner')
def review_order(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    feasibility = SalesService.check_order_stock_feasibility(order.id)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'approve':
            try:
                SalesService.approve_order(order.id, current_user.id)
                flash(f"Order {order.order_number} has been APPROVED.", "success")
                return redirect(url_for('billing.create_invoice', order_id=order.id))
            except ValueError as ve:
                flash(str(ve), "danger")
                return redirect(url_for('sales.review_order', order_id=order.id))
        elif action == 'reject':
            reason = request.form.get('rejection_reason', 'Rejected by Admin')
            SalesService.reject_order(order.id, current_user.id, reason)
            flash(f"Order {order.order_number} has been REJECTED.", "info")
            return redirect(url_for('sales.index'))

    return render_template('sales/review.html', order=order, feasibility=feasibility)
