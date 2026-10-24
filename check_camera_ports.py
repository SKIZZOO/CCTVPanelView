import socket
import sys

ip = "192.168.1.100"
ports = [554, 80, 8080, 8899, 8000, 5000, 34567, 37777, 8554, 8081, 6688, 10000, 20000, 8082, 8001, 8888, 9999, 10554, 5540]

print(f"Checking ports on {ip}...")
for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.2)
    try:
        s.connect((ip, port))
        print(f"--> PORT {port} IS OPEN!")
        s.close()
    except Exception as e:
        # print(f"Port {port} closed ({e})")
        pass
print("Done check.")
