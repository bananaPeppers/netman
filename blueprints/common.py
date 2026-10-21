import re

from flask import abort, redirect, render_template, session, url_for
from jinja2 import TemplateNotFound


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
