# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Tue Nov 04 2026
# Description: Security page stats. Aggregates the network_stats rows for one of the
# logged-in user's devices over a time window (10 min / 30 min / 1 hr / 24 hr) and
# returns the inbound/outbound totals the security tile shows.
# =====================================================================================================================================================

from datetime import datetime, timedelta

from flask import jsonify, request, session
from sqlalchemy import func

from api import bp
from api.targetCheck import owned_target
from extensions import db
from models import NetworkStats

# windows the security page offers, in minutes
ALLOWED_MINUTES = {10, 30, 60, 1440}
DEFAULT_MINUTES = 10


@bp.route("/security/stats", methods=["POST"])
def security_stats():
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    data = request.get_json(silent=True) or {}

    # only report on a device the logged-in user owns
    target = owned_target({"device_id": data.get("device_id")})
    if not target:
        return jsonify(error="Device not found"), 404
    device_id = target[1]

    # clamp the range to one of the allowed windows
    try:
        minutes = int(data.get("minutes"))
    except (TypeError, ValueError):
        minutes = DEFAULT_MINUTES
    if minutes not in ALLOWED_MINUTES:
        minutes = DEFAULT_MINUTES

    # network_stats.timestamp is stored as naive local time by the client,
    # so compare against local "now"
    cutoff = datetime.now() - timedelta(minutes=minutes)

    row = (
        db.session.query(
            func.coalesce(func.sum(NetworkStats.incoming_packets), 0),
            func.coalesce(func.sum(NetworkStats.outgoing_packets), 0),
            func.coalesce(func.sum(NetworkStats.incoming_bytes), 0),
            func.coalesce(func.sum(NetworkStats.outgoing_bytes), 0),
            func.coalesce(func.sum(NetworkStats.tcp_packets), 0),
            func.coalesce(func.sum(NetworkStats.udp_packets), 0),
            func.count(NetworkStats.id),
        )
        .filter(
            NetworkStats.device_id == device_id,
            NetworkStats.timestamp >= cutoff,
        )
        .one()
    )

    in_pkts, out_pkts, in_bytes, out_bytes, tcp, udp, samples = row

    return jsonify(
        device_id=device_id,
        minutes=minutes,
        # one network_stats row per monitoring interval; used as the activity count
        total_connections=int(samples),
        inbound={"packets": int(in_pkts), "bytes": int(in_bytes)},
        outbound={"packets": int(out_pkts), "bytes": int(out_bytes)},
        # tcp/udp are not split by direction in network_stats, so these are totals
        tcp=int(tcp),
        udp=int(udp),
    ), 200
