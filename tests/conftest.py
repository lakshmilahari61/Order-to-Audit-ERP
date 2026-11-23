import pytest
from app import create_app, db
from config import TestingConfig
from scripts.seed_data import reset_and_seed_database

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        reset_and_seed_database()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
