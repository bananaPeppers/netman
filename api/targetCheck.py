# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Sat Oct 31 2026
# Description: rules (blocked domains, safe mode) can belong to a group or to a single device.
# This works out which one a request is for and checks it belongs to the logged-in user.
# =====================================================================================================================================================

from flask import session
from api.groupCheck import owned_group
from extensions import db
from models import Device


# a device belongs to the logged-in user when its user_id matches
def _owned_device(device_id):
    device = db.session.get(Device, device_id)
    if not device or device.user_id != session.get("user_id"):
        return None
    return device


# returns ("group_id" | "device_id", id) for the group/device in the request, or None if it isn't theirs
def owned_target(data):
    if data.get("group_id") is not None:
        group = owned_group(data["group_id"])
        return ("group_id", group.group_id) if group else None
    if data.get("device_id") is not None:
        device = _owned_device(data["device_id"])
        return ("device_id", device.device_id) if device else None
    return None
