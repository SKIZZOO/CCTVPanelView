"""Resolve Drive for desktop folders without OAuth, database scraping or sharing changes."""
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid


def resolve_drive_folder_url(folder):
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError("The selected Google Drive folder is unavailable. Start Drive for desktop and check the folder.")
    try:
        # Drive for desktop's virtual filesystem exposes this small metadata
        # stream. Treat absence/temporary local IDs as unresolved, never guess.
        with open(str(folder) + ":user.drive.id", "rb") as stream:
            identifier = stream.read(513).decode("utf-8").strip("\x00\r\n ")
    except (OSError, UnicodeError):
        raise ValueError("Cannot resolve this folder's Drive link. Choose a synced folder in Drive for desktop's virtual drive.") from None
    if identifier.startswith("local") or not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", identifier):
        raise ValueError("Google Drive has not assigned this folder a cloud ID yet. Let it sync, then check the folder again.")
    return "https://drive.google.com/drive/folders/" + identifier


def stage_drive_recording(source, folder):
    """Keep originals. Copy outside recordings in bounded chunks, without overwriting."""
    source, folder = Path(source).resolve(), Path(folder).resolve()
    link = resolve_drive_folder_url(folder)
    if not source.is_file():
        raise ValueError("The completed recording is unavailable.")
    if source.is_relative_to(folder):
        return link, str(source.relative_to(folder))
    destination = folder / (source.stem + "-" + uuid.uuid4().hex[:12] + source.suffix)
    temp_name = None
    try:
        with source.open("rb") as original, tempfile.NamedTemporaryFile(
                prefix=".cctv-copy-", suffix=".tmp", dir=folder, delete=False) as output:
            temp_name = output.name
            shutil.copyfileobj(original, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        # Windows rename fails if the destination already exists.
        os.rename(temp_name, destination)
        temp_name = None
    finally:
        if temp_name:
            try: os.unlink(temp_name)
            except OSError: pass
    return link, destination.name
