from datetime import datetime, timedelta, timezone

from flask import Blueprint, session

from blueprints.common import (
    ONLINE_WINDOW_SECONDS,
    activity_since,
    device_stats,
    render_section,
    require_login,
)
from events import all_events
from extensions import db
from models import Device, User

bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


# a device seen since this time counts as online
def online_cutoff():
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        seconds=ONLINE_WINDOW_SECONDS
    )


# dashboard has two sub pages: "overview" (network overview) and "activity"
# (device activity). each sub page is its own template under templates/dashboard/.
@bp.route("", defaults={"section": "overview"})
@bp.route("/<section>")
def dashboard(section):
    context = {}
    if section == "overview":
        user = db.session.get(User, session["user_id"])
        context["network"] = user.network if user else "-"
        context["devices"] = Device.query.filter_by(
            user_id=session["user_id"]
        ).all()
        context["online_cutoff"] = online_cutoff()
        context["events"] = all_events(session["user_id"])
        context.update(device_stats())
    elif section == "activity":
        context["since"] = activity_since()
        context["devices"] = Device.query.filter_by(
            user_id=session["user_id"]
        ).all()
        context["online_cutoff"] = online_cutoff()
    return render_section("dashboard", section, **context)
