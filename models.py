from extensions import db


# Users table
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    network = db.Column(db.String(100), nullable=True)


# Devices table
class Device(db.Model):
    __tablename__ = "devices"

    device_id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    device_name = db.Column(db.String(100), nullable=True)

    operating_system = db.Column(db.String(100), nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)

    last_online = db.Column(db.DateTime, nullable=True)

    # group this device is assigned to; cleared automatically if that group is deleted
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.group_id", ondelete="SET NULL"),
        nullable=True,
    )


# Device groups table, one set of groups per network
class Group(db.Model):
    __tablename__ = "groups"
    __table_args__ = (
        db.UniqueConstraint("network", "group_name", name="unique_network_group"),
    )

    group_id = db.Column(db.Integer, primary_key=True)
    network = db.Column(db.String(100), nullable=False)
    group_name = db.Column(db.String(100), nullable=False)


# Domains blocked for either one device group or one device (never both)
class BlockedDomain(db.Model):
    __tablename__ = "blocked_domains"
    __table_args__ = (
        db.UniqueConstraint("group_id", "domain", name="unique_group_domain"),
    )

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=True,
    )
    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=True,
    )
    domain = db.Column(db.String(255), nullable=False)


# Safe mode flag for either one group or one device (never both)
class SafeMode(db.Model):
    __tablename__ = "safe_mode"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    enabled = db.Column(db.Boolean, nullable=False, default=False)


# Pairing codes table
class PairingCode(db.Model):
    __tablename__ = "pairing_codes"

    pairing_id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Associated device after successful pairing
    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.device_id"),
        nullable=True
    )

    pairing_code = db.Column(db.String(8), nullable=False, unique=True)

    code_hash = db.Column(db.String(64), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False)

    expires_at = db.Column(db.DateTime, nullable=False)

    status = db.Column(
        db.Enum("pending", "claimed", "approved", "expired", "rejected"),
        nullable=False,
        default="pending",
    )