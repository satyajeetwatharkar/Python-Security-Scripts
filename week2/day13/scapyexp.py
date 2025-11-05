#!/usr/bin/env python3
"""
scapy_examples.py — craft and parse a packet locally (DO NOT send)
"""
from scapy.all import IP, TCP, Raw


# 1. Craft an IP/TCP packet (layers are stacked left-to-right)
packet = IP(dst="10.0.0.5", src="10.0.0.10")/TCP(sport=4444, dport=80, flags="S")/Raw(b"Hello-Scapy")


# 2. Show a summary (one-line)
print("SUMMARY:")
print(packet.summary())


# 3. Show a detailed representation (all layers & fields)
print("\nDETAILED SHOW:")
packet.show()


# 4. Access specific fields programmatically
print("\nFIELDS:")
print("IP src:", packet[IP].src)
print("IP dst:", packet[IP].dst)
print("TCP sport:", packet[TCP].sport)
print("TCP dport:", packet[TCP].dport)
print("TCP flags:", packet[TCP].flags)
print("Payload raw bytes:", bytes(packet[Raw].load))


# 5. Demonstrate parsing from raw bytes (simulate receiving)
raw = bytes(packet)
print("\nPARSE FROM RAW BYTES:")
parsed = IP(raw)
parsed.show()


# Note: This script never calls send() or sr() — it only constructs and parses locally.