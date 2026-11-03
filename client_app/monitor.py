# =====================================================================================================================================================
# Written by: Samip Kafle
# Date: Mon Nov 02 2026
# Description: packet sniffer. captures packets with scapy and prints the details of each one continuously
# =====================================================================================================================================================
import socket
import ipaddress
from datetime import datetime
import psutil
from scapy.all import sniff, IP, TCP, UDP


# =====================================================================================================================================================
# required functions to get packet info
# =====================================================================================================================================================

# timestamp
def get_timestamp(packet):
    return datetime.fromtimestamp(float(packet.time)).strftime("%Y-%m-%d %H:%M:%S")


# source ip address (ipv4)
def get_source_ip(packet):
    if packet.haslayer(IP):
        return packet[IP].src
    return None


# destination ip address (ipv4)
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

# packet interface
from scapy.all import conf

# get active network interface
def get_interface():
    result = conf.route.route("1.1.1.1")
    interface = result[0]

    return interface



# print captured packet info
def print_packet(packet):
        # print each item separated by |
        # output: 2026-11-02 21:45:10 | 192.168.1.10 | 8.8.8.8 | 54321 | 53 | UDP | None | 82 bytes
        print(get_timestamp(packet),"|",
        get_source_ip(packet),"|",
        get_dest_ip(packet),"|",
        get_source_port(packet),"|",
        get_dest_port(packet),"|",
        get_protocol(packet),"|",
        get_tcp_flags(packet),"|",
        get_byte_size(packet), "bytes"
        )
        # print("press ctrl+c to stop. \n")


# =====================================================================================================================================================
# main function to capture packets and print them 
# =====================================================================================================================================================
def main():

    # get active network interface
    interface = get_interface()

    # if no active interface fcund
    if not interface:
        print("No active network interface found.")
        print("Exiting...")
        return

    # display initial info once interface confirmed
    print("===== NETMAN PACKET SNIFFER =====")
    print(f"Network Interface: {interface}")
    print("capturing packets.....\n")

    
    # start packet capture and print continuously
    sniff(
        # select interface
        iface = interface,
        # only capture IPV4
        filter = "ip",
        # print captured info
        prn = print_packet,
        )


    #send captured packet package to client sync app
    

    #send it over to security agent
     
    

if __name__ == "__main__":
    main()
