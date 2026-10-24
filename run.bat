@echo off
title CCTVPanelView - Professional AI Surveillance Suite
cd /d "%~dp0"
echo Starting CCTVPanelView...
python "%~dp0main.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application stopped with code %ERRORLEVEL%.
    pause
)
