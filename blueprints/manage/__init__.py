from flask import Blueprint

from blueprints.common import device_stats, render_section, require_login

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
def index(section):
    context = device_stats() if section == "devices" else {}
    return render_section("manage", section, **context)
