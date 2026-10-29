# CCTVPanelView 2.3.6 — Readable phone attachments

Phone preview videos and snapshot attachments now show the event, camera name and original event date/time, for example:

`Person_Front-Gate_2026-10-29_09-04-48_Preview.mp4`

Snapshot names use the same format with `Snapshot.jpg`. Names are bounded and sanitized for Windows, HTTP headers and phone downloads. Original recordings and existing files are unchanged.

ntfy titles now read “Person video | Front Gate” or “Person detected | Front Gate”. Confidence and event time sit in the message, with one icon and shorter playback instructions. The native MP4 attachment remains playable using download, then tap again. ntfy/iOS may still prepend their own download identifier in Quick Look; CCTVPanelView cannot control that client behavior or rename previously delivered notifications.

Tests verify event timestamps, snapshot/video names, safe handling of long or malformed names, concise titles and preservation of native attachment delivery. No camera media was sent during validation.
