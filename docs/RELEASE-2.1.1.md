# CCTVPanelView 2.1.1 — camera setup hotfix

This update fixes camera details being saved without the camera appearing in a video tile.

- Completing setup now releases the setup guard before assigning the configured stream to its requested tile.
- Startup restoration allows already-configured streams to create real camera workers. It still avoids opening setup dialogs for incomplete cameras during startup.
- Cameras with anonymous RTSP streams can be configured without a password, matching the setup form's documented behavior.
- The add-camera dialog explicitly marks completed configuration, and generates unique camera/stream IDs even when cameras share an address.
- Failed configuration writes roll back the new camera and show an error instead of reporting success.
- Fixes a missing `time` import in video tile motion/AI callbacks.

## Install

Close the running app, run **CCTVPanelView-2.1.1-Setup.exe**, and select the same installation folder. Existing camera configuration is preserved. Reopen the app and save the camera's setup again if it was incomplete.

## Validation

40 tests pass. Six new tests exercise the actual Qt camera dialog and Save button, persistence and assignment to real worker objects, anonymous-camera setup, startup restoration, setup completion followed by tile assignment, disk-write failure feedback, and camera ID uniqueness. Workers are prevented from making camera connections during these tests.

The app and installer also undergo offline packaged checks for module loading, AI model inference, bundled media tools, configuration round-trip, and installer payload deployment. Physical camera connection success remains dependent on the camera's address, stream path, credentials, and network.

See [2.1.0 release notes](RELEASE-2.1.0.md) for the preceding detection, recording, layout, and installer improvements.
