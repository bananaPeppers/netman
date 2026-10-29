import requests
import platform
import socket
import json
import psutil
import ipaddress
import time
from pathlib import Path


# Server configuration
SERVER_URL = "http://127.0.0.1:5000/api/pairing/deviceInfo"

# Local configuration
CONFIG_FILE = Path.home() / ".client_config.json"


# Load saved pairing code
def load_pairing_code():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            return config.get("pairing_code")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# load device name
def load_device_name():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            return config.get("device_name")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# Save pairing code locally
def save_pairing_code(pairing_code, device_name):
    with open(CONFIG_FILE, "w") as file:
        json.dump({
            "pairing_code": pairing_code,
            "device_name": device_name
        }, file)


# Send request to server
def send_request(payload):
    try:
        response = requests.post(
            SERVER_URL,
            json=payload,
            timeout=10
        )

        try:
            result = response.json()
        except ValueError:
            print("\n===== SERVER ERROR =====")
            print("HTTP Status:", response.status_code)
            print("Response:", response.text[:2000])
            print("========================\n")
            return {
                "error": "Server returned an invalid response"
            }

        result["_http_status"] = response.status_code

        # Display server message on successful request
        if response.ok:
            print(result.get("message", "Connected to server successfully!"))

        return result

    except requests.RequestException:
        return {
            "error": "Connection to server failed"
        }

  

# Get operating system
def get_os():
    try:
        return platform.system()
    except Exception:
        return None


# Get IP address
def get_ip():
    for interface, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family == socket.AF_INET:
                ip = ipaddress.ip_address(addr.address)

                if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                    return addr.address

    return None


# Main client function
def main():

    print("===== NETMAN CLIENT =====")

    pairing_code = load_pairing_code()
    device_name = load_device_name()

    # Step 1: Verify pairing code
    while True:

        if not pairing_code:
            pairing_code = input("Enter pairing code: ").strip()

        response = send_request({
            "action": "verify",
            "pairing_code": pairing_code
        })

        if response.get("paired") is True:

            print("Pairing code verified!")

            if response.get("registered") is True:
                print("Device already registered.")
                print("Device ID:", response.get("device_id"))
            else:
                print("Please register this device.")

                # Ask for device name after successful pairing
                while True:
                    device_name = input("Enter device name: ").strip()

                    if device_name:
                        break

                    print("Device name cannot be empty.")

                print("Device Name:", device_name)

            break

        elif response.get("_http_status") == 404:
            print("Invalid pairing code. Try again.")
            pairing_code = None

        else:
            print("Verification failed:", response.get("error"))
            return

    # Step 2: Collect device information
    print("\nCollecting device information...")

    operating_system = get_os()
    ip_address = get_ip()

    print("Operating System:", operating_system)
    print("IP Address:", ip_address)

    # Step 3: Synchronize device information every 60 seconds
    while True:

        print("\nCollecting device information...")

        operating_system = get_os()
        ip_address = get_ip()

        print("Operating System:", operating_system)
        print("IP Address:", ip_address)

        print("\nSynchronizing with server...")

        response = send_request({
            "action": "sync",
            "pairing_code": pairing_code,
            "operating_system": operating_system,
            "ip_address": ip_address
        })

        # Step 4: Process server response
        if response.get("synced") is True:

            
            print("Device Name:", device_name)
            print("Status:", response.get("status"))

            save_pairing_code(pairing_code, device_name)

        else:
            print("Synchronization failed!")
            print("Error:", response.get("error"))

            sync_status = response.get("sync_status", {})

            for field, status in sync_status.items():
                print(f"{field}: {'OK' if status else 'FAILED'}")

        # Wait 60 seconds before the next synchronization
        print("\nNext synchronization in 10 seconds...")
        time.sleep(10)


if __name__ == "__main__":
    main()