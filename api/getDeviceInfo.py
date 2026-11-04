# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Fri Oct 30 2026
# Description: API to get device updates. device will send updates every 10 seconds to the server 
# =====================================================================================================================================================


from flask import jsonify, request
from datetime import datetime, timezone
from api import bp
from extensions import db
from models import Device, PairingCode, NetworkStats


@bp.route("/pairing/deviceInfo", methods=["POST"])

# main function to get devie info
def get_device_info():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON"), 400

    pairing_code = data.get("pairing_code")
    action = data.get("action")

    # =====================================================================================================================================================
    # Step 1: Verify pairing code is valid- check stored code hash from table
    # =====================================================================================================================================================
    pairing = PairingCode.query.filter_by(
        pairing_code=pairing_code
    ).with_for_update().first()

    # if the pairing code is invalid
    if not pairing:
        return jsonify(
            paired=False,
            registered=False,
            error="Invalid pairing code"
        ), 404
    
    # =====================================================================================================================================================
    # Step 2: Verify code with device before establishing communication. device sends its stored pairing code to the server and it authenticates it first. 
    # =====================================================================================================================================================
    if action == "verify":

        # if device already registered with that code
        if pairing.device_id is not None:
            return jsonify(
                paired=True,
                registered=True,
                device_id=pairing.device_id
            ), 200

        # if device not registered yet
        return jsonify(
            paired=True,
            registered=False
        ), 200
    # =====================================================================================================================================================
    # once device has been verified then proced to sync info 
    # Step 3: Synchronize device information
    # =====================================================================================================================================================
    if action == "sync":
        # get the requred fields
        operating_system = data.get("operating_system")
        ip_address = data.get("ip_address")
        device_name = data.get("device_name")


        # Check if all fields synced- true. else it returns false
        sync_status = {
            "has_os": bool(operating_system),
            "has_ip": bool(ip_address)
        }

        # Identify missing fields from above boolean. 
        missing_fields = [
            field for field, status in sync_status.items()
            if not status
        ]

        # send back response to client for fields that could not be synced
        if missing_fields:
            return jsonify(
                synced=False,
                sync_status=sync_status,
                error=f"Could not sync: {', '.join(missing_fields)}"
            ), 400

        # once the fields are synced-save them in db tables for each device. updates are overwritten. registration will result in initial entry
        try:
            # if this is the first synchronization: register device and initial entry
            if pairing.device_id is None:

                device = Device(
                    user_id=pairing.user_id,
                    operating_system=operating_system,
                    ip_address=ip_address,
                    device_name=device_name,
                    last_online= datetime.now(timezone.utc)
                )

                db.session.add(device)
                db.session.flush()

                pairing.device_id = device.device_id
                status = "registered"


            # for devices that are already pired, it will simply update the entries in its table
            else:
                device = db.session.get(Device, pairing.device_id)

                if not device:
                    return jsonify(
                        synced=False,
                        error="Device not found"
                    ), 404

                device.operating_system = operating_system
                device.ip_address = ip_address
                device.device_name = device_name
                device.last_online = datetime.now(timezone.utc)
                status = "updated"

            db.session.commit()



            # send status result response back to the client at the end
            return jsonify(
                paired=True,
                registered=True,
                synced=True,
                status=status,
                device_id=device.device_id,
                message="initial Sync successful"
            ), 200
        
        except Exception as e:
            db.session.rollback()

            print("DATABASE ERROR:", str(e))

            return jsonify(
                synced=False,
                error="Sync to server failed"
            ), 500

    
    # =====================================================================================================================================================
    # Heartbeat sync - update device last_online
    # =====================================================================================================================================================
    if action == "heartbeat_sync":

        if pairing.device_id is None:
            return jsonify(
                synced=False,
                error="Device not registered"
            ), 409

        try:
            device = db.session.get(Device, pairing.device_id)

            if not device:
                return jsonify(
                    synced=False,
                    error="Device not found"
                ), 404

            device.last_online = datetime.now(timezone.utc)

            db.session.commit()

            return jsonify(
                synced=True,
                device_id=device.device_id,
                message="Heartbeat sync successful"
            ), 200

        except Exception as e:
            db.session.rollback()
            print("HEARTBEAT ERROR:", str(e))

            return jsonify(
                synced=False,
                error="Heartbeat sync failed"
            ), 500


    # =====================================================================================================================================================
    # Monitor sync - receive network statistics
    # =====================================================================================================================================================
    if action == "monitor_sync":

        if pairing.device_id is None:
            return jsonify(
                synced=False,
                error="Device not registered"
            ), 409

        device = db.session.get(Device, pairing.device_id)

        if not device:
            return jsonify(
                synced=False,
                error="Device not found"
            ), 404

        # Get network statistics from client
        network_stats = data.get("network_stats")

        if not isinstance(network_stats, dict):
            return jsonify(
                synced=False,
                error="Invalid network statistics"
            ), 400

        # Required statistics
        fields = (
            "incoming_packets",
            "outgoing_packets",
            "incoming_bytes",
            "outgoing_bytes",
            "tcp_packets",
            "udp_packets"
        )

        values = {}

        # Validate timestamp and packet statistics
        try:
            timestamp = datetime.strptime(
                network_stats["timestamp"],
                "%Y-%m-%d %H:%M:%S"
            )

            for field in fields:
                value = network_stats[field]

                if type(value) is not int or value < 0:
                    return jsonify(
                        synced=False,
                        error=f"Invalid {field}"
                    ), 400

                values[field] = value

        except (KeyError, ValueError, TypeError):
            return jsonify(
                synced=False,
                error="Missing or invalid network statistics"
            ), 400

        try:
            stats = NetworkStats(
                device_id=device.device_id,
                timestamp=timestamp,
                **values
            )

            db.session.add(stats)
            db.session.commit()

            return jsonify(
                synced=True,
                device_id=device.device_id,
                message="Monitor statistics saved successfully"
            ), 200

        except Exception as e:
            db.session.rollback()
            print("MONITOR DATABASE ERROR:", str(e))

            return jsonify(
                synced=False,
                error="Failed to save monitor statistics"
            ), 500


    # =====================================================================================================================================================
    # Step 6: Security sync - receive security events
    # =====================================================================================================================================================
    if action == "security_sync":

        if pairing.device_id is None:
            return jsonify(
                synced=False,
                error="Device not registered"
            ), 409

        device = db.session.get(Device, pairing.device_id)

        if not device:
            return jsonify(
                synced=False,
                error="Device not found"
            ), 404

        security_log = data.get("security_log")

        if not isinstance(security_log, dict) or not security_log:
            return jsonify(
                synced=False,
                error="Invalid or missing security log"
            ), 400

        return jsonify(
            synced=True,
            device_id=device.device_id,
            message="Security data received successfully"
        ), 200


    # =====================================================================================================================================================
    # Step 7: Handle unsupported actions
    # =====================================================================================================================================================
    return jsonify(
        error="Invalid action"
    ), 400

