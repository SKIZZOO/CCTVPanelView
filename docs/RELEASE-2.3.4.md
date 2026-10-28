# CCTVPanelView 2.3.4 — Animated startup and Windows taskbar icons

Restores the animated camera intro in an independent lightweight Qt process. It continues animating while the main process imports modules and builds the workstation, then fades out once the window is ready. There is no fixed minimum startup delay. It hides during the setup wizard, supports skip, and stops if the parent exits.

Fixes onedir installer shortcuts that still pointed at missing root assets. New shortcuts use the embedded executable icon and matching Windows AppUserModelID. Existing legacy icon files are restored during upgrades for older pinned shortcuts. Native Windows COM shortcut creation replaces temporary VBS/PowerShell scripts.

Validation covers animation ticks while the parent is blocked, high-DPI icon frames, native shortcut icon/identity properties, legacy icon restoration, Windows native window icon handles, and packaged application/installer checks. Camera profiles and layouts remain preserved.
