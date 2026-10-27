"""Preserve saved stream identities when revisiting first-run setup."""
from copy import deepcopy
import uuid
from core.camera_urls import build_rtsp_url


def prepare_camera(camera):
    result = deepcopy(camera)
    result["id"] = result.get("id") or "cam_" + uuid.uuid4().hex
    streams = result.get("streams") or []
    if streams:
        for index, stream in enumerate(streams):
            stream["id"] = stream.get("id") or f"{result['id']}_lens{index + 1}"
        return result
    streams = []
    for index in range(2 if result.get("is_dual_lens") else 1):
        streams.append({"id": f"{result['id']}_lens{index + 1}", "name": f"Lens {index + 1}",
            "channel": index, "is_ptz": index == 0,
            "url": build_rtsp_url(result.get("username", "admin"), result.get("password", ""),
                result.get("ip", "127.0.0.1"), result.get("port", 554),
                result.get(f"lens{index + 1}_path") or f"/live/ch0{index}_0")})
    result["streams"] = streams
    return result


def merge_setup_cameras(incoming, existing):
    """A setup rescan must not invent new identities for an existing camera."""
    merged = []
    for camera in incoming:
        previous = next((old for old in existing if old.get("id") and old.get("id") == camera.get("id")), None)
        if previous is None and camera.get("ip"):
            candidates = [old for old in existing if old.get("ip") == camera["ip"]]
            scanned = [new for new in incoming if new.get("ip") == camera["ip"]]
            if len(candidates) == len(scanned) == 1:
                previous = candidates[0]
        if previous is not None and camera.get("configured") is False:
            merged.append(prepare_camera(previous))
            continue
        result = prepare_camera(camera)
        if previous is not None:
            result["id"] = previous["id"]
            old_streams = previous.get("streams", [])
            used = set()
            for index, stream in enumerate(result["streams"]):
                old = next((item for item in old_streams if item.get("id") == stream.get("id")), None)
                if old is None and stream.get("channel") is not None:
                    candidates = [item for item in old_streams if item.get("channel") == stream["channel"]]
                    if len(candidates) == 1: old = candidates[0]
                if old is None and len(old_streams) == len(result["streams"]):
                    old = old_streams[index]
                if old and old.get("id") and old["id"] not in used:
                    stream["id"] = old["id"]
                    used.add(old["id"])
        merged.append(result)
    return merged
