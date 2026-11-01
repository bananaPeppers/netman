from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, session

from blueprints.common import device_stats, require_login, ONLINE_WINDOW_MINUTES
from extensions import db
from models import User, Device

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
def dashboard():
    user = db.session.get(User, session["user_id"])
    online_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=ONLINE_WINDOW_MINUTES
    )
    devices = Device.query.filter_by(user_id=session["user_id"]).all()
    return render_template(
        "dashboard/dashboard.html",
        network=user.network if user else "-",
        devices=devices,
        online_cutoff=online_cutoff,
        **device_stats(),
    )
