# CCTVPanelView 2.3.1 — ntfy delivery repair

- Fixes the packaged Windows TLS failure that raised `FileNotFoundError` before an HTTPS request could be sent. The frozen runtime now includes the certificate policy data required by its Python distribution. Also bundles certifi's maintained public CA roots, keeps certificate and hostname verification enabled, and supplements with system roots when available. Explicit custom CA settings remain respected. The same verified TLS context is used for notification delivery, updater HTTPS and RTSPS backchannels.

- Fixes clip delivery failing because `web_url` was undefined.
- Removes optional Google Drive database/lookup work from the ntfy delivery path. Snapshot and video attachments publish directly to the configured ntfy server/topic; no cloud-sync files or hardcoded cloud-folder links are required.
- Falls back to a plain text alert when the server returns HTTP 413 for an attachment. Does not claim the clip was uploaded to a cloud service.
- Sanitizes single-line ASCII headers while preserving UTF-8 notification text. Checks the server's JSON acknowledgement before reporting success. Authentication failures, quotas/rate limits, TLS/network errors and invalid proxy responses are reported without logging the topic URL.
- Adds **Settings → Alerts & Sounds → Send text-only test**. Runs in the background using the currently entered topic. The test sends no camera images, clips, names or addresses. The phone-access dialog also uses the configured server and no longer falls back to a shared public topic.
- Preserves the existing people-only filter, camera configuration, layout, updater and startup improvements.

## Validation

109 automated tests pass. New tests exercise verified TLS when Windows' default certificate loading fails, explicit CA configuration errors, HTTP request construction for text/snapshots/clips, attachment-size rejection, acknowledgement validation, error redaction and background Settings tests. External HTTP delivery is mocked in automated tests. Packaged checks additionally create a verified TLS context with loaded CA roots and exercise photo/video request construction without contacting ntfy.

Live text-only delivery was accepted with HTTP 200 and confirmed received on a phone. No real camera image or video was sent as a diagnostic test. This confirms the tested topic/subscription worked; it does not independently verify every attachment format or self-hosted server.

## Update

Use **Settings → General & layout → Application updates**, or quit the app completely and run **CCTVPanelView-2.3.1-Setup.exe** over the existing installation folder. Then use **Alerts & Sounds → Send text-only test** to check delivery. Save changed notification preferences with Save & Apply.
