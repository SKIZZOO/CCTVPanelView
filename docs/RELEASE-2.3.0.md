# CCTVPanelView 2.3.0 — preserved layouts, verified updates and startup responsiveness

- Setup detects the existing registered installation folder, backs up its camera configuration, and preserves grid assignments, custom layouts and preferences. Moving to a new folder migrates the profile and keeps relative recording/snapshot paths pointing at existing media.
- Prevents the first-run wizard from reopening during upgrades. Revisiting setup manually preserves existing stream IDs, stream URLs and additional streams; it no longer invalidates layout assignments by rebuilding every stream.
- Adds **Settings → General & layout → Application updates**. Background checks query the official GitHub repository's latest stable release 30 seconds after startup and every six hours, with an opt-out switch. Downloads and installation remain explicit actions.
- Compares version numbers numerically. Validates the repository, release tag, exact installer asset, HTTPS hosts, size and GitHub SHA-256 digest. Rejects incomplete, oversized and checksum-mismatched downloads and disallows downgrades. Checks the file again before installation.
- **Install and restart** saves and backs up the current layout, safely closes the app and passes the actual installation folder to Setup. Setup waits for the old process to exit. Finish Setup to restart; no BAT/VBS launcher is involved. Installers remain unsigned; hashes are not an independent signing identity.
- Keeps the app runtime installed in `_internal/`, avoiding full runtime extraction at every app launch. Setup is still a single EXE. Replaces the animated intro and forced delay with a lightweight loading screen shown before workstation imports.
- Moves startup orphan cleanup, storage quota enforcement and automatic retention deletion to a background worker after one minute. Confirmation prompts remain on the UI thread; retention settings and snooze are respected.

## Validation

99 automated tests pass, covering real installer deployment to an isolated fixture, preserved configuration backups and custom assignments, wizard stream identities, profile relocation, version comparisons, unsafe release/redirect rejection, bounded download and SHA-256 failures, background checks/maintenance, updater handoff arguments and saved layout before launch. Network delivery and actual installer execution are mocked in updater tests. Windows packaged app and installer-payload checks additionally exercise imports, decoding, AI inference, audio and profile preservation without opening user cameras or altering the live installation.

## Install

Quit the old app completely and run **CCTVPanelView-2.3.0-Setup.exe**. Confirm the detected existing folder, such as your current CCTVPanelView installation. Subsequent releases can be checked and downloaded from inside the app. Existing camera data is preserved; configurations or arrangements already lost in older versions cannot be reconstructed automatically.
