import socket

ips = [
    "192.168.1.100", "192.168.1.101", "192.168.0.101", 
    "192.168.1.105", "192.168.0.103", "192.168.0.108", 
    "192.168.1.102", "192.168.1.103", "192.168.1.104"
]

print("Checking port 554 on potential camera IPs...")
for ip in ips:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.8)
    res = s.connect_ex((ip, 554))
    if res == 0:
        print(f"*** FOUND RTSP (554) ON: {ip} ***")
    s.close()
print("Scan complete.")
