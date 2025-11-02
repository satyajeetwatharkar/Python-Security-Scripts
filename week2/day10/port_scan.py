#!/usr/bin/env python3
"""
port_scan.py
Simple TCP port scanner using socket + ThreadPoolExecutor.

Usage:
  python port_scan.py --host 192.168.1.10 --ports 1-1024 --timeout 0.5 --workers 100 --banner

Examples:
  python port_scan.py --host 10.0.0.5
  python port_scan.py --host example.com --ports 22,80,443 --banner
"""

import argparse
import socket
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

def parse_ports(ports_arg):
    """
    Accept formats:
      - "1-100" -> range 1..100
      - "22,80,443" -> list of ints
      - None -> default 1..100
    """
    if not ports_arg:
        return list(range(1, 101))  # default: ports 1 to 100
    ports = set()
    for part in ports_arg.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(part))
    return sorted(p for p in ports if 1 <= p <= 65535)

def scan_port(host, port, timeout=0.5, do_banner=False):
    result = {"port": port, "open": False, "banner": None, "error": None}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            res = s.connect_ex((host, port))
            if res == 0:
                result["open"] = True
                if do_banner:
                    try:
                        # try to receive small banner
                        s.settimeout(1.0)
                        # send a short probe for some services (HTTP newline)
                        try:
                            s.sendall(b"\r\n")
                        except Exception:
                            pass
                        banner = s.recv(1024)
                        if banner:
                            try:
                                result["banner"] = banner.decode(errors="ignore").strip()
                            except Exception:
                                result["banner"] = repr(banner)
                    except Exception as be:
                        result["banner"] = f"<banner error: {be}>"
            # else closed
    except Exception as e:
        result["error"] = str(e)
    return result

def run_scan(host, ports, timeout=0.5, workers=100, do_banner=False):
    start = datetime.utcnow().isoformat() + "Z"
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(scan_port, host, p, timeout, do_banner): p for p in ports}
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception as e:
                r = {"port": futures[fut], "open": False, "banner": None, "error": str(e)}
            results.append(r)
    end = datetime.utcnow().isoformat() + "Z"
    summary = {
        "host": host,
        "ports_scanned_count": len(ports),
        "timeout_sec": timeout,
        "workers": workers,
        "scanned_at": start,
        "completed_at": end,
        "results": sorted(results, key=lambda x: x["port"])
    }
    return summary

def main():
    p = argparse.ArgumentParser(description="Simple threaded TCP port scanner.")
    p.add_argument("--host", "-t", required=True, help="Target host (IP or hostname)")
    p.add_argument("--ports", "-p", help="Ports: '1-100' or '22,80,443' (default 1-100)")
    p.add_argument("--timeout", type=float, default=0.5, help="Socket timeout (seconds)")
    p.add_argument("--workers", type=int, default=100, help="Concurrent worker threads")
    p.add_argument("--banner", action="store_true", help="Attempt to grab a small banner from open ports")
    p.add_argument("--output", "-o", default=None, help="Write JSON results to file (optional)")
    args = p.parse_args()

    ports = parse_ports(args.ports)
    print(f"Scanning {args.host} — {len(ports)} ports (timeout={args.timeout}s, workers={args.workers})")
    summary = run_scan(args.host, ports, timeout=args.timeout, workers=args.workers, do_banner=args.banner)

    open_ports = [r for r in summary["results"] if r["open"]]
    if open_ports:
        print("Open ports:")
        for r in open_ports:
            line = f" - {r['port']}"
            if r.get("banner"):
                line += f"  banner: {r['banner']}"
            print(line)
    else:
        print("No open ports found in the scanned range.")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        print(f"Results written to {args.output}")
    else:
        # print JSON summary to stdout
        print("\nJSON summary:")
        print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
