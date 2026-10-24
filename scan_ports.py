import socket
from concurrent.futures import ThreadPoolExecutor

def check_port(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        s.connect((ip, port))
        s.close()
        return port
    except:
        return None

def scan_ports(ip, start_port=1, end_port=10000):
    open_ports = []
    with ThreadPoolExecutor(max_workers=250) as executor:
        futures = {executor.submit(check_port, ip, p): p for p in range(start_port, end_port)}
        for f in futures:
            res = f.result()
            if res:
                open_ports.append(res)
                print(f"Open port found: {res}")
    return open_ports

if __name__ == "__main__":
    print("Scanning 192.168.1.100 for open ports (1-10000)...")
    ports = scan_ports("192.168.1.100", 1, 10000)
    print("Finished scan! Open ports:", ports)
