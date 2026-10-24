import urllib.request
import urllib.parse
import hashlib

ip = "192.168.1.100"
pwd = "password123"
md5_pwd = hashlib.md5(pwd.encode()).hexdigest()

keys = ["System", "PTZ", "Motor", "Camera", "Video", "NetWork", "Audio", "Device", "Motion", "Alarm", "Preset"]

for k in keys:
    tmpl = f'{{"{k}":{{}}}}'
    url = f"http://{ip}/goform/getOtherSetttings?userid=admin&userkey={md5_pwd}&singleCMD=GetJsonConf&json_string=" + urllib.parse.quote(tmpl)
    try:
        resp = urllib.request.urlopen(url, timeout=2)
        txt = resp.read().decode('utf-8', errors='ignore')
        print(f"Key {k}: {txt.strip()}")
    except Exception as e:
        print(f"Key {k} err: {e}")
