# Frigate review — 27 October 2026

## Assessment

Frigate is worth considering as an optional, separately deployed NVR and detection server. This is a review of official documentation, release notes and public advisories, not an independent source-code audit or a guarantee of safety. Integration is deferred at the user's request; this CCTVPanelView release installs no Frigate services and sends no camera data to Frigate.

The latest stable release checked was **0.18.2**, published 15 October 2026. Its security fixes include two critical authenticated remote-code-execution vulnerabilities affecting 0.18.0–0.18.1, including one reachable by a viewer account. Both advisories identify 0.18.2 as patched. Use a current patched release and monitor future advisories rather than deploying an older image.

Sources: [0.18.2 release](https://github.com/blakeblackshear/frigate/releases/tag/v0.18.2), [viewer-role vulnerability](https://github.com/blakeblackshear/frigate/security/advisories/GHSA-93xj-hg88-ffg7), [admin-authenticated vulnerability](https://github.com/blakeblackshear/frigate/security/advisories/GHSA-qjjw-3v66-279f), [advisory list](https://github.com/blakeblackshear/frigate/security/advisories).

## Deployment boundaries

Frigate's authenticated UI/API uses port **8971**. Port **5000** is an unauthenticated internal interface that should remain limited to its intended internal network. A future connector should use authenticated HTTPS with certificate verification and only the camera access it needs. Do not disable certificate checks or expose internal services to make integration easier. Keep the server behind a trusted network/VPN or an appropriately secured reverse proxy, change the initial administrator password, and avoid unnecessary privileged container/device access.

Windows is not officially supported. The project notes that WSL/virtual-machine installations can have difficult or unavailable accelerator passthrough. My recommendation for this Windows workstation is to consider a separate Linux/Docker host, then connect through a restricted interface if integration is added. This avoids making the Windows installer responsible for deploying and administering another server.

Sources: [authentication and ports](https://docs.frigate.video/configuration/authentication/), [installation support and container configuration](https://docs.frigate.video/frigate/installation/).

## Notifications and possible future integration

Frigate can restrict review alerts to selected object labels, such as `person`. Its native WebPush notifications currently apply to review alerts and require authenticated HTTPS and browser registration. Push delivery contacts the browser vendor's push infrastructure, so native push is not an entirely offline feature. These notifications are separate from CCTVPanelView's ntfy/Telegram/Discord preferences.

Frigate exposes HTTP APIs and MQTT events. A future optional connector could consume detections and deduplicate them by event ID, map camera IDs explicitly, and apply CCTVPanelView's outgoing category policy. It should start disabled and avoid importing camera credentials or enabling duplicate alerts automatically. The precise API, authentication and event lifecycle need implementation and fixture testing before this becomes a working Settings option.

Sources: [review label selection](https://docs.frigate.video/configuration/review/), [native notifications](https://docs.frigate.video/configuration/notifications/), [MQTT integration](https://docs.frigate.video/integrations/mqtt/).
