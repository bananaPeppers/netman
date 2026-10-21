from flask import Blueprint, render_template, session

from blueprints.common import device_stats, require_login
from extensions import db
from models import User

bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


# show the logged-in user's network name
@bp.route("")
def index():
    user = db.session.get(User, session["user_id"])
    return render_template(
        "dashboard/index.html",
        network=user.network if user else "-",
        **device_stats(),
    )
