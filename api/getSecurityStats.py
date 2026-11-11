# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Tue Nov 04 2026
# Description: API to get security stats for devices top build charts and totals in security page
# =====================================================================================================================================================

from datetime import datetime, timedelta, timezone
from flask import jsonify, request, session
from sqlalchemy import func
from api import bp
from api.targetCheck import owned_target
from extensions import db
from models import NetworkStats

# =====================================================================================================================================================
# global variables and stuffs
# =====================================================================================================================================================

# alowed time interval that the security page allows to select
ALLOWED_MINUTES = {10, 30, 60, 1440}
DEFAULT_MINUTES = 10

# number of time to display in charts plotted in horiwontal row. 
SERIES_BUCKETS = 12

# get current time in est to make calculation consistant since server may be using different time format
# doesnot howevr account for daylight savings- not important yet. 
def _est_now():
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5)


@bp.route("/security/stats", methods=["POST"])

# =====================================================================================================================================================
# main function to get a device's security stats for a selected time window
# =====================================================================================================================================================
def security_stats():

    #--------------------------------------------------------------Step 1: initial validation and settings ---------------------------------------------    
    
    # check if user's logged in
    if "user_id" not in session:
        return jsonify(error="Not authenticated"), 401

    # get JSON data from the security page
    data = request.get_json(silent=True) or {}

    # verify that the selected device belongs to the logged-in user
    target = owned_target({"device_id": data.get("device_id")})

    if not target:
        return jsonify(error="Device not found"), 404

    # get the validated device ID
    device_id = target[1]


    # Set the user selected range. default is 10 minutes
    try:
        minutes = int(data.get("minutes"))
    except (TypeError, ValueError):
        minutes = DEFAULT_MINUTES
    if minutes not in ALLOWED_MINUTES:
        minutes = DEFAULT_MINUTES

    # start time calculated by substracting current time and selected range time
    cutoff = _est_now() - timedelta(minutes=minutes)

    #--------------------------------step -2: Calculate total packets, bytes, protocols, and samples for the selected time interval ----------------------------    
    row = (
        db.session.query(
            func.coalesce(func.sum(NetworkStats.incoming_packets), 0),
            func.coalesce(func.sum(NetworkStats.outgoing_packets), 0),
            func.coalesce(func.sum(NetworkStats.incoming_bytes), 0),
            func.coalesce(func.sum(NetworkStats.outgoing_bytes), 0),
            func.coalesce(func.sum(NetworkStats.tcp_packets), 0),
            func.coalesce(func.sum(NetworkStats.udp_packets), 0),
        )
        .filter(
            NetworkStats.device_id == device_id,
            NetworkStats.timestamp >= cutoff,
        )
        .one()
    )

    # set totals from above row query
    in_pkts, out_pkts, in_bytes, out_bytes, tcp, udp = row

    #--------------------------------------------------------------get stats for eachs series -----------------------------------------------------------------    
    series = _traffic_series(device_id, cutoff, minutes)


    #---------------------------------------------------------step 4: return response to the security page ----------------------------------------------------    
    return jsonify(
        device_id=device_id,
        minutes=minutes,
        inbound={"packets": int(in_pkts), "bytes": int(in_bytes)},
        outbound={"packets": int(out_pkts), "bytes": int(out_bytes)},
        tcp=int(tcp),
        udp=int(udp),
        series=series,
    ), 200

# =====================================================================================================================================================
# total builder for each time point out of 12 time slots
# =====================================================================================================================================================
def _traffic_series(device_id, cutoff, minutes):

    # size of one slot in seconds
    slot = (minutes * 60) / SERIES_BUCKETS

    # pull the raw rows in the window (one row per monitoring interval)
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

    # drop each row into its slot and add up the totals
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

    # label each slot by its end time (HH:MM) for the chart x-axis
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
