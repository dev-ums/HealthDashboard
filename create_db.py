# filepath: e:\HealthDashboard\create_db.py
from app import app, db  # Import the app and database instance
with app.app_context():   # Create tables inside the app context
    db.create_all()       # Generates the SQLite database file (`instance/site.db`)