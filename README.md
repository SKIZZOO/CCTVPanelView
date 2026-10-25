# CCTVPanelView

<div align="center">

<img src="assets/cctvpanelview_logo.png" width="96" alt="CCTVPanelView logo">

### CCTV monitoring and recording for Windows

A desktop viewer for RTSP/ONVIF IP cameras, with motion alerts, optional on-device object detection, local recording, and a browser interface for phones and tablets.

[**Download for Windows**](https://github.com/SKIZZOO/CCTVPanelView/releases/latest) · [Features](#what-you-can-do) · [Quick start](#install-the-windows-release) · [Security](#security-and-privacy) · [2.1.2 independent camera recovery](docs/RELEASE-2.1.2.md)

![Windows 10 and 11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![MIT License](https://img.shields.io/badge/License-MIT-green)

</div>

---

<img src="docs/screenshots/workstation.png" width="1100" alt="CCTVPanelView desktop with responsive header and camera grid">

## What you can do

| Live monitoring | Recording and alerts | Browser access |
| --- | --- | --- |
| View cameras in 1, 2, 4, or 9 tile layouts. Maximize a tile, zoom, and use supported camera controls. | Record video, save snapshots, set storage and retention options, and configure motion or object alerts. | Open the optional web viewer on a phone, tablet, or another browser. View supported camera feeds, alerts, and PTZ actions. |

CCTVPanelView is designed for trusted home and small-site networks. Camera compatibility and performance depend on the camera model, stream format, PC, and network. It has not been benchmarked for a fixed camera count.

## Screenshots

### Desktop setup and camera management

<table>
<tr>
<td width="50%"><img src="docs/screenshots/first_time_setup_prompt.png" alt="First launch setup choices"><br><sub>Choose initial setup tasks at first launch.</sub></td>
<td width="50%"><img src="docs/screenshots/wizard_add_camera.png" alt="Add camera wizard"><br><sub>Add a camera and enter its connection details.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/screenshots/camera_quick_assign.png" alt="Camera quick assignment"><br><sub>Assign a configured camera to a video tile.</sub></td>
<td width="50%"><img src="docs/screenshots/installer_welcome.png" alt="Windows installer welcome"><br><sub>Install the packaged Windows application.</sub></td>
</tr>
</table>

### Settings

Use Settings to adjust appearance, recording and storage, motion/object detection, and notification options.

<table>
<tr>
<td width="50%"><img src="docs/screenshots/settings_general.png" alt="General appearance settings"><br><sub>Appearance and window behavior.</sub></td>
<td width="50%"><img src="docs/screenshots/settings_storage.png" alt="Storage settings"><br><sub>Recording location and retention settings.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/screenshots/settings_ai_motion.png" alt="AI and motion settings"><br><sub>Motion and local object-detection options.</sub></td>
<td width="50%"><img src="docs/screenshots/settings_notifications.png" alt="Notification settings"><br><sub>Configure supported notification channels.</sub></td>
</tr>
</table>

## Independent camera recovery

Each stream connects and decodes in its own process. An offline camera, stalled read, or connection test can time out and restart without holding another camera's native decoder. A single latest-frame buffer per stream prevents delayed playback from accumulating. Repeated failures back off automatically; network status checks report each camera independently.

Process isolation uses additional memory per active stream. Cameras still share the PC's CPU, storage, and network capacity, so use substreams or a lower display frame rate for large camera grids.

## Install the Windows release

1. Open [the latest release](https://github.com/SKIZZOO/CCTVPanelView/releases/latest).
2. Download **CCTVPanelView-2.1.2-Setup.exe** and run it.
3. Choose an installation folder and shortcuts, then launch the app from the Desktop or Start Menu.

The installer bundles Python, Qt, AI models, and FFmpeg/FFplay/FFprobe. Normal use needs no Python setup or batch files. Updates preserve existing camera configuration. Close the running app before an update so recordings can finish. A graphical uninstaller is available through Windows Installed Apps.

## Run from source

**Requirements:** Windows 10 or 11 (64-bit), Python 3.11+, and Git.

```powershell
git clone https://github.com/SKIZZOO/CCTVPanelView.git
cd CCTVPanelView
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If environment activation is blocked, invoke `.venv\Scripts\python.exe` directly. Use `cameras_config.example.json` as a reference; keep real camera passwords and notification secrets private.

## Add a camera

At first launch, open the setup flow or choose **Add Camera**. Enter the camera’s address, RTSP/ONVIF ports, credentials, and stream profile or URL. Test the connection and save it. Camera stream paths and ONVIF features vary across manufacturers, so consult your camera’s documentation if the provided profile does not work.

Select a 1, 2, 4, or 9 tile layout, then assign configured cameras to tiles. Recording, storage, motion detection, AI options, and notifications are managed from Settings.

## Use the mobile web viewer

In the desktop app, select **More → Mobile access**, then copy or scan the complete access link. Open it on a phone or tablet on the same trusted network. The link grants access to the web session, so treat it like a password. It and its browser sessions expire when the server restarts.

The web server uses HTTP. Keep it on a trusted LAN or use a trusted VPN. For access over an untrusted network, place it behind an HTTPS reverse proxy and preserve the original Host header. Do not expose the plain HTTP server directly to the public internet. Headless mode prints its private link to its local console; protect the console and logs.

## Settings at a glance

- **Appearance:** window and display behavior.
- **Storage:** recording location and retention.
- **Motion and AI:** motion sensitivity and optional local YOLOv5 ONNX detection.
- **Notifications:** configure available phone and desktop notification options.

Availability can depend on the camera, notification provider, and settings in use.

### Tune detection for the scene

<img src="docs/screenshots/settings_triggers.png" width="1050" alt="Detection settings with confirmation delays, cooldown, hold and scene presets">

Start with an **Outdoor**, **Indoor**, or **Fast crossing** preset, then observe real activity and adjust:

| Setting | What it controls |
| --- | --- |
| Minimum object size | Rejects small motion contours, measured in source-frame pixels. Recalibrate if stream resolution changes. |
| Minimum AI confidence | Rejects uncertain classifications. Higher values can reduce false positives and miss more objects. |
| Motion confirmation | How long solid movement must continue before motion confirms. |
| AI confirmation | How long an object must persist across at least two detections. |
| Motion hold | Keeps motion active briefly after movement stops. |
| Alert cooldown | Minimum spacing between consecutive alerts from a stream. |

The background model warms up before motion alerts become active. Lighting shifts reset pending motion. Arming/disarming preserves your choices. Layout, empty tiles, hidden assignments, window size/position, and sidebar state are saved when you exit and restored at startup.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `F11` | Toggle fullscreen |
| `Esc` | Exit fullscreen or restore the grid |
| `1`, `2`, `4`, `9` | Choose a tile layout |
| `Ctrl + ,` | Open Settings |
| `Ctrl + S` | Save camera configuration |
| `Ctrl + M` | Toggle global motion detection |
| Double-click a tile | Maximize or restore it |
| Mouse wheel over video | Zoom; drag to pan while zoomed |
| Right-click a tile | Open available camera actions |

## Security and privacy

The web viewer requires a per-launch access link and session cookie. The access link is a shared capability: anyone who has it can access the web session until the server restarts. Keep camera and notification secrets out of source control and protect the local configuration files.

Direct API clients exchange the access code using `POST /api/session` with JSON and retain the returned session cookie. State-changing requests use JSON POST. Remote camera deletion is not supported; manage cameras in the desktop app.

See [the UI, reliability, scaling, and security review](docs/REVIEW-2026-10-24.md) for the implemented changes, test results, and known limitations. Automated tests use local fixtures and simulated workers; they do not test physical cameras, installers, or long-duration recording.

## Run the tests

```powershell
python -m unittest discover -s tests -v
```

## Build a Windows installer

Install `requirements.txt` and `requirements-build.txt` in a Windows virtual environment. Obtain a Windows FFmpeg build containing `ffmpeg.exe`, `ffplay.exe`, and `ffprobe.exe`, then run:

```powershell
python tools/build_windows.py --ffmpeg-dir C:\path\to\ffmpeg\bin
```

The build produces the app, uninstaller, and setup executable in `dist/` and runs an offline packaged-app check. See [release validation](docs/RELEASE-2.1.0.md) and [third-party notices](docs/THIRD_PARTY_NOTICES.md).

## License

[MIT](LICENSE)
