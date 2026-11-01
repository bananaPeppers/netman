from flask import Blueprint, jsonify, session

bp = Blueprint("api", __name__, url_prefix="/api")


# api calls get a 401 (not a redirect to the login page) when not logged in
# @bp.before_request
# def require_login():
#     if not session.get("user_id"):
#         return jsonify(error="not logged in"), 401


# import the endpoint files last, so they can use bp (importing registers their routes)
from api import postPairingCode  # noqa: E402,F401
from api import getDeviceInfo  # noqa: E402,F401
from api import postGroup  # noqa: E402,F401
from api import postBlockedDomain  # noqa: E402,F401
from api import postSafeMode  # noqa: E402,F401
from api import postDeviceGroup  # noqa: E402,F401
