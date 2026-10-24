# CCTVPanelView 2.1.0

This release improves detection confirmation, session restoration, and Windows installation.

## Detection and settings

- Motion uses a short background warmup and continuous confirmation; rejected lighting shifts reset pending triggers.
- Stationary motion suppression requires elapsed time, so high camera frame rates no longer suppress movement before it can confirm.
- AI movement cannot bypass the selected confirmation delay. Unconfirmed tracks restart after a detection gap.
- Motion confirmation, AI confirmation, motion hold, and alert cooldown have separate controls in Settings → AI & Motion.
- Outdoor, indoor, and fast-crossing presets provide starting values to tune for each scene.
- Arming/disarming preserves notification, detection, and recording preferences.
- Saved numeric detection settings are checked for finite values and sensible limits.

## Layout and recording

- Startup no longer saves newly constructed empty tiles over the previous session.
- Empty tiles stay empty; hidden tile assignments survive shrinking and expanding the grid.
- Window position, size, maximized state, sidebar state, and selected tile are saved.
- Fixes AI auto-recording's nonexistent object-field reference.
- Parked AI objects no longer keep automatic recordings active. Auto recordings finish after quiet activity or a five-minute segment limit.
- The pre-alarm buffer control now controls the actual compressed-frame buffer. Alert queues use a pixel-memory budget.
- Invalid PTZ connection details no longer crash the camera selector.

## Windows installation

Run **CCTVPanelView-2.1.0-Setup.exe**. The installer contains the app, Python runtime, Qt UI, AI model, and FFmpeg tools. Normal use needs no Python installation, batch file, or script launcher.

Desktop/Start Menu shortcuts open the app executable. Windows Installed Apps offers the graphical uninstaller. Updating preserves camera configuration; both installer and uninstaller ask that you close an active app so recording can finish. The uninstaller no longer terminates unrelated Python applications.

## Validation and limits

- 34 regression tests pass, including synthetic motion/AI tracks, exclusion zones, layout restoration, settings persistence, upgrade preservation, HTTP authorization, path restrictions, and byte-range playback.
- Manual and alert recording tests produce MP4 files that OpenCV can reopen and decode. Alert recording includes compressed pre-alarm frames.
- The packaged app's offline self-test checks module loading, model inference, FFmpeg/FFplay/FFprobe, and configuration round-trip.
- The installer has an offline payload check that deploys its bundled executable into a temporary directory and runs the app self-test without registering shortcuts or modifying Windows settings.

Physical camera connections, manufacturer-specific PTZ/two-way audio, notification-provider delivery, real-world detection accuracy, and multi-day recording remain dependent on the target hardware/network and were not verified here. There is no claim that every camera feature or outdoor scene has been tested.

The embedded HTTP viewer should remain on a trusted network or VPN, or use an HTTPS reverse proxy for untrusted networks. Camera and notification secrets remain in local configuration.
