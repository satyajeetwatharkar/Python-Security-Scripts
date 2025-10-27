#!/usr/bin/env python3
"""
Day 4 — File I/O + Log Parser
Author: Satyajeet
Task: Parse sample auth log, count failed logins, export to CSV.
"""

import re
import csv
import os

# Path to log file
LOG_PATH = "Sample_auth.log"
OUTPUT_CSV = "results.csv"

def parse_log(log_path):
    """
    Parses the log file for failed SSH logins.
    Returns a dictionary mapping IP -> failed attempt count.
    """
    failed_logins = {}

    # Safely open file
    with open(log_path, "r") as f:
        for line in f:
            # Check for failed password entries
            if "Failed password" in line:
                # Regex to extract username & IP
                match = re.search(r'Failed password for (?:invalid user )?(\S+) from (\S+)', line)
                if match:
                    user, ip = match.groups()
                    failed_logins[ip] = failed_logins.get(ip, 0) + 1

    return failed_logins


def export_to_csv(data, output_path):
    """
    Exports the failed login counts to a CSV file.
    """
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["IP Address", "Failed_Attempts"])
        for ip, count in data.items():
            writer.writerow([ip, count])


def main():
    print("🔍 Parsing log file:", LOG_PATH)
    
    if not os.path.exists(LOG_PATH):
        print("❌ Log file not found! Please check path:", LOG_PATH)
        return

    # Parse the log
    failed_logins = parse_log(LOG_PATH)

    # Export results
    export_to_csv(failed_logins, OUTPUT_CSV)

    # Print summary
    print("\n📊 Failed login attempts by IP:")
    for ip, count in failed_logins.items():
        print(f"{ip:20} → {count} attempts")

    print(f"\n✅ Results exported to '{OUTPUT_CSV}'")


if __name__ == "__main__":
    main()
