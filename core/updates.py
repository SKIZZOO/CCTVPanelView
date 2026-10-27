"""Versioned GitHub release discovery and bounded, hash-verified downloads."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request
from urllib.parse import urlsplit
from core.version import APP_VERSION, GITHUB_REPOSITORY

LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
MAX_INSTALLER_BYTES = 1024 * 1024 * 1024
_DOWNLOAD_HOSTS = {"github.com", "api.github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}


def version_tuple(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value))
    if not match:
        raise ValueError("The release does not have a supported stable version number.")
    return tuple(int(part) for part in match.groups())


def validate_download_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in _DOWNLOAD_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("The update download is not on an approved HTTPS GitHub host.")
    return url


class GitHubRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        validate_download_url(newurl)
        return super().redirect_request(request, fp, code, message, headers, newurl)


def open_url(url):
    validate_download_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": f"CCTVPanelView/{APP_VERSION}", "Accept": "application/vnd.github+json" if url == LATEST_URL else "application/octet-stream"})
    return urllib.request.build_opener(GitHubRedirects()).open(request, timeout=20)


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    installer_url: str
    sha256: str
    size: int


def parse_release(data):
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        raise ValueError("GitHub did not return a published stable release.")
    tag = data.get("tag_name", "")
    if not isinstance(tag, str) or not tag.startswith("v"):
        raise ValueError("The stable release tag must start with v.")
    version_tuple(tag)
    version = tag.lstrip("v")
    expected_page = f"https://github.com/{GITHUB_REPOSITORY}/releases/tag/{tag}"
    if data.get("html_url") != expected_page:
        raise ValueError("The release belongs to a different repository.")
    name = f"CCTVPanelView-{version}-Setup.exe"
    expected_download = f"https://github.com/{GITHUB_REPOSITORY}/releases/download/{tag}/{name}"
    assets = [asset for asset in data.get("assets", []) if isinstance(asset, dict) and asset.get("name") == name]
    if len(assets) != 1:
        raise ValueError("This release does not contain one matching Windows installer.")
    asset = assets[0]
    digest = asset.get("digest", "")
    size = asset.get("size")
    if asset.get("state") != "uploaded" or asset.get("browser_download_url") != expected_download:
        raise ValueError("The Windows installer is not ready or has an unexpected download URL.")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest):
        raise ValueError("This release has no verifiable SHA-256 installer digest.")
    if type(size) is not int or not 0 < size <= MAX_INSTALLER_BYTES:
        raise ValueError("The installer size is invalid.")
    return Release(version, expected_page, expected_download, digest[7:].lower(), size)


def check_latest():
    with open_url(LATEST_URL) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("The release response was too large.")
    return parse_release(json.loads(raw))


def verify_installer(path, release):
    path = Path(path)
    if path.stat().st_size != release.size:
        raise ValueError("The update download is incomplete or changed size.")
    with path.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if digest != release.sha256:
        raise ValueError("The installer checksum does not match GitHub's release digest.")


def download_release(release, cache_dir, progress=None, cancelled=None):
    # Reconstruct the expected URL rather than trusting a caller-provided path.
    expected = f"https://github.com/{GITHUB_REPOSITORY}/releases/download/v{release.version}/CCTVPanelView-{release.version}-Setup.exe"
    version_tuple(release.version)
    if release.installer_url != expected:
        raise ValueError("Unexpected installer location.")
    cache = Path(cache_dir); cache.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=f"{release.version}-", dir=cache))
    partial = folder / "installer.part"
    destination = folder / "CCTVPanelView-Setup.exe"
    total = 0
    last_percent = -1
    try:
        with open_url(release.installer_url) as response, partial.open("xb") as output:
            while True:
                if cancelled and cancelled.is_set():
                    raise ValueError("Update download cancelled.")
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > release.size or total > MAX_INSTALLER_BYTES:
                    raise ValueError("The download exceeded the published installer size.")
                output.write(chunk)
                percent = int(total * 100 / release.size)
                if progress and percent != last_percent:
                    progress(percent)
                    last_percent = percent
            output.flush(); os.fsync(output.fileno())
        verify_installer(partial, release)
        os.replace(partial, destination)
        return str(destination)
    finally:
        partial.unlink(missing_ok=True)
