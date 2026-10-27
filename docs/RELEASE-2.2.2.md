# CCTVPanelView 2.2.2 — outgoing notification categories

- Adds **Settings → Alerts & Sounds → Send notifications for**, with People, Cars/vehicles, Animals and Motion switches and a **People only** preset. The selection applies to both photos and clips sent to ntfy, Telegram and Discord. An empty selection sends none.
- Separates outgoing categories from **Detection → Create incident alerts** and the incident-feed display filters. Existing local incident choices are preserved. Enable AI person detection and People incidents to generate person events.
- Fixes substring/description-based classification that could treat unrelated alerts as people. Delivery uses structured categories or whole detection-label words; unknown or ambiguous labels are excluded.
- Keeps category choices when disarming/rearming. Pending work checks current delivery settings before starting. Disarming also blocks completed clips from being sent.
- Removes the shared ntfy topic fallback and makes unconfigured delivery default to off. Fixes Telegram's mismatched token setting names and masks the token field.
- Includes a [Frigate security and integration review](FRIGATE-REVIEW-2026-10-27.md). Frigate integration is deferred; no server is installed or connected.

## Validation

86 automated tests pass, including simulated delivery through all three service adapters, photo/video filtering, misleading descriptions, Romanian labels, empty selections, pending delivery changes, saved preferences and rearming. External service calls are mocked: no test notifications or camera images are sent to third parties. The Windows packaged app and installer payload also pass their offline checks.

## Update

Quit CCTVPanelView completely, run **CCTVPanelView-2.2.2-Setup.exe**, and select the existing installation folder. Camera configuration and the 2.2.1 layout persistence fix are preserved. Open Alerts & Sounds, choose **People only**, configure a delivery service and save Settings.
