from flask import jsonify, request
from datetime import datetime, timezone
from api import bp
from api.postPairingCode import hash_code
from extensions import db
from models import Device, PairingCode


@bp.route("/pairing/deviceInfo", methods=["POST"])

# main function to get devie info
def get_device_info():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON"), 400

    pairing_code = data.get("pairing_code")
    action = data.get("action")


    # Step 1: Verify pairing code
    pairing = PairingCode.query.filter_by(
        code_hash=hash_code(pairing_code)
    ).with_for_update().first()

    if not pairing:
        return jsonify(
            paired=False,
            registered=False,
            error="Invalid pairing code"
        ), 404

    # Step 2: Verify code with device
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

    # once device has been verified then proced to sync info 

    # Step 3: Synchronize device information
    if action == "sync":

        operating_system = data.get("operating_system")
        ip_address = data.get("ip_address")



        # Check if all fields synced
        sync_status = {
            "has_os": bool(operating_system),
            "has_ip": bool(ip_address)
        }

        # Identify missing fields 
        missing_fields = [
            field for field, status in sync_status.items()
            if not status
        ]

        if missing_fields:
            return jsonify(
                synced=False,
                sync_status=sync_status,
                error=f"Could not sync: {', '.join(missing_fields)}"
            ), 400




        # once the fields are synced-save them in db tables
        try:
            # First synchronization: register device
            if pairing.device_id is None:

                device = Device(
                    user_id=pairing.user_id,
                    operating_system=operating_system,
                    ip_address=ip_address,
                    last_online= datetime.now(timezone.utc)
                )

                db.session.add(device)
                db.session.flush()

                pairing.device_id = device.device_id
                status = "registered"

            else:
                # Existing device: onl y update information
                device = db.session.get(Device, pairing.device_id)

                if not device:
                    return jsonify(
                        synced=False,
                        error="Device not found"
                    ), 404

                device.operating_system = operating_system
                device.ip_address = ip_address
                device.last_online = datetime.now(timezone.utc)
                status = "updated"

            db.session.commit()

            return jsonify(
                paired=True,
                registered=True,
                synced=True,
                status=status,
                device_id=device.device_id,
                message="Sync successful"
            ), 200
        
        except Exception as e:
            db.session.rollback()

            print("DATABASE ERROR:", str(e))

            return jsonify(
                synced=False,
                error="Sync to server failed"
            ), 500