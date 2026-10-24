import subprocess
from concurrent.futures import ThreadPoolExecutor

def ping(ip):
    res = subprocess.run(["ping", "-n", "1", "-w", "400", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0:
        return ip
    return None

def sweep():
    ips = [f"192.168.0.{i}" for i in range(1, 255)]
    print("Pinging subnet...")
    with ThreadPoolExecutor(max_workers=60) as ex:
        results = [r for r in ex.map(ping, ips) if r]
    print("Alive IPs on 192.168.0.0/24:")
    for ip in sorted(results, key=lambda x: int(x.split(".")[-1])):
        print(" ", ip)

if __name__ == "__main__":
    sweep()
