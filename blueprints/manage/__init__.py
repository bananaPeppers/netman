from datetime import datetime, timedelta, timezone

from flask import Blueprint, session

from blueprints.common import render_section, require_login
from models import Device

# a device counts as online if it was seen within last 1 minutes. 
ONLINE_WINDOW_MINUTES = 1

bp = Blueprint(
    "manage",
    __name__,
    url_prefix="/manage",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


# get device stats from the db
def device_stats():
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=ONLINE_WINDOW_MINUTES
    )
    mine = Device.query.filter_by(user_id=session["user_id"])
    total = mine.count()
    if total == 0:
        return {"total": "-", "online": "-", "offline": "-"}
    online = mine.filter(Device.last_online >= cutoff).count()
    return {"total": total, "online": online, "offline": total - online}



@bp.route("", defaults={"section": "devices"})
@bp.route("/<section>")
def index(section):
    context = device_stats() if section == "devices" else {}
    return render_section("manage", section, **context)
