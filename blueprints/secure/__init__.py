from flask import Blueprint

from blueprints.common import render_section, require_login

bp = Blueprint(
    "secure",
    __name__,
    url_prefix="/secure",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


# /secure opens secure.html; /secure/<name> renders templates/secure/<name>.html
@bp.route("", defaults={"section": "secure"})
@bp.route("/<section>")
def secure(section):
    return render_section("secure", section)
