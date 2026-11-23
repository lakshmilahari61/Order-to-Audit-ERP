import io
from datetime import datetime
from decimal import Decimal
import pandas as pd
from app import db
from app.models import (
    GSTInvoice, InvoiceItem, Purchase, PurchaseItem, ProductionRun,
    ProductionMaterialIssue, InventoryTransaction, Payment, Customer,
    Product, RawMaterial, PackagingMaterial
)
from app.services.inventory_service import InventoryService

class ReportService:
    """
    Comprehensive Auditing and Reporting Engine.
    Generates operational and statutory financial registers,
    inventory valuation statements, production variances, and exports to CSV & Excel.
    """

    @staticmethod
    def get_sales_register(start_date=None, end_date=None):
        query = GSTInvoice.query.filter(GSTInvoice.status != 'Cancelled')
        if start_date:
            query = query.filter(GSTInvoice.invoice_date >= start_date)
        if end_date:
            query = query.filter(GSTInvoice.invoice_date <= end_date)
        invoices = query.order_by(GSTInvoice.invoice_date.desc()).all()

        data = []
        for inv in invoices:
            data.append({
                'Invoice No': inv.invoice_number,
                'Date': inv.invoice_date.strftime('%Y-%m-%d'),
                'Customer': inv.customer_name,
                'State': inv.customer_state,
                'GSTIN': inv.customer_gstin,
                'Taxable Value (₹)': float(inv.taxable_amount),
                'CGST (₹)': float(inv.cgst_amount),
                'SGST (₹)': float(inv.sgst_amount),
                'IGST (₹)': float(inv.igst_amount),
                'Total Amount (₹)': float(inv.total_amount),
                'Status': inv.status
            })
        return data

    @staticmethod
    def get_gst_summary(start_date=None, end_date=None):
        sales = ReportService.get_sales_register(start_date, end_date)
        tot_taxable = sum((s['Taxable Value (₹)'] for s in sales), 0.0)
        tot_cgst = sum((s['CGST (₹)'] for s in sales), 0.0)
        tot_sgst = sum((s['SGST (₹)'] for s in sales), 0.0)
        tot_igst = sum((s['IGST (₹)'] for s in sales), 0.0)
        tot_tax = tot_cgst + tot_sgst + tot_igst
        tot_grand = sum((s['Total Amount (₹)'] for s in sales), 0.0)

        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_invoices': len(sales),
            'total_taxable': tot_taxable,
            'total_cgst': tot_cgst,
            'total_sgst': tot_sgst,
            'total_igst': tot_igst,
            'total_tax': tot_tax,
            'grand_total': tot_grand
        }

    @staticmethod
    def get_purchase_register(start_date=None, end_date=None):
        query = Purchase.query
        if start_date:
            query = query.filter(Purchase.purchase_date >= start_date)
        if end_date:
            query = query.filter(Purchase.purchase_date <= end_date)
        purchases = query.order_by(Purchase.purchase_date.desc()).all()

        data = []
        for p in purchases:
            for item in p.items:
                data.append({
                    'Purchase ID': p.id,
                    'Invoice Ref': p.invoice_number or 'N/A',
                    'Date': p.purchase_date.strftime('%Y-%m-%d'),
                    'Supplier': p.supplier.name if p.supplier else 'N/A',
                    'Material Type': item.material_type,
                    'Item Name': item.item_name,
                    'Quantity': float(item.quantity),
                    'Unit': item.unit,
                    'Rate (₹)': float(item.unit_rate),
                    'Total Amount (₹)': float(item.total_amount)
                })
        return data

    @staticmethod
    def get_stock_ledger(start_date=None, end_date=None):
        query = InventoryTransaction.query
        if start_date:
            query = query.filter(InventoryTransaction.created_at >= start_date)
        if end_date:
            query = query.filter(InventoryTransaction.created_at <= end_date)
        transactions = query.order_by(InventoryTransaction.id.asc()).all()

        data = []
        for tx in transactions:
            item_name = "Unknown"
            if tx.item_type == 'RAW_MATERIAL':
                rm = RawMaterial.query.get(tx.item_id)
                item_name = rm.name if rm else f"RM#{tx.item_id}"
            elif tx.item_type == 'PACKAGING':
                pm = PackagingMaterial.query.get(tx.item_id)
                item_name = pm.name if pm else f"PKG#{tx.item_id}"
            elif tx.item_type == 'FINISHED_GOOD':
                p = Product.query.get(tx.item_id)
                item_name = p.name if p else f"FG#{tx.item_id}"

            data.append({
                'Tx ID': tx.id,
                'Timestamp': tx.created_at.strftime('%Y-%m-%d %H:%M'),
                'Type': tx.transaction_type,
                'Category': tx.item_type,
                'Item': item_name,
                'Quantity': float(tx.quantity),
                'Unit': tx.unit,
                'Unit Cost (₹)': float(tx.unit_cost or 0),
                'Running Balance': float(tx.running_balance or 0),
                'Document': f"{tx.source_doc_type} #{tx.source_doc_id}" if tx.source_doc_type else 'Direct',
                'Notes': tx.notes or ''
            })
        return data

    @staticmethod
    def get_production_costing_report(start_date=None, end_date=None):
        query = ProductionRun.query
        if start_date:
            query = query.filter(ProductionRun.production_date >= start_date)
        if end_date:
            query = query.filter(ProductionRun.production_date <= end_date)
        runs = query.order_by(ProductionRun.production_date.desc()).all()

        data = []
        for r in runs:
            product = r.product
            selling_price = float(product.selling_price) if product else 0.0
            cost_pkt = float(r.cost_per_packet or 0.0)
            margin = selling_price - cost_pkt
            margin_pct = (margin / selling_price * 100.0) if selling_price > 0 else 0.0

            data.append({
                'Batch No': r.batch_number,
                'Date': r.production_date.strftime('%Y-%m-%d'),
                'Product': product.name if product else 'N/A',
                'Expected Output': float(r.expected_output),
                'Actual Output': float(r.actual_good_output),
                'Yield Var (%)': float(r.yield_variance_pct),
                'RM Cost (₹)': float(r.total_material_cost),
                'Pkg Cost (₹)': float(r.total_packaging_cost),
                'Labour (₹)': float(r.labour_expense),
                'Power/Gas (₹)': float(r.power_gas_expense),
                'Total Cost (₹)': float(r.total_production_cost),
                'Cost/Pkt (₹)': cost_pkt,
                'Selling Price (₹)': selling_price,
                'Margin/Pkt (₹)': round(margin, 2),
                'Margin (%)': round(margin_pct, 1)
            })
        return data

    @staticmethod
    def get_material_consumption_variance_report(production_run_id=None):
        query = ProductionMaterialIssue.query
        if production_run_id:
            query = query.filter_by(production_run_id=production_run_id)
        issues = query.all()

        data = []
        for issue in issues:
            run = issue.production_run
            data.append({
                'Batch No': run.batch_number if run else 'N/A',
                'Type': issue.material_type,
                'Material': issue.item_name,
                'Planned Qty': float(issue.planned_qty),
                'Actual Qty': float(issue.actual_qty),
                'Unit': issue.unit,
                'Variance (%)': float(issue.variance_pct),
                'Rate (₹)': float(issue.unit_rate),
                'Total Cost (₹)': float(issue.total_cost),
                'Alert': abs(float(issue.variance_pct)) > 3.0
            })
        return data

    @staticmethod
    def export_to_excel(data: list, sheet_name="Report") -> bytes:
        """Converts data list to an Excel XLSX byte stream."""
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_to_csv(data: list) -> str:
        """Converts data list to a CSV string."""
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
