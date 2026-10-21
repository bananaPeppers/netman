from flask_sqlalchemy import SQLAlchemy

# shared db object, so blueprints can use it without importing app.py
db = SQLAlchemy()
