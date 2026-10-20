from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from config.config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)


@app.route("/")
def home():
    return render_template("login.html")


@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e.__class__.__name__}"
    return {"status": "healthy", "database": db_status}


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
