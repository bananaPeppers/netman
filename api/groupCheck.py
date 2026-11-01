# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Fri Oct 30 2026
# Description: check if a group belongs to a logged-in user
# Without this check, anyone logged in could change another network's groups just by sending a different group_id in the request.
# =======================================================================================================================

from flask import session
from extensions import db
from models import Group, User



def owned_group(group_id):
    user = db.session.get(User, session.get("user_id"))
    group = db.session.get(Group, group_id)
    if not user or not group or group.network != user.network:
        return None
    return group
