import socket

def test_rtsp(ip, port=554):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4.0)
        s.connect((ip, port))
        req = (
            f"OPTIONS rtsp://{ip}:{port}/live/ch00_0 RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"User-Agent: Cam720Revamped\r\n\r\n"
        )
        s.sendall(req.encode("utf-8"))
        res = s.recv(4096)
        print("=== OPTIONS Response ===")
        print(res.decode("utf-8", errors="ignore"))

        req2 = (
            f"DESCRIBE rtsp://{ip}:{port}/live/ch00_0 RTSP/1.0\r\n"
            f"CSeq: 2\r\n"
            f"Accept: application/sdp\r\n"
            f"User-Agent: Cam720Revamped\r\n\r\n"
        )
        s.sendall(req2.encode("utf-8"))
        res2 = s.recv(4096)
        print("=== DESCRIBE Response ===")
        print(res2.decode("utf-8", errors="ignore"))
        s.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    print("Connecting to 192.168.1.100:554...")
    test_rtsp("192.168.1.100", 554)
