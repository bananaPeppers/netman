import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app, jsonify, session

from api import bp
from extensions import db
from models import PairingCode

# a pairing code stops working this many minutes after it is created
CODE_VALID_MINUTES = 5


# hash a code with the app's secret key, so the db never holds the real code
def hash_code(code):
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, code.encode(), hashlib.sha256).hexdigest()


# create a pairing code for the logged-in user: store its hash, return the code
@bp.route("/pairing/pairCode", methods=["POST"])
def create_pairing_code():
    # random 8-digit code, zero padded
    code = f"{secrets.randbelow(10**8):08d}"

    # times are stored in UTC
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.add(
        PairingCode(
            user_id=session["user_id"],
            code_hash=hash_code(code),
            created_at=now,
            expires_at=now + timedelta(minutes=CODE_VALID_MINUTES),
            status="pending",
        )
    )
    db.session.commit()

    response = jsonify(code=code, expires_in=CODE_VALID_MINUTES * 60)
    response.headers["Cache-Control"] = "no-store"
    return response
