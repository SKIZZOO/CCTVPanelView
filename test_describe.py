import socket

def test_rtsp(ip):
    print(f"\n--- Testing RTSP DESCRIBE on {ip}:554 ---")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect((ip, 554))
        # Send simple RTSP DESCRIBE
        req = (
            f"DESCRIBE rtsp://{ip}:554/live/ch00_0 RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"Accept: application/sdp\r\n\r\n"
        )
        s.sendall(req.encode())
        resp = s.recv(4096)
        print("Response:\n" + resp.decode("latin1", errors="replace"))
        s.close()
    except Exception as e:
        print(f"Error on {ip}:", e)

if __name__ == "__main__":
    test_rtsp("192.168.1.100")
    test_rtsp("192.168.1.101")
