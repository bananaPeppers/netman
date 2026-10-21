from flask_sqlalchemy import SQLAlchemy

# shared db object, so all blueprints can use it without importing app.py
db = SQLAlchemy()
