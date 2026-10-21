import re
from datetime import datetime, timedelta, timezone

from flask import abort, redirect, render_template, session, url_for
from jinja2 import TemplateNotFound

from models import Device

# a device counts as online if it was seen within last 1 minutes
ONLINE_WINDOW_MINUTES = 1


# runs before every request in a blueprint: only logged-in users get in
def require_login():
    if not session.get("user_id"):
        return redirect(url_for("home"))


# render <folder>/<section>.html, so a new sub page is just a new template file
def render_section(folder, section, **context):
    if not re.fullmatch(r"[a-z_]+", section):
        abort(404)
    try:
        return render_template(f"{folder}/{section}.html", section=section, **context)
    except TemplateNotFound:
        abort(404)


# get device stats from the db (the logged-in user's devices only)
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
