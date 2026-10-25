# CCTVPanelView 2.2.0 — workstation reliability and settings

- Preserves every supported layout in Settings instead of falling back to an unrelated selection. Custom-layout templates are updated with the latest tile assignments; explicit empty saved slots remain empty. Failed saves are shown in the status bar.
- Adds persistent Motion, Person, Animal and Car/Vehicle display filters for existing and new incident cards and desktop toasts. Display filters leave recording and notification preferences intact.
- Fixes mismatched sound-profile identifiers and volume units. Actual PCM amplitude scales from 0–100%; 0 stops playback. Alarm previews and live alarms share the same setting. Custom PCM WAV files are supported, with preview feedback and mute controls.
- Samples top-bar telemetry in the background. Process-time deltas include decoder/helper children without losing their counters on each refresh. Shows decimal CPU usage and a sample timestamp in the tooltip.
- Defers AI model loading to the inference worker, indexes alert media in the background and fills alert cards in small batches. Removes forced working-set trims from the UI timer. Status-message timers stop with their owning widget.
- Rebuilds intercom negotiation around the advertised ONVIF speaker track and G.711 PCMA/PCMU codec. Uses PLAY with the backchannel Require header, negotiated TCP channels, Basic/MD5 Digest authentication and session keepalives.
- Intercom capture stays on the Qt thread; network writes use a bounded background queue. Supported native microphone formats are converted to mono 8 kHz with filtering. Device selection and microphone gain persist. Stops during connection, device/camera changes and panel closure prevent a late microphone start.
- Groups Settings into six sections with search. Sound controls sit with alerts, stabilization with detection, and image controls with cameras. Legacy performance and volume values migrate.

## Hardware limits

Intercom requires an advertised ONVIF audio backchannel with mono 8 kHz PCMA or PCMU. A vendor-only speaker interface cannot be driven by this implementation. Real-camera capability checks request metadata only; they do not capture microphone audio or broadcast sound.

## Validation

78 automated tests pass, including layout persistence, custom assignments, supported layout selections, category filters, PCM volume scaling, child-process CPU accounting, lazy model loading, microphone conversion, G.711 samples, stale/cancelled sessions, and a local RTSP server with fragmented responses and authentication. Native app/installer checks cover decoding, audio scaling and backchannel track/codec helpers. These checks do not establish universal camera/speaker compatibility or confirm a particular physical speaker's output.

## Install

Close CCTVPanelView, run **CCTVPanelView-2.2.0-Setup.exe**, and select the current installation folder. Camera configuration is preserved. Use Test Audio under Alerts & Sounds to check the Windows playback device. Use the incident-feed checkboxes to choose visible categories.
