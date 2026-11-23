import os
from decimal import Decimal

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nit-trichy-erp-2026-secret-key-salt-9876')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'food_erp.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Factory State for GST intra/inter-state taxation determination
    FACTORY_STATE = "Tamil Nadu"
    FACTORY_NAME = "South Indian Traditional Foods Ltd."
    FACTORY_ADDRESS = "14 Industrial Estate, Thuvakudi, Tiruchirappalli, Tamil Nadu - 620015"
    FACTORY_GSTIN = "33AAAAA0000A1Z5"
    
    # Variance Threshold for alert flags (3%)
    VARIANCE_TOLERANCE_PERCENT = Decimal('3.0')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
