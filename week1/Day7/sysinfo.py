import logging
import platform
import socket
import getpass
import os

# Setup logging
logging.basicConfig(
    filename='sysinfo.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_hostname():
    try:
        host = socket.gethostname()
        logging.info(f"Hostname: {host}")
        return host
    except Exception as e:
        logging.error(f"Failed to get hostname: {e}")
        return "Unknown"

def get_user():
    try:
        user = getpass.getuser()
        logging.info(f"Current user: {user}")
        return user
    except Exception as e:
        logging.error(f"Failed to get user: {e}")
        return "Unknown"

def main():
    logging.info("Starting sysinfo collector script")
    hostname = get_hostname()
    user = get_user()
    os_info = platform.system() + " " + platform.release()
    logging.info(f"OS info: {os_info}")

    print(f"Hostname: {hostname}")
    print(f"Current User: {user}")
    print(f"OS Info: {os_info}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Script crashed: {e}")
        print("Critical error occurred! Check sysinfo.log for details.")
