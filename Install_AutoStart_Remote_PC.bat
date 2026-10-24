@echo off
title CCTVPanelView - AutoStart Setup
cd /d "%~dp0"

echo =================================================================
echo   CCTVPanelView - Configure 24/7 Auto-Start on System Boot
echo =================================================================
echo.

set "TARGET_BAT=%~dp0Start_CCTV_Headless_Server.bat"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\CCTVPanelView_Server.lnk"

echo Creating autostart shortcut in:
echo "%SHORTCUT_PATH%"
echo.

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_BAT%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'CCTVPanelView 24/7 Background Surveillance'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [OK] AutoStart shortcut created successfully!
    echo CCTVPanelView 24/7 Server will now automatically start every time this PC boots up.
) else (
    echo [ERROR] Failed to create shortcut.
)

echo.
pause
