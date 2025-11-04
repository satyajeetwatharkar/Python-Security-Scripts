#!/usr/bin/env python3
"""
banner_grab.py
Connect to host:port pairs, attempt to read banners (and HTTP headers for HTTP ports),
and save results to JSON.

Usage:
  python banner_grab.py --host example.com --ports 22,80,443 --output banners.json
  python banner_grab.py --targets targets.txt --output banners.json

targets.txt example:
example.com:22
192.168.1.10:80
"""

import argparse
import socket
import json
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

HTTP_PORTS = {80, 8080, 8000, 443, 8443}

def try_banner(host, port, timeout=2.0, http_probe=True, use_ssl=False):
    """
    Attempt to connect to host:port and read a banner.
    If http_probe is True and port in HTTP_PORTS, send a minimal HTTP request.
    use_ssl forces wrapping the socket with TLS (useful for 443/8443).
    Returns dict with keys: host, port, success, banner, error, elapsed.
    """
    out = {
        "host": host,
        "port": port,
        "success": False,
        "banner": None,
        "error": None,
        "elapsed_ms": None,
        "probing": "http" if (http_probe and port in HTTP_PORTS) else "tcp"
    }
    start = time.time()
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)

        # Connect
        s.connect((host, port))

        # Optionally wrap in SSL (useful for HTTPS)
        if use_ssl or port in (443, 8443):
            try:
                context = ssl.create_default_context()
                s = context.wrap_socket(s, server_hostname=host)
            except Exception as e:
                # SSL wrapping failed; continue as plain socket (note the error)
                out["error"] = f"ssl_wrap_error: {e}"

        # If HTTP probe is appropriate, send a minimal request
        if http_probe and port in HTTP_PORTS:
            try:
                req = f"HEAD / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
                s.sendall(req.encode())
            except Exception:
                # It's okay if send fails; we'll still try to recv banner
                pass

        # Try to receive up to 4 KB
        try:
            data = s.recv(4096)
            if data:
                try:
                    out["banner"] = data.decode(errors="ignore").strip()
                except Exception:
                    out["banner"] = repr(data)
                out["success"] = True
            else:
                out["banner"] = None
        except socket.timeout:
            out["error"] = "recv_timeout"
        except Exception as e:
            out["error"] = f"recv_error: {e}"
    except socket.timeout:
        out["error"] = "connect_timeout"
    except Exception as e:
        out["error"] = f"connect_error: {e}"
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass
        out["elapsed_ms"] = int((time.time() - start) * 1000)
    return out

def parse_ports(ports_arg):
    if not ports_arg:
        return []
    ports = set()
    for p in ports_arg.split(","):
        p = p.strip()
        if "-" in p:
            a, b = p.split("-", 1)
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(p))
    return sorted(p for p in ports if 1 <= p <= 65535)

def read_targets_file(path):
    targets = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                host, port = line.split(":", 1)
                targets.append((host.strip(), int(port.strip())))
            else:
                # default port 80 if none provided
                targets.append((line, 80))
    return targets

def build_targets_from_args(host, ports_list):
    targets = []
    if not host or not ports_list:
        return targets
    for p in ports_list:
        targets.append((host, p))
    return targets

def run_bulk(targets, timeout=2.0, workers=50, http_probe=True, ssl_force=False):
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(try_banner, t[0], t[1], timeout, http_probe, ssl_force): t for t in targets}
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception as e:
                host, port = futures[fut]
                r = {"host": host, "port": port, "success": False, "banner": None, "error": f"exception:{e}", "elapsed_ms": None}
            results.append(r)
    return results

def main():
    p = argparse.ArgumentParser(description="Banner grabber - collect banners/headers from host:port pairs")
    p.add_argument("--host", help="Single host (use with --ports)")
    p.add_argument("--ports", help="Comma list or range, e.g., 22,80,443 or 1-100")
    p.add_argument("--targets", help="File with host:port per line (overrides --host/--ports)")
    p.add_argument("--timeout", type=float, default=2.0, help="Socket timeout seconds")
    p.add_argument("--workers", type=int, default=50, help="Concurrent workers")
    p.add_argument("--no-http-probe", action="store_true", help="Disable sending HTTP HEAD on HTTP ports")
    p.add_argument("--ssl", action="store_true", help="Force SSL/TLS wrapping (useful for testing HTTPS on non-standard ports)")
    p.add_argument("--output", "-o", default=f"banners_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json", help="Output JSON file")
    args = p.parse_args()

    # Build targets
    if args.targets:
        targets = read_targets_file(args.targets)
    else:
        ports = parse_ports(args.ports) if args.ports else [80]
        targets = build_targets_from_args(args.host, ports)

    if not targets:
        print("No targets specified. Use --host/--ports or --targets file.")
        return

    print(f"Probing {len(targets)} targets (workers={args.workers}, timeout={args.timeout}s)...")
    results = run_bulk(targets, timeout=args.timeout, workers=args.workers, http_probe=not args.no_http_probe, ssl_force=args.ssl)

    # Save JSON
    out = {
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "results": results
    }
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"Done. Results written to {args.output}")

if __name__ == "__main__":
    from datetime import datetime
    main()
