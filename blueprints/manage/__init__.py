from datetime import datetime, timedelta, timezone

from flask import Blueprint, session

from blueprints.common import (
    ONLINE_WINDOW_MINUTES,
    device_stats,
    render_section,
    require_login,
)
from models import Device

bp = Blueprint(
    "manage",
    __name__,
    url_prefix="/manage",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


@bp.route("", defaults={"section": "devices"})
@bp.route("/<section>")
def manage(section):
    context = device_stats() if section == "devices" else {}
    if section == "devices":
        context["devices"] = Device.query.filter_by(user_id=session["user_id"]).all()
        # a device seen since this time counts as online
        context["online_cutoff"] = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(minutes=ONLINE_WINDOW_MINUTES)
    return render_section("manage", section, **context)
