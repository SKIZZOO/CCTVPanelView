@echo off
cd /d "%~dp0"
if exist "C:\Users\SKIZZOO\AppData\Local\Programs\Python\Python313\pythonw.exe" (
    start "" "C:\Users\SKIZZOO\AppData\Local\Programs\Python\Python313\pythonw.exe" "%~dp0main.py"
) else (
    start "" pythonw "%~dp0main.py"
)
exit
