"""Short, safe names for phone attachments; original recordings stay untouched."""
import re
import unicodedata
from datetime import datetime


def attachment_name(camera, label, timestamp=None, *, snapshot=False):
    def slug(value, fallback, limit):
        value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
        return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")[:limit].rstrip("-") or fallback

    try:
        recorded = datetime.fromisoformat(str(timestamp))
    except (TypeError, ValueError):
        recorded = datetime.now()
    camera = str(camera).split(" (")[0].strip()
    event = slug(str(label).title(), "Detection", 24)
    camera = slug(camera, "Camera", 40)
    kind, ext = ("Snapshot", "jpg") if snapshot else ("Preview", "mp4")
    return f"{event}_{camera}_{recorded:%Y-%m-%d_%H-%M-%S}_{kind}.{ext}"
