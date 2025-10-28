#!/usr/bin/env python3
"""
Day 5 — Subprocess & Shell Automation
Author: Satyajeet
Task: Run multiple shell commands, capture output/errors, save to timestamped log.
"""

import subprocess
import datetime
import platform
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Detect OS for cross-platform compatibility
is_windows = platform.system().lower() == "windows"

# Define commands
commands = [
    ["ping", "google.com", "-n", "2"] if is_windows else ["ping", "-c", "2", "google.com"],
    ["ver"] if is_windows else ["uname", "-a"],
    ["whoami"]
]

# Timestamped log file
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_path = os.path.join("logs", f"command_log_{timestamp}.txt")

with open(log_path, "w") as log_file:
    log_file.write(f"Command Run Log — {timestamp}\n")
    log_file.write("=" * 60 + "\n\n")

    for cmd in commands:
        log_file.write(f"Command: {' '.join(cmd)}\n")
        log_file.write("-" * 60 + "\n")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            log_file.write("STDOUT:\n" + result.stdout + "\n")
            log_file.write("STDERR:\n" + result.stderr + "\n")
            log_file.write(f"Return Code: {result.returncode}\n")
            log_file.write("=" * 60 + "\n\n")

        except Exception as e:
            log_file.write(f"Error running command {cmd}: {str(e)}\n")
            log_file.write("=" * 60 + "\n\n")

print(f"✅ Commands executed. Log saved at: {log_path}")
