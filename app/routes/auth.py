from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def role_required(*allowed_roles):
    """
    Decorator to restrict view access to specific user roles.
    Prevents unauthorized URL-tampering.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            
            user_role = current_user.role.name if current_user.role else None
            # Owner and Admin generally have overarching administrative privileges where appropriate
            if user_role not in allowed_roles:
                flash(f"Access Denied: Your role '{user_role}' is not authorized to view this section.", "danger")
                # Redirect to their appropriate dashboard
                return redirect(url_for(f'dashboard.{user_role}' if user_role in ['owner', 'admin', 'salesman', 'production', 'auditor'] else 'auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        role_name = current_user.role.name if current_user.role else 'admin'
        return redirect(url_for(f'dashboard.{role_name}'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("This account is currently inactive. Please contact your system administrator.", "danger")
                return render_template('auth/login.html')

            login_user(user)
            role_name = user.role.name if user.role else 'admin'
            flash(f"Welcome back, {user.full_name} ({role_name.capitalize()})!", "success")
            
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for(f'dashboard.{role_name}'))
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out securely.", "info")
    return redirect(url_for('auth.login'))
