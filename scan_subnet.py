import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor

def check_ip(i):
    ip = f"192.168.0.{i}"
    # check common camera ports: 554, 80, 8899, 8000, 5000, 8080
    for port in [554, 8899, 80, 8080, 5000]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        try:
            s.connect((ip, port))
            s.close()
            return (ip, port)
        except:
            s.close()
    return None

def scan_network():
    print("Scanning subnet 192.168.0.1 - 254 for RTSP/ONVIF ports...")
    with ThreadPoolExecutor(max_workers=100) as executor:
        results = executor.map(check_ip, range(1, 255))
        found = [r for r in results if r]
        for ip, port in found:
            print(f"FOUND CAMERA SERVICE: {ip}:{port}")
        return found

if __name__ == "__main__":
    scan_network()
