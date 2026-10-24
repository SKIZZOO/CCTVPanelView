import socket

def probe_auth(ip="192.168.1.100", port=554):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    try:
        s.connect((ip, port))
        req = (
            f"DESCRIBE rtsp://{ip}:{port}/live/ch00_0 RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"User-Agent: Lavf61.1.101\r\n"
            f"Accept: application/sdp\r\n\r\n"
        )
        s.sendall(req.encode("ascii"))
        data = s.recv(4096)
        print("Raw RTSP Response:")
        print(data.decode("latin1", errors="replace"))
        s.close()
    except Exception as e:
        print("Probe error:", e)

if __name__ == "__main__":
    probe_auth()
