@echo off
title CCTVPanelView 24/7 Headless Server
cd /d "%~dp0"
echo =================================================================
echo   CCTVPanelView - 24/7 Surveillance NVR Server
echo =================================================================
echo Starting background camera feeds, motion detection, and Google Drive recording...

if exist "C:\Users\SKIZZOO\AppData\Local\Programs\Python\Python313\python.exe" (
    "C:\Users\SKIZZOO\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0cctv_server.py"
) else (
    python "%~dp0cctv_server.py"
)

pause
