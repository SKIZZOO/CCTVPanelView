import socket
import hashlib
import base64
import re

def parse_auth_header(header):
    auth_dict = {}
    matches = re.findall(r'(\w+)="?([^",]+)"?', header)
    for k, v in matches:
        auth_dict[k] = v
    return auth_dict

def test_auth(ip, uri, username, password):
    print(f"\n==========================================")
    print(f"Testing {ip} uri={uri} user={username} pass={password}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    try:
        s.connect((ip, 554))
        # Step 1: Send DESCRIBE without auth
        req1 = (
            f"DESCRIBE {uri} RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"Accept: application/sdp\r\n\r\n"
        )
        s.sendall(req1.encode())
        resp1 = s.recv(4096).decode("latin1", errors="replace")
        
        auth_line = None
        for line in resp1.split("\r\n"):
            if line.startswith("WWW-Authenticate:"):
                auth_line = line
                break
        
        if not auth_line:
            print("No WWW-Authenticate header found! Response:")
            print(resp1)
            s.close()
            return False

        print("Auth challenge:", auth_line)
        cseq = 2
        
        if "Digest" in auth_line:
            realm_match = re.search(r'realm="([^"]+)"', auth_line)
            nonce_match = re.search(r'nonce="([^"]+)"', auth_line)
            realm = realm_match.group(1) if realm_match else "ipc"
            nonce = nonce_match.group(1) if nonce_match else ""
            
            # HA1 = md5(username:realm:password)
            ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
            # HA2 = md5(method:uri)
            ha2 = hashlib.md5(f"DESCRIBE:{uri}".encode()).hexdigest()
            # response = md5(HA1:nonce:HA2)
            response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            
            auth_header = (
                f'Digest username="{username}", realm="{realm}", nonce="{nonce}", '
                f'uri="{uri}", response="{response}"'
            )
        else: # Basic
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            auth_header = f"Basic {token}"
            
        req2 = (
            f"DESCRIBE {uri} RTSP/1.0\r\n"
            f"CSeq: {cseq}\r\n"
            f"Authorization: {auth_header}\r\n"
            f"Accept: application/sdp\r\n\r\n"
        )
        s.sendall(req2.encode())
        resp2 = s.recv(4096).decode("latin1", errors="replace")
        s.close()
        
        status_line = resp2.split("\r\n")[0]
        print("Auth attempt result:", status_line)
        if "200 OK" in status_line:
            print("SUCCESS! Authenticated successfully!")
            print("SDP snippet:\n" + "\n".join(resp2.split("\r\n")[:15]))
            return True
        else:
            return False
    except Exception as e:
        print("Error:", e)
        return False

if __name__ == "__main__":
    passwords = ["password123", "password123"]
    
    # Test 192.168.1.100 with both channels (ch00_0 and ch01_0)
    for pw in passwords:
        for ch in ["/live/ch00_0", "/live/ch01_0", "/onvif1", "/onvif2"]:
            uri = f"rtsp://192.168.1.100:554{ch}"
            if test_auth("192.168.1.100", uri, "admin", pw):
                print(f"*** FOUND WORKING STREAM FOR 192.168.1.100: {uri} (pw: {pw}) ***")
                
    # Test 192.168.1.101
    for pw in passwords:
        uri = f"rtsp://192.168.1.101:554/live/ch00_0"
        if test_auth("192.168.1.101", uri, "admin", pw):
            print(f"*** FOUND WORKING STREAM FOR 192.168.1.101: {uri} (pw: {pw}) ***")
