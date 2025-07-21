import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime
from models import db, MenuItem, AdminUser, ActivityLog
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/restaurant_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_development')

db.init_app(app)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

def login_required(f):
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
    menu_items = MenuItem.query.order_by(MenuItem.name).all()
    activity_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
    return render_template('index.html', menu_items=menu_items, activity_logs=activity_logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = AdminUser.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    menu_items = MenuItem.query.order_by(MenuItem.name).all()
    return render_template('admin.html', menu_items=menu_items)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price_str = request.form['price'].replace(',', '') # Get price as string, remove commas
        print(f"DEBUG: Received add request for: Name='{name}', Description='{description}', Price_str='{price_str}'") # Debug print

        try:
            price = int(price_str) # Convert to integer
            new_item = MenuItem(name=name, description=description, price=price)
            db.session.add(new_item) # Add the new MenuItem to the session
            db.session.add(ActivityLog(action=f'Added new item: {name}')) # Add log entry

            print("DEBUG: Added MenuItem and ActivityLog to session. Attempting commit...") # Debug print
            db.session.commit() # Commit the transaction to the database
            print("DEBUG: db.session.commit() successful!") # Debug print

            flash('Item added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except ValueError:
            print(f"DEBUG: ValueError: Price '{price_str}' is not a whole number.") # Debug print
            flash('Price must be a whole number.', 'danger')
            db.session.rollback() # Rollback if price conversion fails
        except Exception as e:
            db.session.rollback() # Rollback the session in case of any other error
            print(f"DEBUG: Error during add_item: {e}") # Debug print
            flash(f'Error adding item: {e}', 'danger')
    return render_template('admin_add_edit.html', title='Add New Item')

@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        new_price = request.form['price'].replace(',', '')
        try:
            item.price = int(new_price)
            db.session.add(ActivityLog(action=f'Updated item: {item.name}'))
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
    item = MenuItem.query.get_or_404(item_id)
    try:
        db.session.delete(item)
        db.session.add(ActivityLog(action=f'Deleted item: {item.name}'))
        db.session.commit()
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
