' ==============================================================================
' CCTVPanelView - Stealth Windowless Launcher (No CMD / No Terminal Window)
' ==============================================================================
Option Explicit

Dim WshShell, FSO, ScriptDir, PythonwPath

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = ScriptDir

PythonwPath = "C:\Users\SKIZZOO\AppData\Local\Programs\Python\Python313\pythonw.exe"
If FSO.FileExists(PythonwPath) Then
    WshShell.Run """" & PythonwPath & """ """ & ScriptDir & "\main.py""", 0, False
Else
    WshShell.Run "pythonw.exe """ & ScriptDir & "\main.py""", 0, False
End If

Set WshShell = Nothing
Set FSO = Nothing
