# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Sat Oct 31 2026
# Description: API to add/remove domains blocked for a device group or a single device, stored in the blocked_domains table
# =====================================================================================================================================================


from flask import jsonify, request, session
from sqlalchemy.exc import IntegrityError
from api import bp
from api.targetCheck import owned_target
from extensions import db
from models import BlockedDomain


@bp.route("/manage/addBlockedDomain", methods=["POST"])
def add_blocked_domain():
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    data = request.get_json(silent=True) or {}
    target = owned_target(data)
    if not target:
        return jsonify(error="Group or device not found"), 404
    column, target_id = target

    domain = (data.get("domain") or "").strip().lower()
    if not domain:
        return jsonify(error="Domain cannot be empty"), 400
    if len(domain) > 255:
        return jsonify(error="Domain must be 255 characters or fewer"), 400

    # the table only has a unique key for groups, so check devices ourselves
    if BlockedDomain.query.filter_by(**{column: target_id, "domain": domain}).first():
        return jsonify(error="That domain is already blocked here"), 409

    entry = BlockedDomain(**{column: target_id, "domain": domain})
    try:
        db.session.add(entry)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="That domain is already blocked here"), 409

    return jsonify(id=entry.id, domain=entry.domain), 201


@bp.route("/manage/deleteBlockedDomain", methods=["POST"])
def delete_blocked_domain():
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    data = request.get_json(silent=True) or {}
    entry = db.session.get(BlockedDomain, data.get("id"))
    owner = (
        owned_target({"group_id": entry.group_id, "device_id": entry.device_id})
        if entry
        else None
    )
    if not entry or not owner:
        return jsonify(error="Domain not found"), 404

    db.session.delete(entry)
    db.session.commit()
    return jsonify(deleted=True), 200
