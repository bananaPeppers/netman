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
from pathlib import Path





# =====================================================================================================================================================
# configuration 
# =====================================================================================================================================================
  
# server IP. change this if the srever is running on a different ip address
SERVER_URL = "http://127.0.0.1:5000/api/pairing/deviceInfo"

# Local configuration to save the config file locally
CONFIG_FILE = Path.home() / ".client_config.json"



# =====================================================================================================================================================
# functions to load saved pairing code and device name from the config file if it exists. 
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

# =====================================================================================================================================================
# connection request to server. 
# =====================================================================================================================================================
  
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

  

# =====================================================================================================================================================
# once connection is established, move on to collecting device stats and info
# =====================================================================================================================================================
  
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


# more info is added in this section later.....


# =====================================================================================================================================================
# registering, pairing and authentication
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

     
    #********** at this point the client should have 1: established connection to the server and 2: registered and or paired the device with the server **********#

   
    # -----------------------------------------------Step 2: Synchronize device information every 10 seconds---------------------------
    while True:
        operating_system = get_os()
        ip_address = get_ip()


        print("IP Address:", ip_address)

        print("\nSynchronizing with server...")

        response = send_request({
            "action": "sync",
            "pairing_code": pairing_code,
            "operating_system": operating_system,
            "ip_address": ip_address,
            "device_name": device_name
        })

        if not response.get("synced"):
            print("Sync with the server failed!")
            print("Error:", response.get("error"))

            sync_status = response.get("sync_status", {})

            for field, status in sync_status.items():
                print(f"{field}: {'OK' if status else 'FAILED'}")
           
        

        # Wait 10 seconds before the next synchronization
        print("\nNext sync in 10 seconds...")
        time.sleep(10)


if __name__ == "__main__":
    main()