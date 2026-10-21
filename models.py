from extensions import db


# users class to get user info from db
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    network = db.Column(db.String(100), nullable=True)


# class to get device info from db
class Device(db.Model):
    __tablename__ = "devices"
    device_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    last_online = db.Column(db.DateTime, nullable=True)


# pairing_codes table: short-lived codes used to connect a client app to a user
class PairingCode(db.Model):
    __tablename__ = "pairing_codes"
    pairing_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(
        db.Enum("pending", "claimed", "approved", "expired", "rejected"),
        nullable=False,
        default="pending",
    )
