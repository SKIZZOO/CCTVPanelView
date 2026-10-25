# CCTVPanelView 2.2.1 — remember camera assignments after restart

Fixes the startup lifecycle that prevented cameras from returning to their saved grid slots. The previous startup timer could fire while the splash screen still hid the main window. It then skipped restoration and left session saving disabled, so later camera assignments were lost on restart.

The workstation now restores its layout and camera assignments exactly once after its first appearance. Restoration runs independently of the optional performance prompt. Camera placement, removal and layout changes then save normally. Opening the window again from the tray does not replay startup restoration or replace current assignments. Explicitly empty slots and assignments in hidden slots are preserved.

## Validation

80 automated tests pass. New lifecycle tests reproduce the old failure by keeping the window hidden past the startup timer, then exercise real tile assignment, closing to the tray, reloading configuration into another window and restoring the saved layout. Camera network startup is disabled in these tests; tile assignment and configuration writes use the real application paths. Both regression tests failed before the fix and pass with it.

## Update

Quit CCTVPanelView completely, then run **CCTVPanelView-2.2.1-Setup.exe** and choose the existing installation folder. Your camera configuration is preserved. If the previous version already lost your arrangement, place the cameras once in the desired slots; this version remembers subsequent changes. All 2.2.0 features remain included. Intercom still requires a compatible advertised ONVIF audio backchannel.
