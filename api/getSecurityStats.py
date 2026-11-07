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

    # time series for the traffic line chart: bucket the window into N slots and
    # sum inbound/outbound packets per slot, so the chart has a fixed, simple shape
    series = _traffic_series(device_id, cutoff, minutes)

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
        series=series,
    ), 200


# number of points on the traffic line chart
SERIES_BUCKETS = 12


def _traffic_series(device_id, cutoff, minutes):
    """Bucket the [cutoff, now] window into SERIES_BUCKETS equal slots. For each
    slot, sum inbound/outbound packets and inbound+outbound bytes (throughput).
    Returns a list of {label, inbound, outbound, bytes}, oldest first, with empty
    slots as zeros."""
    now = datetime.now()
    span = (now - cutoff).total_seconds()
    slot = span / SERIES_BUCKETS if span > 0 else 1

    rows = (
        db.session.query(
            NetworkStats.timestamp,
            NetworkStats.incoming_packets,
            NetworkStats.outgoing_packets,
            NetworkStats.incoming_bytes,
            NetworkStats.outgoing_bytes,
        )
        .filter(
            NetworkStats.device_id == device_id,
            NetworkStats.timestamp >= cutoff,
        )
        .all()
    )

    buckets = [
        {"inbound": 0, "outbound": 0, "bytes": 0}
        for _ in range(SERIES_BUCKETS)
    ]
    for ts, inc, out, in_b, out_b in rows:
        idx = int((ts - cutoff).total_seconds() / slot)
        idx = min(max(idx, 0), SERIES_BUCKETS - 1)
        buckets[idx]["inbound"] += int(inc or 0)
        buckets[idx]["outbound"] += int(out or 0)
        buckets[idx]["bytes"] += int(in_b or 0) + int(out_b or 0)

    series = []
    for i, b in enumerate(buckets):
        end = cutoff + timedelta(seconds=slot * (i + 1))
        series.append({
            "label": end.strftime("%H:%M"),
            "inbound": b["inbound"],
            "outbound": b["outbound"],
            "bytes": b["bytes"],
        })
    return series
