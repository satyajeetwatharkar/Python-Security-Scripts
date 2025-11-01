import socket
import sys
import logging

# Setup logging
logging.basicConfig(
    filename='tcp_client.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def tcp_client(host, port, message):
    try:
        # 1️⃣ Create a socket (AF_INET = IPv4, SOCK_STREAM = TCP)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.info(f"Socket created for {host}:{port}")

        # 2️⃣ Set timeout (avoid waiting forever)
        client.settimeout(5)
        logging.info("Timeout set to 5 seconds")

        # 3️⃣ Connect to target
        client.connect((host, port))
        logging.info(f"Connected to {host}:{port}")

        # 4️⃣ Send data
        client.sendall(message.encode())
        logging.info(f"Sent message: {message}")

        # 5️⃣ Receive response
        response = client.recv(4096)
        logging.info(f"Received response: {response.decode(errors='ignore')}")

        print("Response from server:", response.decode(errors='ignore'))

    except socket.timeout:
        logging.error("Connection timed out.")
        print("❌ Connection timed out.")
    except socket.error as e:
        logging.error(f"Socket error: {e}")
        print(f"❌ Socket error: {e}")
    except Exception as e:
        logging.critical(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
    finally:
        # 6️⃣ Always close the connection
        client.close()
        logging.info("Connection closed.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python tcp_client.py <host> <port> <message>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    message = sys.argv[3]

    tcp_client(host, port, message)
