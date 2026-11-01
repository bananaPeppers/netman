# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Sat Oct 31 2026
# Description: API to turn safe mode on/off for a device group or a single device, stored in the safe_mode table
# =====================================================================================================================================================


from flask import jsonify, request, session
from sqlalchemy.exc import IntegrityError
from api import bp
from api.targetCheck import owned_target
from extensions import db
from models import SafeMode


@bp.route("/manage/setSafeMode", methods=["POST"])
def set_safe_mode():
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    data = request.get_json(silent=True) or {}
    target = owned_target(data)
    if not target:
        return jsonify(error="Group or device not found"), 404
    column, target_id = target

    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        return jsonify(error="enabled must be true or false"), 400

    # one row per group/device: update it if it exists, otherwise create it
    row = SafeMode.query.filter_by(**{column: target_id}).first()
    if row:
        row.enabled = enabled
    else:
        db.session.add(SafeMode(**{column: target_id, "enabled": enabled}))

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Could not save safe mode"), 409

    return jsonify(enabled=enabled), 200
