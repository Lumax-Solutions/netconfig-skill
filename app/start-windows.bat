@echo off
rem NetConfig Assistant - double-click to start. Keep this window open while you use the app.
cd /d "%~dp0"
title NetConfig Assistant
where py >nul 2>nul && (py -3 netconfig_app.py %* & goto :end)
where python >nul 2>nul && (python netconfig_app.py %* & goto :end)
echo.
echo Python 3 is needed but was not found.
echo Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"),
echo or run:  winget install Python.Python.3.12
echo Then double-click this file again.
:end
pause
