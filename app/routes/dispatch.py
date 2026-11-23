from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import GSTInvoice, DispatchRecord, AuditLog
from app.services.inventory_service import InventoryService
from app.routes.auth import role_required

dispatch_bp = Blueprint('dispatch', __name__, url_prefix='/dispatch')

@dispatch_bp.route('/')
@login_required
def index():
    dispatches = DispatchRecord.query.order_by(DispatchRecord.dispatch_date.desc(), DispatchRecord.id.desc()).all()
    # Also find invoices ready for dispatch
    ready_invoices = GSTInvoice.query.filter(
        GSTInvoice.status.in_(['Issued', 'Partial', 'Paid']),
        ~GSTInvoice.dispatches.any()
    ).all()
    return render_template('dispatch/list.html', dispatches=dispatches, ready_invoices=ready_invoices)

@dispatch_bp.route('/record/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'owner')
def record_dispatch(invoice_id):
    invoice = GSTInvoice.query.get_or_404(invoice_id)
    if invoice.dispatches:
        flash(f"Invoice {invoice.invoice_number} has already been dispatched.", "warning")
        return redirect(url_for('dispatch.index'))

    if request.method == 'POST':
        vehicle_no = request.form.get('vehicle_no', '').strip()
        carrier_name = request.form.get('carrier_name', '').strip()
        dispatch_date_str = request.form.get('dispatch_date')
        notes = request.form.get('notes', '')

        d_date = datetime.strptime(dispatch_date_str, '%Y-%m-%d').date() if dispatch_date_str else datetime.utcnow().date()

        try:
            total_dispatched_qty = Decimal('0.00')

            # Atomically deduct finished goods stock
            for item in invoice.items:
                InventoryService.record_movement(
                    transaction_type='DISPATCH',
                    item_type='FINISHED_GOOD',
                    item_id=item.product_id,
                    quantity=-item.quantity, # Negative for reduction
                    unit=item.product.unit if item.product else 'packets',
                    unit_cost=item.unit_price,
                    source_doc_type='GSTInvoice',
                    source_doc_id=invoice.id,
                    notes=f"Dispatched under Invoice {invoice.invoice_number} to {invoice.customer_name}"
                )
                total_dispatched_qty += item.quantity

            # Create Dispatch Record
            disp = DispatchRecord(
                invoice_id=invoice.id,
                dispatch_date=d_date,
                vehicle_no=vehicle_no,
                carrier_name=carrier_name,
                quantity_dispatched=total_dispatched_qty,
                notes=notes,
                created_by_id=current_user.id
            )
            db.session.add(disp)

            if invoice.sales_order:
                invoice.sales_order.status = 'Dispatched'

            db.session.add(AuditLog(
                user_id=current_user.id,
                action='RECORD_DISPATCH',
                entity_type='DispatchRecord',
                entity_id=invoice.id,
                details=f"Dispatched {total_dispatched_qty} units for Invoice {invoice.invoice_number} via {carrier_name} ({vehicle_no})"
            ))

            db.session.commit()
            flash(f"Dispatch recorded successfully. Finished goods inventory reduced by {total_dispatched_qty} units.", "success")
            return redirect(url_for('dispatch.index'))

        except Exception as e:
            db.session.rollback()
            flash(f"Dispatch failed: {str(e)}", "danger")
            return redirect(url_for('dispatch.record_dispatch', invoice_id=invoice.id))

    return render_template('dispatch/record.html', invoice=invoice, today_date=datetime.utcnow().strftime('%Y-%m-%d'))
