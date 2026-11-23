from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from flask import current_app
from app import db
from app.models import SalesOrder, SalesOrderItem, Product, Customer, CustomerProductPrice, AuditLog
from app.services.inventory_service import InventoryService

class SalesService:
    """
    Sales and Order Lifecycle Service.
    Handles salesman order placement, tax calculation, stock shortage checks,
    admin approval/rejection, and audit logging.
    """

    @staticmethod
    def get_unit_price(customer_id: int, product_id: int) -> Decimal:
        """Retrieves customer-contracted price or standard catalog selling price."""
        special = CustomerProductPrice.query.filter_by(customer_id=customer_id, product_id=product_id).first()
        if special:
            return Decimal(str(special.special_price))
        product = Product.query.get(product_id)
        if not product:
            raise ValueError(f"Product ID {product_id} not found.")
        return Decimal(str(product.selling_price))

    @staticmethod
    def generate_order_number() -> str:
        """Generates sequential order number (ORD-YYYY-XXXX)."""
        year = datetime.utcnow().strftime('%Y')
        count = SalesOrder.query.filter(SalesOrder.order_number.like(f'ORD-{year}-%')).count() + 1
        return f"ORD-{year}-{count:04d}"

    @staticmethod
    def create_order(salesman_id: int, customer_id: int, items_data: list, notes: str = None) -> SalesOrder:
        """
        Creates a new sales order submitted by a salesman.
        Performs tax breakdown and computes stock shortage if any.
        """
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"Customer ID {customer_id} not found.")

        factory_state = current_app.config.get('FACTORY_STATE', 'Tamil Nadu')
        is_intra_state = (customer.state.strip().lower() == factory_state.strip().lower())

        order_no = SalesService.generate_order_number()
        order = SalesOrder(
            order_number=order_no,
            salesman_id=salesman_id,
            customer_id=customer_id,
            order_date=datetime.utcnow().date(),
            status='Submitted',
            notes=notes
        )
        db.session.add(order)
        db.session.flush()

        total_taxable = Decimal('0.00')
        total_gst = Decimal('0.00')
        total_order = Decimal('0.00')
        total_shortage = Decimal('0.00')

        for item in items_data:
            p_id = int(item['product_id'])
            qty = Decimal(str(item['quantity']))
            product = Product.query.get(p_id)
            if not product:
                raise ValueError(f"Product ID {p_id} not found.")

            price = SalesService.get_unit_price(customer_id, p_id)
            taxable = (qty * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Tax calculations
            gst_rate = Decimal(str(product.gst_rate or '5.00'))
            if is_intra_state:
                # CGST 2.5% + SGST 2.5%
                half_rate = gst_rate / Decimal('2.0')
                cgst = (taxable * (half_rate / Decimal('100.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                sgst = (taxable * (half_rate / Decimal('100.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                igst = Decimal('0.00')
            else:
                # Inter-state: IGST 5.0%
                cgst = Decimal('0.00')
                sgst = Decimal('0.00')
                igst = (taxable * (gst_rate / Decimal('100.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            item_total = taxable + cgst + sgst + igst

            # Check stock
            is_avail, current_stock, shortage = InventoryService.check_stock('FINISHED_GOOD', p_id, qty)
            if not is_avail:
                total_shortage += shortage

            order_item = SalesOrderItem(
                sales_order_id=order.id,
                product_id=p_id,
                quantity=qty,
                unit_price=price,
                taxable_amount=taxable,
                gst_rate=gst_rate,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                total_amount=item_total
            )
            db.session.add(order_item)

            total_taxable += taxable
            total_gst += (cgst + sgst + igst)
            total_order += item_total

        order.total_taxable_amount = total_taxable
        order.total_gst_amount = total_gst
        order.total_order_amount = total_order
        order.shortage_quantity = total_shortage

        db.session.add(AuditLog(
            user_id=salesman_id,
            action='SUBMIT_SALES_ORDER',
            entity_type='SalesOrder',
            entity_id=order.id,
            details=f"Order {order_no} created for {customer.name}. Total: ₹{total_order}, Shortage: {total_shortage}"
        ))

        return order

    @staticmethod
    def check_order_stock_feasibility(order_id: int):
        """
        Inspects each line item against live finished goods inventory.
        Returns detailed status for Admin review.
        """
        order = SalesOrder.query.get(order_id)
        if not order:
            raise ValueError(f"Order ID {order_id} not found.")

        feasible = True
        items_detail = []
        overall_shortage = Decimal('0.00')

        for item in order.items:
            is_avail, current_stock, shortage = InventoryService.check_stock('FINISHED_GOOD', item.product_id, item.quantity)
            if not is_avail:
                feasible = False
                overall_shortage += shortage

            items_detail.append({
                'product_name': item.product.name,
                'quantity_ordered': item.quantity,
                'current_stock': current_stock,
                'shortage': shortage,
                'is_available': is_avail
            })

        order.shortage_quantity = overall_shortage
        db.session.commit()

        return {
            'order': order,
            'is_feasible': feasible,
            'total_shortage': overall_shortage,
            'items': items_detail
        }

    @staticmethod
    def approve_order(order_id: int, user_id: int):
        """
        Admin approves order.
        Strictly blocks approval if finished goods stock is insufficient.
        """
        check = SalesService.check_order_stock_feasibility(order_id)
        if not check['is_feasible']:
            raise ValueError(
                f"Cannot approve order {check['order'].order_number}: Stock shortage of {check['total_shortage']} packets exists."
            )

        order = check['order']
        order.status = 'Approved'

        db.session.add(AuditLog(
            user_id=user_id,
            action='APPROVE_SALES_ORDER',
            entity_type='SalesOrder',
            entity_id=order.id,
            details=f"Order {order.order_number} approved by Admin."
        ))
        db.session.commit()
        return order

    @staticmethod
    def reject_order(order_id: int, user_id: int, reason: str = "Insufficient stock / Admin rejected"):
        """Rejects order with recorded explanation."""
        order = SalesOrder.query.get(order_id)
        if not order:
            raise ValueError(f"Order ID {order_id} not found.")
        
        order.status = 'Rejected'
        order.notes = f"{order.notes or ''}\nRejection Reason: {reason}".strip()

        db.session.add(AuditLog(
            user_id=user_id,
            action='REJECT_SALES_ORDER',
            entity_type='SalesOrder',
            entity_id=order.id,
            details=f"Order {order.order_number} rejected. Reason: {reason}"
        ))
        db.session.commit()
        return order
