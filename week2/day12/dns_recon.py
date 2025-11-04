#!/usr/bin/env python3
"""
dns_recon.py
Perform DNS lookups (A, MX, NS, TXT) for a target domain.
Uses dnspython if installed; falls back to socket.getaddrinfo for A records.

Usage:
  python dns_recon.py --domain example.com --output example_example.com.json
  python dns_recon.py --domain example.com --nameserver 8.8.8.8
"""

import argparse
import json
import socket
import sys
from datetime import datetime

# Try to import dnspython
try:
    import dns.resolver
    HAVE_DNSPY = True
except Exception:
    HAVE_DNSPY = False

def query_with_dnspython(domain, qtype, resolver=None, lifetime=3.0):
    """Query using dnspython and return list of strings (or empty list)."""
    answers = []
    try:
        res = dns.resolver.resolve(domain, qtype, lifetime=lifetime, resolver=resolver)
        for r in res:
            answers.append(r.to_text())
    except Exception as e:
        # return error as a string in answers? We'll return [] and capture error elsewhere
        return [], str(e)
    return answers, None

def query_a_fallback(domain):
    """Fallback to socket.getaddrinfo for A/AAAA addresses."""
    addrs = []
    try:
        infos = socket.getaddrinfo(domain, None)
        for info in infos:
            family, _, _, _, sockaddr = info
            ip = sockaddr[0]
            # include IPv4 and IPv6 but deduplicate
            if ip not in addrs:
                addrs.append(ip)
    except Exception as e:
        return [], str(e)
    return addrs, None

def run_dns_recon(domain, nameserver=None, timeout=3.0):
    """
    Run A, MX, NS, TXT queries for domain.
    If dnspython not available, A uses socket fallback and other types will be attempted via dns.resolver if possible.
    """
    out = {
        "domain": domain,
        "queried_at": datetime.utcnow().isoformat() + "Z",
        "nameserver_used": nameserver or "system-default",
        "results": {},
        "errors": {}
    }

    # Setup resolver if dnspython is available and nameserver provided
    resolver = None
    if HAVE_DNSPY:
        try:
            resolver = dns.resolver.Resolver()
            resolver.lifetime = timeout
            if nameserver:
                resolver.nameservers = [nameserver]
        except Exception as e:
            out["errors"]["resolver_setup"] = str(e)

    # A records
    if HAVE_DNSPY:
        res, err = query_with_dnspython(domain, "A", resolver=resolver, lifetime=timeout)
        if err:
            # fallback to socket
            out["errors"]["A_dnspython"] = err
            res2, err2 = query_a_fallback(domain)
            out["results"]["A"] = res2
            if err2:
                out["errors"]["A_socket_fallback"] = err2
        else:
            out["results"]["A"] = res
    else:
        res, err = query_a_fallback(domain)
        out["results"]["A"] = res
        if err:
            out["errors"]["A_socket_fallback"] = err

    # MX records
    if HAVE_DNSPY:
        mx, err = query_with_dnspython(domain, "MX", resolver=resolver, lifetime=timeout)
        if err:
            out["errors"]["MX"] = err
            out["results"]["MX"] = []
        else:
            # MX answers are like: "10 mail.example.com."
            mx_parsed = []
            for m in mx:
                try:
                    # split on whitespace to separate preference & exchange
                    parts = m.split()
                    if len(parts) >= 2:
                        pref = parts[0]
                        exch = " ".join(parts[1:]).rstrip(".")
                        mx_parsed.append({"preference": int(pref), "exchange": exch})
                    else:
                        mx_parsed.append({"raw": m})
                except Exception:
                    mx_parsed.append({"raw": m})
            out["results"]["MX"] = mx_parsed
    else:
        out["results"]["MX"] = []
        out["errors"]["MX"] = "dnspython not available — MX lookup skipped"

    # NS records
    if HAVE_DNSPY:
        ns, err = query_with_dnspython(domain, "NS", resolver=resolver, lifetime=timeout)
        if err:
            out["errors"]["NS"] = err
            out["results"]["NS"] = []
        else:
            # strip trailing dots
            out["results"]["NS"] = [n.rstrip(".") for n in ns]
    else:
        out["results"]["NS"] = []
        out["errors"]["NS"] = "dnspython not available — NS lookup skipped"

    # TXT records
    if HAVE_DNSPY:
        txt, err = query_with_dnspython(domain, "TXT", resolver=resolver, lifetime=timeout)
        if err:
            out["errors"]["TXT"] = err
            out["results"]["TXT"] = []
        else:
            # txt entries often appear as quoted slices; join them
            txt_parsed = []
            for t in txt:
                # dns returns like: "v=spf1 -all" or strings with quotes
                txt_parsed.append(t)
            out["results"]["TXT"] = txt_parsed
    else:
        out["results"]["TXT"] = []
        out["errors"]["TXT"] = "dnspython not available — TXT lookup skipped"

    return out

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

def parse_args():
    p = argparse.ArgumentParser(description="DNS recon: A, MX, NS, TXT lookups")
    p.add_argument("--domain", required=True, help="Domain to query (example.com)")
    p.add_argument("--nameserver", help="Optional DNS resolver to use (e.g., 8.8.8.8)")
    p.add_argument("--timeout", type=float, default=3.0, help="Timeout per query (seconds)")
    p.add_argument("--output", "-o", default=None, help="Output JSON file path")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    out = run_dns_recon(args.domain, nameserver=args.nameserver, timeout=args.timeout)
    out_file = args.output or f"dns_{args.domain.replace('.', '_')}.json"
    save_json(out, out_file)
    print(f"DNS recon for {args.domain} saved to {out_file}")
    if out.get("errors"):
        print("Some lookups returned errors or fallbacks. See JSON 'errors' field for details.")
