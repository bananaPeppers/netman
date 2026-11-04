# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Mon Nov 02 2026
# Description: packet sniffer. captures packets with scapy and stores it in queue. then another parallel process sends the JSON to TCP ports
# =====================================================================================================================================================
import socket
import queue
import time
import json
from datetime import datetime
from scapy.all import sniff, IP, TCP, UDP, conf
import threading
import csv
from pathlib import Path
import os
from datetime import datetime 

# =====================================================================================================================================================
# Data structures and global variables
# =====================================================================================================================================================
INTERVAL = 5

# Store CSV in the same directory as monitor.py
CSV_FILE = Path(__file__).resolve().parent / "logs.csv"

# these queues store output stream for client adn security separately
security_queue = queue.Queue(maxsize=1000)
client_queue = queue.Queue(maxsize=1000)

# csv queue to store csv log export
csv_queue = queue.Queue(maxsize=1000)

# 24 hours in seconds
CSV_RETENTION = 24 * 60 * 60 
# cleanup interval
CSV_CLEANUP_INTERVAL = 60 * 60  

# CSV columns
CSV_FIELDS = [
    "timestamp",
    "packet_time",
    "direction",
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "protocol",
    "tcp_flags",
    "byte_size"
]

# =====================================================================================================================================================
# required functions to build packet info 
# =====================================================================================================================================================

# timestamp
def get_timestamp(packet):
    return datetime.fromtimestamp(float(packet.time)).strftime("%Y-%m-%d %H:%M:%S")


# packet direction: "IN" and "OUT"
def get_packet_direction(packet):
    if not packet.haslayer(IP):
        return None
    local_ip = conf.route.route("1.1.1.1")[1]
    if packet[IP].dst == local_ip:
        return "IN"
    if packet[IP].src == local_ip:
        return "OUT"
    return None


# source ip address (ipv4 only)
def get_source_ip(packet):
    if packet.haslayer(IP):
        return packet[IP].src
    return None


# destination ip address (ipv4 only)
def get_dest_ip(packet):
    if packet.haslayer(IP):
        return packet[IP].dst
    return None


# source port
def get_source_port(packet):
    if packet.haslayer(TCP):
        return packet[TCP].sport
    if packet.haslayer(UDP):
        return packet[UDP].sport
    return None


# destination port
def get_dest_port(packet):
    if packet.haslayer(TCP):
        return packet[TCP].dport
    if packet.haslayer(UDP):
        return packet[UDP].dport
    return None


# protocol name 
def get_protocol(packet):
    if packet.haslayer(TCP):
        return "TCP"
    if packet.haslayer(UDP):
        return "UDP"

    return None


# tcp flags.
def get_tcp_flags(packet):
    if packet.haslayer(TCP):
        return str(packet[TCP].flags)
    return None


# packet size
def get_byte_size(packet):
    return len(packet)


# get active network interface
def get_interface():
    result = conf.route.route("1.1.1.1")
    interface = result[0]
    return interface


# build dictionary from captured values and store them as keys in dictionary
def build_packet(packet):
    packet_info = {
        "timestamp": get_timestamp(packet),
        "packet_time": float(packet.time),
        "direction": get_packet_direction(packet),
        "source_ip": get_source_ip(packet),
        "destination_ip": get_dest_ip(packet),
        "source_port": get_source_port(packet),
        "destination_port": get_dest_port(packet),
        "protocol": get_protocol(packet),
        "tcp_flags": get_tcp_flags(packet),
        "byte_size": get_byte_size(packet)
    }
    return packet_info


# =====================================================================================================================================================
# queue handlers
# =====================================================================================================================================================

# FIFO buffer handler for both the queue and csv write. 
# this helps to make sure data doesnot grow indefinetely for csv export and the queue storage
def fifo_buffer(target_queue, packet_info):
        
    try:
        target_queue.put_nowait(packet_info) 

    except queue.Full:
        try:
            # Remove oldest entry
            target_queue.get_nowait()
            target_queue.task_done()

        except queue.Empty:
            pass
        # Add newest entry
        try:
            target_queue.put_nowait(packet_info)
        except queue.Full:
            pass

# add captured packet to both queues
def store_packet(packet):

    # build packet_info dictionary
    packet_info = build_packet(packet)

    # 1. add the same packet information to security queue for only latest 1000 entries only
    fifo_buffer(security_queue, packet_info)
    # 2. add the same packet information to client queue
    fifo_buffer(client_queue, packet_info)
    # 3. add the same packet information to csv file for only latest 1000 entries only
    fifo_buffer(csv_queue, packet_info)

# =====================================================================================================================================================
# csv creation handlers
# =====================================================================================================================================================


def write_csv():

    # Create CSV if it does not exist
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writeheader()

    # Function to remove logs older than 24 hours
    def cleanup_csv():

        cutoff = time.time() - CSV_RETENTION
        temp_file = CSV_FILE.with_suffix(".tmp")

        try:
            with open(CSV_FILE, "r", newline="", encoding="utf-8") as source:
                with open(temp_file, "w", newline="", encoding="utf-8") as destination:

                    reader = csv.DictReader(source)
                    writer = csv.DictWriter(destination, fieldnames=CSV_FIELDS)
                    writer.writeheader()

                    for row in reader:
                        try:
                            packet_time = float(row["packet_time"])

                            if packet_time >= cutoff:
                                writer.writerow(row)

                        except (ValueError, TypeError, KeyError):
                            continue

            os.replace(temp_file, CSV_FILE)

        except OSError as e:
            print("CSV cleanup failed:", e)

            if temp_file.exists():
                temp_file.unlink()

    # Remove expired logs when monitor starts
    cleanup_csv()

    last_cleanup = time.monotonic()

    # Continuously process incoming packets
    while True:

        try:
            packet_info = csv_queue.get(timeout=1)

        except queue.Empty:
            packet_info = None

        if packet_info is not None:
            try:
                # Append packet instead of rewriting CSV
                with open(CSV_FILE, "a", newline="", encoding="utf-8") as file:
                    writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
                    writer.writerow(packet_info)

            except OSError as e:
                print("CSV write failed:", e)

            finally:
                csv_queue.task_done()

        # Clean up expired logs every hour
        if time.monotonic() - last_cleanup >= CSV_CLEANUP_INTERVAL:
            cleanup_csv()
            last_cleanup = time.monotonic()


# =====================================================================================================================================================
# stats creation handlers 
# =====================================================================================================================================================

# convert captured apckets into totals
def packet_stats(packet_info, counters):

    # get information from packet dictionary
    direction = packet_info["direction"]
    protocol = packet_info["protocol"]
    size = packet_info["byte_size"]

    # count incoming packets
    if direction == "IN":
        counters["total_in"] += 1
        counters["total_in_bytes"] += size

    # count outgoing packets
    elif direction == "OUT":
        counters["total_out"] += 1
        counters["total_out_bytes"] += size

    # count TCP/UDP
    if protocol == "TCP":
        counters["tcp"] += 1

    elif protocol == "UDP":
        counters["udp"] += 1

# reset counter dictionary keys for next interval
def resetInterval():
    return {
            "total_in" : 0,
            "total_out" : 0,
            "total_in_bytes" : 0,
            "total_out_bytes" : 0,
            "tcp" : 0,
            "udp" : 0
    }

# function to send built json packtes to client agent
def send_client_stats(stats_json):
    # connect to the tcp listener first
    try:
        # connect to client
        with socket.create_connection(
            ("127.0.0.1", 5002),
            timeout=1
        ) as sock:

            # send JSON 
            sock.sendall(
                (stats_json + "\n").encode("utf-8")
            )

        print("packets for client sync sent successfully for this interval")

    except OSError:
        print("send failed. moving on to next packet interval")

#-------------------------------------------------------------------------------------------------------------------------------------------------------
def build_stats():

    # initialize counter dictionary
    counters = resetInterval()

    # starting time
    start = time.time()

    while True:
        try:
            # get stuff from teh client queue
            packet_info = client_queue.get(timeout=0.1)
            packet_stats(packet_info, counters)
            client_queue.task_done()
        except queue.Empty:
            pass

        # current time for next iteration
        end = time.time()

        # check if 5 seconds have passed
        if end - start >= INTERVAL:
            # create network statistics dictionary
            stats = {
                "timestamp": datetime.fromtimestamp(end).strftime("%Y-%m-%d %H:%M:%S"),

                "incoming_packets": counters["total_in"],
                "outgoing_packets": counters["total_out"],

                "incoming_bytes": counters["total_in_bytes"],
                "outgoing_bytes": counters["total_out_bytes"],

                "tcp_packets": counters["tcp"],
                "udp_packets": counters["udp"]
            }

            # convert dictionary to JSON
            stats_json = json.dumps(stats)

            # print JSON
            print("\n===== NETWORK TRAFFIC JSON =====")
            print(json.dumps(stats, indent=4))

            # send JSON to client
            send_client_stats(stats_json)

            # reset counters
            counters = resetInterval()

            # next interval
            start = end


# =====================================================================================================================================================
# log creation handlers 
# =====================================================================================================================================================

# function to send json logs to security agent
def send_security_log(log):
    # connect to the tcp listener first
        try:
            # connect to security agent
            with socket.create_connection(
                ("127.0.0.1", 5003),
                timeout=1
            ) as sock:
    
                # send JSON 
                sock.sendall(
                    (log + "\n").encode("utf-8")
                )
    
            print("packets for IDS sent successfully")
    
        except OSError:
            print("send to IDS failed")

#-------------------------------------------------------------------------------------------------------------------------------------------------------
def build_log():
    while True:
        try:
            # get stuff from the security queue
            packet_info = security_queue.get(timeout=0.1)
            

        except queue.Empty:
            continue


        # dictionary to JSON
        logs_json = json.dumps(packet_info)

        # print log line
        print(json.dumps(packet_info, indent=4))


        # send json to security
        send_security_log(logs_json)

        security_queue.task_done()


# =====================================================================================================================================================
# main function 
# =====================================================================================================================================================
def main():

    # get active network interface
    interface = get_interface()

    # if no active interface found
    if not interface:
        print("No active network interface found.")
        print("Exiting...")
        return

    # display initial info once interface confirmed
    print("===== NETMAN PACKET SNIFFER =====")
    print(f"Network Interface: {interface}")

#------------------------------------------------------------------ process 1: packet capture------------------------------------------------------
    capture_thread = threading.Thread(
        target=sniff,
        kwargs={
            "iface": interface,
            "filter": "ip",
            "prn": store_packet,
            "store": False
            }
        )

#------------------------------------------------------------------ process 2: client data transfer---------------------------------------------------
    client_thread = threading.Thread(
        target=build_stats
    )

#----------------------------------------------------------------- process 3: security data transfer--------------------------------------------------- 
    security_thread = threading.Thread(
        target=build_log
    )

#--------------------------------------------------------------------- process 4: csv write------------------------------------------------------------- 
    csv_thread = threading.Thread(
        target=write_csv
    )

#------------------------------------------------------------------------------------------------------------------------------------------------------ 
    capture_thread.start()
    client_thread.start()
    security_thread.start()
    csv_thread.start()




if __name__ == "__main__":

    main()


