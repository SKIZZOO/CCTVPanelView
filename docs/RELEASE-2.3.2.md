# CCTVPanelView 2.3.2 — Playable ntfy video alerts

- Converts a temporary copy of recorded incidents into phone-compatible H.264/AAC MP4 previews under 1.8 MB, including larger original recordings.
- Adds an **Open video** action and clickable attachment link after ntfy confirms the uploaded file. Uses only the configured server attachment URL.
- Caps previews at 60 seconds, 640×360 and 12 fps; preserves original recordings. Encoding runs off the UI/capture threads, one preview at a time, with timeouts.
- Reports upload/preparation failures rather than silently skipping files over 15 MB.
- Preserves outgoing categories and the existing clip preference. Enable Send Video Clip to Phone if previously disabled.
- ntfy attachments expire according to the server policy (normally 3 hours). The quiet upload entry appears before the playable notification.

Validation includes automated transport/URL/filter tests, real FFmpeg preview encoding, and packaged application/installer checks. Actual phone playback still depends on the ntfy client/browser and server quotas.
