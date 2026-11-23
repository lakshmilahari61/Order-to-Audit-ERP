import os
from app import create_app, db
from app.models import User

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Check if database has been seeded; if not, seed cleanly
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            print("[*] Performing first-time database seed with demo data...")
            from scripts.seed_data import reset_and_seed_database
            reset_and_seed_database()
            print("[+] Seed complete! Server ready.")

    port = int(os.environ.get('PORT', 5000))
    print(f"\n=======================================================")
    print(f" Order-to-Audit ERP — NIT Tiruchirappalli Winter 2026")
    print(f" Web Server Running at: http://127.0.0.1:{port}")
    print(f" Demo Admin: admin / admin123")
    print(f" NIT Benchmark UI: http://127.0.0.1:{port}/benchmark")
    print(f"=======================================================\n")
    app.run(host='127.0.0.1', port=port, debug=True)
