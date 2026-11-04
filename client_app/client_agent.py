# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Fri Oct 30 2026
# Description: this is the client side script that registers teh device witht eh server and maintains communication
# =====================================================================================================================================================
import requests
import platform
import socket
import json
import psutil
import ipaddress
import time
import threading
import queue
from pathlib import Path


# =====================================================================================================================================================
# configuration 
# =====================================================================================================================================================
  
# server IP. change this if the srever is running on a different ip address
SERVER_URL = "http://127.0.0.1:5000/api/pairing/deviceInfo"

# Local configuration to save the config file locally
CONFIG_FILE = Path.home() / ".client_config.json"

# listen on tcp port 5002 for network packets sent by the monitor
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 5002

# Queue for network stats received from monitor
network_queue = queue.Queue()

# Heartbeat interval
HEARTBEAT_INTERVAL = 5


# =====================================================================================================================================================
# startup functions
# =====================================================================================================================================================

# check if config file exists
def config_exists():
    return CONFIG_FILE.exists()

# load saved pairing code
def load_pairing_code():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            return config.get("pairing_code")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# load saved devie name
def load_device_name():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            return config.get("device_name")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Save pairing code locally when registering. it creates the config file if it doesnot exist already
def save_config(key, value):
    config = {}
    if config_exists():
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
    config[key] = value
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

# connection to the server
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

# =====================================================================================================================================================
# registering, pairing and initial sync
# =====================================================================================================================================================

def registerDevice():
    pairing_code = input(
        "Enter pairing code to register your device: ").strip()
    print("Verifying pairing code...")
    while not verifyDevice(pairing_code):
        print("Invalid code. Try again.")
        pairing_code = input(
            "Enter pairing code: "
        ).strip()
        print("Verifying pairing code...")
    print("Code verified!")

    while True:
        device_name = input("Enter device name: ").strip()
        if device_name:
            break
        print("Device name cannot be empty.")

    save_config("device_name", device_name)
    save_config("pairing_code", pairing_code)
    print("Device configuration saved successfully!")


    return pairing_code, device_name


def verifyDevice(pairing_code):
    response = send_request({
        "action": "verify",
        "pairing_code": pairing_code
    })
    if response.get("paired") is True:
        print("Pairing code verified successfully!")
        return True
    else:
        print("Pairing code verification failed!")
        print("Error:", response.get("error"))
        return False


def initial_sync(pairing_code, device_name):
            response = send_request({
                "action": "sync",
                "pairing_code": pairing_code,
                "operating_system": get_os(),
                "ip_address": get_ip(),
                "device_name": device_name
            })
    
            if response.get("synced"):
                print("initial sync successful")
                return True
                
            else:
                print("initial sync failed:", response.get("error"))
                return False
                

# =====================================================================================================================================================
# heart beat sync every 5 sec
# =====================================================================================================================================================

def heartbeat_sync(pairing_code, device_name):

    while True:
        response = send_request({
            "action": "heartbeat_sync",
            "pairing_code": pairing_code,
            "operating_system": get_os(),
            "ip_address": get_ip(),
            "device_name": device_name
        })

        if not response.get("synced"):
            print("Heartbeat sync failed:", response.get("error"))
        else:
            print("Heartbeat sync successful")

        time.sleep(HEARTBEAT_INTERVAL)


# =====================================================================================================================================================
# listen on TCP port 5002 for network stats and send it to the server
# =====================================================================================================================================================

def monitor_sync(pairing_code):

    # Create TCP listener
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:

        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((LISTEN_HOST, LISTEN_PORT))
        server.listen()

        print(f"listening on: {LISTEN_HOST}:{LISTEN_PORT}")

        while True:
            # Wait for monitor.py to connect
            conn, addr = server.accept()
            with conn:
                try:
                    # Read JSON messages sent by monitor.py
                    with conn.makefile("r", encoding="utf-8") as stream:
                        for line in stream:
                            if not line.strip():
                                continue

                             # Convert received JSON to dictionary
                            network_stats = json.loads(line)

                            
                            # Build request for Flask server
                            payload = {
                                "action": "monitor_sync",
                                "pairing_code": pairing_code,
                                "network_stats": network_stats
                            }

                            # send it to server
                            response = send_request(payload)

                            if response.get("synced") is True:
                                print("Monitor sync successful")

                            else:
                                print(
                                    "Monitor sync failed:",
                                    response.get("error")
                                )

                except (OSError, UnicodeError) as e:
                    print("Monitor TCP error:", e)

# =====================================================================================================================================================
# Main client function to process the info and talk with the server
# =====================================================================================================================================================
def main():
    print("===== NETMAN CLIENT APP =====")
    print("======V1. Oct 30, 2026=======")


    # -----------------------------------------------Step 1: registering, pairing and authentication-----------------------------------------------
    # first get the pairing code and device name if exists
    pairing_code = load_pairing_code()
    device_name = load_device_name()
    


    #verify if device is registered
    if not pairing_code or not device_name:
        print("device has not been registered yet. please register...")
        pairing_code, device_name = registerDevice()
        
    # if registered already, skip to pairing
    else:
        print("pairing device...")
        if verifyDevice(pairing_code):
            print("device successfully paired")

        else:
            print("device could not be paired. plese check the pairing code in config file")
            return 0
        
    # initial sync
    if not initial_sync(pairing_code, device_name):
        return
     
    #at this point the client should have 1: established connection to the server and 2: registered and or paired the device with the server 

   
    # ------------------------------------------------------------------process 1: heartbeat sync process----------------------------------------------
    heartbeat_thread = threading.Thread(
            target=heartbeat_sync,
            args=(pairing_code, device_name)
    )

   # ------------------------------------------------------------------process 2: monitor sync process-------------------------------------------------
    monitor_thread = threading.Thread(
        target=monitor_sync,
        args=(pairing_code,)
    )

    # ------------------------------------------------------------------process 3: security sync process------------------------------------------------
 


    # ---------------------------------------------------------------------------start all processes------------------------------------------------------
    heartbeat_thread.start()
    monitor_thread.start()


if __name__ == "__main__":
    main()