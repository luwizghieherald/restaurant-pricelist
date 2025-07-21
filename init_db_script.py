import os
from app import app # Import the Flask app instance
from models import db, AdminUser # Import db and AdminUser model
from werkzeug.security import generate_password_hash

# Load environment variables (important for DATABASE_URL)
from dotenv import load_dotenv
load_dotenv()

with app.app_context():
    print("Attempting to initialize database...")

    # IMPORTANT: db.drop_all() has been removed.
    # This script will now only create tables if they do not exist,
    # preserving existing data.
    print("Creating new database tables based on models (if they don't exist)...")
    db.create_all() # Create all defined database tables from models.py
    print("Tables created (or already existed).")

    # Create a default admin user if one does not already exist
    if not AdminUser.query.filter_by(username='admin').first():
        print("Creating default admin user...")
        admin_user = AdminUser(username='admin')
        # IMPORTANT: Change this password immediately after the first successful deployment and login!
        admin_user.set_password('adminpassword')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created (username: admin, password: adminpassword).")
        print("**REMEMBER TO CHANGE THIS PASSWORD IMMEDIATELY AFTER LOGIN!**")
    else:
        print("Admin user already exists. Skipping creation.")

    print("Database initialization script finished.")
