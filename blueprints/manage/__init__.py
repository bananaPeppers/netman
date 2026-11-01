from datetime import datetime, timedelta, timezone

from flask import Blueprint, session

from blueprints.common import (
    ONLINE_WINDOW_MINUTES,
    device_stats,
    render_section,
    require_login,
)
from extensions import db
from models import BlockedDomain, Device, Group, SafeMode, User

bp = Blueprint(
    "manage",
    __name__,
    url_prefix="/manage",
    template_folder="templates",
    static_folder="static",
)
bp.before_request(require_login)


# blocked domains and safe mode for the groups/devices shown on a page, keyed by their id.
# column is "group_id" or "device_id"
def rules_data(column, ids):
    domains, safe_mode = {}, {}
    if ids:
        blocked_col = getattr(BlockedDomain, column)
        rows = (
            BlockedDomain.query.filter(blocked_col.in_(ids))
            .order_by(BlockedDomain.id)
            .all()
        )
        for row in rows:
            domains.setdefault(getattr(row, column), []).append(
                {"id": row.id, "domain": row.domain}
            )

        safe_col = getattr(SafeMode, column)
        for row in SafeMode.query.filter(safe_col.in_(ids)).all():
            safe_mode[getattr(row, column)] = row.enabled
    return domains, safe_mode


# the groups on the logged-in user's network
def network_groups():
    user = db.session.get(User, session["user_id"])
    network = user.network if user else None
    if not network:
        return []
    return Group.query.filter_by(network=network).order_by(Group.group_id).all()


@bp.route("", defaults={"section": "devices"})
@bp.route("/<section>")
def manage(section):
    context = device_stats() if section == "devices" else {}
    if section == "devices":
        devices = Device.query.filter_by(user_id=session["user_id"]).all()
        context["devices"] = devices
        context["groups"] = network_groups()
        # a device seen since this time counts as online
        context["online_cutoff"] = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(minutes=ONLINE_WINDOW_MINUTES)
        context["rule_domains"], context["rule_safe_mode"] = rules_data(
            "device_id", [d.device_id for d in devices]
        )
    elif section == "groups":
        groups = network_groups()
        context["groups"] = groups
        context["rule_domains"], context["rule_safe_mode"] = rules_data(
            "group_id", [g.group_id for g in groups]
        )
    return render_section("manage", section, **context)
