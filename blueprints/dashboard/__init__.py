from flask import Blueprint, render_template

from blueprints.common import require_login

bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


# dashboard page
@bp.route("")
def index():
    return render_template("dashboard/index.html")
