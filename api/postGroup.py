# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Sat Oct 31 2026
# Description: API to create a device group. groups belong to the logged-in user's network and are saved in the groups table
# =====================================================================================================================================================


from flask import jsonify, request, session
from sqlalchemy.exc import IntegrityError
from api import bp
from extensions import db
from models import Group, User


@bp.route("/manage/createGroup", methods=["POST"])
def create_group():
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    user = db.session.get(User, session["user_id"])
    if not user or not user.network:
        return jsonify(error="Set up your network before creating groups"), 400

    data = request.get_json(silent=True) or {}
    group_name = (data.get("group_name") or "").strip()

    if not group_name:
        return jsonify(error="Group name cannot be empty"), 400
    if len(group_name) > 100:
        return jsonify(error="Group name must be 100 characters or fewer"), 400

    group = Group(network=user.network, group_name=group_name)
    try:
        db.session.add(group)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="A group with that name already exists"), 409

    return jsonify(group_id=group.group_id, group_name=group.group_name), 201


@bp.route("/manage/deleteGroup", methods=["POST"])
def delete_group():
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    user = db.session.get(User, session["user_id"])
    data = request.get_json(silent=True) or {}
    group = db.session.get(Group, data.get("group_id"))

    # only delete groups on the logged-in user's own network
    if not user or not group or group.network != user.network:
        return jsonify(error="Group not found"), 404

    try:
        db.session.delete(group)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Group is still in use and cannot be deleted"), 409

    return jsonify(deleted=True), 200
