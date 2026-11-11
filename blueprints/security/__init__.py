from flask import Blueprint

from blueprints.common import render_section, require_login

bp = Blueprint(
    "security",
    __name__,
    url_prefix="/security",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


# security has two sub pages: "overview" and "logs". each sub page is its
# own template under templates/security/.
@bp.route("", defaults={"section": "overview"})
@bp.route("/<section>")
def security(section):
    return render_section("security", section)
