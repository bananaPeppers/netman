# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Fri Oct 30 2026
# Description: API to generate random pairing key when the api is called. it will generate a key, hash it and save it in a db table: pairing_codes
# then the API will post the pairing code to the front end so that users can see it on the popup and use it to pait devices
# =====================================================================================================================================================


import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app, jsonify, session
from api import bp
from extensions import db
from models import PairingCode


# old logic. may use in future but for now code never expires
CODE_VALID_MINUTES = 10


# hash the pairing code
def hash_code(code):
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, code.encode(), hashlib.sha256).hexdigest()


# create a pairing code for the logged-in user, store its hash, return the code
@bp.route("/pairing/pairCode", methods=["POST"])
def create_pairing_code():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    code = f"{secrets.randbelow(10**8):08d}"
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        db.session.add(
            PairingCode(
                user_id=session["user_id"],
                pairing_code=code,
                code_hash=hash_code(code),
                created_at=now,
                expires_at=now + timedelta(minutes=CODE_VALID_MINUTES), #this is not userd for now
                status="pending",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create pairing code"}), 500

    return jsonify({"code": code}), 201