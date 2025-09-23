# This script is for one-time use to create your database tables.
from main import app, db

print("Connecting to the database and creating tables...")

# The 'with app.app_context()' is crucial. It sets up the
# necessary environment for SQLAlchemy to work.
with app.app_context():
    db.create_all()

print("Tables created successfully!")