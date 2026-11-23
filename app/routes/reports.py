from datetime import datetime
from flask import Blueprint, render_template, request, Response, send_file, flash, redirect, url_for
from flask_login import login_required
import io
from app.services.report_service import ReportService
from app.services.inventory_service import InventoryService
from app.models import Product, Customer, Payment

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    report_type = request.args.get('type', 'sales_register')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

    report_data = []
    summary_data = None

    if report_type == 'sales_register':
        report_data = ReportService.get_sales_register(start_date, end_date)
    elif report_type == 'gst_summary':
        summary_data = ReportService.get_gst_summary(start_date, end_date)
    elif report_type == 'purchase_register':
        report_data = ReportService.get_purchase_register(start_date, end_date)
    elif report_type == 'stock_ledger':
        report_data = ReportService.get_stock_ledger(start_date, end_date)
    elif report_type == 'raw_materials_stock':
        report_data = InventoryService.get_stock_summary('RAW_MATERIAL')
    elif report_type == 'packaging_stock':
        report_data = InventoryService.get_stock_summary('PACKAGING')
    elif report_type == 'finished_goods_stock':
        report_data = InventoryService.get_stock_summary('FINISHED_GOOD')
    elif report_type == 'production_costing':
        report_data = ReportService.get_production_costing_report(start_date, end_date)
    elif report_type == 'consumption_variance':
        report_data = ReportService.get_material_consumption_variance_report()
    elif report_type == 'customer_sales':
        sales = ReportService.get_sales_register(start_date, end_date)
        cust_map = {}
        for s in sales:
            c = s['Customer']
            cust_map[c] = cust_map.get(c, 0.0) + s['Total Amount (₹)']
        report_data = [{'Customer': k, 'Total Sales (₹)': round(v, 2)} for k, v in cust_map.items()]
    elif report_type == 'receivables':
        customers = Customer.query.filter_by(is_active=True).all()
        report_data = [
            {
                'Customer': c.name,
                'Type': c.customer_type,
                'State': c.state,
                'Total Invoiced (₹)': float(c.get_total_invoiced()),
                'Total Collected (₹)': float(c.get_total_paid()),
                'Outstanding (₹)': float(c.get_outstanding_balance())
            }
            for c in customers
        ]

    return render_template(
        'reports/index.html',
        report_type=report_type,
        report_data=report_data,
        summary_data=summary_data,
        start_date=start_date_str or '',
        end_date=end_date_str or ''
    )

@reports_bp.route('/export/csv/<report_type>')
@login_required
def export_csv(report_type):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    s_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    e_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

    data = _get_export_data(report_type, s_date, e_date)
    if not data:
        flash("No data available to export.", "warning")
        return redirect(url_for('reports.index', type=report_type))

    csv_content = ReportService.export_to_csv(data)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={report_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

@reports_bp.route('/export/excel/<report_type>')
@login_required
def export_excel(report_type):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    s_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    e_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

    data = _get_export_data(report_type, s_date, e_date)
    if not data:
        flash("No data available to export.", "warning")
        return redirect(url_for('reports.index', type=report_type))

    excel_bytes = ReportService.export_to_excel(data, sheet_name=report_type[:30])
    return send_file(
        io.BytesIO(excel_bytes),
        as_attachment=True,
        download_name=f"{report_type}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def _get_export_data(report_type, start_date, end_date):
    if report_type == 'sales_register':
        return ReportService.get_sales_register(start_date, end_date)
    elif report_type == 'purchase_register':
        return ReportService.get_purchase_register(start_date, end_date)
    elif report_type == 'stock_ledger':
        return ReportService.get_stock_ledger(start_date, end_date)
    elif report_type == 'production_costing':
        return ReportService.get_production_costing_report(start_date, end_date)
    elif report_type == 'consumption_variance':
        return ReportService.get_material_consumption_variance_report()
    elif report_type == 'receivables':
        customers = Customer.query.filter_by(is_active=True).all()
        return [
            {
                'Customer': c.name,
                'Type': c.customer_type,
                'State': c.state,
                'Total Invoiced (₹)': float(c.get_total_invoiced()),
                'Total Collected (₹)': float(c.get_total_paid()),
                'Outstanding (₹)': float(c.get_outstanding_balance())
            }
            for c in customers
        ]
    return []
