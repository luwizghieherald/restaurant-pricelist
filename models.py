from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False) # Store as integer
    category = db.Column(db.String(50), nullable=False, default='Uncategorized') # New category field

    def __repr__(self):
        return f'<MenuItem {self.name}>'

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255)) # Increased length for modern hashes

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # CORRECTED AGAIN: Hashed password (self.password_hash) is the first argument,
        # plain password (password) is the second.
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<AdminUser {self.username}>'

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ActivityLog {self.action} at {self.timestamp}>'
