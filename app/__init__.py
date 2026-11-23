import os
from decimal import Decimal
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'

def format_currency(value):
    if value is None:
        return "₹0.00"
    try:
        dec = Decimal(str(value))
        return f"₹{dec:,.2f}"
    except Exception:
        return f"₹{value}"

def format_qty(value, unit=""):
    if value is None:
        return "0"
    try:
        dec = Decimal(str(value))
        # Format cleanly without trailing zeroes if whole number
        formatted = f"{dec:f}".rstrip('0').rstrip('.') if '.' in f"{dec:f}" else f"{dec}"
        return f"{formatted} {unit}".strip()
    except Exception:
        return f"{value} {unit}".strip()

def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        from config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)

    # Ensure instance directory exists
    instance_dir = os.path.join(app.root_path, '..', 'instance')
    os.makedirs(instance_dir, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Register Jinja context filters
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['qty'] = format_qty

    # Context processor to make factory metadata available to all templates
    @app.context_processor
    def inject_global_vars():
        return {
            'factory_name': app.config.get('FACTORY_NAME', 'South Indian Traditional Foods Ltd.'),
            'factory_state': app.config.get('FACTORY_STATE', 'Tamil Nadu'),
            'factory_gstin': app.config.get('FACTORY_GSTIN', '33AAAAA0000A1Z5'),
        }

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.master import master_bp
    from app.routes.purchases import purchases_bp
    from app.routes.production import production_bp
    from app.routes.sales import sales_bp
    from app.routes.billing import billing_bp
    from app.routes.dispatch import dispatch_bp
    from app.routes.payments import payments_bp
    from app.routes.reports import reports_bp
    from app.routes.benchmark import benchmark_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(master_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(production_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(benchmark_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
