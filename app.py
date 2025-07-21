import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime
from models import db, MenuItem, AdminUser, ActivityLog
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/restaurant_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_development')

print(f"DEBUG: SQLALCHEMY_DATABASE_URI configured as: {app.config['SQLALCHEMY_DATABASE_URI']}")

db.init_app(app)

@app.context_processor
def inject_now():
    """Makes the current datetime object available as 'now' in all templates."""
    return {'now': datetime.utcnow()}

def login_required(f):
    """Decorator to protect admin routes, ensuring a user is logged in."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    """Renders the public price list, categorizing and ordering menu items."""
    all_menu_items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    
    # Define the desired order of categories
    # IMPORTANT: Ensure these strings match the 'Category' input exactly in admin panel
    category_order = [
        "Petiscos (Starters)", "Salads", "Pizzas", "Burgers", "Chips", "Pastas",
        "Sea Food", "Prego no Pao", "Frango no churrasco", "Sweet Stuff",
        "Hot Drinks", "Cold Beverages", "Bar"
    ]

    # Group menu items by category
    categorized_menu_items = defaultdict(list)
    for item in all_menu_items:
        categorized_menu_items[item.category].append(item)

    # Create an ordered dictionary based on category_order
    ordered_categorized_menu_items = {}
    for category_name in category_order:
        if category_name in categorized_menu_items:
            # Sort items within each category by name
            categorized_menu_items[category_name].sort(key=lambda item: item.name)
            ordered_categorized_menu_items[category_name] = categorized_menu_items[category_name]
    
    # Add any categories not in the predefined order at the end (e.g., "Uncategorized")
    # These will be sorted alphabetically by category name
    for category_name in sorted(categorized_menu_items.keys()):
        if category_name not in ordered_categorized_menu_items:
            categorized_menu_items[category_name].sort(key=lambda item: item.name)
            ordered_categorized_menu_items[category_name] = categorized_menu_items[category_name]

    # Activity logs are fetched but not displayed on the public home page as per request
    activity_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
    
    return render_template('index.html', categorized_menu_items=ordered_categorized_menu_items, activity_logs=activity_logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles admin login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = AdminUser.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username # Store username in session
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handles admin logout."""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None) # Remove username from session
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    """Displays the admin dashboard with all menu items."""
    menu_items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template('admin.html', menu_items=menu_items)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_item():
    """Allows admin to add a new menu item."""
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        price_str = request.form['price'].replace(',', '').strip()
        category = request.form['category'].strip()
        if not category:
            category = 'Uncategorized'

        print(f"DEBUG: Received add request for: Name='{name}', Description='{description}', Price_str='{price_str}', Category='{category}'")

        try:
            price = int(price_str)
            new_item = MenuItem(name=name, description=description, price=price, category=category)
            db.session.add(new_item)
            db.session.add(ActivityLog(action=f'Added new item: {name} (Category: {category}) by {session.get("admin_username", "Admin")}'))

            print("DEBUG: Added MenuItem and ActivityLog to session. Attempting commit...")
            db.session.commit()
            print("DEBUG: db.session.commit() successful!")
            
            all_items_after_commit = MenuItem.query.all()
            print(f"DEBUG: Items in DB after commit ({len(all_items_after_commit)} total):")
            for item in all_items_after_commit:
                print(f"  - ID: {item.id}, Name: {item.name}, Category: {item.category}, Price: {item.price}")

            flash('Item added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except ValueError:
            print(f"DEBUG: ValueError: Price '{price_str}' is not a whole number.")
            flash('Price must be a whole number.', 'danger')
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Error during add_item: {e}")
            flash(f'Error adding item: {e}', 'danger')
    return render_template('admin_add_edit.html', title='Add New Item')

@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Allows admin to edit an existing menu item."""
    item = MenuItem.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['name'].strip()
        item.description = request.form['description'].strip()
        new_price = request.form['price'].replace(',', '').strip()
        item.category = request.form['category'].strip()
        if not item.category:
            item.category = 'Uncategorized'

        try:
            item.price = int(new_price)
            db.session.add(ActivityLog(action=f'Updated item: {item.name} (Category: {item.category}) by {session.get("admin_username", "Admin")}'))
            db.session.commit()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except ValueError:
            flash('Price must be a whole number.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {e}', 'danger')
    return render_template('admin_add_edit.html', title='Edit Item', item=item)

@app.route('/admin/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    """Allows admin to delete a menu item."""
    item = MenuItem.query.get_or_404(item_id)
    try:
        db.session.delete(item)
        db.session.add(ActivityLog(action=f'Deleted item: {item.name} (Category: {item.category}) by {session.get("admin_username", "Admin")}'))
        db.session.commit()
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allows logged-in admin to change their password."""
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        admin_username = session.get('admin_username')
        admin_user = AdminUser.query.filter_by(username=admin_username).first()

        if not admin_user:
            flash('Admin user not found.', 'danger')
            return redirect(url_for('logout')) # Log out if user somehow not found

        if not admin_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('New password and confirm password do not match.', 'danger')
        elif len(new_password) < 6: # Basic password length validation
            flash('New password must be at least 6 characters long.', 'danger')
        else:
            try:
                admin_user.set_password(new_password)
                db.session.add(ActivityLog(action=f'Password changed for {admin_username}'))
                db.session.commit()
                flash('Password changed successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error changing password: {e}', 'danger')

    return render_template('change_password.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
