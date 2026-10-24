import socket
import time

WS_DISCOVERY_PROBE = """<?xml version="1.0" encoding="utf-8"?>
<Envelope xmlns:dn="http://www.onvif.org/ver10/network/wsdl"
          xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Header>
    <wsa:MessageID xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">uuid:c0a80001-dead-beef-cafe-0123456789ab</wsa:MessageID>
    <wsa:To xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    <wsa:Action xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
  </Header>
  <Body>
    <Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">
      <Types>dn:NetworkVideoTransmitter</Types>
    </Probe>
  </Body>
</Envelope>"""

def discover():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(3.0)
    try:
        sock.sendto(WS_DISCOVERY_PROBE.encode("utf-8"), ("239.255.255.250", 3702))
        print("Sent WS-Discovery probe, listening for responses...")
    except Exception as e:
        print("Send error:", e)
        return

    found = []
    start = time.time()
    while time.time() - start < 4.0:
        try:
            data, addr = sock.recvfrom(65535)
            print(f"=== Found device at {addr[0]}:{addr[1]} ===")
            text = data.decode("utf-8", errors="ignore")
            for line in text.splitlines():
                if any(k in line.lower() for k in ["xaddr", "onvif", "device", "scope", "http://"]):
                    print("  ", line.strip())
            found.append((addr, text))
        except socket.timeout:
            break
        except Exception as e:
            print("Recv error:", e)
            break

    if not found:
        print("No WS-Discovery responses received.")

if __name__ == "__main__":
    discover()
