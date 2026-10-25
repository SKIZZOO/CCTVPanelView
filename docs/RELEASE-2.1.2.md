# CCTVPanelView 2.1.2 — independent camera recovery

- Each stream owns an isolated native decoder process. A blocked connection or read can be terminated without holding another stream's OpenCV backend.
- Camera connection tests use the same isolation, so testing an unreachable camera does not share the live feeds' decoder context.
- Open and read deadlines bound failed attempts. Reconnects back off until a connection has remained healthy for five seconds.
- A bounded latest-frame shared-memory buffer replaces stale frame draining, with no growing frame queue.
- Closing a tile or deleting a camera stops its worker asynchronously so the GUI can keep painting the other feeds.
- Network probes run concurrently, publish individual results immediately, and cannot accumulate duplicate probes for a camera.
- Video downloads release the Windows file handle before sending their final data, fixing a download/delete race uncovered during validation.

## Install

Close the running app, run **CCTVPanelView-2.1.2-Setup.exe**, and choose your existing installation folder. Camera configuration is preserved.

## Validation

All 47 tests pass. Regression tests cover an unresponsive native decoder alongside a healthy frame producer, cancellation and forced cleanup, a real live HTTP MJPEG feed alongside an unresponsive endpoint, actual OpenCV decoding in a spawned process, and independent network probes. The packaged self-test also decodes a temporary local video in a child process. No physical camera credentials are used in these checks.

Process isolation adds memory overhead per stream. It isolates decoder hangs; CPU, disk, and network bandwidth remain shared PC resources.
