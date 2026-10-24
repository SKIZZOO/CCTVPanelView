<div align="center">

<img src="assets/cctvpanelview_logo.png" width="112" alt="CCTVPanelView" />

# CCTVPanelView

**A Windows desktop CCTV viewer and recorder for IP cameras, with an optional browser-based monitoring interface.**

[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)](https://github.com/SKIZZOO/CCTVPanelView)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Download](https://github.com/SKIZZOO/CCTVPanelView/releases/latest) · [Features](#features) · [Install from source](#run-from-source) · [Security](#web-access-and-security) · [Review notes](docs/REVIEW-2026-10-24.md)

</div>

---

CCTVPanelView connects to RTSP/ONVIF-capable IP cameras, displays multiple streams in a configurable grid, and provides recording, motion alerts, and optional local object detection. It includes a Windows desktop application and an optional HTTP/MJPEG web interface for phones and other browsers.

The project is intended for trusted home or small-site networks. Camera compatibility, decoding performance, and practical camera count depend on the camera, stream settings, and PC hardware.

## Features

- Multi-camera live view with 1, 2, 4, or 9 tile layouts, camera assignment, and fullscreen viewing.
- RTSP streams and camera controls for supported devices; ONVIF and camera-specific behavior vary by model.
- Recording, snapshots, storage settings, and configurable retention.
- Motion detection, optional local YOLOv5 ONNX detection, and configurable notifications.
- Optional browser interface with live views, alerts, and supported PTZ controls.
- Responsive desktop header that moves secondary actions into a **More** menu at narrower window widths.
- Headless web-server startup is also available with `Start_CCTV_Headless_Server.bat`.

## Download and install

For the packaged Windows build, open [Releases](https://github.com/SKIZZOO/CCTVPanelView/releases/latest), download `CCTVPanelView-v2.0-Setup.zip`, extract it, then run `CCTVPanelView-Setup.exe`. Follow the installer prompts.

The release is a ZIP containing the installer; the standalone `.exe` is inside the extracted archive.

## Run from source

### Requirements

- Windows 10 or 11 (64-bit)
- Python 3.11 or newer
- Git

### Setup

```powershell
git clone https://github.com/SKIZZOO/CCTVPanelView.git
cd CCTVPanelView
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks environment activation, use the virtual environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

The application uses local configuration and model files. Keep camera credentials and notification secrets out of source control. The repository includes `cameras_config.example.json` as a configuration reference.

## First launch and cameras

Use the startup prompt or **Add Camera** to configure a camera. Enter the camera address, RTSP/ONVIF ports, credentials, and stream URL/profile supported by that camera. Test the connection, then save the camera. Camera-specific RTSP paths and ONVIF features differ; check the camera documentation if the default profile does not work.

Use the tile layout controls to choose the number of visible cameras. Unassigned tiles can be assigned from the tile itself. Recording paths, retention, notifications, and motion/object detection are configured in Settings.

## Web access and security

The optional web server provides browser monitoring. To open it, use **More → Mobile access** in the desktop app and copy or scan the complete access link. Treat this link as a password: it grants access to the web session. The link and browser sessions expire when the server restarts. Headless mode prints the private link to its local console; protect access to that console and its logs.

The embedded server uses HTTP. Use it only on a trusted LAN or through a trusted VPN. For access over an untrusted network, put it behind an HTTPS reverse proxy and preserve the original Host header. Do not expose the plain HTTP server directly to the public internet.

Direct API clients must exchange the access code with `POST /api/session` using JSON and retain the returned session cookie. State-changing requests use JSON POST; GET requests are read-only. Remote camera deletion is not available; delete cameras in the desktop app.

Camera passwords, stream credentials, and notification secrets are stored in local configuration. Protect the PC and its files, and do not commit real configuration or secrets.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `F11` | Toggle fullscreen |
| `Esc` | Exit fullscreen or restore the grid |
| `1`, `2`, `4`, `9` | Select a 1, 2, 4, or 9 tile layout |
| `Ctrl + ,` | Open Settings |
| `Ctrl + S` | Save camera configuration |
| `Ctrl + M` | Toggle global motion detection |
| Double-click a tile | Maximize or restore the selected tile |
| Mouse wheel over video | Zoom; drag to pan while zoomed |
| Right-click a tile | Open available camera actions |

## Run the regression tests

Install the application requirements, then run:

```powershell
python -m unittest discover -s tests -v
```

The automated tests use local HTTP requests, temporary files, and simulated workers; they do not connect to physical cameras. See [the review report](docs/REVIEW-2026-10-24.md) for the changes in the UI, web access, recording/configuration reliability, validation results, and remaining limits.

Physical camera compatibility, two-way audio, PTZ devices, installer behavior, long-running recording, and multi-day resource use require testing on the target hardware. Performance and supported camera counts have not been established for every system.

## License

CCTVPanelView is licensed under the [MIT License](LICENSE).
