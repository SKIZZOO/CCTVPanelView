import socket
from concurrent.futures import ThreadPoolExecutor

def check_ip_rtsp(i):
    ip = f"192.168.0.{i}"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    res = s.connect_ex((ip, 554))
    s.close()
    if res == 0:
        return ip
    return None

if __name__ == "__main__":
    print("Fast-scanning entire 192.168.0.x for RTSP port 554...")
    with ThreadPoolExecutor(max_workers=100) as ex:
        results = [ip for ip in ex.map(check_ip_rtsp, range(1, 255)) if ip]
    print(f"RTSP 554 open on: {results}")
