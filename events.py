# =====================================================================================================================================================
# Modular event logging. Every event in the app (a device coming online,
# going offline, being added, and future event types) goes through log_event
# so every row in the events table has the same shape: who it's for, which
# device (if any), how severe it is, a short source tag, and a description.
#
# Add a new event type by adding a small wrapper function below that calls
# log_event with a fixed severity/source and a formatted description -
# callers never build Event rows by hand.
# =====================================================================================================================================================

import threading
import time
from datetime import datetime, timedelta, timezone

from blueprints.common import ONLINE_WINDOW_SECONDS
from extensions import db
from models import Device, Event

# how often the background watcher checks for devices that just went offline.
# kept well under ONLINE_WINDOW_SECONDS so "connection lost" fires promptly.
OFFLINE_CHECK_INTERVAL_SECONDS = 2


def _now():
    # naive UTC, matching how Device.last_online is stored
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ----- the single modular entry point every event goes through -----
def log_event(user_id, device_id, severity, source, description):
    db.session.add(Event(
        event_timestamp=_now(),
        user_id=user_id,
        device_id=device_id,
        severity=severity,
        source=source,
        event_description=description,
    ))


# ----- specific event types (add new ones here, following this pattern) -----
def log_device_added(user_id, device_id):
    log_event(user_id, device_id, "cold", "device", "New device added")


def log_connection_established(user_id, device_id, device_name):
    name = device_name or "unnamed device"
    log_event(
        user_id, device_id, "cold", "connection",
        f"Connection established with node: {name}",
    )


def log_connection_lost(user_id, device_id, device_name):
    name = device_name or "unnamed device"
    log_event(
        user_id, device_id, "warm", "connection",
        f"connection lost with node: {name}",
    )


# ----- fetch recent events for the dashboard -----
def recent_events(user_id, hours=24, limit=50):
    cutoff = _now() - timedelta(hours=hours)
    return (
        Event.query
        .filter(Event.user_id == user_id, Event.event_timestamp >= cutoff)
        .order_by(Event.event_timestamp.desc())
        .limit(limit)
        .all()
    )


# ----- background watcher: detects devices going offline -----
# Nothing signals "a device went offline" directly (the client just stops
# heartbeating), so this polls for devices whose last_online has fallen
# behind the online window and logs one "connection lost" event per offline
# stretch (it won't re-log on every poll - it checks whether a lost event
# already exists for this stretch before adding another).
def _check_offline_devices(app):
    with app.app_context():
        cutoff = _now() - timedelta(seconds=ONLINE_WINDOW_SECONDS)

        stale_devices = Device.query.filter(
            Device.last_online.isnot(None),
            Device.last_online < cutoff,
        ).all()

        if not stale_devices:
            return

        for device in stale_devices:
            already_logged = Event.query.filter(
                Event.device_id == device.device_id,
                Event.source == "connection",
                Event.severity == "warm",
                Event.event_timestamp >= device.last_online,
            ).first()
            if already_logged:
                continue
            log_connection_lost(device.user_id, device.device_id, device.device_name)

        db.session.commit()


def start_event_watcher(app):
    def loop():
        while True:
            try:
                _check_offline_devices(app)
            except Exception as e:
                print("event watcher error:", e)
            time.sleep(OFFLINE_CHECK_INTERVAL_SECONDS)

    threading.Thread(target=loop, daemon=True).start()
