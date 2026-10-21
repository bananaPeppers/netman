from flask import Flask, abort, render_template, request, redirect, url_for, session
from sqlalchemy import text
from werkzeug.security import check_password_hash

from blueprints.dashboard import bp as dashboard_bp
from blueprints.manage import bp as manage_bp
from blueprints.secure import bp as secure_bp
from config.config import Config
from extensions import db
from models import User

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# each main page lives in its own folder under blueprints/
app.register_blueprint(dashboard_bp)
app.register_blueprint(manage_bp)
app.register_blueprint(secure_bp)

# login page: GET shows the form, POST authenticates the user
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template("login.html")

    # look up the user by username
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = User.query.filter_by(username=username).first()

    # reject if user is missing or the password doesn't match the stored hash
    if not user or not check_password_hash(user.password_hash, password):
        return render_template("login.html", username=username), 401

    # log the user in (clear any old session first)
    session.clear()
    session["user_id"] = user.id

    # users with a network go home, others must create one first
    return redirect(url_for("dashboard.index" if user.network else "network"))


# network page: GET shows the form, POST saves the network name for the user
@app.route("/network", methods=["GET", "POST"])
def network():
    # only logged-in users can access this page
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("network_name", "").strip()[:100]
        if name:
            # save the network name on this user's row, then go home
            user.network = name
            db.session.commit()
            return redirect(url_for("dashboard.index"))

    return render_template("network.html")


# clear the session and go back to the login page when logout btn is clicked
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


# health check to make sure if teh app has db connection or not
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
