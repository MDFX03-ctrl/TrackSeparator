@echo off
cd /d "%~dp0"
if exist "dist\TrackSeparator\TrackSeparator.exe" (
  start "" "dist\TrackSeparator\TrackSeparator.exe" app
  exit /b 0
)
if exist ".runtime\python\pythonw.exe" (
  start "" ".runtime\python\pythonw.exe" -m trackseparator app
  exit /b 0
)
start "" pythonw -m trackseparator app
