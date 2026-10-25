"""Consistent camera URLs for setup, tests, playback and network status."""
from urllib.parse import quote, urlsplit


def stream_path(url, default="/live/ch00_0"):
    if not url:
        return default
    try:
        parts = urlsplit(url)
        path = parts.path or default
        return path + ("?" + parts.query if parts.query else "")
    except ValueError:
        return default


def build_rtsp_url(user, password, host, port, path, scheme="rtsp"):
    # Encode credentials as URL components, never as part of the host or path.
    auth = f"{quote(user, safe='')}:{quote(password, safe='')}@" if user and password else ""
    host = host.strip().strip("[]")
    if ":" in host:
        host = f"[{host}]"
    path = path if path.startswith("/") else "/" + path
    return f"{scheme}://{auth}{host}:{int(port)}{path}"


def camera_endpoint(url):
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("rtsp", "rtsps", "http", "https") or not parts.hostname:
        raise ValueError("Enter a complete camera stream URL.")
    defaults = {"rtsp": 554, "rtsps": 322, "http": 80, "https": 443}
    return parts.hostname, parts.port or defaults[parts.scheme.lower()]
