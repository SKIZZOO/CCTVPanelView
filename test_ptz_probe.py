import urllib.request
import urllib.error
import socket

# Test standard SOAP 1.1 and 1.2
soap_req_12 = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <soap:Body>
    <tds:GetCapabilities>
      <tds:Category>All</tds:Category>
    </tds:GetCapabilities>
  </soap:Body>
</soap:Envelope>"""

soap_req_11 = """<?xml version="1.0" encoding="utf-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <SOAP-ENV:Body>
    <tds:GetCapabilities>
      <tds:Category>All</tds:Category>
    </tds:GetCapabilities>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

for ip in ["192.168.1.100", "192.168.1.101"]:
    for port in [8899, 80]:
        for path in ["/onvif/device_service", "/onvif/ptz_service", "/"]:
            url = f"http://{ip}:{port}{path}"
            for req_body, ct in [
                (soap_req_12, "application/soap+xml; charset=utf-8"),
                (soap_req_11, "text/xml; charset=utf-8")
            ]:
                try:
                    req = urllib.request.Request(url, data=req_body.encode('utf-8'), headers={"Content-Type": ct})
                    res = urllib.request.urlopen(req, timeout=1.5)
                    print(f"SUCCESS {url} -> {res.status}")
                    print("Body:", res.read()[:200])
                    break
                except urllib.error.HTTPError as e:
                    print(f"HTTPError {url} -> {e.code}")
                    body = e.read()[:200]
                    print("Error Body:", body)
                except Exception as e:
                    pass
