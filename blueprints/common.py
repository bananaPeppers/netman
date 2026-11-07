import re
from datetime import datetime, timedelta, timezone

from flask import abort, redirect, render_template, session, url_for
from jinja2 import TemplateNotFound

from models import Device


ONLINE_WINDOW_SECONDS = 15


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


def offline_since(last_online):
    if not last_online:
        return ""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = now - last_online
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return ""
    if hours < 24:
        return f"{int(hours)} hr"
    days = hours / 24
    if days < 7:
        return f"{int(days)} d"
    weeks = days / 7
    if weeks < 4:
        return f"{int(weeks)} wk"
    months = days / 30
    if months < 2:
        return "1m"
    return ""


# format a naive-UTC timestamp (e.g. Event.event_timestamp) as "HH:MM" in
# EST, the same fixed UTC-5 offset the security page's JS clock uses.
def est_time(dt):
    if not dt:
        return ""
    return (dt - timedelta(hours=5)).strftime("%H:%M")


# get device stats from the db (the logged-in user's devices only)
def device_stats():
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        seconds=ONLINE_WINDOW_SECONDS
    )
    mine = Device.query.filter_by(user_id=session["user_id"])
    total = mine.count()
    if total == 0:
        return {"total": "-", "online": "-", "offline": "-"}
    online = mine.filter(Device.last_online >= cutoff).count()
    return {"total": total, "online": online, "offline": total - online}
