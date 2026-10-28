# CCTVPanelView 2.3.5 — Update prompts and clean settings text

Fixes corrupted punctuation in the update button, settings search, camera labels, connection test status and sound preview labels.

A persistent update banner now appears beneath the top toolbar when a newer stable release is found. A nonblocking prompt offers Update now or Not now once per version per app session. It waits while the app is hidden, minimized, inactive or another modal dialog is open. Not now leaves the banner and Review update button available. Accepting opens the verified download flow; installing and restarting still requires a separate user action and saves the layout through the existing upgrade handoff.

Tests cover repaired UI text, banner position, deferral, declining without downloading/installing, explicit acceptance and suppression for older/current releases. Existing HTTPS, size/SHA256 checks and profile preservation remain in place.
