#!/usr/bin/env python3
"""
sysinfo.py
Collect OS, hostname, IPs, current user, CPU count, memory info.
Outputs JSON by default or plain text if requested.
"""

import argparse
import json
import platform
import socket
import getpass
import os
import multiprocessing
from datetime import datetime

# try to import psutil for richer info
try:
    import psutil
    HAVE_PSUTIL = True
except Exception:
    psutil = None
    HAVE_PSUTIL = False

def get_basic_info():
    info = {
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        },
        "hostname": socket.gethostname(),
        "current_user": getpass.getuser(),
        "cpu_count_logical": os.cpu_count() or multiprocessing.cpu_count()
    }
    return info

def get_network_info():
    nets = []
    # Attempt to get interface-level addresses via psutil if available
    if HAVE_PSUTIL:
        try:
            for ifname, addrs in psutil.net_if_addrs().items():
                for a in addrs:
                    # only include IPv4 and IPv6
                    if a.family.name.startswith("AF_INET") or a.family.name.startswith("AF_INET6"):
                        nets.append({
                            "interface": ifname,
                            "address": a.address,
                            "netmask": getattr(a, "netmask", None),
                            "broadcast": getattr(a, "broadcast", None)
                        })
        except Exception:
            pass

    # Fallback: use gethostbyname_ex to get some IPs for the hostname
    try:
        hostname = socket.gethostname()
        host_info = socket.gethostbyname_ex(hostname)
        # host_info = (hostname, aliaslist, ipaddrlist)
        for ip in host_info[2]:
            if not any(n.get("address") == ip for n in nets):
                nets.append({"interface": "hostname_lookup", "address": ip})
    except Exception:
        pass

    # As an extra fallback attempt to connect to a remote host to determine outbound IP
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # doesn't have to be reachable — we won't send data
            s.connect(("8.8.8.8", 80))
            outbound_ip = s.getsockname()[0]
            if not any(n.get("address") == outbound_ip for n in nets):
                nets.append({"interface": "outbound", "address": outbound_ip})
    except Exception:
        pass

    return nets

def get_memory_info():
    if HAVE_PSUTIL:
        vm = psutil.virtual_memory()
        return {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "free": getattr(vm, "free", None),
            "percent": vm.percent
        }
    else:
        # graceful fallback: unavailable without psutil
        return {
            "note": "psutil not installed — install psutil for detailed memory stats. (pip install psutil)"
        }

def collect_all():
    out = get_basic_info()
    out["network"] = get_network_info()
    out["memory"] = get_memory_info()
    return out

def main():
    parser = argparse.ArgumentParser(description="Collect system information (OS, IPs, user, CPU, memory).")
    parser.add_argument("--output", "-o", default="sample_sysinfo.json",
                        help="Output file path (default: sample_sysinfo.json). JSON format.")
    parser.add_argument("--text", action="store_true",
                        help="Print a human-readable text summary to stdout (still writes JSON file).")
    args = parser.parse_args()

    data = collect_all()

    # Write JSON file
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

    if args.text:
        # print readable summary
        print("=== System Info Summary ===")
        print(f"Host: {data.get('hostname')}")
        p = data.get("platform", {})
        print(f"OS: {p.get('system')} {p.get('release')} ({p.get('machine')})")
        print(f"User: {data.get('current_user')}")
        print(f"CPU (logical count): {data.get('cpu_count_logical')}")
        print("Network interfaces / IPs:")
        for n in data.get("network", []):
            print(f" - {n.get('interface')}: {n.get('address')}")
        mem = data.get("memory", {})
        if "total" in mem:
            print(f"Memory total: {mem['total']:,} bytes, used: {mem.get('used', 'N/A'):,}, percent: {mem.get('percent')}%")
        else:
            print(mem.get("note"))
        print("===========================")
    else:
        print(f"Wrote JSON output to {args.output}")

if __name__ == "__main__":
    main()
