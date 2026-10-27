"""ONVIF RTSP audio-backchannel negotiation, independent of Qt/audio devices."""
import base64
import hashlib
import re
import secrets
import socket
import time
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote

REQUIRE = "www.onvif.org/ver20/backchannel"


class AudioProtocolError(Exception):
    pass


def select_audio_track(sdp, base):
    sections = re.split(r"(?m)^m=", sdp.replace("\r", ""))[1:]
    for section in sections:
        lines = section.splitlines()
        if not lines or not lines[0].startswith("audio ") or "a=sendonly" not in lines:
            continue
        control = next((line[10:] for line in lines if line.startswith("a=control:")), "")
        mappings = {0: ("PCMU", 8000), 8: ("PCMA", 8000)}
        for line in lines:
            match = re.match(r"a=rtpmap:(\d+) (PCMA|PCMU)/(\d+)(?:/1)?$", line, re.I)
            if match:
                mappings[int(match[1])] = (match[2].upper(), int(match[3]))
        for value in lines[0].split()[3:]:
            payload = int(value) if value.isdigit() else -1
            if payload in mappings and mappings[payload][1] == 8000 and control and control != "*":
                return urljoin(base, control), payload, mappings[payload][0]
    raise AudioProtocolError("Camera does not advertise a supported ONVIF speaker track (G.711 PCMA/PCMU).")


class RTSPBackchannel:
    def __init__(self, url, username="", password="", stop=None):
        import threading
        parts = urlsplit(url)
        self.host, self.port = parts.hostname, parts.port or (322 if parts.scheme == "rtsps" else 554)
        self.username = unquote(parts.username) if parts.username is not None else username
        self.password = unquote(parts.password) if parts.password is not None else password
        host = f"[{self.host}]" if ":" in (self.host or "") else self.host
        self.uri = urlunsplit((parts.scheme, f"{host}:{self.port}", parts.path, parts.query, ""))
        self.tls = parts.scheme == "rtsps"
        self.stop = stop or threading.Event()
        self.sock = None
        self.buffer = b""
        self.session = ""
        self.challenge = ""
        self.cseq = 0
        self.nonce_count = 0
        self.channel, self.payload, self.codec = 0, 8, "PCMA"

    def _authorization(self, method, uri):
        if self.challenge.lower().startswith("basic"):
            return "Basic " + base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        if not self.challenge.lower().startswith("digest"):
            return ""
        fields = {m[1].lower(): m[2] if m[2] is not None else m[3]
                  for m in re.finditer(r'(\w+)=(?:"([^"]*)"|([^,\s]+))', self.challenge)}
        realm, nonce = fields.get("realm", ""), fields.get("nonce", "")
        algorithm = fields.get("algorithm", "MD5").upper()
        if algorithm not in ("MD5", "MD5-SESS"):
            raise AudioProtocolError("Camera uses an unsupported audio authentication algorithm.")
        md5 = lambda value: hashlib.md5(value.encode()).hexdigest()
        cnonce = secrets.token_hex(8)
        ha1 = md5(f"{self.username}:{realm}:{self.password}")
        if algorithm == "MD5-SESS":
            ha1 = md5(f"{ha1}:{nonce}:{cnonce}")
        ha2 = md5(f"{method}:{uri}")
        self.nonce_count += 1
        count = f"{self.nonce_count:08x}"
        qop = fields.get("qop", "")
        if qop and "auth" not in [v.strip() for v in qop.split(",")]:
            raise AudioProtocolError("Camera requires an unsupported audio authentication mode.")
        response = md5(f"{ha1}:{nonce}:{count}:{cnonce}:auth:{ha2}") if qop else md5(f"{ha1}:{nonce}:{ha2}")
        header = f'Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{response}"'
        if qop:
            header += f', qop=auth, nc={count}, cnonce="{cnonce}"'
        elif algorithm == "MD5-SESS":
            header += f', cnonce="{cnonce}"'
        if fields.get("opaque"):
            header += f', opaque="{fields["opaque"]}"'
        return header

    def _message(self, method, uri, headers=None):
        self.cseq += 1
        values = {"CSeq": str(self.cseq), "User-Agent": "CCTVPanelView", "Require": REQUIRE}
        if self.session:
            values["Session"] = self.session
        auth = self._authorization(method, uri)
        if auth:
            values["Authorization"] = auth
        values.update(headers or {})
        return (f"{method} {uri} RTSP/1.0\r\n" + "".join(f"{k}: {v}\r\n" for k, v in values.items()) + "\r\n").encode()

    def _receive(self):
        deadline = time.monotonic() + 4
        while not self.stop.is_set() and time.monotonic() < deadline:
            # A camera can interleave RTCP with RTSP responses.
            if self.buffer.startswith(b"$") and len(self.buffer) >= 4:
                size = int.from_bytes(self.buffer[2:4], "big") + 4
                if len(self.buffer) >= size:
                    self.buffer = self.buffer[size:]
                    continue
            elif b"\r\n\r\n" in self.buffer:
                header, body = self.buffer.split(b"\r\n\r\n", 1)
                lines = header.decode("utf-8", "replace").split("\r\n")
                values = {k.lower(): v.strip() for line in lines[1:] if ":" in line for k, v in [line.split(":", 1)]}
                length = int(values.get("content-length", "0"))
                if length < 0 or length > 1024 * 1024:
                    raise AudioProtocolError("Invalid camera audio response.")
                if len(body) >= length:
                    self.buffer = body[length:]
                    return int(lines[0].split()[1]), values, body[:length].decode("utf-8", "replace")
            try:
                chunk = self.sock.recv(8192)
            except socket.timeout:
                continue
            if not chunk:
                raise AudioProtocolError("Camera closed the audio connection.")
            self.buffer += chunk
            if len(self.buffer) > 1024 * 1024 + 65536:
                raise AudioProtocolError("Camera audio response is too large.")
        raise AudioProtocolError("Camera audio request cancelled or timed out.")

    def request(self, method, uri=None, headers=None):
        uri = uri or self.uri
        for attempt in range(2):
            if self.stop.is_set():
                raise AudioProtocolError("Audio connection cancelled.")
            self.sock.sendall(self._message(method, uri, headers))
            code, values, body = self._receive()
            if code == 401 and attempt == 0:
                self.challenge = values.get("www-authenticate", "")
                continue
            if code == 401:
                raise AudioProtocolError("Camera rejected the intercom username/password.")
            if code != 200:
                raise AudioProtocolError(f"Camera rejected audio {method} (RTSP {code}).")
            return values, body
        raise AudioProtocolError("Camera audio authentication failed.")

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=3)
        if self.tls:
            from core.network_tls import verified_tls_context
            self.sock = verified_tls_context().wrap_socket(self.sock, server_hostname=self.host)
        self.sock.settimeout(.3)
        headers, sdp = self.request("DESCRIBE", headers={"Accept": "application/sdp"})
        track, self.payload, self.codec = select_audio_track(sdp, headers.get("content-base", self.uri.rstrip("/") + "/"))
        headers, _ = self.request("SETUP", track, {"Transport": "RTP/AVP/TCP;unicast;interleaved=0-1"})
        self.session = headers.get("session", "").split(";", 1)[0]
        if not self.session:
            raise AudioProtocolError("Camera did not create an audio session.")
        transport = headers.get("transport", "")
        match = re.search(r"interleaved=(\d+)-(\d+)", transport)
        if not match or int(match[1]) > 255:
            raise AudioProtocolError("Camera did not accept TCP audio transport.")
        self.channel = int(match[1])
        self.request("PLAY")

    def close(self):
        if self.sock:
            try:
                if self.session:
                    self.sock.sendall(self._message("TEARDOWN", self.uri))
            except Exception:
                pass
            finally:
                self.sock.close()
                self.sock = None
