import urllib.request
import urllib.parse
import base64

def test_url(url, auth_user="admin", auth_pass="password123"):
    req = urllib.request.Request(url)
    auth_str = base64.b64encode(f"{auth_user}:{auth_pass}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth_str}")
    try:
        resp = urllib.request.urlopen(req, timeout=2)
        print(f"SUCCESS {url} -> {resp.status} : {resp.read()[:200]}")
        return True
    except urllib.error.HTTPError as e:
        body = e.read()[:200]
        print(f"HTTP {e.code} for {url} -> body: {body}")
        return False
    except Exception as e:
        print(f"ERR {url} -> {e}")
        return False

# Test combinations of arguments
ip = "192.168.1.100"
args_list = [
    "-step=0&-act=left&-speed=45",
    "-step=1&-act=left&-speed=45",
    "act=left&speed=5",
    "cmd=left",
    "action=left",
    "-act=left",
    "-step=0&-act=right",
    "direction=left",
    "-act=stop",
    "-step=0&-act=stop"
]

for script in ["/cgi-bin/hi3510/ptzctrl.cgi", "/cgi-bin/ptzctrl.cgi", "/cgi-bin/ptz.cgi"]:
    for a in args_list:
        test_url(f"http://{ip}{script}?{a}")
