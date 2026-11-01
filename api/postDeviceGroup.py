# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Sat Oct 31 2026
# Description: API to assign a device to a group (or clear it), stored in devices.group_id
# =====================================================================================================================================================


from flask import jsonify, request, session
from api import bp
from api.groupCheck import owned_group
from api.targetCheck import owned_target
from extensions import db
from models import Device


@bp.route("/manage/setDeviceGroup", methods=["POST"])
def set_device_group():
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    data = request.get_json(silent=True) or {}
    target = owned_target({"device_id": data.get("device_id")})
    if not target:
        return jsonify(error="Device not found"), 404
    device = db.session.get(Device, target[1])

    # group_id null means "no group"
    group = None
    if data.get("group_id") is not None:
        group = owned_group(data["group_id"])
        if not group:
            return jsonify(error="Group not found"), 404

    device.group_id = group.group_id if group else None
    db.session.commit()

    return jsonify(
        device_id=device.device_id,
        group_id=device.group_id,
        group_name=group.group_name if group else None,
    ), 200
