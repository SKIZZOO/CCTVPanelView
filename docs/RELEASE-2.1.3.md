# CCTVPanelView 2.1.3 — reliable camera tests and status

- Tests and saves preserve the exact stream URL, including custom credentials, host, port, scheme, query parameters and stream path. The unrelated form IP/port no longer blocks a URL test.
- Loading a camera does not trigger connection-field rewrites. Editing connection fields encodes reserved characters in credentials; password spaces are preserved.
- Decoder startup, connection negotiation and first-frame decoding have separate deadlines. Tests allow a slow keyframe instead of timing out the entire operation after 3.5 seconds.
- Removes aggressive initial decoder flags that can discard useful probe/keyframe data. Each camera retains its isolated decoder and bounded latest-frame buffer.
- Failed video verification is distinguished from an unreachable endpoint. A failed decode alone is not labelled offline.
- Pending tests can be cancelled on dialog close. A result for an old URL or previously selected camera cannot mark changed settings as verified.
- Network status probes use the actual configured stream endpoints, including custom RTSP ports. Fresh video can confirm streaming; stale frames and historical FPS cannot.
- The watchdog allows the decoder's bounded read deadline to expire before requesting recovery.
- Adds explicit read-only native camera diagnostics: `CCTVPanelView.exe --camera-diagnostics --camera-config=PATH --camera-report=PATH`. Reports omit camera URLs and credentials. This mode makes actual camera connections only when explicitly invoked.

## Install

Close the running app, run **CCTVPanelView-2.1.3-Setup.exe**, and choose the existing installation folder. Camera configuration is preserved.

## Validation

All 59 automated tests pass. Coverage includes exact-URL setup/testing/saving, credential encoding, nonstandard ports, independent timeouts, cancellation, stale test results and stale live frames, plus the existing isolation, setup, detection, recording and web security checks. The packaged app and installer are checked with a spawned decoder and local video. Live-camera validation is performed locally; private camera configuration and images are excluded from release files.
