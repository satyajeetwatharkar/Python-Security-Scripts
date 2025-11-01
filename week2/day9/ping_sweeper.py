#!/usr/bin/env python3
"""
ping_sweeper.py
Scan a /24 subnet (e.g., 192.168.1.0/24) for live hosts.

Usage:
  python ping_sweeper.py --subnet 192.168.1 --mode icmp --timeout 1 --delay 0.05 --workers 50

Modes:
  - icmp : use system ping (recommended; no root required usually)
  - tcp  : try TCP connect to specified port (useful if ICMP blocked)

Output:
  Writes results to results_<subnet>_<mode>.json
"""

import argparse
import platform
import subprocess
import socket
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

def ping_icmp(host, timeout=1):
    """
    Use system ping. Cross-platform handling for basic options.
    Returns True if host replies, False otherwise.
    """
    system = platform.system().lower()
    if system == "windows":
        # -n count, -w timeout(ms)
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
    else:
        # Unix: -c count, -W timeout(seconds)
        # Note: on some systems -W is per-packet timeout, on others it's in ms; this works for most modern Linux/macOS.
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), host]

    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def tcp_probe(host, port=80, timeout=1):
    """
    Try a TCP connect to host:port. Returns True if connect succeeded.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except Exception:
        return False

def scan_ip(ip, mode="icmp", tcp_port=80, timeout=1, delay=0.0):
    """
    Scan single IP with specified mode.
    Returns dict: {"ip": ip, "alive": True/False, "method": mode}
    """
    result = {"ip": ip, "alive": False, "method": mode}
    if mode == "icmp":
        ok = ping_icmp(ip, timeout=timeout)
        result["alive"] = ok
    else:
        ok = tcp_probe(ip, port=tcp_port, timeout=timeout)
        result["alive"] = ok
        result["port"] = tcp_port
    if delay:
        # small polite delay
        time.sleep(delay)
    return result

def sweep(subnet_prefix, mode="icmp", tcp_port=80, timeout=1, delay=0.02, workers=100):
    """
    Sweep x.x.x.0/24 (subnet_prefix example: '192.168.1')
    Returns list of result dicts for each IP scanned.
    """
    ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]  # skip .0 and .255 usually
    results = []
    start = datetime.utcnow().isoformat() + "Z"
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(scan_ip, ip, mode, tcp_port, timeout, delay): ip for ip in ips}
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception as e:
                r = {"ip": futures[fut], "alive": False, "error": str(e)}
            results.append(r)
    end = datetime.utcnow().isoformat() + "Z"
    summary = {
        "subnet": f"{subnet_prefix}.0/24",
        "mode": mode,
        "tcp_port": tcp_port if mode == "tcp" else None,
        "timeout_sec": timeout,
        "delay_sec": delay,
        "workers": workers,
        "scanned_at": start,
        "completed_at": end,
        "results": results
    }
    return summary

def save_results(summary, filename=None):
    if not filename:
        filename = f"results_{summary['subnet'].replace('/', '_')}_{summary['mode']}.json"
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return filename

def parse_args():
    p = argparse.ArgumentParser(description="Ping sweeper for /24 subnet (ICMP or TCP).")
    p.add_argument("--subnet", required=True, help="Subnet prefix, e.g., 192.168.1 (scans .1-.254)")
    p.add_argument("--mode", choices=["icmp", "tcp"], default="icmp", help="Scan mode (icmp or tcp)")
    p.add_argument("--tcp-port", type=int, default=80, help="TCP port to probe when using tcp mode")
    p.add_argument("--timeout", type=float, default=1.0, help="Timeout per probe in seconds")
    p.add_argument("--delay", type=float, default=0.02, help="Delay after each probe (seconds) to be polite")
    p.add_argument("--workers", type=int, default=100, help="Number of concurrent threads")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print(f"Starting sweep: {args.subnet}.0/24  mode={args.mode} workers={args.workers}")
    summary = sweep(args.subnet, mode=args.mode, tcp_port=args.tcp_port,
                    timeout=args.timeout, delay=args.delay, workers=args.workers)
    out_file = save_results(summary)
    alive_hosts = [r["ip"] for r in summary["results"] if r.get("alive")]
    print(f"Done. Found {len(alive_hosts)} live hosts. Results saved to {out_file}")
    if alive_hosts:
        print("Live hosts:")
        for h in alive_hosts:
            print(" -", h)
